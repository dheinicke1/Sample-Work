import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.metrics import roc_auc_score, roc_curve
plt.style.use('seaborn')

DATA_PATH = 'C:\\Users\\Dave\\Documents\\Python Scripts\\Transit\\'
# DATA_PATH = 'C:\\Users\\dheinicke\\Google Drive\\Data Science Training\\Python Scripts\\Transit\\'


# Function to plot ROC curve
def plot_roc_curve(test_y, preds_proba):
    preds_proba = preds_proba[:, 1]
    fpr, tpr, thresholds = roc_curve(test_y, preds_proba)

    plt.plot(fpr, tpr, color='b',
             lw=2, alpha=.8)
    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.show()


# Function to score model on 10 random train-test splits
def shuffle_verify(X, y, model):

    shuffle_arr = np.arange(1, 11, 1)

    scores = []

    for rs in shuffle_arr:

        train_X, test_X, train_y, test_y = train_test_split(X, y,
                                                            test_size=0.2,
                                                            random_state=rs)
        model.fit(train_X, train_y)
        preds = model.predict(test_X)
        scores.append(roc_auc_score(test_y, preds))

    return(np.mean(scores))


# Read Data

full_data = pd.read_csv(DATA_PATH + 'clean_data.csv', index_col=0)
master = pd.read_csv(DATA_PATH + 'clean_data.csv',
                     usecols=['5_digit_NTD_ID',
                              # 'Agency',
                              'Modes',
                              # 'HQ_City',
                              'HQ_State',
                              # 'UZA',
                              'UZA_Name',
                              'UZA_Area_SQ_Miles',
                              'UZA_Population',
                              'Service_Area_SQ_Miles',
                              'Service_Area_Population',
                              'Passenger_Miles_FY',
                              'Unlinked_Passenger_Trips_FY',
                              'Average_Trip_Length_FY',
                              'Fares_FY',
                              'Operating_Expenses_FY',
                              'Average_Cost_per_Trip_FY',
                              'Average_Fares_per_Trip_FY'
                              ])
# Extract Unlinked Passenger Trips (UPT) to create target

UPT_cols = []

for col in full_data.columns:
    if col.endswith('UPT'):
        UPT_cols.append(col)

df_UPT = full_data[UPT_cols]

# Interopalte missing values
# df_UPT = df_UPT.dropna(thresh=60)
df_UPT = df_UPT[UPT_cols[3:]].interpolate(axis=1,
                                          limit=None,
                                          limit_direction='both')
# Add Agency ID Bck
df_UPT['5_digit_NTD_ID'] = full_data['5_digit_NTD_ID']

# Combine Ridership by Agency
df_UPT = df_UPT.groupby('5_digit_NTD_ID').sum()

# ### Create target ####
# Compare average total ridership between 2007 - 2014 (about the average peak)
# to 2014 - 2017. If ridership was greater than 95%, considered stable or
# increaseing [1], if recent ridership is less than 90% of past ridership,
# considered decreasing [0]

# Initial annual ridership, 2007-2014

init_cols = []
years_init = ['07', '08', '09', '10', '11', '12', '13', '14']

for year in years_init:
    for col in df_UPT.columns:
        if year in col:
            init_cols.append(col)

final_cols = []
years_final = ['15', '16', '17']

for year in years_final:
    for col in df_UPT.columns:
        if year in col:
            final_cols.append(col)


df_UPT['initial_ridership'] = df_UPT[init_cols].sum(axis=1)
df_UPT['initial_ridership'] = df_UPT['initial_ridership'].\
                              apply(lambda x: x / len(years_init))

df_UPT['recent_ridership'] = df_UPT[final_cols].sum(axis=1)
df_UPT['recent_ridership'] = df_UPT['recent_ridership'].\
                              apply(lambda x: x / len(years_final))

df_UPT['ridership_ratio'] = df_UPT['recent_ridership'] /\
                                  df_UPT['initial_ridership']
df_UPT['target'] = df_UPT['ridership_ratio'].\
                     apply(lambda x: 1 if x >= 0.95 else 0)

df_UPT['target'].describe()

df_UPT.head()

# ### Create Master Features ####

master = master.fillna(0)

# Encode transit modes
master = pd.concat([master.drop('Modes', axis=1),
                    pd.get_dummies(master.Modes, prefix='mode_')], axis=1)

master = pd.concat([master.drop('HQ_State', axis=1),
                    pd.get_dummies(master.HQ_State)], axis=1)

master.columns

