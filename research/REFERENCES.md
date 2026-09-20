# Research References

This document lists the research papers, thermal-comfort model, and standards that informed the development direction of ThermoShelter AI.

The references are used as a research and engineering basis for concepts such as shelter thermal modelling, thermal comfort, PMV/PPD, building-envelope performance, ventilation, passive thermal strategies, and area-specific shelter design.

> **Important:** The current ThermoShelter AI prototype does not reproduce the complete simulation methods of these publications. The references inform the project's methodology and future development direction.

---

# 1. Research Papers

## 1.1 ShelTherm: An aid-centric thermal model for shelter design

**Authors:** Manuela de Castro, Noorullah Kuchai, Sukumar Natarajan, Kemi Adeyeye, Daniel Fosas, Francis Moran, Nick McCullen, Zu Wang, David Coley

**Journal:** Journal of Building Engineering

**Year:** 2021

**Volume:** 44

**Article:** 102579

**DOI:** 10.1016/j.jobe.2021.102579

### Relevance to ThermoShelter AI

This research presents a thermal model developed specifically for simple shelters and considers characteristics such as high ventilation/infiltration rates and thin shelter materials.

The work demonstrates the importance of considering:

- Shelter-specific thermal behaviour
- Heat transfer
- Ventilation/infiltration
- Material properties
- Time-varying environmental conditions
- Real shelter configurations

### Contribution to this project

The paper informs the planned development of a more detailed shelter thermal model beyond a simplified steady-state heat-transfer calculation.

---

## 1.2 The Thermal Comfort Performance in an Indonesian Refugee Tent: Existing Conditions and Redesigns

**Journal:** Energies

**Year:** 2025

**Volume:** 18

**Article:** 1249

**DOI:** 10.3390/en18051249

### Relevance to ThermoShelter AI

This research combines field measurements and computational simulation to investigate thermal comfort in refugee tents.

The study evaluates environmental parameters including:

- Temperature
- Humidity
- Airflow

It also evaluates thermal comfort using:

- Effective Temperature
- PMV
- PPD

The research investigates redesign strategies involving upper ventilation and a double-layer outer skin.

### Contribution to this project

The paper supports the consideration of:

- Ventilation strategies
- Multi-layer shelter envelopes
- Air movement
- Thermal comfort evaluation
- Shelter redesign based on environmental conditions

The study provides evidence that shelter configuration and ventilation can influence indoor thermal conditions.

---

## 1.3 A simplified tool for building layout design based on thermal comfort simulations

**Authors:** Prashant Anand, Chirag Deb, Ramachandraiah Alur

**Journal:** Frontiers of Architectural Research

**Year:** 2017

**Volume:** 6

**Issue:** 2

**Pages:** 218–230

**DOI:** 10.1016/j.foar.2017.03.001

### Relevance to ThermoShelter AI

This research presents a simplified design tool based on thermal comfort simulations using the PMV index.

The study investigated different room layouts and window configurations across three climatic zones in India.

The research demonstrates how thermal comfort analysis can support design decisions involving:

- Building layout
- Orientation
- Window configuration
- Climatic conditions
- PMV-based analysis

### Contribution to this project

This work supports the concept of using a software-based thermal comfort analysis tool to assist early-stage shelter and building design decisions.

---

## 1.4 Evaluating indoor thermal resilience of passive and low-power cooling shelters for outdoor workers in India

**Authors:** Yi Wu, Jeetika Malik, Tianzhen Hong, Elif Kilic, Prasad Vaidya, Da Yan, Ashok J. Gadgil

**Journal:** Building Simulation

**Year:** 2025

**Volume:** 18

**Pages:** 3373–3391

**DOI:** 10.1007/s12273-025-1391-y

### Relevance to ThermoShelter AI

This study evaluates passive and low-power cooling shelter strategies in the hot-dry climate of Jodhpur, India.

The research considers design strategies including:

- Natural ventilation
- Fans
- Envelope improvements
- Cool roofs
- Thermal mass
- Passive cooling measures
- Low-power active measures

### Contribution to this project

The research supports the idea that shelter thermal performance can be improved through combinations of envelope and ventilation strategies rather than relying on a single design parameter.

It also demonstrates the importance of evaluating shelter designs against location-specific environmental conditions.

---

## 1.5 Study on the Indoor Thermal Environment of Prefabricated Railway Buildings in High-Altitude Cold Regions for Sustainable Development

**Authors:** Hui Li, Lintao Ma, Haojie Zhang, Zhixiang Yu, Hu Xu

**Journal:** Sustainability

**Year:** 2026

**Volume:** 18

**Issue:** 10

**Article:** 4667

**DOI:** 10.3390/su18104667

### Relevance to ThermoShelter AI

This research investigates the indoor thermal environment of prefabricated buildings in high-altitude cold regions.

The study considers:

- Thermal bridges
- Thermal transmittance
- Building orientation
- Window-to-wall ratio
- Exterior wall insulation
- Local solar radiation
- Altitude
- Indoor thermal conditions

The research provides region-specific analysis for high-altitude locations and demonstrates that environmental and envelope parameters can substantially influence indoor thermal performance.

### Contribution to this project

This work supports ThermoShelter AI's focus on area-specific shelter design rather than treating every location as thermally identical.

It also provides a research basis for future improvements involving:

- Thermal bridges
- Orientation
- Envelope optimization
- Region-specific material parameters
- High-altitude shelter modelling

---

# 2. Thermal Comfort Model

## Fanger Thermal Comfort Model

**Reference:** P. O. Fanger

**Book:** Thermal Comfort: Analysis and Applications in Environmental Engineering

