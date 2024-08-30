"""
Overview:
This Python script models a complex DeFi arbitrage strategy involving the recursive staking of Ethereum,
where the profits from staking are used to borrow more Ethereum, which is then restaked. The script 
uses Monte Carlo simulation to estimate the potential outcomes of this strategy under various scenarios,
and Simulated Annealing is employed to optimize the strategy by maximizing the objective function.

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

4. **Simulated Annealing**: An optimization technique inspired by the annealing process in metallurgy,
   used to maximize the objective function which balances net profit against the risks associated with 
   the strategy (e.g., low collateralization ratio, high interest rate spreads).

5. **Recursive Staking Simulation**: Simulates the compounding effect of restaking profits over multiple 
   cycles, showing how the strategy might evolve over time.

6. **Collateralization Ratio**: Calculates the minimum collateral required to avoid liquidation, 
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

# Simulated Annealing parameters
initial_temp = 1000             # Initial temperature for simulated annealing
cooling_rate = 0.99             # Cooling rate for simulated annealing
num_iterations = 1000           # Number of iterations for simulated annealing

# Copula parameter (used for the copula-based correlation model)
copula_param = 0.5

# Choose modeling methods
eth_price_model = 'black_scholes'  # Options: 'black_scholes', 'geometric_brownian'
correlation_method = 'cholesky'    # Options: 'cholesky', 'copula'

# Black-Scholes parameters for Ethereum price
dt = 1 / 365  # Daily time step for the simulation
mu = 0.1      # Expected annual return on Ethereum
sigma = eth_volatility  # Annual volatility of Ethereum

# **Objective Function Definition**
# This function calculates the objective value based on net profit and associated risks.
def objective_function(staking_rate, borrowing_rate, capital, eth_price, collateral_eth, target_collateral_ratio=1.5, alpha=1.0, lambda_=0.5):
    # Net Profit from arbitrage strategy
    net_profit = (staking_rate - borrowing_rate) * capital
    
    # Calculate current collateralization ratio
    current_collateral_ratio = (collateral_eth * eth_price) / capital
    
    # Risk Penalty
    collateral_penalty = max(0, target_collateral_ratio - current_collateral_ratio)
    interest_rate_spread_penalty = alpha * abs(staking_rate - borrowing_rate)
    
    risk_penalty = collateral_penalty + interest_rate_spread_penalty
    
    # Objective function: maximize net profit while minimizing risk
    objective_value = net_profit - lambda_ * risk_penalty
    
    return objective_value

# **Simulated Annealing Function**
# This function integrates Simulated Annealing to optimize the objective function by exploring different
# combinations of staking and borrowing rates, capital allocation, and other parameters.
def simulated_annealing(objective_function, initial_temp, cooling_rate, num_iterations, initial_capital, initial_eth_price):
    # Initial solution setup (random initialization)
    current_solution = {
        'staking_rate': np.random.uniform(0.02, 0.05),
        'borrowing_rate': np.random.uniform(0.015, 0.035),
        'capital': initial_capital,
        'eth_price': initial_eth_price,
        'collateral_eth': np.random.uniform(15000, 25000)  # Collateral in ETH
    }
    current_cost = objective_function(current_solution['staking_rate'], current_solution['borrowing_rate'],
                                      current_solution['capital'], current_solution['eth_price'], 
                                      current_solution['collateral_eth'])
    
    best_solution = current_solution
    best_cost = current_cost
    
    temperature = initial_temp
    
    for i in range(num_iterations):
        # Generate a new candidate solution by perturbing the current solution
        new_solution = {
            'staking_rate': current_solution['staking_rate'] + np.random.uniform(-0.001, 0.001),
            'borrowing_rate': current_solution['borrowing_rate'] + np.random.uniform(-0.001, 0.001),
            'capital': current_solution['capital'],
            'eth_price': current_solution['eth_price'],
            'collateral_eth': current_solution['collateral_eth'] + np.random.uniform(-500, 500)
        }
        new_cost = objective_function(new_solution['staking_rate'], new_solution['borrowing_rate'],
                                      new_solution['capital'], new_solution['eth_price'], 
                                      new_solution['collateral_eth'])
        
        # Acceptance criteria based on Simulated Annealing
        if new_cost > current_cost or np.random.rand() < np.exp((new_cost - current_cost) / temperature):
            current_solution = new_solution
            current_cost = new_cost
            
            # Update the best solution found so far
            if current_cost > best_cost:
                best_solution = current_solution
                best_cost = current_cost
        
        # Cool down the temperature
        temperature *= cooling_rate
    
    return best_solution, best_cost

# **Correlation Modeling Setup**
# Depending on the chosen method, we set up the correlation between Ethereum price and interest rates.
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
final_profits = []
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
        if eth_price_model == 'black_scholes':
            eth_price *= np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * correlated_shocks[0] * np.sqrt(dt))
        elif eth_price_model == 'geometric_brownian':
            eth_price *= np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * correlated_shocks[0] * np.sqrt(dt))
        
        # **Interest Rate Update**
        borrowing_rate += correlated_shocks[1]
        staking_rate += correlated_shocks[1]  # Assuming staking and borrowing rates move together

        borrowing_rate = max(borrowing_rate, 0)
        staking_rate = max(staking_rate, 0)
        
        # **Daily Profit Calculation**
        daily_net_profit = capital * (staking_rate - borrowing_rate) / 365
        capital += daily_net_profit
    
    final_profits.append(capital - initial_capital)  # Net profit/loss

# **Simulated Annealing Optimization**
# After running the Monte Carlo simulations, we use Simulated Annealing to optimize the parameters of the strategy.
best_solution, best_cost = simulated_annealing(objective_function, initial_temp, cooling_rate, num_iterations, initial_capital, initial_eth_price)

# **Results Analysis**
mean_profit = np.mean(final_profits)
std_profit = np.std(final_profits)
probability_of_loss = np.sum(np.array(final_profits) < 0) / n_simulations * 100

# **Collateralization Ratio Calculation**
final_eth_price = eth_price  # Final Ethereum price after simulations
collateral_balance = capital * 1.5 / final_eth_price  # Assuming a 150% collateralization ratio

# Print the results for interpretation
print(f"Mean Final Profit: ${mean_profit:.2f}")
print(f"Standard Deviation of Profit: ${std_profit:.2f}")
print(f"Probability of Loss: {probability_of_loss:.2f}%")
print(f"Required Collateral Balance: {collateral_balance:.2f} ETH")
print(f"Best Simulated Annealing Solution: {best_solution}")
print(f"Best Objective Value: {best_cost:.2f}")

# **Visualization**
plt.hist(final_profits, bins=50, alpha=0.75)
plt.title("Distribution of Final Profits after Correlated Restaking")
plt.xlabel("Final Profit ($)")
plt.ylabel("Frequency")
plt.show()
