# Jupyter Notebook: RL_PopulationMethod.ipynb, downloaded as Python script for size constraints.

import gymnasium as gym
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import copy

#Hyperparameters and configuration
EPISODES = 1000             # Number of training episodes - iterations of the algorithm
EVAL_EPISODES = 5           # Evaluations per episode, to evaluate each policy 
POPULATION_SIZE = 20        # Population size for population-based optimisation
STD_DEV = 0.02              # Standard deviation of the perturbation
SEED = 0
DEVICE = "cpu"


class LandEnvironment:
    def __init__(self, render=False):
        self.env = gym.make("LunarLander-v3", continuous=True, render_mode="human" if render else None)
        self.env = gym.wrappers.TimeLimit(self.env, max_episode_steps=500)

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
       


# Creating policy network by using simple neural network
class PolicyNet(nn.Module):
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 128), # First fully connected layer of 128 neurons
            nn.ReLU(),                 # Non-linear activation ReLU
            nn.Linear(128, output_dim),# Output layer that maps to action space
            nn.Tanh()                  # this keeps action in the range -1, 1
        )
        for p in self.parameters():
            p.requires_grad = False

    def forward(self, x):              # forward pass through the policy network
        return self.network(x)

    def clone(self):
        return copy.deepcopy(self)     # deep copy for perturbation/evaluation



# Logging to record for episode performances
class EpisodeLogger:
    def __init__(self, file_name):
        self.log_path = Path("logs") / file_name
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_file = open(self.log_path, 'w')
        self.start_time = datetime.now()

    def write(self, episode, score):
        #print(f"EPISODE {episode}: REWARD = {score:.2f}" ) #({datetime.now() - self.start_time})")
        print(f"{episode}, {score}", file=self.log_file)

    def close(self):
        self.log_file.close()



# Population method to learn the policy
def population_method(policy, environment, std_dev, population_size, eval_episodes):
    best_score = -float("inf")               # initializing best score for infinity
    best_candidate = None
    seed = np.random.randint(0, 2 ** 31 - 1) # random seed for reproducability

    # population perturbed policies
    for _ in range(population_size):
        candidate = policy.clone()           #deep copy for current policy
        for name, param in policy.named_parameters():
            noise = torch.randn_like(param) * std_dev         # add guassian noise for each parameter
            candidate.state_dict()[name].copy_(param + noise) # apply perturbation

        # Evaluate (20) candidate policies and the candidate policy with best score is selected as the policy for the next episode 
        score = environment.evaluate_policy(candidate, eval_episodes, seed=seed)
        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate, best_score



# Training the population method 
def train():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    # initialize environment and policy
    env = LandEnvironment()
    policy = PolicyNet(env.env.observation_space.shape[0], env.env.action_space.shape[0])
    policy.to(DEVICE)

    logger = EpisodeLogger(f"pop_rl_E{EVAL_EPISODES}_std{STD_DEV}_pop{POPULATION_SIZE}.log")

    best_reward = -float("inf")
    worst_reward = float("inf")
    best_episode = -1
    worst_episode = -1

    # finding the best candidate policy and tracking the overall best and worst episode and scores
    for ep in range(1, EPISODES + 1):
        policy, reward = population_method(policy, env, STD_DEV, POPULATION_SIZE, EVAL_EPISODES)
        logger.write(ep, reward)

        if reward > best_reward:
            best_reward = reward
            best_episode = ep

        if reward < worst_reward:
            worst_reward = reward
            worst_episode = ep

    print(f"\nBest Reward: {best_reward:.2f} at Episode {best_episode}")
    print(f"Worst Reward: {worst_reward:.2f} at Episode {worst_episode}")

    # Save final optimized policy
    torch.save(policy.state_dict(), "final_policy.pt")
    logger.close()
    return logger.log_path


# Plot the learning curve
def plot_log(log_file_path):
    data = np.loadtxt(log_file_path, delimiter=",")
    x = data[:, 0]
    y = data[:, 1]
    
    smooth_window = max(1, len(x) // 100)
    y_smooth = np.convolve(y, np.ones(smooth_window) / smooth_window, mode='valid')
    x_smooth = x[:len(y_smooth)]

    plt.figure(figsize=(10, 5))
    plt.plot(x_smooth, y_smooth)
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.title("Population-Based Optimization - Learning Curve")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(str(log_file_path) + ".png", dpi=300)
    plt.show()

# Main execution

log_path = train()
plot_log(log_path)

# Human evalution
env_human = LandEnvironment(render=True)
final_policy = PolicyNet(8, 2)
final_policy.load_state_dict(torch.load("final_policy.pt"))
env_human.evaluate_policy(final_policy, 5)





