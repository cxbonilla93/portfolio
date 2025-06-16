# ==========================================================
# Load Required Libraries ----
# ==========================================================
library(tidyverse)    # ggplot2, dplyr, readr, etc.
library(dplyr)        # data manipulation verbs
library(sf)           # spatial data
library(readxl)       # Excel import
library(data.table)   # fast table operations
library(ggspatial)    # spatial utilities
library(writexl)      # write Excel
library(ggplot2)      # plotting
library(RColorBrewer) # brewer.pal()
library(scales)

# ==========================================================
# Set Global Options ----
# ==========================================================
options(tigris_use_cache = TRUE)  # cache TIGER data
sf_use_s2(FALSE)                  # planar geometry

# ==========================================================
# Clear Environment & Set Working Directory ----
# ==========================================================
rm(list = ls())
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# ==========================================================
# Read Spatial & Attribute Data ----
# ==========================================================
parishes <- st_read("parish_tm06_apr_19_2025.gpkg")
raw_data <- read_excel("Data from Client - 4.22.2025.xlsx") %>%
  set_names(c(
    "Parish",
    "Median Sale Price per Sq M",
    "Median Sale Price per Sq M - New Build",
    "Percent Difference from Citywide Price",
    "Status Category",
    "Tier"
  )) %>%
  mutate(
    Parish = case_when(
      Parish == "Ajuda"                  ~ "Ajuda",
      Parish == "Alcantara"              ~ "Alcântara",
      Parish == "Alvalade"               ~ "Alvalade",
      Parish == "Areeiro"                ~ "Areeiro",
      Parish == "Arroios"                ~ "Arroios",
      Parish == "Avenidas Novas"         ~ "Avenidas Novas",
      Parish == "Beatos"                 ~ "Beato",
      Parish == "Belem"                  ~ "Belém",
      Parish == "Benfica"                ~ "Benfica",
      Parish == "Campo de Ourique"       ~ "Campo de Ourique",
      Parish == "Campolide"              ~ "Campolide",
      Parish == "Carnide"                ~ "Carnide",
      Parish == "Estrela"                ~ "Estrela",
      Parish == "Lumiar"                 ~ "Lumiar",
      Parish == "Marvila"                ~ "Marvila",
      Parish == "Misericordia"           ~ "Misericórdia",
      Parish == "Olivais"                ~ "Olivais",
      Parish == "Parque das Nacoes"      ~ "Parque das Nações",
      Parish == "Penha de Franca"        ~ "Penha de França",
      Parish == "Sta Clara"              ~ "Santa Clara",
      Parish == "Sta Maria Maior"        ~ "Santa Maria Maior",
      Parish == "Sto Antonio"            ~ "Santo António",
      Parish == "S Domingos de Benfica"  ~ "São Domingos de Benfica",
      Parish == "S Vicente"              ~ "São Vicente",
      TRUE                               ~ NA_character_
    )
  )

# join spatial & attribute data
parishes <- parishes %>%
  select(fre_name, fre_code) %>%
  inner_join(raw_data, by = c("fre_name" = "Parish"))

# ----------------------------------------------------------
# 1) Continuous map: Median Sale Price per m² ----
# ----------------------------------------------------------
ggplot(parishes) +
  geom_sf(
    aes(fill = `Median Sale Price per Sq M`),
    color = "black",
    size  = 0.2,
    alpha = 0.9
  ) +
  scale_fill_distiller(
    name      = "Sale Price (€/m²)",
    palette   = "Greens",
    direction = 1,
    na.value  = "grey90",
    labels    = comma       # formats 4500 → "4,500"
  ) +
  labs(
    title    = "Median Sale Price per m² by Parish",
    subtitle = "Darker = higher"
  ) +
  theme_minimal() +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid       = element_blank(),
    axis.text        = element_blank(),
    axis.ticks       = element_blank(),
    axis.title       = element_blank(),
    legend.position  = "bottom"
  )

# ----------------------------------------------------------
# 2) Continuous map: New‑Build Median Sale Price ----
# ----------------------------------------------------------
parishes <- parishes %>%
  mutate(FORPLOT2 = na_if(`Median Sale Price per Sq M - New Build`, 0))

ggplot(parishes) +
  geom_sf(
    aes(fill = FORPLOT2),
    color = "black", size = 0.2, alpha = 0.9
  ) +
  scale_fill_distiller(
    name      = "New Build Sale Price (€/m²)",
    palette   = "Greens",
    direction = 1,
    na.value  = "darkgrey",
    labels    = comma       # formats 4500 → "4,500"
  ) +
  labs(
    title    = "Median New Build Sale Price per m² by Parish",
    subtitle = "Gray = no data"
  ) +
  theme_minimal() +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid       = element_blank(),
    axis.text        = element_blank(),
    axis.ticks       = element_blank(),
    axis.title       = element_blank(),
    legend.position  = "bottom"
  )

# ----------------------------------------------------------
# 3) Tier map: Sale Price Tiers ----
# ----------------------------------------------------------
parishes <- parishes %>%
  mutate(
    FORPLOT3TIER = factor(
      Tier,
      levels = 1:5,
      labels = paste("Tier", 1:5)
    )
  )

tier_colors_sale <- c(
  "Tier 1" = brewer.pal(5, "Greens")[5],
  "Tier 2" = brewer.pal(5, "Greens")[4],
  "Tier 3" = brewer.pal(5, "Greens")[3],
  "Tier 4" = brewer.pal(5, "Greens")[2],
  "Tier 5" = "white"
)

ggplot(parishes) +
  geom_sf(
    aes(fill = FORPLOT3TIER),
    color = "black", size = 0.2, alpha = 0.9
  ) +
  scale_fill_manual(
    name   = "Sale Price Tier",
    values = tier_colors_sale,
    drop   = FALSE
  ) +
  labs(
    title    = "Parish Sale Price Tiers",
    subtitle = "Tier 1 = darkest green → Tier 5 = white"
  ) +
  theme_minimal() +
  theme(
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid       = element_blank(),
    axis.text        = element_blank(),
    axis.ticks       = element_blank(),
    axis.title       = element_blank(),
    legend.position  = "bottom"
  )