grouped = master.groupby('5_digit_NTD_ID')
# grouped.describe
sum_cols = ['Passenger_Miles_FY',
            'Unlinked_Passenger_Trips_FY',
            'Fares_FY',
            'Operating_Expenses_FY']

agency_cols = ['UZA_Area_SQ_Miles',
               'UZA_Population',
               'Service_Area_SQ_Miles',
               'Service_Area_Population',
               'UZA_Name',
               '5_digit_NTD_ID'
               ]

encoded_cols = ['mode__AG', 'mode__AR', 'mode__CB', 'mode__CC', 'mode__CR',
                'mode__DR', 'mode__DT', 'mode__FB', 'mode__HR', 'mode__IP',
                'mode__LR', 'mode__MB', 'mode__MG', 'mode__MO', 'mode__OR',
                'mode__PB', 'mode__RB', 'mode__SR', 'mode__TB', 'mode__TR',
                'mode__VP', 'mode__YR', 'AK', 'AL', 'AR', 'AZ', 'CA', 'CO',
                'CT', 'DC', 'DE', 'FL', 'GA', 'HI', 'IA', 'ID', 'IL', 'IN',
                'KS', 'KY', 'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MS',
                'MT', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH',
                'OK', 'OR', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT',
                'VA', 'VI', 'VT', 'WA', 'WI', 'WV', 'WY']

funcs = defaultdict()

for col in master.columns:
    if col in sum_cols:
        funcs[col] = np.sum
    elif col in agency_cols:
        funcs[col] = stats.mode
    elif col in encoded_cols:
        funcs[col] = np.max

master = grouped.agg(funcs).fillna(0)

for col in agency_cols:
    master[col] = master[col].apply(lambda x: x.mode[0])

# Create agencies per HQ City feature
agencies_per_city = master.groupby(['UZA_Name']).count()
agencies_per_city = pd.DataFrame(agencies_per_city['5_digit_NTD_ID'])

master = master.merge(agencies_per_city,
                      how='left',
                      left_on='UZA_Name',
                      right_index=True,
                      suffixes=('', "_y"))

master.rename(columns={'5_digit_NTD_ID_y': 'agencies_per_city'}, inplace=True)

master = master.drop('UZA_Name', axis=1)

temp = pd.DataFrame(df_UPT.target)

master = master.join(temp, how='left')


# Feature Extraction
def divide_with_zeros(a, b):
    if b == 0:
        return np.nan
    else:
        return (a/b)


master['trips_per_mile'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['Unlinked_Passenger_Trips_FY'],
                                    row['Passenger_Miles_FY']),
                                  axis=1)

master['fares_per_mile'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['Fares_FY'],
                                    row['Passenger_Miles_FY']),
                                  axis=1)

master['cost_per_mile'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['Operating_Expenses_FY'],
                                    row['Passenger_Miles_FY']),
                                  axis=1)

master['miles_per_trip'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['Passenger_Miles_FY'],
                                    row['Unlinked_Passenger_Trips_FY']),
                                  axis=1)

master['fare_per_trip'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['Fares_FY'],
                                    row['Unlinked_Passenger_Trips_FY']),
                                  axis=1)

master['cost_per_trip'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['Operating_Expenses_FY'],
                                    row['Unlinked_Passenger_Trips_FY']),
                                  axis=1)

master['net_per_trip'] = master['cost_per_trip'] - master['fare_per_trip']

master['net_per_mile'] = master['cost_per_mile'] - master['fares_per_mile']

master['net_revenue'] = master['Fares_FY'] - master['Operating_Expenses_FY']

master['UZA_pop_density'] = master.\
                            apply(lambda row:
                                  divide_with_zeros(
                                    row['UZA_Population'],
                                    row['UZA_Area_SQ_Miles']),
                                  axis=1)

master['service_area_pop_density'] = master.\
                                        apply(lambda row:
                                              divide_with_zeros(
                                              row['Service_Area_Population'],
                                              row['Service_Area_SQ_Miles']),
                                              axis=1)

master['service_to_uza_pop'] = master.\
                                    apply(lambda row:
                                          divide_with_zeros(
                                            row['Service_Area_Population'],
                                            row['UZA_Population']),
                                          axis=1)

master['service_to_uza_area'] = master.\
                                    apply(lambda row:
                                          divide_with_zeros(
                                            row['Service_Area_SQ_Miles'],
                                            row['UZA_Area_SQ_Miles']),
                                          axis=1)

master['cost_per_person'] = master.\
                                apply(lambda row:
                                      divide_with_zeros(
                                        row['Operating_Expenses_FY'],
                                        row['Service_Area_Population']),
                                      axis=1)