**Publisher:** McGraw-Hill

**Year:** 1970

### Relevance to ThermoShelter AI

Fanger's thermal comfort model provides the theoretical basis for PMV and PPD calculations.

The model considers environmental and personal parameters including:

- Air temperature
- Mean radiant temperature
- Relative humidity
- Air velocity
- Metabolic rate
- Clothing insulation

### Contribution to this project

ThermoShelter AI uses PMV/PPD concepts as part of its thermal comfort analysis workflow.

The PMV result should be interpreted together with the input assumptions and environmental conditions used by the model.

---

# 3. Thermal Comfort Standards

## ASHRAE Standard 55-2023

**Title:** Thermal Environmental Conditions for Human Occupancy

**Standard:** ANSI/ASHRAE Standard 55-2023

### Relevance to ThermoShelter AI

ASHRAE Standard 55 provides a framework for evaluating thermal environmental conditions for human occupancy.

It is relevant to the project's use of:

- Thermal comfort parameters
- PMV-based evaluation
- Environmental conditions
- Comfort assessment

> The prototype references the standard as a technical basis. This does not imply that ThermoShelter AI is certified for ASHRAE compliance.

---

## ISO 7730:2025

**Title:** Ergonomics of the thermal environment — Analytical determination and interpretation of thermal comfort using calculation of the PMV and PPD indices and local thermal comfort criteria

**Standard:** ISO 7730:2025

### Relevance to ThermoShelter AI

ISO 7730:2025 specifies methods for evaluating general thermal comfort and discomfort using:

- Predicted Mean Vote (PMV)
- Predicted Percentage of Dissatisfied (PPD)
- Local thermal comfort criteria

### Contribution to this project

The standard provides a technical reference for the interpretation of PMV/PPD-based thermal comfort analysis.

> The prototype should not be interpreted as an ISO-certified or ISO-compliant engineering tool.

---

# 4. Research-to-Feature Mapping

| Research / Standard | ThermoShelter AI Concept |
|---|---|
| ShelTherm | Shelter thermal modelling, heat transfer, ventilation |
| Indonesian Refugee Tent Study | Ventilation, multi-layer envelope, PMV/PPD |
| Simplified Layout Design Tool | Software-based thermal comfort and design analysis |
| Passive / Low-Power Cooling Shelters | Passive strategies, ventilation and envelope design |
| High-Altitude Railway Building Study | Area-specific design, insulation, orientation, thermal transmittance |
| Fanger Thermal Comfort Model | PMV / PPD |
| ASHRAE 55-2023 | Thermal comfort assessment framework |
| ISO 7730:2025 | PMV / PPD interpretation and thermal comfort criteria |

---

# 5. Relationship to the Current Prototype

The current ThermoShelter AI prototype implements a simplified software workflow containing:

- Shelter geometry inputs
- Manual climate inputs
- Material parameters
- Thermal resistance / U-value calculations
- Simplified heat-transfer calculations
- PMV / PPD analysis
- 3D thermal visualization
- Analytics
- Recommendations
- PDF report generation
- Administrative review functionality

The current prototype does **not** implement the complete modelling capabilities of the referenced research papers.

In particular, it should not currently be described as:

- A CFD solver
- A complete building-energy simulation engine
- A validated replacement for EnergyPlus
- A certified thermal-comfort assessment tool
- A field-validated engineering design system

These are potential areas for future development and validation.

---

# 6. Future Research Directions

Future versions of ThermoShelter AI may investigate:

1. Dynamic shelter thermal modelling
2. Ventilation and infiltration modelling
3. Thermal-bridge modelling
4. Solar radiation and solar-gain modelling
5. Improved material databases
6. Location-specific climate datasets
7. CFD-based airflow analysis
8. Advanced shelter optimization
9. Field measurements and validation
10. Integration with established building-energy simulation tools

---

# 7. Reference Policy

The research papers and standards listed above are used as technical references for the project.

The project does not claim ownership of the referenced research.

Where applicable, users should consult the original publications and standards for the complete methodology, equations, assumptions, limitations, and validation procedures.

---

## Primary Sources

- de Castro et al. (2021), *ShelTherm: An aid-centric thermal model for shelter design*. Journal of Building Engineering, 44, 102579. DOI: 10.1016/j.jobe.2021.102579
- *The Thermal Comfort Performance in an Indonesian Refugee Tent: Existing Conditions and Redesigns* (2025). Energies, 18, 1249. DOI: 10.3390/en18051249
- Anand, P., Deb, C., & Alur, R. (2017), *A simplified tool for building layout design based on thermal comfort simulations*. Frontiers of Architectural Research, 6(2), 218–230. DOI: 10.1016/j.foar.2017.03.001
- Wu et al. (2025), *Evaluating indoor thermal resilience of passive and low-power cooling shelters for outdoor workers in India*. Building Simulation, 18, 3373–3391. DOI: 10.1007/s12273-025-1391-y
- Li et al. (2026), *Study on the Indoor Thermal Environment of Prefabricated Railway Buildings in High-Altitude Cold Regions for Sustainable Development*. Sustainability, 18(10), 4667. DOI: 10.3390/su18104667
- Fanger, P. O. (1970), *Thermal Comfort: Analysis and Applications in Environmental Engineering*. McGraw-Hill.
- ANSI/ASHRAE Standard 55-2023, *Thermal Environmental Conditions for Human Occupancy*.
- ISO 7730:2025, *Ergonomics of the thermal environment — Analytical determination and interpretation of thermal comfort using calculation of the PMV and PPD indices and local thermal comfort criteria*.
