*********************************************************************************
*PROGRAM NAME: 		longbase-reformat
*DESCRIPTION: 		Reformats the FRB/US LONGBASE data file to make pre-2018 revision ("v0")
*			  		files forward-compatible with current version of FRBUS ("v1").
*LAST MODIFIED:		October 24, 2023
*LAST MODIFIED BY:	Harris Eppsteiner (harris.eppsteiner@yale.edu
*********************************************************************************

clear all
set more off
set trace off
pause on

*********************************************************************************
*1. Program inputs
*********************************************************************************
*FRBUS data directory
local FRBUS_data_dir "/gpfs/gibbs/project/sarin/shared/model_data/FRBUS/"

*Directory for figures:
local fig_dir "/gpfs/gibbs/project/sarin/hre2/FRBUS_figs/"

*Directory for output
local output_dir "/gpfs/gibbs/project/sarin/hre2/"

*Vintage of current ("v1") LONGBASE file:
local current_vintage "20230927"

*Vintages of previous ("v0") files to be reformatted:
local reformat_vintages "20171220 20180614"

*Last historical quarter (for use in imputations)
local last_hist_qtr "2017q3"

*Base year for v0 real variables (for use in imputations)
local base_yr_v0 "2009"

*List of fiscal policy variables
local policy_vars "GTN TRCI TRP TRFCIM TRFPM"

*Toggle for producing comparison graphs of reformatted variables vs. current
local make_comp_grph 0

*Toggle for producing CSV file of policy shocks
local make_policy_shocks 1


*********************************************************************************
*2. Load current vintage
*********************************************************************************
cd "`FRBUS_data_dir'/v1/`current_vintage'"

insheet using LONGBASE.TXT, clear
rename * *_current
rename obs_current obs

tempfile longbase_`current_vintage'
save `longbase_`current_vintage''

foreach vintage in `reformat_vintages' {
*********************************************************************************
*2. Load vintage(s) to be reformatted and merge with current file
*********************************************************************************
	cd "`FRBUS_data_dir'/v0/`vintage'"
	
	import excel using `vintage'.xlsx, firstrow clear
	rename * *_v0
	rename *, lower
	rename obs_v0 obs
	
	merge 1:1 obs using `longbase_`current_vintage'', assert(using matched) keep(matched) nogen

	*Reformat date for time-series operations below
	gen date = quarterly(obs, "YQ")
	format date %tq
	order date, first
	drop obs
	tsset date

	*Change "NA" variables to missing and destring
	ds, has(type string)
	foreach var of varlist `r(varlist)' {
		replace `var'="." if `var' == "NA"
	}
	destring _all, replace

