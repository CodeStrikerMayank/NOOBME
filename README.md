# ThermoShelter AI

### Area-Specific Shelter Design and Thermal Comfort Analysis

ThermoShelter AI is a Python-based software prototype designed to support the analysis and design of shelters for location-specific thermal conditions.

The system combines climate inputs, shelter dimensions, material properties, thermodynamic calculations, PMV/PPD-based thermal comfort evaluation, 3D thermal visualization, recommendations, and PDF report generation in a single workflow.

---

## 🚀 Project Overview

Generic shelters may not perform equally well across different environmental conditions.

ThermoShelter AI aims to provide a software-based workflow for evaluating shelter thermal performance using area-specific environmental inputs and shelter design parameters.

The prototype is intended for research, demonstration, and engineering-design exploration.

> **Note:** This project is a software prototype. It is not a certified engineering, medical, or building-compliance tool.

---

## 🎯 Problem Statement

Shelters deployed in different climatic environments can experience significantly different thermal conditions.

Factors such as:

- Outdoor temperature
- Relative humidity
- Wind speed
- Solar radiation
- Mean radiant temperature
- Shelter dimensions
- Wall thickness
- Insulation/material properties
- Occupant assumptions

can influence the resulting indoor thermal environment.

A single generic shelter configuration may therefore require different design considerations for different locations.

---

## 💡 Proposed Solution

ThermoShelter AI provides a unified software workflow to:

1. Collect shelter dimensions and location information
2. Enter environmental/climate conditions
3. Calculate thermal performance
4. Evaluate thermal comfort using PMV/PPD
5. Visualize thermal conditions using a 3D heatmap
6. Generate design recommendations
7. Export the analysis as a PDF report
8. Provide an administrative view for reviewing user sessions and results

---

# 🔄 User Workflow

```text
Login / Signup
      ↓
GPS and Shelter Dimensions
      ↓
Climate Data Collection
      ↓
Thermodynamic Solver
      ↓
3D Heatmap Visualization
      ↓
Export Blueprint PDF
