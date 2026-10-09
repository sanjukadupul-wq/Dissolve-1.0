FreeFEM Zn biodegradation model - v4 (conservative interface coupling + surface film)
====================================================================================
v4 = v3 (v2 + Cl molar-unit fix + O2 molar fix) + the changes below. All changes are inactive unless their flag is set, so
"-conservative 0 -o2_molar_fix 0" reproduces v2 exactly (checked: 0.133143 % at 168 h, identical to v2).

Flags (config/settings.idp)
  -conservative 0|1|2   2 = recommended: v_n = v_ORR at the interface (no min()); Zn source = rho_Zn*|v_n|*delta_Gamma; no Zn
                        reservoir inside the solid (Zn = 0 initially, no pin, Zn diffusion masked to the electrolyte); O2 sink is the
                        Robin term kORR*O2*kappa(theta) on the interface. O2 consumed, Zn released and metal lost are tied by
                        O2 + 2Zn + 2H2O -> 2Zn2+ + 4OH-. (1 = min() with solubility cap + scaled sink: unstable, kept for reference.)
  -film_mode 1          corrosion-product film as an INTERFACE state theta in [0,1] (coverage), needs -conservative 2:
                        d(theta)/dt = k_f*(rho_Zn|v|/m_f)*(1-theta) - k_d*theta*C_Cl^2, m_f = rho_film(1-eps)*delta_f*M_Zn/M_film.
                        Precipitated Zn is withdrawn from the Zn source and dissolved film returns it (Zn conserved at every node).
                        The film blocks the ORR: kappa = 1 - theta*(1 - del*eps/tau), applied to the O2 sink and to v_ORR.
                        theta is carried with the receding interface (semi-Lagrangian shift). Film_Interface in mechanism_data.txt = theta*F_max.
  -film_thickness <mm>  delta_f, film thickness at full coverage (default 0.005; 0.001 used for the latest calibration).
  -kf_rate_units 1      -k_f is a rate in 1/h; internal share = k_f*delta_f^2/D_Zn (thin-film reduction of the literature law).
  -kd_mass_units 1      -k_d in mm^6 g^-2 h^-1 (Cl in g/mm3); internally divided by (1e6/35.45)^2 (the term squares the molar Cl).
  -oh_fix 0|1           OH- sources on a molar basis; NOT validated.
  -zn_sat <g/mm3>       solubility cap, only with -conservative 1.
Diagnostics: the per-step log line prints O2sinkCum (g) and ZnSrcCum (g); mass_loss_smooth.txt holds the smoothed-Heaviside mass loss.

Units: fields are mass-based (g/mm3) except OH- (mol/L); k_f [1/h] (or dimensionless share without -kf_rate_units);
k_d [L^2 mol^-2 h^-1] (or mm^6 g^-2 h^-1 with -kd_mass_units); k_ORR [mm/h]. In the manuscript everything is written in mol/L.

Settings used for the latest calibration (film mode, hmin1.0 mesh)
  -input_mesh disc_10x2_hmin1.0_topinlet.mesh  (top face z=+15 relabelled 4 = inlet -> Dirichlet O2; other faces 3 = wall)
  -conservative 2 -film_mode 1 -film_thickness 0.001 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0
  -dt_hours 4 -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 -film_tortuosity 120
Best parameters so far (hmin1.0, raw smoothed mass loss, NOT yet corrected to the fine mesh): k_f 3e5 1/h, k_d 1e8 mm^6 g^-2 h^-1, k_ORR 80 mm/h.

Edited files vs v3: config/settings.idp, state/fields.idp, state/initial_state.idp, physics/governing_equations.idp,
physics/interface_velocity.idp, io/write_results.idp, dissolve.edp. Scripts: slurms/ (calibration, tests, fine-mesh pairs), tools/zn_balance_v4.py.
Status: coarse-to-fine mesh correction for the film mode in progress; OH-/pH equation not validated.
