import org.apache.spark.{SparkConf, SparkContext}
import org.apache.spark.rdd.RDD
import scala.math._

//Implementation of the Expectation-Maximization (EM) algorithm for fitting a GMM model to 1D data
object EMGMM {

  val EPSILON = 0.01            // convergence threshold (Δ log-likelihood)
  val MAX_ITERATIONS = 5      // max EM iterations
  val MIN_VARIANCE = 1e-6       // variance floor used in M-step
  val MIN_PROB = 1e-10          // min prob threshold to avoid divide-by-zero, log (0)
  val NUM_PARTITIONS = 40       // Number of partitions = numExecutors 10 * coresPerExecutor 4

  // Main - Reads data, runs EM for multiple values of K (number of mixture components)
  def main(args: Array[String]): Unit = {
    val conf = new SparkConf()
      .setAppName("SJ000049")
      //.setMaster("local[*]")  // Use all available cores locally
      // Executor configs
      .set("spark.executor.instances", "10")            // num-executors
      .set("spark.executor.cores", "4")                 // executor-cores
      .set("spark.executor.memory", "30G")              // executor-memory
      .set("spark.executor.memoryOverhead", "2048")
      .set("spark.driver.memory", "4G")                 // Driver configs: driver-memory
      // Optional optimizations
      .set("spark.default.parallelism", "40")

    val sc = new SparkContext(conf)
    sc.setLogLevel("WARN")

    try {
      //val filePath = "datasets/dataset.txt" // Local dataset path
      val filePath="/data/bigDataSecret/dataset-medium.txt"  // Remote Isabelle cluster path

      val data: RDD[Double] = sc.textFile(filePath, NUM_PARTITIONS)
        .flatMap(_.split("\\s+"))     //Split lines by whitespace
        .filter(_.matches("-?\\d+(\\.\\d+)?([eE][+-]?\\d+)?"))  // - Filter tokens matching floating-point numbers (including scientific notation)
        .map(_.toDouble)
        .filter(x => !x.isNaN && !x.isInfinity)     // filter out NaN and Infinity values
        .persist()      // Cache data for efficiency    .persist(StorageLevel.MEMORY_AND_DISK)

      val kValues = Array(1, 2, 3)       // Different K values to evaluate GMM with varying number of components
      val startAll = System.currentTimeMillis()

      // Run EM for each value of K and output results
      for (k <- kValues) {
        println(s"\nRunning EM for K = $k :")
        val startK = System.currentTimeMillis()

        val (phi, mu, sigma2, iterations, logL, converged) = EM(data, k)    // Run EM algorithm

        val duration = (System.currentTimeMillis() - startK) / 1000.0
        if (iterations >= MAX_ITERATIONS && !converged)
          println(f"Max iterations reached: $iterations iterations, ${duration}%.2f sec")
        else
          println(f"Converged in $iterations iterations, ${duration}%.2f sec")

        println(f"Log-Likelihood: $logL%.3f | Epsilon: $EPSILON")
        println("GMM Parameters:")
        for (i <- 0 until k) {
          println(f"  Component ${i + 1}: weight=${phi(i)}%.3f, mean=${mu(i)}%.3f, " +
            f"variance=${sigma2(i)}%.3f, stddev=${sqrt(sigma2(i))}%.3f")
        }
      }

      val totalDuration = (System.currentTimeMillis() - startAll) / 1000.0
      println(f"\nTotal runtime: $totalDuration%.2f sec")
      data.unpersist()    // Free cache from memory

    } finally {
      sc.stop()
    }
  }

