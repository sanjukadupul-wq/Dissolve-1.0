# Building and Running Dissolve™

## Overview

Dissolve™ is a FreeFEM solver that requires FreeFEM with MPI and PETSc support. This guide covers
obtaining the exact v1.1.0 release, setting up FreeFEM, running a simulation, and running the
regression suite that checks the installation.

The v1.1.0 regression suite and the revised study were run in the software environment listed
below. Other environments may work, but have not been tested with v1.1.0; after any change of
FreeFEM, MPI, PETSc or compiler, re-run the regression suite
([Step 8](#step-8-run-the-regression-suite)).

### Tested software environment (v1.1.0)

| Component | Version |
|---|---|
| FreeFEM | 4.12 (`FreeFem++ v4.12`, git v4.12, built 7 Dec 2022) |
| PETSc | 3.18.2 (bundled with the FreeFEM image) |
| MPI | MPICH 4.0.2 (bundled with the FreeFEM image, ABI `libmpi.so.12`) |
| Compiler | GCC 12.1.0 runtime libraries (Ubuntu 22.04); the compiler that built FreeFEM is not recorded in the image |
| Container OS | Ubuntu 22.04.1 LTS |
| Container runtime | Apptainer 1.5.1 (`singularity` command) |
| Host OS | Rocky Linux 9 (kernel 5.14) |
| Scheduler and launcher | Slurm, `srun --mpi=pmi2` |
| Container image | `freefem.sif`, sha256 `14b627e77793ce0d3f615b072f65aec9368625b9609ce1e33f8fcbe255a10373` |
| MPI processes | 4 (regression suite) |
| Executable | `FreeFem++-mpi` (run with `-nw`) |

The FreeFEM 4.14 source build described in [Step 3, Option B](#option-b-build-from-source-not-tested-for-v110)
was **not** used for the v1.1.0 results.

If you are on Windows, install WSL2 with Ubuntu 22.04 first ([Step 1](#step-1-install-wsl2-windows-users));
on Linux or an HPC cluster, start at [Step 3](#step-3-set-up-freefem-with-mpi-and-petsc).

## Step 1: Install WSL2 (Windows Users)

Windows users should run Dissolve™ inside Windows Subsystem for Linux 2 (WSL2) with Ubuntu 22.04 LTS.
Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu-22.04
```

Restart your computer if prompted. Launch Ubuntu 22.04 from the Start Menu, create a Linux username
and password, and check that Ubuntu runs under WSL2:

```powershell
wsl -l -v
```

Expected output:

```text
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
```

If Ubuntu reports `VERSION 1`, convert it and check again:

```powershell
wsl --set-version Ubuntu-22.04 2
wsl -l -v
```

Then continue with [Step 2](#step-2-install-required-system-packages).

## Step 2: Install Required System Packages

Update the package lists and install the build tools, compilers, numerical libraries and utilities:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y \
  build-essential gfortran cmake autoconf automake libtool git pkg-config \
  bison flex python3 python3-pip python3-venv \
  libopenblas-dev liblapack-dev libx11-dev freeglut3-dev wget curl unzip
```

These packages provide the compilers, build tools, BLAS/LAPACK, X11/OpenGL libraries needed by some
FreeFEM utilities, and the Python environment used by the regression suite (Python 3 with NumPy:
`python3 -m pip install numpy`). Check the core tools:

```bash
gcc --version
g++ --version
gfortran --version
python3 --version
git --version
```

Each command should print a version number. These commands install only system prerequisites.

## Step 3: Set Up FreeFEM with MPI and PETSc

### Option A: Container image (the tested environment)

The tested environment is the `freefem.sif` container image listed in the table above, run with
Apptainer or Singularity. Obtain or build an image that provides FreeFEM 4.12 with PETSc 3.18.2
and MPICH 4.0.2, and record its checksum:

```bash
sha256sum freefem.sif
```

Compare the result with the checksum in the tested-environment table. Run the solver through the
container with the launcher described in [Step 9](#step-9-running-dissolve-on-hpc-clusters-optional).

### Option B: Build from source (not tested for v1.1.0)

The commands below follow the FreeFEM 4.14 sources. They were **not** exercised for v1.1.0 and
may differ from the tested environment (FreeFEM 4.12, MPICH 4.0.2). FreeFEM's PETSc-enabled build
has additional steps that are documented in the FreeFEM repository for the release you check out;
follow those as well. After building, run the regression suite to confirm that your build is usable.

```bash
cd ~
git clone https://github.com/FreeFem/FreeFem-sources.git
cd FreeFem-sources
git checkout v4.14
autoreconf -i
./configure --enable-download --enable-optim
cd 3rdparty
./getall -a
cd ..
make -j$(nproc)
sudo make install
```

The build downloads and compiles PETSc and other third-party libraries and can take a long time.
If WSL2 runs out of memory while compiling PETSc, increase its memory allocation (8 GB or more is
recommended) in `.wslconfig`.

## Step 4: Check the FreeFEM Installation

These checks confirm that FreeFEM starts, MPI processes communicate and the plugins Dissolve™ loads
are present. **They do not verify the installation**: only the regression suite in
[Step 8](#step-8-run-the-regression-suite) does.

Check the FreeFEM version, which every FreeFEM run prints in its first line:

```bash
echo 'cout << "ok" << endl;' > /tmp/version.edp
FreeFem++-mpi -nw /tmp/version.edp
```

Expected first line (for the tested environment):

```text
-- FreeFem++ v4.12 (Wed Dec  7 13:22:45 UTC 2022 - git v4.12)
```

Check MPI communication with four processes:

```bash
cat > /tmp/test.edp << 'EOF'
cout << "rank " << mpirank << " of " << mpisize << endl;
EOF
mpirun -np 4 FreeFem++-mpi -nw /tmp/test.edp
```

Expected output (order may vary):

```text
rank 0 of 4
rank 1 of 4
rank 2 of 4
rank 3 of 4
```

Check that the plugins loaded by `config/dependencies.idp` are available:

```bash
cat > /tmp/test_plugins.edp << 'EOF'
load "PETSc"
load "msh3"
load "tetgen"
load "mshmet"
load "distance"
load "mmg"
load "medit"
cout << "All required plugins loaded successfully" << endl;
EOF
FreeFem++-mpi -nw /tmp/test_plugins.edp
```

Expected output:

```text
All required plugins loaded successfully
```

## Step 5: Obtain Dissolve™ (v1.1.0)

Check out the exact release so that your results can be traced to a defined version:

```bash
cd ~
git clone https://github.com/sanjukadupul-wq/Dissolve-1.0.git
cd Dissolve-1.0
git checkout v1.1.0
git describe --tags --always
```

Expected output of the last command:

```text
v1.1.0
```

Run the repository from the native Linux filesystem (for example `~/Dissolve-1.0`), not from a
Windows-mounted path such as `/mnt/c/...`, which can slow I/O considerably. The repository
contains:

```text
CHANGELOG.md
LICENSE
Mesh Generation/
README.md
Scripts/
Src Codes/
Third-Party Software/
```

The solver directory contains:

```text
Src Codes/
├── INSTALL.md
├── README.md
├── THEORY.md
├── VALIDATION.md
├── config/
├── dissolve.edp
├── domain/
├── io/
├── numerics/
├── physics/
├── state/
├── tests/
└── utils/
```

## Step 6: Obtain or Generate a Simulation Mesh

Dissolve™ requires a tetrahedral mesh in Medit `.mesh` format that defines the implant, the
surrounding medium, the material regions and the boundary labels. **No meshes are distributed with
the repository.** Generate your own with the tools in
[`Mesh Generation/`](../Mesh%20Generation/README.md), or use a compatible mesh from another source.
Examples in this guide use `/path/to/mesh.mesh` for a mesh that you have generated.

Generation has two stages: a geometry script in `Mesh Generation/<Geometry>/` writes a watertight STL
surface, and `Mesh Generation/stl_to_freefem_mesh.py` converts it into a tetrahedral mesh in a box
(`--box Lx Ly Lz`), labelling the region and the box faces (wall tag 3). The oxygen Dirichlet face is
the boundary with the tag given by `-tag_inlet` (default 4).

The mesh must be a valid tetrahedral Medit `.mesh` file with the region and boundary labels above.
Avoid spaces in mesh paths: FreeFEM's `getARGV` truncates string arguments at the first space.

## Step 7: Run a Dissolve™ Simulation

Run from the `Src Codes` directory so the relative `include` paths resolve. The v1.1.0 defaults are
`-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1`. The commands in this guide still give them
explicitly so that the recorded command line states the formulation used (see
[`README.md`](README.md#solver-modes)); the superseded probe-based formulation needs `-flux_first 0`:

```bash
cd ~/Dissolve-1.0/"Src Codes"
mpirun -np 4 FreeFem++-mpi -nw dissolve.edp -v 0 \
  -input_mesh /path/to/mesh.mesh \
  -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 \
  -dt_hours 4 -sim_duration 672 \
  -results_file output/result.txt
```

where `-np 4` sets the number of MPI processes, `FreeFem++-mpi` is the MPI-enabled FreeFEM
executable, `-nw` disables graphical output, `-v 0` reduces FreeFEM verbosity, `-dt_hours` is the time
step, `-sim_duration` the duration in hours (672 h = 28 days) and `-results_file` the main output file.
The material, kinetic and numerical parameters are listed in the
[command-line reference](README.md#command-line-reference). The reference configuration used for the
revised study (film barrier, calibrated kinetics, material inputs) is listed in
[`README.md`](README.md#reference-configuration-revised-study); replace `-input_mesh` with your own mesh.

Increase `-np` for larger meshes. To keep the console history:

```bash
mpirun -np 8 FreeFem++-mpi -nw dissolve.edp -v 0 \
  -input_mesh /path/to/mesh.mesh \
  -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 \
  -dt_hours 4 -sim_duration 672 \
  -results_file output/result.txt \
  > simulation.log 2>&1
```

Outputs are written to the folder of `-results_file`: `result.txt` (cut-cell mass loss), `mass_loss.txt`,
`global_balance.tsv`, `o2_interface_diag.tsv`, `mechanism_data.txt`, checkpoints, and (with
`-emit_vtk 1`) `.vtu` and `.pvd` files that ParaView can open. Check that disk space is sufficient
before long runs.

## Step 8: Run the Regression Suite

The regression suite is `Src Codes/tests/check.py`, driven by `Src Codes/tests/run_tests.sbatch`. It
runs short simulations in the flux-first mode and checks the Zn:O₂ balance, the closed-box oxygen cap,
the cut-cell and flux-integrated mass loss, the reinitialisation volume conservation, the projection
residuals, the flag guards, the zinc closure and the film-barrier option. All checks fail closed; the
suite prints `ALL PASS` and exits with code 0 only if every check passes. The tolerances are stated in
each check's output line. Run it after checkout and after any change to the software environment.

The suite needs two meshes that you generate yourself (none are distributed): a closed-box disc mesh
(a Ø10 × 2 mm disc in a 30 × 30 × 30 mm box, all six box faces tagged 3) and an open-top disc mesh
(the same, with the top face z = +15 mm tagged 4 as the oxygen inlet). The reported v1.1.0 results used
meshes of 3 902 vertices and 21 407 tetrahedra; their checksums are listed in the
[reproducibility checklist](#reproducibility-checklist). Python 3 with NumPy is required.

### Run locally

```bash
cd ~/Dissolve-1.0/"Src Codes"
export MESH=/path/to/closed_box_disc.mesh
export MESH_INLET=/path/to/open_top_disc.mesh
export FREEFEM_CMD="mpirun -np 4 FreeFem++-mpi -nw"
export OUT_DIR=$PWD/tests_out
bash tests/run_tests.sbatch
```

### Run through Slurm

```bash
cd ~/Dissolve-1.0/"Src Codes"
export SOLVER_DIR=$PWD
export MESH=/path/to/closed_box_disc.mesh
export MESH_INLET=/path/to/open_top_disc.mesh
export FREEFEM_SIF=/path/to/freefem.sif
export FREEFEM_BIND=/path/to/shared/filesystem
export OUT_DIR=/path/to/shared/filesystem/tests_out
sbatch --account=<account> --export=ALL tests/run_tests.sbatch
```

`SOLVER_DIR` must be set under Slurm because the batch script is copied to a spool directory. The job
writes `dissolve_tests_<jobid>.log` in the submission directory; the last lines are the check results
and `exit code 0` on success. `FREEFEM_CMD` can replace the whole launch command if your site uses
a different launcher.

## Step 9: Running Dissolve™ on HPC Clusters (Optional)

For large meshes and long simulations, run Dissolve™ under a batch scheduler. The launcher, module
names and container options are site-specific; use the MPI launcher your site supports.

**Native FreeFEM install.** Launch `FreeFem++-mpi` with your site's MPI launcher (`mpirun` or `srun`) from
inside a batch script, with the same arguments as in [Step 7](#step-7-run-a-dissolve-simulation).

**Container.** The host and the container each carry an MPI library, and they must be compatible: use
a launcher that starts the container's MPI ranks through a process-management interface the container
MPI supports. Do not start `mpirun` inside a container that is itself started by `mpirun` unless your
site documents that this works. The v1.1.0 tests used the Slurm launcher with PMI2 and the MPICH
bundled in the image. One Slurm example (adapt the account, paths and launcher to your site):

```bash
#!/bin/bash
#SBATCH --job-name=dissolve
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=24:00:00
#SBATCH --account=<account>
#SBATCH --output=dissolve_%j.out

module load singularity   # site-specific; omit if not needed

cd "$SLURM_SUBMIT_DIR/Src Codes"

srun --mpi=pmi2 singularity exec --bind /path/to/shared/filesystem /path/to/freefem.sif \
  FreeFem++-mpi -nw dissolve.edp -v 0 \
  -input_mesh /path/to/mesh.mesh \
  -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 \
  -dt_hours 4 -sim_duration 672 \
  -results_file /path/to/shared/filesystem/run1/result.txt
```

Submit and monitor:

```bash
sbatch run_dissolve.slurm
squeue -u $USER
scancel JOBID
```

| Mesh size | Suggested CPU cores | Memory |
|---|---|---|
| Small (< 0.5 M elements) | 4–8 | 8–16 GB |
| Medium (0.5–2 M elements) | 8–16 | 16–32 GB |
| Large (2–10 M elements) | 16–64 | 32–128 GB |
| Very large (> 10 M elements) | 64+ | 128 GB+ |

Requirements depend on geometry, duration, remeshing frequency and output settings. Parameter studies
can be run as Slurm job arrays (`#SBATCH --array=1-20`). Visualise results on a workstation, not on a
login node.

## Reproducibility Checklist

For every simulation or test campaign, record:

| Item | Value to record | v1.1.0 regression suite |
|---|---|---|
| Release | git tag and commit (`git describe --tags --always`, `git rev-parse HEAD`) | `v1.1.0` |
| Runtime parameters | the complete command line, including `-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1` and the film-barrier settings | regression suite: `tests/run_tests.sbatch`; revised study: `README.md`, reference configuration |
| Film barrier (revised study) | `-film_mech 1 -film_beta 12 -film_beta_couple 1 -film_beta_tau_ref 2 -film_beta_eps_ref 0.25 -film_thickness 0.001` | `-film_beta 0` and `12` in the film-barrier checks |
| Mesh | file name and `sha256sum` | closed box: `2479ec84ca978846b6912e279a926b79ae1b2a98aa9a1f91e85b6b0c1ca92dae`; open top: `7b7e2fde875e98eb288e7961f7c6c7abbc85fb9b7e4006bc9d7e90cd4521f129` |
| MPI processes | `-np` / `--ntasks` | 4 |
| FreeFEM | version | 4.12 |
| PETSc | version | 3.18.2 |
| MPI | implementation and version | MPICH 4.0.2 |
| Compiler | name and version | GCC 12.1.0 runtime libraries (build compiler not recorded) |
| Container | image and `sha256sum` | `14b627e77793ce0d3f615b072f65aec9368625b9609ce1e33f8fcbe255a10373` |
| Duration and time step | `-sim_duration`, `-dt_hours` | 168 h, 4 h |

## Next Steps

Once Dissolve™ runs, consult:

- [`README.md`](README.md) for solver modes and the command-line reference
- [`THEORY.md`](THEORY.md) for the governing equations and numerical methods
- [`VALIDATION.md`](VALIDATION.md) for verification results and known limitations
- [`../Mesh Generation/`](../Mesh%20Generation/README.md) for creating implant geometries
- [`../Scripts/`](../Scripts/README.md) for parameter-identification workflows

The installation is ready for research simulations once the regression suite passes.

## Troubleshooting

| Issue | Possible cause | Solution |
|---|---|---|
| `FreeFem++-mpi: command not found` | FreeFEM is not installed or is not on `PATH`. | Check the installation and run `which FreeFem++-mpi`. |
| `mpirun: command not found` | No MPI launcher is on `PATH`. | Load your MPI module or use your site's launcher (for example `srun`). |
| MPI job hangs with no output | Host and container MPI are incompatible, or the MPI runtime differs from the one FreeFEM was built with. | Use a launcher compatible with the MPI in the image (see Step 9); do not mix MPI implementations. |
| `load "PETSc"` fails | PETSc was not built or is not found by FreeFEM. | Rebuild FreeFEM with PETSc following the FreeFEM documentation, or use the container image. |
| `load "mmg"` or `load "tetgen"` fails | The plugin was not built. | Rebuild FreeFEM with its third-party libraries. |
| Mesh file cannot be found | Wrong path or filename. | Check the path given to `-input_mesh`. |
| Simulation stops immediately | Invalid mesh or missing labels. | Check that the mesh is a tetrahedral Medit `.mesh` with the region and boundary labels of Step 6. |
| `getARGV` does not read the full path | Path contains spaces. | Rename directories or files to avoid spaces. |
| `ERROR_FLUXFIRST_REQUIRES_V_PICARD_0` | `-flux_first 1` (the default) was combined with `-v_picard` ≠ 0. | Remove `-v_picard`, or give `-v_picard 0`; use `-flux_first 0` only for the superseded path. |
| `ERROR_FLUXFIRST_REQUIRES_O2_AND_CONSERVATIVE_MODE_2` | `-flux_first 1` with `-conservative` ≠ 2 or without the oxygen equation. | Use `-conservative 2` and keep the oxygen equation enabled. |
| `ERROR_FLUXFIRST_PROJECTION_BALANCE` | The projected zinc flux differs from the oxygen sink by more than `-flux_proj_tol` (default 1e-4), which happens with a coarse mesh and the `β` = 12 film barrier (residual 1.2×10⁻⁴ on the 3 900-vertex test mesh). | Refine the mesh, or give `-flux_proj_tol 1e-3` (the flux is rescaled exactly afterwards) and report the value used. |
| Very slow I/O | Repository on a Windows-mounted path under WSL. | Move the repository into the native Linux filesystem. |
| Out-of-memory error | Mesh too large for the available memory. | Use more memory, a coarser mesh or more nodes. |
| No `.vtu` or `.pvd` files | `-emit_vtk 1` was not given, or the run ended early. | Add `-emit_vtk 1` and check the log. |
