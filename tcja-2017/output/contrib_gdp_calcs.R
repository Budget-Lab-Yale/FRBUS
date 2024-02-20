#### Program to compute contributions to difference in real GDP from FRBUS output #### 

library(readr)
library(ggplot2)
#install.packages("readr")
library(readr)
library(gridExtra)
library(dplyr)

dynamic <- read_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/dynamic_econ_int.csv", show_col_types = FALSE)
baseline <- read_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/baseline_econ.csv", show_col_types = FALSE)
cbo <- read_csv("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/cbo_dynamic_econ.csv", show_col_types = FALSE)

colnames(dynamic)[c(1)] <- c("year")
colnames(baseline)[c(1)] <- c("year")
colnames(cbo)[c(1)] <- c("year")


### For the variables that are relative to PXP covert to level ###

dynamic <- dynamic %>%
    mutate(PKBFIR_level = PKBFIR*PXP,
           PHR_level = PHR*PXP, 
           PEGFR_level = PEGFR*PXP, 
           PXR_level = PXR*PXP)

baseline <- baseline %>%
  mutate(PKBFIR_level = PKBFIR*PXP,
         PHR_level = PHR*PXP, 
         PEGFR_level = PEGFR*PXP, 
         PXR_level = PXR*PXP)

### Function to calculate contribution ###

# Calculate denominator that will be used in function below
dynamic$gov_expen = dynamic$EGFE +   dynamic$EGSE
baseline$gov_expen = baseline$EGFE +   baseline$EGSE

contrib_gdp <- function(x_dynamic,x_baseline, x_price_dynamic,  x_price_base) {
  
  numerator = ((x_price_dynamic/dynamic$PGDP) + x_price_base)*
            (x_dynamic- x_baseline)
  
  denominator = (((dynamic$PCNIA/dynamic$PGDP) + baseline$PCNIA)*baseline$ECNIA) +
               (((dynamic$PKBFIR_level/dynamic$PGDP) + baseline$PKBFIR_level)*baseline$EBFI) +
               (((dynamic$PHR_level/dynamic$PGDP) + baseline$PHR_level)*baseline$EH) + 
                (((dynamic$PEGFR_level/dynamic$PGDP) + baseline$PEGFR_level)*(baseline$gov_expen)) +
               (((dynamic$PXR_level/dynamic$PGDP) + baseline$PXR_level)*(baseline$EX)) +
               (((dynamic$PMO/dynamic$PGDP) + baseline$PMO)*(baseline$EM))


  contrib_gdp <- numerator/denominator*100 
  return(contrib_gdp)
}

dynamic$XGDP_contrib <- contrib_gdp(dynamic$XGDP, baseline$XGDP, dynamic$PGDP, baseline$PGDP)
dynamic$PCE_contrib <- contrib_gdp(dynamic$ECNIA, baseline$ECNIA, dynamic$PCNIA, baseline$PCNIA)
dynamic$nonres_contrib <- contrib_gdp(dynamic$EBFI, baseline$EBFI, dynamic$PKBFIR_level, baseline$PKBFIR_level)
dynamic$res_contrib <- contrib_gdp(dynamic$EH, baseline$EH, dynamic$PHR_level, baseline$PHR_level)
dynamic$gov_contrib <- contrib_gdp(dynamic$gov_expen, baseline$gov_expen, dynamic$PEGFR_level, baseline$PEGFR_level)
dynamic$ex_contrib <- contrib_gdp(dynamic$EX, baseline$EX, dynamic$PXR_level, baseline$PXR_level)
dynamic$im_contrib <- contrib_gdp(dynamic$EM, baseline$EM, dynamic$PMO, baseline$PMO)


### Make Plots ####
real_pce <- ggplot() +
  geom_line(data = dynamic, aes(x = year, y = PCE_contrib, color = "Dynamic Int")) +
  geom_line(data = cbo, aes(x = year, y = ECNIA_cbo, color = "CBO"), linetype = "dashed" ) +
  labs(title = "Real PCE", x = "Year", y = "Percentage Point Contrib. To Real GDP") +
  scale_color_manual(values = c("Dynamic" = "blue", "Dynamic Int" = "red", "CBO" = "black")) +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_x_continuous(breaks = 2017:2027, labels = as.character(2017:2027)) +
  theme(legend.position = "bottom", legend.title=element_blank(),
        panel.background = element_rect(fill = "white",
                                        colour = "black",
                                        size = 0.5, linetype = "solid"))


