/********************************************************************************
****************** Program create dec-17 longbase file ******************
********************************************************************************/

/* NAMING CONVENTIONS FOR VARIABLES BELOW 

*_dec17 : came from the raw dec-17 longbase line 

* (no underscore) : came directly from the raw current longbase files

*_dec17final : variables that we are using the pre-tcja version of the longbase file 
(i.e. our imputed values and stuff) --- you will see a whole section that I started with 
filling in my variables


* Last historical value: 2017Q3 *
*/



clear all 

* Change this path to point to folder -- shouldn't need to change anything else * 

cd "/Users/sarahrobinson/Library/CloudStorage/OneDrive-SharedLibraries-YaleUniversity/Budget Lab - Old FRBUS files/create_pretcja/"

/********************************************************************************
*********** Merging current & dec-17 longbase files ************************
Saving values from dec-17 as *_dec17. Current values have no underscore
********************************************************************************/

*** Loading December 2017 File ***
import excel Dec_2017/dec_2017.xlsx, sheet("Sheet1") firstrow


rename * *_dec17

rename _date_ obs 

gen month=month(obs)
gen year=year(obs)

gen date = qofd(dofm(ym(year, month)))
format date %tq

drop obs

save "TEMP/dec_2017.dta", replace 


*** Loading Current Longbase File ***
clear 

import excel "Current/Current LONGBASE.xlsx",  sheet("LONGBASE") firstrow

save "TEMP/current.dta", replace 

rename *, lower

gen date = quarterly(obs, "YQ")
format date %tq
drop obs

*** Merge two files ***
merge 1:1 date using "TEMP/dec_2017.dta"
drop _merge

order date

ds , has(type string)

foreach var of varlist `r(varlist)' {
    quietly replace `var'="." if `var' == "NA"
}

quietly destring, replace

tsset date

save "TEMP/combined.dta", replace  // Save combined file



/********************************************************************************
*********** Creating the longbase file to use in pre-TCJA baseline *************
1) Start with setting current vairables equal to dec-17 values where possible 
2) Variable imputations where dec-17 versions don't exist
********************************************************************************/

********************************************************************************
**** Step 1) Setting current variables equal to dec-17 values were possible ****************

/*
 Looping through the variables in the current file - note that all the variables 
 in the current file are adjlegrt-zynid, so we will use that in loops below 
*/

