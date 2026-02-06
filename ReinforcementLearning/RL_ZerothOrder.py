# Jupyter Notebook: RL_ZerothOrder.ipynb, downloaded as Python script for size constraints.

import gymnasium as gym
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import copy

#Hyperparameters and configuration
NUM_EPISODES = 5000                      # Number of training episodes - iterations of the algorithm
NUM_EVALUATIONS_PER_EPISODE = 5          # Evaluations per episode, to evaluate each policy 
PERT_STD_DEV = 0.01                      # Standard deviation of the perturbation

#Step size for parameter updates
LEARNING_RATE = 0.02     

# Random seed for reproducibility
SEED = 0
DEVICE = "cpu"



class LandEnvironment:
    def __init__(self, render=False):
        self.env = gym.make("LunarLander-v3", continuous=True, render_mode="human" if render else None)
        self.env = gym.wrappers.TimeLimit(self.env, max_episode_steps=500)

    #Evaluate Policy 
    def evaluate_policy(self, policy_net, episodes, seed=None):
        total_reward = 0.0
        for i in range(episodes):
            state, _ = self.env.reset(seed=(seed + i if seed else None))
            done, truncated = False, False
            while not (done or truncated):
                state_tensor = torch.tensor(state, dtype=torch.float32).to(DEVICE)
                action = policy_net(state_tensor).detach().cpu().numpy()
                state, reward, done, truncated, _ = self.env.step(action)
                total_reward += reward
        return total_reward / episodes
   


# Creating policy network by using simple neural network with 8 inputs, 128 hidden neurons, and 2 outputs.
class PolicyNet(nn.Module):
    def __init__(self, input_dim:int, output_dim:int, hidden_dim: int = 128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),  
            nn.Tanh(),                         
            nn.Linear(hidden_dim, output_dim), 
            nn.Tanh()                          
        )
        for param in self.parameters():
            param.requires_grad = False 

    def forward(self, x):          
        return self.network(x)

    def clone(self):
        return copy.deepcopy(self) # deep copy for perturbation / evaluation


# Logging episode performances
class EpisodeLogger:
    def __init__(self, file_name):
        self.log_path = Path("logs") / file_name
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_file = open(self.log_path, 'w')
        self.start_time = datetime.now()

    # Write the episode number and return to the log
    def write(self, episode, score):
        print(f"{episode}, {score}", file=self.log_file)

    def close(self):
        self.log_file.close()



# Zeroth-order optimization method
def zeroth_order(policy, std_dev, learning_rate, environment):

    perturbations = {}  
    policy_pos = policy.clone() # positive perturbaton of the policy
    policy_neg = policy.clone() # negative perturbation of policy

    for name, param in policy.named_parameters():    # Apply perturbation to each parameter
        noise = torch.randn_like(param) * std_dev    # Generate Gaussian noise
        perturbations[name] = noise
        policy_pos.state_dict()[name].copy_(param + noise)  #apply positive perturbation
        policy_neg.state_dict()[name].copy_(param - noise)  #apply negative perturbation
 
    # Evaluate both perturbed policies
    pos_score = environment.evaluate_policy(policy_pos, NUM_EVALUATIONS_PER_EPISODE)
    neg_score = environment.evaluate_policy(policy_neg, NUM_EVALUATIONS_PER_EPISODE)
    
    #Estimate gradient and update original policy parameters
    for name, param in policy.named_parameters():
        gradient = (pos_score - neg_score) / 2 * perturbations[name]
        param.data += learning_rate * gradient

    #Return best score from both perturbations
    return max(pos_score, neg_score)



def train():
    torch.manual_seed(SEED) #seed for reproducibility
    np.random.seed(SEED)

    #initialize environment and policy
    env = LandEnvironment()    
    policy = PolicyNet(env.env.observation_space.shape[0], env.env.action_space.shape[0])
    policy.to(DEVICE)

    logger = EpisodeLogger(f"zeroth_rl_E{NUM_EVALUATIONS_PER_EPISODE}_std{PERT_STD_DEV}_lr{LEARNING_RATE}.log")

    for episode in range(1, NUM_EPISODES):
        reward = zeroth_order(policy, PERT_STD_DEV, LEARNING_RATE, env)
        logger.write(episode, reward)

    logger.close()
    return logger.log_path



#Plotting reward over time, with x as Episode number and y as Reward
def plot_log(log_file_path):
    data = np.loadtxt(log_file_path, delimiter=",")
    x = data[:, 0]
    y = data[:, 1]
    smooth_factor = max(len(x) // 100, 1)  
    y_smooth = np.convolve(y, np.ones(smooth_factor)/smooth_factor, mode='valid')
    x_smooth = x[:len(y_smooth)]

    #plot for learning curve
    plt.figure(figsize=(10, 6))
    plt.plot(x_smooth, y_smooth)
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.title("Learning Curve - Zeroth-Order Optimization")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(str(log_file_path) + ".png", dpi=300)
    plt.show()


# Main execution
log_path = train()
plot_log(log_path)
