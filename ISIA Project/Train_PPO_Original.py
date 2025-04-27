import gymnasium as gym
from stable_baselines3                   import PPO

env = gym.make("LunarLander-v3")

env.reset()
model = PPO("MlpPolicy", env, verbose = 1, tensorboard_log = "logs")

TIME_STEPS = 50000
iters = 0

while True:
    iters += 1
    model.learn(total_timesteps = TIME_STEPS, reset_num_timesteps = False, tb_log_name = "v2_PPO_Original")
    model.save(f"models/v2_PPO_Original/{iters * TIME_STEPS}")    
    print(f"Iteração {iters}:")