*********************************************************************************
*3. Reformat variables in v0 data to be compatible with FRBUS v1
*********************************************************************************
	*STEP 1: 	Loop through the variables in the current file, and set the v1 
	*			versions of the vintage to be reformatted equal to their v0
	*			values wherever possible
	foreach var of varlist *_current {
		local varstem: subinstr local var "_current" "", all
		noi di "`varstem'"
		capture confirm variable `varstem'_v0
		if !_rc gen `varstem'_v0reformat = `varstem'_v0
		else gen `varstem'_v0reformat = .	
	}
	rename *_current *

	*STEP 2: 	Variable imputations
	** ADJLEGRT **
	replace adjlegrt_v0reformat = adjlegrt

	** ANNGR **
	replace anngr_v0reformat = anngr

	** EBFI **
	replace ebfi_v0reformat = epd_v0 + epi_v0 + eps_v0

	** EBFIN **
	replace ebfin_v0reformat = epdn_v0 + epin_v0 + epsn_v0

	** EGFEN **
	replace egfen_v0reformat = egfen if date<=tq(`last_hist_qtr') //Setting historical values 
	replace egfen_v0reformat = L.egfen_v0reformat*(egfn_v0/L.egfn_v0) if date>tq(`last_hist_qtr') //using growth of dec-17 file 

	** EGFE **
	gen implic_egfe = egfen/egfe //back out implicit index 
	gen indexfed_`base_yr_v0'_temp = implic_egfe if inrange(date,tq(`base_yr_v0'q1),tq(`base_yr_v0'q4)) //rebase so base year=1
	egen indexfed_`base_yr_v0' = mean(indexfed_`base_yr_v0'_temp)
	gen egfe`base_yr_v0' = (implic_egfe/indexfed_`base_yr_v0')^(-1)*egfen //real variable in base-year$
	replace egfe_v0reformat = egfe`base_yr_v0' if date<=tq(`last_hist_qtr') //Setting historical values 
	replace egfe_v0reformat = L.egfe_v0reformat*(egf_v0/L.egf_v0) if date>tq(`last_hist_qtr') //using growth of dec-17 file 
	drop implic_egfe indexfed_`base_yr_v0'_temp indexfed_`base_yr_v0' egfe`base_yr_v0'

	** EGFET **
	gen egft_ratio = (egfit_v0 + egflt_v0 + egfot_v0)/ /// trend to actual ratio
						(egfi_v0 + egfl_v0 + egfo_v0)		
	replace egfet_v0reformat = egft_ratio*egfe_v0reformat
	drop egft_ratio

	** EGSEN **
	replace egsen_v0reformat = egsen if date<=tq(`last_hist_qtr') //Setting historical values 
	replace egsen_v0reformat = L.egsen_v0reformat*(egsn_v0/L.egsn_v0) if date>tq(`last_hist_qtr') //using growth of dec-17 file 
		
	** EGSE **
	gen implic_egse = egsen/egse //back out implicit index 
	gen indexs_`base_yr_v0'_temp = implic_egse if inrange(date,tq(`base_yr_v0'q1),tq(`base_yr_v0'q4)) //rebase so base year=1
	egen indexs_`base_yr_v0' = mean(indexs_`base_yr_v0'_temp)
	gen egse`base_yr_v0' = (implic_egse/indexs_`base_yr_v0')^(-1)*egsen //real variable in base-year $
	replace egse_v0reformat = egse`base_yr_v0' if date<=tq(`last_hist_qtr') //Setting historical values 
	replace egse_v0reformat = L.egse_v0reformat*(egs_v0/L.egs_v0) if date>tq(`last_hist_qtr') //using growth of dec-17 file 
	drop implic_egse indexs_`base_yr_v0'_temp indexs_`base_yr_v0' egse`base_yr_v0'

	** EGSET **
	gen egst_ratio = (egsit_v0 + egslt_v0 + egsot_v0)/ /// trend to actual ratio
						(egsi_v0 + egsl_v0 + egso_v0)		
	replace egset_v0reformat = egst_ratio*egse_v0reformat
	drop egst_ratio
				
	** EMPTRT **
	replace emptrt_v0reformat = emptrt

	** GTRD **
	replace gtrd_v0reformat = gftrd_v0 + gstrd_v0

	** GTRT **
	replace gtrt_v0reformat = gftrt_v0 + gstrt_v0

	** GTR - using regression  **
	replace gtr_v0reformat = (gtrd_v0reformat+gtrt_v0reformat)*xgdpt_v0reformat

	** GTN - using regression  **
	replace gtn_v0reformat = 0.01*pgdp_v0reformat*gtr_v0reformat

	** GFEXPN **
	replace gfexpn_v0reformat = egfln_v0reformat + 0.64*egfen_v0reformat + gtn_v0reformat + gfintn_v0reformat

	** HGPBFIR **
	replace hgpbfir_v0reformat = hgpbfir

	** HXBTR **
	replace hxbtr_v0reformat = 0 

	** JRBFI **
	replace jrbfi_v0reformat = jrbfi if date<=tq(`last_hist_qtr')
	gen last_jrbfi_temp = jrbfi if date==tq(`last_hist_qtr')
	egen last_jrbfi = max(last_jrbfi_temp)
	replace jrbfi_v0reformat = last_jrbfi if date>tq(`last_hist_qtr')
	drop last_jrbfi_temp last_jrbfi

	** KBFI **
	replace kbfi_v0reformat = kpd_v0 + kpi_v0 + kps_v0

	** UGFDBTP **
	replace ugfdbtp_v0reformat = ugfdbtp if date<=tq(`last_hist_qtr')
	gen last_ugfdbtp_temp = ugfdbtp if date==tq(`last_hist_qtr')
	egen last_ugfdbtp = max(last_ugfdbtp_temp)
	replace ugfdbtp_v0reformat = last_ugfdbtp if date>tq(`last_hist_qtr')
	drop last_ugfdbtp_temp last_ugfdbtp_temp

	* UGFDBTP: TESTING THINGS *
	replace ugfdbtp_v0reformat = 1 if date>tq(`last_hist_qtr')

	** GFDBTNP **
	replace gfdbtnp_v0reformat = gfdbtnp if date<=tq(`last_hist_qtr')
	replace gfdbtnp_v0reformat = ugfdbtp_v0reformat*(L.gfdbtnp_v0reformat - 0.25*gfsrpn_v0reformat) if date>tq(`last_hist_qtr')

	** LEG **
	replace leg_v0reformat = leh_v0reformat - lep_v0reformat - leo_v0reformat

	** PBFIR **
	replace pbfir_v0reformat = pbfir 

	** PEGFR **
	replace pegfr_v0reformat = egfen_v0reformat / (pxp_v0reformat * egfe_v0reformat * 0.01)

	** PEGSR **
	replace pegsr_v0reformat = egsen_v0reformat / (pxp_v0reformat * egse_v0reformat * 0.01)

	** PKBFIR **
	replace pkbfir_v0reformat = pkbfir

	** QEBFI **
	replace qebfi_v0reformat = qebfi

	** QPXB **
	replace qpxb_v0reformat = pwstar_v0reformat + (pl_v0reformat / lprdt_v0reformat)

	** RBFI **
	replace rbfi_v0reformat = rpd_v0

	** RRFF **
	replace rrff_v0reformat = rrffe_v0

	** RTBFI **
	replace rtbfi_v0reformat = rtbfi

	** TCIN **
	replace tcin_v0reformat = tfcin_v0 + tscin_v0

	** TDPV **
	replace tdpv_v0reformat = tdpv

	** TPN **
	replace tpn_v0reformat = tfpn_v0 + tspn_v0

	** TRCI **
	replace trci_v0reformat = trfci_v0 /*+ trsci_v0*/

	** TRCIT **
	* Set initial value
	replace trcit_v0reformat = trcit if date<=tq(`last_hist_qtr')
	replace trcit_v0reformat = trci_v0reformat - 0.0070663*xgap2_v0reformat - 0.81025*(L.trci_v0reformat-L.trcit_v0reformat - 0.0070663*L.xgap2_v0reformat) if date>tq(`last_hist_qtr')	
	
	** TRITC **
	replace tritc_v0reformat = tritc

	** TRP **
	replace trp_v0reformat = trfp_v0 + trsp_v0

	** TRPT **
	replace trpt_v0reformat = trfpt_v0 + trspt_v0

	** TRPTX **
	replace trptx_v0reformat = trfptx_v0 + trsptx_v0

	** UGFSRP **
	replace ugfsrp_v0reformat = ugfsrp

	** ULEG **
	replace uleg_v0reformat = uleg

	** UPKBFIR **
	replace upkbfir_v0reformat = upkbfir

	** UVBFI **
	replace uvbfi_v0reformat = uvbfi

	** UYHIBN **
	replace uyhibn_v0reformat = yhibn_v0reformat / xgdpn_v0reformat

	** UYNICPNR **
	replace uynicpnr_v0reformat = uynicpnr

	** UPGFL **
	replace upgfl_v0reformat = upgfl

	** UPGSL **
	replace upgsl_v0reformat = upgsl

	** UPMP **
	replace upmp_v0reformat = upmp

	** VBFI **
	replace vbfi_v0reformat = uvbfi_v0reformat * (pkbfir_v0reformat / pbfir_v0reformat) / rtbfi_v0reformat

	** XBTR **
	replace xbtr_v0reformat = xbtr

	** YKBFIN **
	replace ykbfin_v0reformat = 0.01 * rtbfi_v0reformat * pxb_v0reformat * (kbfi_v0reformat + L.kbfi_v0reformat) / 2

	** YNIRN **
	replace ynirn_v0reformat = yniin_v0 + ynisen_v0

	** ZEBFI **
	replace zebfi_v0reformat = zebfi

	** GFRECN **
	replace gfrecn_v0reformat = tpn_v0reformat  + tcin_v0reformat + ugfsrp_v0reformat*xgdpn_v0reformat
	
	*These are vars where current value is 0 and dec17 value is -10000
	replace lurtrsh_v0reformat = lurtrsh
	replace pitrsh_v0reformat = pitrsh
	replace rffmin_v0reformat = rffmin
	
	** OBS **
	gen obs_v0reformat = upper(string(date, "%tq"))
	
*********************************************************************************
*4. Produce figures for quality control checks
*********************************************************************************
	if `make_comp_grph' == 1 {
		set graphics off
		putpdf begin

		foreach var of varlist adjlegrt-zynid {
			twoway (line `var' `var'_v0reformat date, lwidth(medthick...))  ///
						if inrange(date, tq(1980q1), tq(2050q1)), ///
						ytitle("Values") title("`var'") name("`var'_`vintage'") /// 
						legend(pos(6) col(2) label(1 "Current Vintage") label(2 "Vintage `vintage' (Reformatted)"))
			graph export "`fig_dir'/charts_`vintage'/chart_`var'.png", as(png) replace //saving  graph
			putpdf paragraph, halign(center) 
			putpdf image "`fig_dir'/charts_`vintage'/chart_`var'.png"		   
		 }
		 
		putpdf save "`fig_dir'/comparison_current_`vintage'.pdf", replace
		set graphics on 
	}

*********************************************************************************
*5. Export TXT file for FRBUS v1
*********************************************************************************
	*Generate list of variables to keep
	local keeplist ""
	foreach var of varlist adjlegrt-zynid {
		local keeplist "`keeplist' `var'_v0reformat"
	}
	keep obs_v0reformat `keeplist'
	rename *_v0reformat *
	rename *, upper
	
	*Temporarily rename and save for generating policy shock file
	rename * *_`vintage'
	rename OBS_`vintage' OBS
	tempfile `vintage'_reformatted
	save ``vintage'_reformatted'
	rename *_`vintage' *
	
	*Reformat to match LONGBASE.TXT format
	foreach var of varlist ADJLEGRT-ZYNID {
		tostring `var', replace format("%13.10f") force
		replace `var' = "NA" if `var'=="."              
		replace `var' = "NA" if `var'=="."              
	}
	order OBS ADJLEGRT-ZYNID
	
	*Export final comma-delimited file:
	export delimited using "`FRBUS_data_dir'/v1/`vintage'/LONGBASE.TXT", replace
	
}

*********************************************************************************
*6. Export CSV file of policy shocks
*********************************************************************************
if `make_policy_shocks' == 1 {
	 
	use `20171220_reformatted', clear
	merge 1:1 OBS using `20180614_reformatted', assert(using matched) nogen keep(matched)
	
	foreach var in `policy_vars' {
		gen d_`var' = `var'_20180614 - `var'_20171220
	}
	
	keep OBS d_*
	export delimited using "`output_dir'/001_POLICY_SHOCKS.TXT", replace
	
}
	
	
