import dotenv
import os
import json
import matplotlib.pyplot as plt  # noqa: E402
import nibabel as nib
import numpy as np
from pathlib import Path
from scipy import stats
from tempfile import TemporaryDirectory
import random

from run_msm import run_msm

dotenv.load_dotenv()
FSL_PATH = os.getenv("FSL_PATH")


def is_same_coordsys(c1, c2):
    return (c1.dataspace == c2.dataspace and c1.xformspace == c2.xformspace
            and np.all(c1.xform == c2.xform))


def prepare_darrays(darrays, coordsys):
    for d in darrays:
        d.data = d.data.astype(np.float32)
        d.datatype = nib.nifti1.data_type_codes.code['NIFTI_TYPE_FLOAT32']
        d.intent = nib.nifti1.intent_codes.code['NIFTI_INTENT_POINTSET']
        if (d.coordsys is not None
                and not is_same_coordsys(d.coordsys, coordsys)):
            raise ValueError(
                "Provided data is in different coordsys than the mesh."
            )
        d.coordsys = coordsys

    return darrays


# Load spherical mesh produced with `mris_convert`
spherical_mesh = './data/lh.sphere.gii'

# load data
subject_input = 'sub-07'
subject_reference = 'sub-04'
data_path = './data/'

#parameters
random.seed(42)
lambd = [0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1]
new_split = False # if true, a new split will be created, if false, data will be loaded
train_mode = False #if true will run MSM, if false will use an existing run_MSM output

# data - dictionary of type: input_fname -> reference_fname

data = {}

data_input = [
    os.path.join(data_path, file)
    for file in os.listdir(data_path)
    if subject_input in file and 'lh' in file and (
        'ses-00' in file or 'ses-01' in file or 'ses-02' in file or 'ses-04' in file
    )
]

data_reference = [
    os.path.join(data_path, file)
    for file in os.listdir(data_path)
    if subject_reference in file and 'lh' in file and (
        'ses-00' in file or 'ses-01' in file or 'ses-02' in file or 'ses-04' in file
    )
]

for input_fname in data_input:
    for reference_fname in data_reference:
        if reference_fname.split(subject_reference)[1] == input_fname.split(subject_input)[1]:
            data[input_fname] = reference_fname

print(len(data))
# split data to train and test

if new_split:
    train_data_input = random.sample(list(data.keys()), int(len(data)*0.8))

    train_data = {
        input_fname : data[input_fname]
        for input_fname in train_data_input
    }

    test_data = {
        input_fname : data[input_fname]
        for input_fname in list(data.keys())
        if input_fname not in train_data_input
    }

    with open("train.json", "w") as outfile:
        json.dump(train_data, outfile)

    with open("test.json", "w") as outfile:
        json.dump(test_data, outfile)
else:
    train_data_fname = "train.json"
    test_data_fname = "test.json"
    with open(train_data_fname) as json_file:
        train_data = json.load(json_file)

    with open(test_data_fname) as json_file:
        test_data = json.load(json_file)

epsilons = [0.01, 0.1, 1, 10, 100, 1000]

cross_correlation = {}
base_cross_correlation = {} # cross-correlation without deformation

for epsilon in epsilons:

    #replacing lambda values in config file
    with open(f"{FSL_PATH}/config/basic_configs/config_standard_MSM_strain", "r") as f:
        list_of_lines = f.readlines()
        list_of_lines[3] = f"--lambda={epsilon},{epsilon},{epsilon},{epsilon}\n"

    with open(f"{FSL_PATH}/config/basic_configs/config_standard_MSM_strain", "w") as f:
        f.writelines(list_of_lines)

    #running MSM with train data
    if train_mode:
        transformed_mesh, transformed_func = run_msm(
            in_data_list=list(train_data.keys()), in_mesh=spherical_mesh,
            ref_data_list=list(train_data.values()),
            debug=False, verbose=True, output_dir='test_outputs_lambda' + str(epsilon)
        )

    #testing MSM with test data

    with TemporaryDirectory(prefix='./') as dir_name:
        dir_name = 'test_outputs_lambda' + str(epsilon)
        deformed = os.path.join(dir_name, "transformed_in_mesh.surf.gii")
        cross_correlation[epsilon] = 0
        base_cross_correlation[epsilon] = 0
        # Load the coordsys from the mesh associated to the data to make
        # sure it is well specified
        mesh = nib.load(spherical_mesh)
        coordsys = mesh.darrays[0].coordsys

        for input_fname, reference_fname in test_data.items():
            data_input = nib.load(input_fname)
            data_input.darrays = prepare_darrays(data_input.darrays, coordsys)
            extra_data = nib.load(input_fname) # copy dataset in order to cope with a bug of MSM
            data_input.darrays.extend(prepare_darrays(
                extra_data.darrays, coordsys
            ))
            filename = str(Path(dir_name) / 'input_test.func.gii')
            data_input.to_filename(filename)
            input_fname_preprocessed = filename

            test_transformed = os.path.join(dir_name, "test_transformed_and_projected" + input_fname.split(subject_input)[1])
            cmd = ' '.join([
            f"{FSL_PATH}/bin/msmresample",
            f"{deformed} ",
            test_transformed,
            f"-labels {input_fname_preprocessed} ",
            f"-project {spherical_mesh}",
            ])
            exit_code = os.system(cmd)
            if exit_code != 0:
                raise RuntimeError(f"Failed to run MSM with command:\n{cmd}")

            #compute cross_correlation
            transformed_data = nib.load(test_transformed+".func.gii")
            transformed_data.darrays = prepare_darrays(transformed_data.darrays, coordsys)
            data_reference = nib.load(reference_fname)
            data_reference.darrays = prepare_darrays(data_reference.darrays, coordsys)

            cross_correlation[epsilon] += stats.pearsonr(transformed_data.darrays[0].data, data_reference.darrays[0].data)[0]/len(test_data)
            base_cross_correlation[epsilon] += stats.pearsonr(data_input.darrays[0].data, data_reference.darrays[0].data)[0]/len(test_data)

print(cross_correlation)
print(base_cross_correlation)
plt.xlabel("Lambda")
plt.ylabel("Pearson correlation")
plt.title("Test data")
plt.semilogx(epsilons, list(cross_correlation.values()), label = "Cross-correlation after transformation")
plt.semilogx(epsilons, list(base_cross_correlation.values()), label = "Cross-correlation before transformation")
plt.legend()
plt.savefig("lambda_optimization_test_data.png")