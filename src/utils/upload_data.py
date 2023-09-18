import pandas as pd
import torch
from scipy.sparse import coo_matrix
from src.utils.generate_synthetic_data import *

# upload the ihdp data
def upload_ihdp(dir):
    # IHDP
    names=['treatment', 'y_factual', 'y_cfactual', 'mu0', 'mu1', 'x1','x2','x3','x4','x5','x6','x7','x8','x9','x10','x11','x12','x13','x14','x15','x16','x17','x18','x19','x20','x21','x22','x23','x24','x25']
    features_ihdp = ['x1','x2','x3','x4','x5','x6','x7','x8','x9','x10','x11','x12','x13','x14','x15','x16','x17','x18','x19','x20','x21','x22','x23','x24','x25']
    ihdp = pd.read_csv(dir,header=0,names=names)
    ihdp_t = torch.tensor(ihdp['treatment'].values,dtype=torch.float32)
    ihdp_y = torch.tensor(ihdp['y_factual'].values,dtype=torch.float32)
    ihdp_ycf = torch.tensor(ihdp['y_cfactual'].values,dtype=torch.float32)
    ihdp_mu0 = torch.tensor(ihdp['mu0'].values,dtype=torch.float32)
    ihdp_mu1 = torch.tensor(ihdp['mu1'].values,dtype=torch.float32)
    ihdp_X = torch.tensor(ihdp[features_ihdp].values,dtype=torch.float32)


    ihdp_y1 = torch.zeros_like(ihdp_y)
    ihdp_y1[ihdp_t==1] = ihdp_y[ihdp_t==1]
    ihdp_y1[ihdp_t==0] = ihdp_ycf[ihdp_t==0]

    ihdp_y0 = torch.zeros_like(ihdp_y)
    ihdp_y0[ihdp_t==1] = ihdp_ycf[ihdp_t==1]
    ihdp_y0[ihdp_t==0] = ihdp_y[ihdp_t==0]
    return ihdp_X,ihdp_t,ihdp_y,ihdp_y0,ihdp_y1,ihdp_mu0,ihdp_mu1


# logistic function that we will need for the twins data
def logistic(z):
    return 1 / (1 + np.exp(-z))
    
# upload the twins data
def upload_twins(data_folder, device):
    # Read CSVs
    twins_X_path = f'{data_folder}/twins/twin_pairs_X_3years_samesex.csv'
    twins_T_path = f'{data_folder}/twins/twin_pairs_T_3years_samesex.csv'
    twins_Y_path = f'{data_folder}/twins/twin_pairs_Y_3years_samesex.csv'
    
    twins_X = pd.read_csv(twins_X_path)
    twins_T = pd.read_csv(twins_T_path)
    twins_Y = pd.read_csv(twins_Y_path)

    # Pre-processing
    col = ['meduc6','data_year', 'nprevistq', 'dfageq', 'feduc6','infant_id_0','infant_id_1','dlivord_min','dtotord_min','bord_0','bord_1']
    twins_X = twins_X.drop(col, axis=1)
    twins_T = twins_T.drop('Unnamed: 0', axis=1)
    twins_Y = twins_Y.drop('Unnamed: 0', axis=1)
    dataframe = pd.concat([twins_X, twins_T, twins_Y], axis=1)
    dataframe = dataframe.drop(['Unnamed: 0', 'Unnamed: 0.1'], axis=1)
    dataframe = dataframe.dropna(axis=0, how='any')
    dataframe = dataframe.reset_index(drop=True)

    # Generate potential outcomes
    noise = np.random.normal(0, 0.1, len(dataframe))
    random_coeffs = np.random.rand(twins_X.shape[1])
    y0 = np.dot(twins_X.values, random_coeffs) + noise  # Linear combination of features for y0
    y1 = np.sin(np.dot(twins_X.values, random_coeffs)) + np.sqrt(np.sum(twins_X.values**2, axis=1)) + noise  # Non-linear combination for y1

    mu0 = np.dot(twins_X.values, random_coeffs)
    mu1 = np.sin(np.dot(twins_X.values, random_coeffs)) + np.sqrt(np.sum(twins_X.values**2, axis=1))
    # Determine the factual and counterfactual based on the treatment
    #treatment = np.random.binomial(1, 0.7, size=len(dataframe))
    treatment_probs = logistic(np.dot(twins_X, random_coeffs))
    treatment = np.random.binomial(1, treatment_probs, size=len(dataframe))
    y_factual = np.where(treatment == 1, y1, y0)
    #y_cfactual = np.where(treatment == 1, y0, y1)

    # Convert to PyTorch tensors
    data_x_tensor = torch.tensor(twins_X.values, dtype=torch.float32, device=device)
    treatment_tensor = torch.tensor(treatment, dtype=torch.float32, device=device).reshape(-1)
    y_factual_tensor = torch.tensor(y_factual, dtype=torch.float32, device=device).reshape(-1)
    y0_tensor = torch.tensor(y0, dtype=torch.float32, device=device)
    y1_tensor = torch.tensor(y1, dtype=torch.float32, device=device)

    return data_x_tensor, treatment_tensor, y_factual_tensor, y0_tensor, y1_tensor,mu0,mu1



