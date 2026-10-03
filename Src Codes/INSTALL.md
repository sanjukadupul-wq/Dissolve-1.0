# Building and Running Dissolve™

## Overview

Dissolve™ requires FreeFEM 4.14 built with MPI and PETSc support. The solver was
developed, validated, and benchmarked using a Linux-based software stack consisting of
FreeFEM, OpenMPI, PETSc, Slurm, and Apptainer. While FreeFEM can be installed on native
Windows, the recommended platform for Windows users is Windows Subsystem for Linux 2
(WSL2), which provides a full Linux environment with the OpenMPI toolchain used
throughout Dissolve™ development and testing. Using WSL2 ensures maximum compatibility
with FreeFEM's parallel execution framework, simplifies PETSc installation, and closely
reproduces the environment used for validation and large-scale HPC simulations.

This guide therefore installs and runs Dissolve™ entirely within WSL2 using Ubuntu
22.04 LTS. If you are already using Linux, macOS, or have access to an HPC cluster, you
may skip directly to [Step 3](#step-3-build-freefem-414-with-mpi-and-petsc-support).

## Step 1: Install WSL2 (Windows Users)

For Windows users, the recommended installation method is Windows Subsystem for Linux
2 (WSL2) with Ubuntu 22.04 LTS, which provides a Linux environment closely matching the
platform used for development, validation, and HPC deployment.

Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu-22.04
```

Restart your computer if prompted.

After installation:

1. Launch Ubuntu 22.04 LTS from the Start Menu.
2. Complete the first-time setup by creating a Linux username and password.
3. Verify that Ubuntu is running under WSL2:

```powershell
wsl -l -v
```

Expected output:

```text
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
```

If Ubuntu reports `VERSION 1`, convert it to WSL2:

```powershell
wsl --set-version Ubuntu-22.04 2
```

Verify the conversion — the system should now report `VERSION 2`:

```powershell
wsl -l -v
```

**Note:** WSL2 is strongly recommended because it provides a Linux/OpenMPI environment
that closely matches the platform used throughout Dissolve™ development and
validation, ensuring maximum compatibility with FreeFEM's MPI and PETSc workflows.

Once WSL2 and Ubuntu 22.04 are installed and configured, proceed to
[Step 2](#step-2-install-required-system-packages).

## Step 2: Install Required System Packages

Once Ubuntu 22.04 is installed under WSL2, install the development tools and libraries
required to build FreeFEM and its dependencies.

Update the package lists and existing packages:

```bash
sudo apt update
sudo apt upgrade -y
```

Install the required build tools, compilers, numerical libraries, and utilities:

```bash
sudo apt install -y \
  build-essential \
  gfortran \
  cmake \
  autoconf \
  automake \
  libtool \
  git \
  pkg-config \
  bison \
  flex \
  python3 \
  python3-pip \
  python3-venv \
  libopenblas-dev \
  liblapack-dev \
  libx11-dev \
  freeglut3-dev \
  wget \
  curl \
  unzip
```

These packages provide:

- **Build tools:** GCC, G++, Make, Autotools, CMake
- **Fortran compiler:** required by PETSc and scientific libraries
- **Python environment:** used for calibration, data processing, and utility scripts
- **BLAS/LAPACK:** high-performance linear algebra libraries used by FreeFEM and PETSc
- **X11/OpenGL libraries:** required by some FreeFEM visualization and mesh utilities
- **Git, wget, curl:** used to download and manage source code and dependencies

Verify that the core tools were installed correctly:

```bash
gcc --version
g++ --version
gfortran --version
python3 --version
git --version
```

Each command should return a version number without errors.

**Note:** The commands above install only the system prerequisites. OpenMPI, PETSc,
SLEPc, TetGen, MMG, Mshmet, and Medit will be automatically downloaded and built as
part of the FreeFEM installation in Step 3.

Proceed to [Step 3](#step-3-build-freefem-414-with-mpi-and-petsc-support).

## Step 3: Build FreeFEM 4.14 with MPI and PETSc Support

Dissolve™ was developed and validated using FreeFEM v4.14 with MPI and PETSc enabled.
The recommended approach is to build FreeFEM from source, allowing FreeFEM to download
and configure a compatible collection of scientific computing libraries, including
PETSc, SLEPc, OpenMPI, and the meshing utilities required by Dissolve™.

Navigate to your home directory and clone the FreeFEM source repository:

```bash
cd ~
git clone https://github.com/FreeFem/FreeFem-sources.git
cd FreeFem-sources
```

Checkout the version used during Dissolve™ development and validation:

```bash
git checkout v4.14
```

Generate the build configuration files:

```bash
autoreconf -i
```

Configure the build:

```bash
./configure \
  --enable-download \
  --enable-optim
```

The configuration options above instruct FreeFEM to:

- Download required third-party dependencies automatically.
- Enable optimized compilation for improved solver performance.

Next, download the external numerical libraries and mesh-generation tools:

```bash
cd 3rdparty
./getall -a
cd ..
```

This command retrieves and prepares the major dependencies used by Dissolve™,
including:

- OpenMPI
- PETSc
- SLEPc
- TetGen
- MMG (mmg3d/mmgs)
- Mshmet
- Medit

Compile FreeFEM and all associated components:

```bash
make -j$(nproc)
```

Once compilation finishes successfully, install FreeFEM system-wide:

```bash
sudo make install
```

**Note:** The build process may take a considerable amount of time depending on your
hardware configuration, as PETSc and related scientific computing libraries are
compiled from source.

### Installed Components

A successful build provides:

- FreeFem++
- FreeFem++-mpi
- PETSc-enabled parallel solvers
- MPI support through OpenMPI
- TetGen mesh-generation capabilities
- MMG adaptive remeshing
- Mshmet mesh metrics
- Medit mesh utilities

No separate installation of these tools is required.

### Version Compatibility

Dissolve™ has been tested with:

```text
FreeFEM 4.14
OpenMPI (FreeFEM bundled build)
PETSc (FreeFEM bundled build)
```

Using newer releases may work, but users seeking exact reproducibility should build
against FreeFEM v4.14. FreeFEM's build tooling changes between releases — if a flag
above doesn't exist in the version you check out, check that checkout's own
`INSTALL.md`/README for the current equivalent.

After installation completes successfully, proceed to
[Step 4](#step-4-verify-the-installation).

## Step 4: Verify the Installation

Before running Dissolve™, verify that FreeFEM, MPI, and PETSc were installed correctly
and that parallel execution is functioning as expected.

### Verify FreeFEM Installation

Check that the serial and MPI-enabled FreeFEM executables are available:

```bash
FreeFem++ -v
FreeFem++-mpi -v
```

Both commands should report the installed FreeFEM version without errors.

### Verify MPI Installation

Confirm that OpenMPI is available:

```bash
mpirun --version
```

The command should display the installed OpenMPI version.

### Test Parallel Execution

Create a simple FreeFEM script to verify MPI communication:

```bash
cat > /tmp/test.edp << 'EOF'
mpiComm comm(mpiCommWorld,0,0);
cout << "rank " << mpirank << " of " << mpisize << endl;
EOF
```

Run the script across four MPI processes:

```bash
mpirun -np 4 FreeFem++-mpi -nw /tmp/test.edp
```

Expected output (order may vary, but four ranks should be reported):

```text
rank 0 of 4
rank 1 of 4
rank 2 of 4
rank 3 of 4
```

### Verify PETSc Support

PETSc is required by Dissolve™ for parallel linear and nonlinear solver operations.
Confirm that the PETSc plugin loads successfully:

```bash
echo 'load "PETSc"; cout << "PETSc loaded successfully" << endl;' > /tmp/test_petsc.edp
FreeFem++-mpi -nw /tmp/test_petsc.edp
```

Expected output:

```text
PETSc loaded successfully
```

### Verify Required Dissolve™ Plugins

Dissolve™ relies on several FreeFEM plugins. Create a simple test:

```bash
cat > /tmp/test_plugins.edp << 'EOF'
load "msh3"
load "PETSc"
load "mmg"
load "tetgen"
cout << "All required plugins loaded successfully" << endl;
EOF

FreeFem++-mpi -nw /tmp/test_plugins.edp
```

Expected output:

```text
All required plugins loaded successfully
```

### Installation Complete

If all tests complete successfully, your system is ready to run Dissolve™. Proceed to
[Step 5](#step-5-obtain-dissolve-and-prepare-the-working-environment).

## Step 5: Obtain Dissolve™ and Prepare the Working Environment

Once FreeFEM, MPI, and PETSc have been successfully installed and verified, download
the Dissolve™ repository and place it in a location suitable for simulation workloads.

### Clone the Repository

Inside your WSL2 Ubuntu terminal:

```bash
cd ~
git clone https://github.com/sanjukadupul-wq/Dissolve-1.0.git
cd Dissolve-1.0
```

Verify that the repository was downloaded correctly:

```bash
ls
```

You should see the main project directories, including:

```text
Src Codes/
Mesh Generation/
Calibration/
Results/
Third-Party Software/
```

### Recommended Repository Location

For best performance, store and run Dissolve™ from the native Linux filesystem inside
WSL2, not through a Windows-mounted drive — large simulation meshes, VTK outputs,
checkpoints, and intermediate files can generate significant disk I/O, and running
directly from Windows-mounted paths may reduce performance.

**Recommended:**
```text
/home/<username>/Dissolve-1.0
```

**Not recommended:**
```text
/mnt/c/Users/<username>/Documents/Dissolve-1.0
```

### Copying an Existing Windows Checkout

If you already downloaded the repository on the Windows side, copy it into the Linux
filesystem rather than running directly from `/mnt/c`:

```bash
cp -r "/mnt/c/path/to/Dissolve-1.0" ~/Dissolve-1.0
cd ~/Dissolve-1.0
```

### Verify the Solver Directory

Navigate to the solver folder:

```bash
cd "Src Codes"
ls
```

You should see:

```text
dissolve.edp
config/
domain/
state/
physics/
numerics/
io/
utils/
```

### Verify Repository Permissions

Ensure the repository is readable and writable by your Linux user:

```bash
chmod -R u+rw ~/Dissolve-1.0
```

### Ready for Simulation Setup

At this point:

- ✅ WSL2 is installed
- ✅ Required packages are installed
- ✅ FreeFEM 4.14 is built with MPI and PETSc support
- ✅ MPI and PETSc have been verified
- ✅ Dissolve™ has been downloaded and configured

Proceed to [Step 6](#step-6-obtain-or-generate-a-simulation-mesh).

## Step 6: Obtain or Generate a Simulation Mesh

Dissolve™ requires a tetrahedral finite-element mesh in Medit `.mesh` format. This mesh
defines the implant geometry, surrounding physiological domain, material regions, and
boundary labels used by the solver.

To keep the repository lightweight, pre-generated meshes are not distributed. Users may
either generate meshes using the workflows provided in `Mesh Generation/` or use
compatible `.mesh` files from an external source.

### Option A: Generate a Mesh Using the Included Workflows

The repository contains scripts used to generate the geometries and meshes employed
during solver development and validation.

From the repository root:

```bash
cd ~/Dissolve-1.0/"Mesh Generation"
```

The workflow consists of two stages:

**1. Generate Geometry** — create a watertight STL surface for the desired implant
architecture, such as:

- Cylinders and discs
- Gyroid TPMS structures
- Schwarz-P TPMS structures
- BCC lattices
- FCC lattices

The geometry-generation scripts are located one per geometry in `Mesh Generation/`
(e.g. `Mesh Generation/Gyroid/gyroid_generator.py`, `Mesh Generation/BCC/bcc_generator.py`).
These scripts generate STL surfaces from implicit geometry definitions and porosity
specifications. The resulting output is a file such as `geometry.stl`.

**2. Convert STL to a Simulation Mesh** — once the STL geometry has been generated, use
`Mesh Generation/stl_to_freefem_mesh.py` (shared across every geometry) to convert the
STL surface into a tetrahedral mesh suitable for Dissolve™. The conversion process:

1. Generates a volumetric tetrahedral mesh.
2. Assigns material regions.
3. Applies boundary labels required by the solver.
4. Exports the final mesh in Medit format.

Example output: `gyroid70.mesh`.

### Option B: Use an Existing Mesh

If you already have a compatible Dissolve™ mesh, note its location — for example
`/home/user/meshes/gyroid70.mesh` or `~/Dissolve-1.0/Meshes/gyroid70.mesh`.

### Mesh Requirements

The input mesh must:

- Be in Medit `.mesh` format
- Contain a valid tetrahedral volume mesh
- Include the required region labels
- Include the required boundary labels
- Be readable by FreeFEM's `mesh3` functionality

### Mesh Path Guidelines

Avoid spaces in mesh file names and directory paths — some command-line arguments and
FreeFEM input parsing routines may not correctly handle paths containing spaces.

**Recommended:** `~/Dissolve-1.0/Meshes/gyroid70.mesh`
**Not recommended:** `~/Dissolve-1.0/My Meshes/Gyroid 70.mesh`

### Verify the Mesh

Before running a simulation, confirm the mesh exists:

```bash
ls -lh ~/Dissolve-1.0/Meshes/gyroid70.mesh
```

You should see the file size and location reported without errors.

Once a valid `.mesh` file is available, Dissolve™ is ready to perform a degradation
simulation. Proceed to [Step 7](#step-7-run-a-dissolve-simulation).

## Step 7: Run a Dissolve™ Simulation

With FreeFEM, MPI, PETSc, and a valid simulation mesh in place, you are now ready to
run Dissolve™.

Navigate to the solver directory:

```bash
cd ~/Dissolve-1.0/"Src Codes"
```

### Basic Simulation

Launch a degradation simulation using four MPI processes:

```bash
mpirun -np 4 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672
```

where:

- `-np 4` specifies the number of MPI processes.
- `FreeFem++-mpi` launches the MPI-enabled FreeFEM executable.
- `-nw` disables graphical output.
- `dissolve.edp` is the main Dissolve™ solver.
- `-input_mesh` specifies the simulation mesh.
- `-sim_duration` specifies the simulation time in hours.

In this example, 672 hours = 28 days, which corresponds to the standard immersion
duration used for many degradation studies.

### Using Additional CPU Cores

For larger meshes and longer simulations, increase the number of MPI processes:

```bash
mpirun -np 8 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672
```

or

```bash
mpirun -np 16 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672
```

The optimal number of processes depends on available CPU cores, mesh size, available
memory, and system architecture.

### Monitoring the Simulation

During execution, Dissolve™ writes progress information to the terminal, including
current simulation time, iteration counts, solver convergence information, mass-loss
calculations, and output generation status.

For long simulations, it is often useful to save the console output:

```bash
mpirun -np 8 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672 \
  > simulation.log 2>&1
```

This creates `simulation.log`, containing the complete simulation history.

### Output Files

Simulation results are automatically written to the configured output directory.
Typical outputs include concentration fields, corrosion-product distributions,
level-set fields, evolving degradation geometries, mass-loss histories, and VTK
visualization files, in formats including `.vtu`, `.pvd`, `.csv`, and `.txt`, depending
on the solver configuration.

### Visualizing Results

VTK outputs can be viewed using ParaView. Launch ParaView and open the generated
`.pvd` or `.vtu` file. Common visualizations include degradation morphology evolution,
oxygen concentration fields, Zn²⁺ distributions, corrosion-product accumulation,
surface recession, and interface evolution.

### Reproducing the Validated Configuration

Dissolve™ provides a validated configuration used for calibration and benchmarking
studies. Refer to [`Src Codes/README.md`](README.md) for the complete list of
recommended runtime parameters and simulation settings. When reproducing a benchmark
case, use the documented parameter set and simply replace `-input_mesh` with the
location of your own mesh file.

### Important Notes

- Use paths without spaces whenever possible.
- Ensure sufficient disk space for large simulations.
- Larger meshes can generate substantial output files.
- For large-scale studies, execution on a multi-core workstation or HPC cluster is
  recommended.

If the simulation starts successfully and begins reporting solver progress, your
Dissolve™ installation is complete and ready for production use.

Proceed to [Step 8](#step-8-running-dissolve-on-hpc-clusters-optional) (optional).

## Step 8: Running Dissolve™ on HPC Clusters (Optional)

For large implant geometries, high-resolution meshes, parameter studies, and long
degradation simulations, Dissolve™ is designed to run efficiently on High-Performance
Computing (HPC) systems using MPI-based parallel execution. The validated production
simulations used during Dissolve™ development were executed on Linux HPC environments
using OpenMPI, Slurm, and Apptainer/Singularity.

### HPC Requirements

A typical HPC deployment requires:

- Linux compute nodes
- Slurm workload manager
- OpenMPI
- FreeFEM 4.14 with PETSc support
- Shared filesystem accessible from compute nodes
- Apptainer/Singularity (recommended)

### Running Directly on a Cluster

If FreeFEM has been installed natively on the cluster, submit Dissolve™ using a Slurm
batch script. Create a file called `run_dissolve.slurm` with the following contents:

```bash
#!/bin/bash
#SBATCH --job-name=dissolve
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=24:00:00
#SBATCH --output=dissolve_%j.out
#SBATCH --error=dissolve_%j.err

module load openmpi

cd $SLURM_SUBMIT_DIR

mpirun -np 16 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672
```

Submit the job:

```bash
sbatch run_dissolve.slurm
```

### Monitoring Jobs

View queued and running jobs:

```bash
squeue -u $USER
```

Inspect completed job output, e.g.:

```bash
cat dissolve_12345.out
```

Cancel a running job:

```bash
scancel JOBID
```

### Using Apptainer/Singularity

Containerized execution is recommended when installing software on compute nodes is
restricted, reproducibility across systems is required, or multiple users share the
cluster.

Build or obtain a FreeFEM container image (`freefem.sif`), then run Dissolve™ inside
the container:

```bash
apptainer exec freefem.sif \
  mpirun -np 16 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672
```

### Resource Recommendations

| Mesh Size | Recommended CPU Cores | Memory |
|---|---|---|
| Small (< 0.5 M elements) | 4–8 | 8–16 GB |
| Medium (0.5–2 M elements) | 8–16 | 16–32 GB |
| Large (2–10 M elements) | 16–64 | 32–128 GB |
| Very Large (> 10 M elements) | 64+ | 128 GB+ |

Actual requirements depend on geometry complexity, simulation duration, adaptive
remeshing frequency, and output settings.

### Parameter Studies and Batch Simulations

HPC environments are particularly useful for porosity sweeps, geometry comparisons,
kinetic parameter calibration, sensitivity analyses, mesh convergence studies, and
design optimization workflows. Large simulation campaigns can be automated through
Slurm job arrays, e.g.:

```bash
#SBATCH --array=1-20
```

allowing multiple Dissolve™ simulations to run simultaneously with different input
parameters.

### Output Management

Large HPC studies may generate substantial data volumes. Recommended practices:

- Compress archived outputs after completion.
- Store meshes separately from simulation results.
- Periodically remove temporary files.
- Transfer only processed results when downloading to local machines.

Visualization should generally be performed after the simulation completes using
ParaView on a workstation rather than on cluster login nodes.

### Reproducibility

For maximum reproducibility, record: FreeFEM version, PETSc version, number of MPI
processes, input mesh, simulation duration, runtime parameters, and the git commit
hash of the Dissolve™ repository. This information allows simulations to be reproduced
and compared across systems and future software releases.

## Next Steps

Once Dissolve™ is running successfully on either a workstation or HPC system, consult:

- [`../README.md`](../README.md) for solver configuration options
- [`THEORY.md`](THEORY.md) for the governing equations and numerical methods
- [`../Mesh Generation/`](../Mesh%20Generation/) for creating new implant geometries
- [`../Calibration/`](../Calibration/) for parameter identification workflows
- [`../Results/`](../Results/) for example benchmark datasets

Your Dissolve™ installation is now fully configured and ready for degradation
simulation studies.

## Troubleshooting

| Issue | Possible Cause | Solution |
|---|---|---|
| `FreeFem++-mpi: command not found` | FreeFEM was not installed successfully or is not on the system `PATH`. | Verify the FreeFEM build completed successfully and run `which FreeFem++-mpi`. Reinstall if necessary. |
| `mpirun: command not found` | OpenMPI was not installed correctly. | Verify the FreeFEM dependency installation completed successfully and check `mpirun --version`. |
| MPI job hangs with no output | MPI runtime mismatch or incorrect OpenMPI configuration. | Ensure the OpenMPI installation used at runtime matches the one built with FreeFEM. Verify using `mpirun --version` and rebuild FreeFEM if necessary. |
| `load "PETSc"` fails | PETSc was not compiled or installed correctly during the FreeFEM build. | Re-run `cd 3rdparty && ./getall -a` followed by `make -j$(nproc)` and `sudo make install`. |
| `load "mmg"` fails | MMG plugin was not built successfully. | Rebuild FreeFEM and verify that the MMG dependencies were downloaded during `./getall -a`. |
| `load "tetgen"` fails | TetGen plugin is missing from the FreeFEM installation. | Rebuild FreeFEM with all third-party dependencies enabled and verify plugin installation. |
| Mesh file cannot be found | Incorrect mesh path or filename. | Verify the path supplied to `-input_mesh` exists and is accessible. |
| Simulation stops immediately after startup | Invalid mesh, missing labels, or incompatible geometry. | Verify the mesh was generated using the approved Dissolve™ mesh-generation workflow. |
| Error reading mesh file | Unsupported format or corrupted mesh. | Ensure the input file is a valid Medit `.mesh` file. |
| `getARGV` does not read the full path | Path contains spaces. | Rename directories or files to avoid spaces. |
| Very slow mesh loading or output writing | Repository is being executed from `/mnt/c/...` in WSL. | Move the repository into the native Linux filesystem (e.g., `~/Dissolve-1.0`). |
| Build fails while compiling PETSc | Insufficient memory available to WSL2. | Increase WSL memory allocation (8 GB or more recommended) through `.wslconfig` and rebuild. |
| FreeFEM build terminates unexpectedly | Missing system packages or interrupted downloads. | Repeat Steps 2 and 3 and ensure all system dependencies are installed. |
| Simulation runs extremely slowly | Mesh too large for available resources or insufficient MPI processes. | Use additional CPU cores, reduce mesh resolution, or execute on an HPC cluster. |
| Out-of-memory error during simulation | Large mesh size or insufficient RAM. | Increase available memory, reduce mesh resolution, or increase HPC resources. |
| No `.vtu` or `.pvd` output files appear | Simulation terminated early or output directory is incorrect. | Check terminal output and log files for errors and verify output paths. |
| ParaView cannot open result files | Incomplete simulation output or corrupted files. | Verify the simulation completed successfully and regenerate the outputs. |