foreach x of varlist adjlegrt-zynid { 
		
	capture confirm variable `x'_dec17
			if !_rc {  
						
						gen `x'_dec17final = `x'_dec17
				
               }
               else { 
						gen `x'_dec17final = .
               }
		
} 

********************************************************************************
******************** Step 2) Variable imputations ******************************


** ADJLEGRT **

replace adjlegrt_dec17final = adjlegrt

** ANNGR **

replace anngr_dec17final = anngr

** EBFI **

replace ebfi_dec17final = epd_dec17 + epi_dec17 + eps_dec17

** EBFIN **

replace ebfin_dec17final = epdn_dec17 + epin_dec17 + epsn_dec17


** EGFEN **

replace egfen_dec17final = egfen if date<=tq(2017q3) //Setting historical values 
replace egfen_dec17final = L.egfen_dec17final*(egfn_dec17/L.egfn_dec17) if date>tq(2017q3) //using growth of dec-17 file 

** EGFE **

gen implic_egfe = egfen/egfe //back out implicit index 
gen indexfed_09_temp = implic_egfe if date==tq(2009q2) //rebase so 2009=1
egen indexfed_09 = max(indexfed_09_temp)

gen egfe09 = (implic_egfe/indexfed_09)^(-1)*egfen //real variable in 2009$

replace egfe_dec17final = egfe09 if date<=tq(2017q3) //Setting historical values 
replace egfe_dec17final = L.egfe_dec17final*(egf_dec17/L.egf_dec17) if date>tq(2017q3) //using growth of dec-17 file 

drop implic_egfe indexfed_09_temp indexfed_09 egfe09

** EGFET **

gen egft_ratio = (egfit_dec17 + egflt_dec17 + egfot_dec17)/ /// trend to actual ratio
					(egfi_dec17 + egfl_dec17 + egfo_dec17)
					
replace egfet_dec17final = egft_ratio*egfe_dec17final

drop egft_ratio

** EGSEN **

replace egsen_dec17final = egsen if date<=tq(2017q3) //Setting historical values 
replace egsen_dec17final = L.egsen_dec17final*(egsn_dec17/L.egsn_dec17) if date>tq(2017q3) //using growth of dec-17 file 

** EGSE **

gen implic_egse = egsen/egse //back out implicit index 
gen indexs_09_temp = implic_egse if date==tq(2009q2) //rebase so 2009=1
egen indexs_09 = max(indexs_09_temp)

gen egse09 = (implic_egse/indexs_09)^(-1)*egsen //real variable in 2009$

replace egse_dec17final = egse09 if date<=tq(2017q3) //Setting historical values 
replace egse_dec17final = L.egse_dec17final*(egs_dec17/L.egs_dec17) if date>tq(2017q3) //using growth of dec-17 file 

drop implic_egse indexs_09_temp indexs_09 egse09

** EGSET **

gen egst_ratio = (egsit_dec17 + egslt_dec17 + egsot_dec17)/ /// trend to actual ratio
					(egsi_dec17 + egsl_dec17 + egso_dec17)
					
replace egset_dec17final = egst_ratio*egse_dec17final

drop egst_ratio

			
** EMPTRT **

replace emptrt_dec17final = emptrt


** GTRD **

replace gtrd_dec17final = gftrd_dec17


** GTRT **

replace gtrt_dec17final = gftrt_dec17 + gstrt_dec17


** GTR - using regression  **

replace gtr_dec17final = (gtrd_dec17final+gtrt_dec17final)*xgdpt_dec17final


** GTN - using regression  **

replace gtn_dec17final = 0.01*pgdp_dec17final*gtr_dec17final


** GFEXPN **

replace gfexpn_dec17final = egfln_dec17final + egfen_dec17final + gtn_dec17final + gfintn_dec17final



** HGPBFIR **

replace hgpbfir_dec17final = hgpbfir


** HXBTR **

replace hxbtr_dec17final = 0 


** JRBFI **

replace jrbfi_dec17final = jrbfi if date<=tq(2017q3)

gen last_jrbfi_temp = jrbfi if date==tq(2017q3)
egen last_jrbfi = max(last_jrbfi_temp)

replace jrbfi_dec17final = last_jrbfi if date>tq(2017q3)

drop last_jrbfi_temp last_jrbfi


** KBFI **

replace kbfi_dec17final = kpd_dec17 + kpi_dec17 + kps_dec17



** UGFDBTP **

replace ugfdbtp_dec17final = ugfdbtp if date<=tq(2017q3)
gen last_ugfdbtp_temp = ugfdbtp if date==tq(2017q3)

egen last_ugfdbtp = max(last_ugfdbtp_temp)
replace ugfdbtp_dec17final = last_ugfdbtp if date>tq(2017q3)

drop last_ugfdbtp_temp last_ugfdbtp_temp

* SER: TESTING THINGS *
replace ugfdbtp_dec17final = 1 if date>tq(2017q3)


** GFDBTNP **

replace gfdbtnp_dec17final = gfdbtnp if date<=tq(2017q3)
replace gfdbtnp_dec17final = ugfdbtp_dec17final*(L.gfdbtnp_dec17final - 0.25*gfsrpn_dec17final) if date>tq(2017q3)


** LEG **

replace leg_dec17final = leh_dec17final - lep_dec17final - leo_dec17final


** PBFIR **

replace pbfir_dec17final = pbfir 


** PEGFR **

replace pegfr_dec17final = egfen_dec17final / (pxp_dec17final * egfe_dec17final * 0.01)


** PEGSR **

replace pegsr_dec17final = egsen_dec17final / (pxp_dec17final * egse_dec17final * 0.01)


** PKBFIR **

replace pkbfir_dec17final = pkbfir


** QEBFI **

replace qebfi_dec17final = qebfi


** QPXB **

replace qpxb_dec17final = pwstar_dec17final + (pl_dec17final / lprdt_dec17final)


** RBFI **

replace rbfi_dec17final = rpd_dec17


** RRFF **

replace rrff_dec17final = rrffe_dec17


** RTBFI **

replace rtbfi_dec17final = rtbfi


** TCIN **

replace tcin_dec17final = tfcin_dec17


** TDPV **

replace tdpv_dec17final = tdpv


** TPN **

replace tpn_dec17final = tfpn_dec17


** TRCI **

replace trci_dec17final = trfci_dec17


** TRCIT **

* Set initial value
replace trcit_dec17final = trcit if date<=tq(2017q3)

*replace trcit_dec17final = trci_dec17final - 0.81025 * (L.trci_dec17final - L.trcit_dec17final) + 0.00132 * (xgap2_dec17final) if date>tq(2017q3)


replace trcit_dec17final = trci_dec17final - 0.0070663*xgap2_dec17final - 0.81025*(L.trci_dec17final-L.trcit_dec17final - 0.0070663*L.xgap2_dec17final) if date>tq(2017q3)



** TRITC **

replace tritc_dec17final = tritc


** TRP **

replace trp_dec17final = trfp_dec17 + trsp_dec17


** TRPT **

replace trpt_dec17final = trfpt_dec17 + trspt_dec17


** TRPTX **

replace trptx_dec17final = trfptx_dec17 + trsptx_dec17



** UGFSRP **

replace ugfsrp_dec17final = ugfsrp


** ULEG **

replace uleg_dec17final = uleg


** UPKBFIR **

replace upkbfir_dec17final = upkbfir


** UVBFI **

replace uvbfi_dec17final = uvbfi


** UYHIBN **

replace uyhibn_dec17final = yhibn_dec17final / xgdpn_dec17final


** UYNICPNR **

replace uynicpnr_dec17final = uynicpnr


** UPGFL **

replace upgfl_dec17final = upgfl

** UPGSL **

replace upgsl_dec17final = upgsl

** UPMP **

replace upmp_dec17final = upmp



** VBFI **

replace vbfi_dec17final = uvbfi_dec17final * (pkbfir_dec17final / pbfir_dec17final) / rtbfi_dec17final


** XBTR **

replace xbtr_dec17final = xbtr


** YKBFIN **

replace ykbfin_dec17final = 0.01 * rtbfi_dec17final * pxb_dec17final * (kbfi_dec17final + L.kbfi_dec17final) / 2


** YNIRN **

replace ynirn_dec17final = yniin_dec17 + ynisen_dec17


** ZEBFI **

replace zebfi_dec17final = zebfi


** GFRECN **

replace gfrecn_dec17final = tpn_dec17final  + tcin_dec17final + ugfsrp_dec17final*xgdpn_dec17final


***************** Fixing some issues with running variables in FRBUS  *****************

*These are vars where current value is 0 and dec17 value is -10000

replace lurtrsh_dec17final = lurtrsh

replace pitrsh_dec17final = pitrsh

replace rffmin_dec17final = rffmin



/*
/********************************************************************************
************************** Quality Control Checks **************************
Create figures to compare the vairables we are using w/ the values in the current file
to make sure nothing too crazy is happening. 
********************************************************************************/


********************************************************************************
/*
 Create charts of variables in the current file vs what we are proposing to use
 in the pre-tcja longbase file (all variables with the underscore *_dec17final)
*/
** Begin output PDF **
 putpdf begin

foreach x of varlist adjlegrt-zynid {
	
	set graphics off // So all the graphs don't pop up
	
	twoway (line `x' `x'_dec17final date, lwidth(medthick...))  ///
				if inrange(date, tq(1980q1), tq(2050q1)), ///
				ytitle("Values") title("`x'") name("`x'") /// 
				legend(pos(6) col(2) label(1 "Current") label(2 "Pre-TCJA"))
				
				graph export "figs/chart_`x'.png", as(png) replace //saving  graph
				
				putpdf paragraph, halign(center) 
				putpdf image "figs/chart_`x'.png"
                       
 }
               

** save combined graphs to pdf file **
putpdf save variables_both.pdf, replace

* Turn graphics back on *
set graphics on 

*/
/*

/********************************************************************************
************************** Export TXT File **************************
Doing some editing to make sure the file format is the exact same as FRBUS
********************************************************************************/

keep date  *_dec17final 


rename *_dec17final *

/*
foreach x of varlist adjlegrt-zynid {
	
	 tostring `x', replace format("%13.10f") force
	 
	 replace `x' = "NA" if `x'=="."
                       
 }
 */
 generate OBS_temp = string(date, "%tq")
 gen OBS = upper(OBS_temp)
 
 drop OBS_temp date 
 
 order OBS

rename *, upper 

export delimited using "output/LONGBASE_pretcja.csv", replace
