import gymnasium as gym
from stable_baselines3 import PPO
from argparse          import ArgumentParser
from sys               import argv, exit
from gymnasium.wrappers import TimeLimit

env = gym.make('LunarLander-v3', render_mode="human")
env = TimeLimit(env, max_episode_steps=500)

# run tensorboard with:
# tensorboard --logdir=logs


def main():
    parser = ArgumentParser(description='Please specify which model to test')

    parser.add_argument( '-o', '--original', action='store_true', help='Test the original model')
    parser.add_argument( '-c', '--custom', action='store_true', help='Test the custom model')

    if len(argv) == 1:
        parser.print_help()
        exit(0)

    args = parser.parse_args()

    env.reset()

    if args.original:
        models_dir = "models/TRPO_Original/"
        model_path = f"{models_dir}/73750000"

    elif args.custom:
        models_dir = "models/TRPO_Alt_R1/"
        model_path = f"{models_dir}/73750000" 

    model = PPO.load(model_path, env=env)

    episodes = 10

    for ep in range(episodes):
        obs, _ = env.reset()
        done = False
        while not done:
            env.render()
            action, _ = model.predict(obs)
            obs, reward, done, truncated, prob = env.step(action.item())
            print(reward)

            if truncated:
                print("Episódio terminado por timeout.")
                break

    env.close()

if __name__ == "__main__":
    main()