# upload the news data
def upload_news(dir_x, dir_y):
    # Read .y file directly as pandas DataFrame
    names_y = ['treatment', 'y_factual', 'y_cfactual', 'mu0', 'mu1']
    y_data = pd.read_csv(dir_y, header=0, names=names_y)

    # Read the .x file and convert it to dense format
    with open(dir_x, 'r') as f:
        # Read matrix dimensions
        rows, cols, _ = map(int, f.readline().strip().split(','))

        # Extract data for sparse matrix
        i_values, j_values, values = [], [], []
        for line in f:
            i, j, v = map(int, line.strip().split(','))
            i_values.append(i-1)  # Adjusting for 0-based index
            j_values.append(j-1)
            values.append(v)

    # Construct sparse matrix and then convert to dense
    x_sparse = coo_matrix((values, (i_values, j_values)), shape=(rows, cols))
    x_data = x_sparse.todense()

    # Convert data to torch tensors
    treatment = torch.tensor(y_data['treatment'].values, dtype=torch.float32)
    y_factual = torch.tensor(y_data['y_factual'].values, dtype=torch.float32)
    y_cfactual = torch.tensor(y_data['y_cfactual'].values, dtype=torch.float32)
    mu0 = torch.tensor(y_data['mu0'].values, dtype=torch.float32)
    mu1 = torch.tensor(y_data['mu1'].values, dtype=torch.float32)
    X = torch.tensor(x_data, dtype=torch.float32)

    # Calculate y0 and y1 similar to IHDP
    y1 = torch.zeros_like(y_factual)
    y1[treatment == 1] = y_factual[treatment == 1]
    y1[treatment == 0] = y_cfactual[treatment == 0]

    y0 = torch.zeros_like(y_factual)
    y0[treatment == 1] = y_cfactual[treatment == 1]
    y0[treatment == 0] = y_factual[treatment == 0]

    return X, treatment, y_factual, y0, y1, mu0, mu1



# load the data 
def load_data(dataset_name):
    # Depending on dataset_name, call appropriate data loading function
    if dataset_name == "ihdp":
        return upload_ihdp('src/data/ihdp/ihdp_npci_2.csv')
    # Add other datasets similarly
    elif dataset_name == "nonlinear":
        return generate_non_linear()
    elif dataset_name == "linear":
        return generate_linear()
    elif dataset_name == "twins":
        return upload_twins('src/data/twins')
    elif dataset_name == "news":
        return upload_news('src/data/news/topic_doc_mean_n5000_k3477_seed_2.csv.x', 'src/data/news/topic_doc_mean_n5000_k3477_seed_2.csv.y')
    else:
        raise ValueError("Dataset name not recognized.")