# Fill missing values with the mean of that feature
master = master.apply(lambda x: x.fillna(x.mean()), axis=0)

columns_to_scale = [column for column in master.columns
                    if type(master[column][1]) == np.float64]

scaler = StandardScaler()

for column in columns_to_scale:
    master[column] = scaler.fit_transform(master[column].values.reshape(-1, 1))

# Save 'master' DataFrame

# master.to_csv(DATA_PATH + 'featurized_data_by_agency.csv')

X = master.drop('target', axis=1)
y = master.target


train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=0.2,
                                                    random_state=2)

# EDA - check for clustering with PCA / TSNE?

from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

perplexity = 100
step = 5000

pca = PCA(n_components=2, random_state=2)
tsne = TSNE(n_components=2,
            learning_rate=200,
            random_state=1,
            perplexity=perplexity,
            n_iter=step)

X_tsne = tsne.fit_transform(X)
tsne_df = pd.DataFrame(np.column_stack((X_tsne, y)),
                       columns=['x', 'y', 'label'])

increasing = tsne_df.loc[tsne_df.label == 1][['x', 'y']]
decreasing = tsne_df.loc[tsne_df.label == 0][['x', 'y']]

fig, ax = plt.subplots()
ax = plt.scatter(increasing.x, increasing.y, color='g')
ax = plt.scatter(decreasing.x, decreasing.y, color='r')
plt.title('TSNE plot, perplexity = {}, step = {}'.format(perplexity, step))
plt.show()

# Logisitc Regression Best Score - 0.55

from sklearn.linear_model import LogisticRegression

lr = LogisticRegression(max_iter=10000,
                        verbose=1,
                        n_jobs=-1)

params_lr = {'penalty': ['l1'],
             'tol': [0.0001],
             'C': [0.5, 1, 1.5],
             'solver': ['liblinear']}

lr_cv = GridSearchCV(lr,
                     param_grid=params_lr,
                     scoring='roc_auc',
                     cv=4,)

lr_cv.fit(train_X, train_y)

lr_cv.best_score_
lr_cv.best_params_

shuffle_verify(X, y, lr_cv.best_estimator_)

preds = lr_cv.best_estimator_.predict(test_X)
preds_proba = lr_cv.best_estimator_.predict_proba(test_X)
score = lr_cv.best_estimator_.score(test_X, test_y)
print(score)
cm = confusion_matrix(test_y, preds)
print(cm)
print(classification_report(test_y, preds))
print(roc_auc_score(test_y, preds))

plot_roc_curve(test_y, preds_proba)

# Naive Bayes - Best Score: 0.51

from sklearn.naive_bayes import GaussianNB

gnb = GaussianNB()
gnb.fit(train_X, train_y)

shuffle_verify(X, y, gnb)

preds_gnb = gnb.predict(test_X)
preds_proba_gnb = gnb.predict_proba(test_X)
score_gnb = gnb.score(test_X, test_y)
print(score_gnb)
cm_gnb = confusion_matrix(test_y, preds)
print(cm_gnb)
print(classification_report(test_y, preds_gnb))
print(roc_auc_score(test_y, preds_gnb))

plot_roc_curve(test_y, preds_proba_gnb)

# KNN - Best Score: 0.53

from sklearn.neighbors import KNeighborsClassifier

knn = KNeighborsClassifier(n_jobs=-1)

params_knn = {'n_neighbors': [2, 3, 4],
              'algorithm': ['ball_tree', 'kd_tree', 'brute']
              }

knn_cv = GridSearchCV(knn,
                      param_grid=params_knn,
                      scoring='roc_auc',
                      cv=4)

knn_cv.fit(train_X, train_y)

knn_cv.best_score_
knn_cv.best_params_

shuffle_verify(X, y, knn_cv.best_estimator_)

preds_knn = knn_cv.best_estimator_.predict(test_X)
preds_proba_knn = knn_cv.best_estimator_.predict_proba(test_X)
score_knn = knn_cv.best_estimator_.score(test_X, test_y)
print(score_knn)
cm_knn = confusion_matrix(test_y, preds_knn)
print(cm_knn)
print(classification_report(test_y, preds_knn))
print(roc_auc_score(test_y, preds_knn))

plot_roc_curve(test_y, preds_proba_knn)

# Random Forrest - Best Score: 0.585
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=650,
                            oob_score=True,
                            n_jobs=-1,
                            random_state=42,
                            )

params_rf = {'criterion': ['entropy'],
             'max_features': [0.45],  # 0.45
             'max_depth': [31],
             'min_samples_split': [2],
             'min_samples_leaf': [2]
             }