ggsave("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/figures/real_pce.png", plot = real_pce, width = 7, height =  5)


real_ebfi <- ggplot() +
  geom_line(data = dynamic, aes(x = year, y = nonres_contrib, color = "Dynamic Int")) +
  geom_line(data = cbo, aes(x = year, y = EBFI_cbo, color = "CBO"), linetype = "dashed" ) +
  labs(title = "Real Business Fixed Investment", x = "Year", y = "Percentage Point Contrib. To Real GDP") +
  scale_color_manual(values = c("Dynamic" = "blue", "Dynamic Int" = "red", "CBO" = "black")) +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_x_continuous(breaks = 2017:2027, labels = as.character(2017:2027)) +
  theme(legend.position = "bottom", legend.title=element_blank(),
        panel.background = element_rect(fill = "white",
                                        colour = "black",
                                        size = 0.5, linetype = "solid"))


ggsave("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/figures/real_ebfi.png", plot = real_ebfi, width = 7, height =  5)

real_ri <- ggplot() +
  geom_line(data = dynamic, aes(x = year, y = res_contrib, color = "Dynamic Int")) +
  geom_line(data = cbo, aes(x = year, y = EH_cbo, color = "CBO"), linetype = "dashed" ) +
  labs(title = "Real Residential Investment", x = "Year", y = "Percentage Point Contrib. To Real GDP") +
  scale_color_manual(values = c("Dynamic" = "blue", "Dynamic Int" = "red", "CBO" = "black")) +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_x_continuous(breaks = 2017:2027, labels = as.character(2017:2027)) +
  theme(legend.position = "bottom", legend.title=element_blank(),
        panel.background = element_rect(fill = "white",
                                        colour = "black",
                                        size = 0.5, linetype = "solid"))


ggsave("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/figures/real_ri.png", plot = real_ri, width = 7, height =  5)

real_gov <- ggplot() +
  geom_line(data = dynamic, aes(x = year, y = gov_contrib, color = "Dynamic Int")) +
  geom_line(data = cbo, aes(x = year, y = GOV_cbo, color = "CBO"), linetype = "dashed" ) +
  labs(title = "Real Government Consumption and Expenditures", x = "Year", y = "Percentage Point Contrib. To Real GDP") +
  scale_color_manual(values = c("Dynamic" = "blue", "Dynamic Int" = "red", "CBO" = "black")) +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_x_continuous(breaks = 2017:2027, labels = as.character(2017:2027)) +
  theme(legend.position = "bottom", legend.title=element_blank(),
        panel.background = element_rect(fill = "white",
                                        colour = "black",
                                        size = 0.5, linetype = "solid"))


ggsave("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/figures/real_gov.png", plot = real_gov, width = 7, height =  5)

real_ex <- ggplot() +
  geom_line(data = dynamic, aes(x = year, y = ex_contrib, color = "Dynamic Int")) +
  geom_line(data = cbo, aes(x = year, y = EX_cbo, color = "CBO"), linetype = "dashed" ) +
  labs(title = "Real Exports", x = "Year", y = "Percentage Point Contrib. To Real GDP") +
  scale_color_manual(values = c("Dynamic" = "blue", "Dynamic Int" = "red", "CBO" = "black")) +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_x_continuous(breaks = 2017:2027, labels = as.character(2017:2027)) +
  theme(legend.position = "bottom", legend.title=element_blank(),
        panel.background = element_rect(fill = "white",
                                        colour = "black",
                                        size = 0.5, linetype = "solid"))


ggsave("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/figures/real_ex.png", plot = real_ex, width = 7, height =  5)


real_em <- ggplot() +
  geom_line(data = dynamic, aes(x = year, y = -im_contrib, color = "Dynamic Int")) +
  geom_line(data = cbo, aes(x = year, y = EM_cbo, color = "CBO"), linetype = "dashed" ) +
  labs(title = "Real Imports", x = "Year", y = "Percentage Point Contrib. To Real GDP") +
  scale_color_manual(values = c("Dynamic" = "blue", "Dynamic Int" = "red", "CBO" = "black")) +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_x_continuous(breaks = 2017:2027, labels = as.character(2017:2027)) +
  theme(legend.position = "bottom", legend.title=element_blank(),
        panel.background = element_rect(fill = "white",
                                        colour = "black",
                                        size = 0.5, linetype = "solid"))


ggsave("/gpfs/gibbs/project/sarin/ser68/FRBUS/tcja-2017/output/figures/real_em.png", plot = real_em, width = 7, height =  5)

