print("Importing nilearn...")
from nilearn import plotting

# Load spherical mesh produced with `mris_convert`
print("Reading data...")
spherical_mesh = './data/lh.sphere.gii'


data_to_load = {
    'sub-07': [
        './data/sub-07_story-math_lh.gii',
        './data/sub-07_relational_lh.gii',
    ],
    'sub-04': [
        './data/sub-04_story-math_lh.gii',
        './data/sub-04_relational_lh.gii',
    ]
}

transformed_mesh = '/mnt/e/Ecole Polytechnique/Parietal/code/msm_on_ibc/test_outputs/transformed_in_mesh.surf.gii'
transformed_func = "/mnt/e/Ecole Polytechnique/Parietal/code/msm_on_ibc/test_outputs/transformed_and_reprojected.func.gii"


##################
# plotting
import matplotlib.pyplot as plt  # noqa: E402

print("Plotting transformed data...")
plotting.plot_surf(
    './data/lh.sphere',
    transformed_func, title='Transformed Data - relational',
    cmap="RdBu"
)
plt.savefig('./transformed_relational.png')


print("Plotting origin data...")
plotting.plot_surf(
    './data/lh.sphere',
    data_to_load['sub-04'][1],
    title='Origin Data - relational',
    cmap="RdBu"
)
plt.savefig('./origin_relational.png')

print("Plotting reference data...")
plotting.plot_surf(
    './data/lh.sphere',
    data_to_load['sub-07'][1],
    title='Reference Data - relational',
    cmap="RdBu"
)
plt.savefig('./reference_relational.png')