rf_cv = GridSearchCV(rf,
                     param_grid=params_rf,
                     scoring='roc_auc',
                     cv=4)

rf_cv.fit(train_X, train_y)

rf_cv.best_score_
rf_cv.best_params_

shuffle_verify(X, y, rf_cv.best_estimator_)

preds_rf = rf_cv.best_estimator_.predict(test_X)
preds_proba_rf = rf_cv.best_estimator_.predict_proba(test_X)
score_rf = rf_cv.best_estimator_.score(test_X, test_y)
print(score_rf)
cm_rf = confusion_matrix(test_y, preds_rf)
print(cm_rf)
print(classification_report(test_y, preds_rf))
print(roc_auc_score(test_y, preds_rf))

plot_roc_curve(test_y, preds_proba_rf)

# LightGBM - Best Score: 0.61
import lightgbm as lgb

# Grid Search CV
lgb_clf = lgb.LGBMClassifier(n_estimators=780,
                             objective='binary',
                             random_state=3,
                             eval_metric='roc_auc',
                             n_jobs=-1
                             )

param_grid = {'boosting_type': ['gbdt'],  # gbdt
              'num_leaves': [34],  # 13
              'max_depth': [5],  # 5
              'learning_rate': [0.01],
              'min_split_gain': [0],
              'min_child_samples': [2],  # 2
              'colsample_bytree': [0.4],  # 0.4
              'reg_alpha': [0],  # 0
              'reg_lambda': [0],  # 0
              }

lgb_cv = GridSearchCV(lgb_clf,
                      param_grid=param_grid,
                      cv=4,
                      scoring='roc_auc',
                      verbose=1)

lgb_cv.fit(X, y)

shuffle_verify(X, y, lgb_cv.best_estimator_)

# 'Manual' Tuning and final LGB model
params = [0]
mean_score = []

for param in params:
    lgb_clf = lgb.LGBMClassifier(n_estimators=650,  # 650
                                 boosting_type='gbdt',  # gbdt
                                 num_leaves=34,  # 34
                                 max_depth=20,  # 20
                                 learning_rate=0.01,
                                 min_split_gain=0,  # 0
                                 min_child_samples=2,  # 2
                                 colsample_bytree=0.6,  # 0.6
                                 objective='binary',
                                 random_state=42,
                                 eval_metric='roc_auc',
                                 is_unbalance=True,
                                 n_jobs=-1)

    mean_score.append(shuffle_verify(X, y, lgb_clf))

print(round(max(mean_score), 3))

plt.plot(params, mean_score)
plt.show()

# XGBoost - Best Score: 0.58
import xgboost as xgb

# Grid Search CV
xgb_clf = xgb.XGBClassifier(n_estimators=1000,
                            objective='binary:logistic',
                            seed=3,
                            nthread=-1
                            )

param_grid_xgb = {'learning_rate': [0.01],  # 0.1
                  'max_depth': [2],  # 2?
                  'gamma': [0],  # 0
                  'min_child_weight': [10],  # 10
                  'max_delta_step': [0],
                  'subsample': [0.5],  # 0.5
                  'colsample_bytree': [0.5],  # 0.5
                  'reg_alpha': [0],
                  'reg_lambda': [0],
                  'scale_pos_weight': [1],
                  'base_score': [0.5],
                  }

xgb_cv = GridSearchCV(xgb_clf,
                      param_grid=param_grid_xgb,
                      cv=4,
                      scoring='roc_auc',
                      verbose=1)

xgb_cv.fit(X, y)

xgb_cv.best_score_
xgb_cv.best_estimator_

shuffle_verify(X, y, xgb_cv.best_estimator_)

# 'Manual' Tuning for XGB model
params = [0]
mean_score = []

for param in params:
    xgb_clf = xgb.XGBClassifier(n_estimators=250,
                                objective='binary:logistic',
                                seed=3,
                                nthread=-1,
                                learning_rate=0.01,  # 0.01
                                max_depth=5,  # 5
                                gamma=0,  # 0
                                min_child_weight=10,  # 10
                                max_delta_step=0,
                                subsample=0.7,  # 0.7
                                colsample_bytree=1,  # 1
                                reg_alpha=0.7,  # 0.7
                                reg_lambda=0.7,  # 0.7
                                scale_pos_weight=1,  # 1
                                )

    mean_score.append(shuffle_verify(X, y, xgb_clf))

print(round(max(mean_score), 3))

plt.plot(params, mean_score)
plt.show()
