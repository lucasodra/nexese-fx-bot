"""
Overview:
This Python script models a complex DeFi arbitrage strategy involving the recursive staking of Ethereum,
where the profits from staking are used to borrow more Ethereum, which is then restaked. The script 
uses Monte Carlo simulation to estimate the potential outcomes of this strategy under various scenarios.

Key Components:
1. **Interest Rate Fluctuations**: Modeled as a stochastic process, where both the borrowing rate and 
   staking rate can change over time, influencing the profitability of the strategy.
   
2. **Ethereum Price Fluctuations**: Simulated using two different methods:
   - **Black-Scholes Model**: Assumes that Ethereum's price follows a log-normal distribution, commonly 
     used in finance to model asset prices.
   - **Geometric Brownian Motion (GBM)**: A generic stochastic process that also assumes a log-normal 
     distribution but is more flexible for different types of financial modeling.
   
3. **Correlation Between Ethereum Price and Interest Rates**: Modeled to reflect the real-world scenario 
   where changes in interest rates can influence Ethereum prices and vice versa. This correlation is 
   modeled using two approaches:
   - **Cholesky Decomposition**: A mathematical technique to generate correlated random variables 
     based on a covariance matrix, ensuring that the simulated interest rates and Ethereum prices move 
     together in a realistic way.
   - **Copula**: An alternative method that allows for more complex dependencies between the variables, 
     not limited to linear correlations.

4. **Recursive Staking Simulation**: Simulates the compounding effect of restaking profits over multiple 
   cycles, showing how the strategy might evolve over time.

5. **Collateralization Ratio**: Calculates the minimum collateral required to avoid liquidation, 
   ensuring that the strategy remains viable even under adverse market conditions.
"""

# Import necessary libraries
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm, multivariate_normal

# Parameters
n_simulations = 10000           # Number of Monte Carlo simulations
n_days = 365                    # Simulate for one year (365 days)
initial_eth_price = 3000        # Initial Ethereum price in USD
initial_borrowing_rate = 0.025  # Initial borrowing rate (2.5%)
initial_staking_rate = 0.033    # Initial staking rate (3.3%)
eth_volatility = 0.3            # Volatility of Ethereum price (30%)
interest_rate_volatility = 0.01 # Volatility of interest rates (1%)
correlation = 0.5               # Correlation between ETH price and interest rates
initial_capital = 50_000_000    # Initial capital in USD ($50 million)

# Copula parameter (used for the copula-based correlation model)
copula_param = 0.5

# Choose modeling methods
eth_price_model = 'black_scholes'  # Options: 'black_scholes', 'geometric_brownian'
correlation_method = 'cholesky'    # Options: 'cholesky', 'copula'

# Black-Scholes parameters for Ethereum price
dt = 1 / 365  # Daily time step for the simulation
mu = 0.1      # Expected annual return on Ethereum
sigma = eth_volatility  # Annual volatility of Ethereum

# Initialize storage for final results
final_profits = []

# **Correlation Modeling Setup**
# Depending on the chosen method, we set up the correlation between Ethereum price and interest rates.
# - **Cholesky Decomposition**: Used to generate correlated random variables based on the covariance 
#   matrix. This is a standard approach in finance to ensure that the variables (in this case, 
#   Ethereum prices and interest rates) move together in a realistic manner.
# - **Copula**: Provides a more flexible way to model the dependency structure between variables, 
#   allowing for non-linear correlations and more complex relationships.
if correlation_method == 'cholesky':
    cov_matrix = np.array([[eth_volatility ** 2, correlation * eth_volatility * interest_rate_volatility],
                           [correlation * eth_volatility * interest_rate_volatility, interest_rate_volatility ** 2]])
    L = np.linalg.cholesky(cov_matrix)  # Decompose the covariance matrix
elif correlation_method == 'copula':
    # Copula-based correlation model setup
    def gaussian_copula(u1, u2, rho):
        # Converts uniform random variables into correlated Gaussian variables using a copula.
        return multivariate_normal.cdf([norm.ppf(u1), norm.ppf(u2)], mean=[0, 0], cov=[[1, rho], [rho, 1]])

