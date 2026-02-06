This Scala project implements Expectation–Maximisation (EM) algorithm for classifying univariate multi-modal from the dataset that contains multiple gaussian distributions of data. 
A Gaussian mixture model (GMM) is a soft clustering machine learning method used in unsupervised learning to determine the probability that a given data point belongs to a cluster. 
It’s composed of several Gaussians, each identified by k ∈ {1,…, K}, where K is the number of clusters in a data set.
As part of implementing EM,•	Initializing parameters for the GMM.
•	Running the EM algorithm with an E-step and M-step.
•	Logging the log-likelihood and checking for convergence.
•	Using Spark to handle large datasets efficiently with parallel processing and distributed computation.
The experiments are run both on local machine and also on a remote Isabelle cluster with 10 executors × 4 cores each, leveraging 40 partitions to optimize resource utilization. 
To optimize performance, I have used several Spark-specific techniques:
•	Persistence () prevented repeated recomputation of RDD lineage across EM iterations.
•	Partitioning was set to 40, to leverage the 10 worker nodes each having 4 cores. This significantly helped to balance workload.
Persisting this intermediate dataset in memory and disk was crucial because the EM algorithm is iterative. Without persistence, Spark would recompute the full lineage of transformations from the raw file on each iteration, causing unnecessary disk I/O and repeated computation. By persisting once, Spark materialized the dataset in memory, which accelerated repeated access and reduced runtime significantly.
This persistence is particularly helpful for iterative algorithms like EM, where the same dataset is scanned multiple times during the iterative refinement of model parameters.