  /* Run EM algorithm for a Gaussian Mixture Model with K components on dataset X.
   * @param @X Input dataset as an RDD of Doubles, @K Number of mixture components (clusters)
   * @return Tuple containing:
   *         - phi: Array of mixture weights
   *         - mu: Array of component means
   *         - sigma2: Array of component variances
   *         - iterations: Number of EM iterations run
   *         - logL: Final log-likelihood value
   *         - converged: Boolean flag indicating whether convergence was reached  */
  def EM(X: RDD[Double], K: Int):
  (Array[Double], Array[Double], Array[Double], Int, Double, Boolean) = {

    val n = X.count().toDouble  // Number of data points
    val mu = sample(X, K)       // Initialize component means
    val initVar = X.variance()  // Initialize variances
    val sigma2 = Array.fill(K)(initVar)
    val phi = Array.fill(K)(1.0 / K)  // Initialize mixture weights uniformly (equal responsibility initially)
    var logL = logLikelihood(X, phi, mu, sigma2)  // Compute initial log-likelihood of data
    var iterations = 0
    var converged = false

    // EM loop: run until convergence or maximum iterations reached
    do {
      iterations += 1

      // Expectation (E) Step:
      // For each data point, calc responsibility (posterior probability) that it belongs to each Gaussian component
      val gamma = X.map { x =>
        val probs = phi.indices.map(k => phi(k) * gaussianPDF(x, mu(k), sigma2(k))).toArray
        val total = probs.sum
        if (total > MIN_PROB) probs.map(_ / total) else Array.fill(K)(1.0 / K)
      }

      // Maximization (M) Step:
      // Aggregate weighted sums required to update mixture weights, means, and variances.
      val stats = X.zip(gamma).map { case (x, g) =>
        g.indices.map(k => (g(k), g(k) * x, g(k) * x * x)).toArray
      }.reduce { (a, b) =>
        a.indices.map(k => (
          a(k)._1 + b(k)._1,
          a(k)._2 + b(k)._2,
          a(k)._3 + b(k)._3
        )).toArray
      }

      // Update parameters for each component based on aggregated statistics
      for (k <- 0 until K) {
        val (sumG, sumGX, sumGXX) = stats(k)
        phi(k) = sumG / n  // Update mixture weight as normalized sum of responsibilities
        mu(k) = if (sumG > MIN_PROB) sumGX / sumG else mu(k)  // Update mean if denominator stable
        val variance = (sumGXX / sumG) - (mu(k) * mu(k))      // Variance formula for Gaussian
        sigma2(k) = max(variance, MIN_VARIANCE)               // Apply variance floor for stability
      }

      val newLogL = logLikelihood(X, phi, mu, sigma2)     // Compute new log-likelihood and check for convergence based on improvement
      val improvement = newLogL - logL
      logL = newLogL
      converged = improvement.abs <= EPSILON

    } while (!converged && iterations < MAX_ITERATIONS)

    (phi, mu, sigma2, iterations, logL, converged)        // Return the estimated parameters and diagnostics
  }

  /* Samples initial means for the K components by selecting quantiles from the data. Goal is to spread initial means evenly across the data distribution.
   * @param @X Input data RDD, @K Number of components
   * @return Array of K initial means   */
  def sample(X: RDD[Double], K: Int): Array[Double] = {
    // Take a sample of the data (at least 100 or 10*K points) for stable quantile estimation
    val data = X.takeSample(withReplacement = false, num = math.max(K * 10, 100), seed = 42)
      .sorted

    // For each component i, pick the (i/(K+1))th quantile as initial mean
    (1 to K).map(i => {
      val q = i.toDouble / (K + 1)
      data((q * (data.length - 1)).toInt)
    }).toArray
  }

  /* Computes the Gaussian Probability Density Function (PDF) for a given x, mean mu, and variance sigma2.
   * @param @x Observation value, @mu & @sigma2 Mean & Variance of the Gaussian
   * @return Probability density at x    */
  def gaussianPDF(x: Double, mu: Double, sigma2: Double): Double = {
    val varSafe = max(sigma2, MIN_VARIANCE)
    val coeff = 1.0 / sqrt(2 * Pi * varSafe)
    val expPart = -0.5 * pow(x - mu, 2) / varSafe

    // Guard against underflow in exponentiation; if too small, return zero
    if (expPart < -700) 0.0 else coeff * exp(expPart)
  }

  /* Computes the log-likelihood of the data X given the GMM parameters.
   * @param @X Input data RDD, @phi Mixture weights, @mu @sigma2 Means and Variances of Gaussian components
   * @return LogLikelihood scalar value   */
  def logLikelihood(X: RDD[Double], phi: Array[Double], mu: Array[Double], sigma2: Array[Double]): Double = {
    X.map { x =>
      // Compute weighted sum of probabilities for all components at x
      val px = phi.indices.map(k => phi(k) * gaussianPDF(x, mu(k), sigma2(k))).sum
      // Sum log probabilities, guarding against log(0)
      log(max(px, MIN_PROB))
    }.sum()
  }
}