# **Monte Carlo Simulation**
# The main loop runs the Monte Carlo simulations, iterating over each day within each simulation.
# Each iteration updates the Ethereum price and interest rates based on the chosen models and 
# correlation method, and then calculates the profit or loss from the staking strategy.
for _ in range(n_simulations):
    eth_price = initial_eth_price
    borrowing_rate = initial_borrowing_rate
    staking_rate = initial_staking_rate
    capital = initial_capital
    
    for _ in range(n_days):
        # Generate correlated random shocks based on the chosen correlation method
        if correlation_method == 'cholesky':
            shocks = np.random.normal(size=2)
            correlated_shocks = L @ shocks
        elif correlation_method == 'copula':
            # Generate uniform random variables and transform them using the Gaussian copula
            u1, u2 = np.random.uniform(size=2)
            correlated_shocks = np.array([norm.ppf(u1), norm.ppf(gaussian_copula(u1, u2, copula_param))])
        
        # **Ethereum Price Modeling**
        # Depending on the chosen model, simulate the price of Ethereum.
        # - **Black-Scholes Model**: Assumes that the price of Ethereum follows a log-normal distribution, 
        #   which is common in financial modeling. The Black-Scholes formula incorporates the expected return 
        #   (mu) and volatility (sigma) to simulate price changes.
        # - **Geometric Brownian Motion (GBM)**: Similar to the Black-Scholes model, GBM assumes that the 
        #   asset price follows a continuous-time stochastic process with a drift and volatility component.
        if eth_price_model == 'black_scholes':
            eth_price *= np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * correlated_shocks[0] * np.sqrt(dt))
        elif eth_price_model == 'geometric_brownian':
            eth_price *= np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * correlated_shocks[0] * np.sqrt(dt))
        
        # **Interest Rate Update**
        # Update the borrowing and staking rates based on the correlated shock.
        # This models the idea that interest rates can be affected by the same factors influencing 
        # Ethereum prices (e.g., market demand/supply, economic conditions).
        borrowing_rate += correlated_shocks[1]
        staking_rate += correlated_shocks[1]  # Assuming staking and borrowing rates move together

        # Ensure rates are bounded (no negative rates)
        borrowing_rate = max(borrowing_rate, 0)
        staking_rate = max(staking_rate, 0)
        
        # **Daily Profit Calculation**
        # Calculate the profit for the day based on the difference between staking and borrowing rates,
        # then add it to the capital. This simulates the recursive staking strategy.
        daily_net_profit = capital * (staking_rate - borrowing_rate) / 365
        capital += daily_net_profit
    
    # Store the final profit or loss after all the simulations
    final_profits.append(capital - initial_capital)  # Net profit/loss

# **Results Analysis**
# After running all the simulations, we analyze the results to understand the potential profitability 
# and risk of the strategy.
mean_profit = np.mean(final_profits)
std_profit = np.std(final_profits)
probability_of_loss = np.sum(np.array(final_profits) < 0) / n_simulations * 100

# **Collateralization Ratio Calculation**
# To avoid liquidation, we calculate the minimum collateralization ratio required. The final Ethereum 
# price is used to determine how much collateral is needed relative to the borrowed amount.
final_eth_price = eth_price  # Final Ethereum price after simulations
collateral_balance = capital * 1.5 / final_eth_price  # Assuming a 150% collateralization ratio

# Print the results for interpretation
print(f"Mean Final Profit: ${mean_profit:.2f}")
print(f"Standard Deviation of Profit: ${std_profit:.2f}")
print(f"Probability of Loss: {probability_of_loss:.2f}%")
print(f"Required Collateral Balance: {collateral_balance:.2f} ETH")

# **Visualization**
# Plot the distribution of final profits to understand the spread of outcomes.
plt.hist(final_profits, bins=50, alpha=0.75)
plt.title("Distribution of Final Profits after Correlated Restaking")
plt.xlabel("Final Profit ($)")
plt.ylabel("Frequency")
plt.show()
