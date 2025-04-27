import gymnasium as gym
from sb3_contrib import TRPO
import rewards
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.monitor import Monitor
import optuna
import joblib


# Função de otimização para Optuna
def optimize_trpo(trial):
    # Hiperparâmetros
    learning_rate = trial.suggest_float('learning_rate', 1e-4, 1e-2, log=True)
    batch_size = trial.suggest_categorical('batch_size', [1024, 2048, 4096])
    gae_lambda = trial.suggest_float('gae_lambda', 0.9, 1.0)
    gamma = trial.suggest_float('gamma', 0.95, 0.999)

    # Criar ambiente com a recompensa personalizada
    env = gym.make("LunarLander-v3")
    env = Monitor(env)
    env = rewards.CustomLunarLander(env)

    # Criar o modelo com os hiperparâmetros 
    model = TRPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=batch_size,
        gae_lambda=gae_lambda,
        gamma=gamma,
        verbose=0
    )

    model.learn(total_timesteps=50000)

    # Avaliar o modelo
    mean_reward, _ = evaluate_policy(model, env, n_eval_episodes=10)
    env.close()

    return mean_reward

# Configurar o estudo Optuna
study = optuna.create_study(direction='maximize')
study.optimize(optimize_trpo, n_trials=20)

# Guarda o estudo
joblib.dump(study, "optimized_trpo_study.pkl")

# Exibir os melhores hiperparâmetros encontrados
print("Melhores hiperparâmetros:", study.best_params)

# Carregar os melhores parâmetros
best_params = study.best_params

# Criar o ambiente com a recompensa personalizada
env = gym.make("LunarLander-v3")
env = rewards.CustomLunarLander(env)


def create_model():
    return TRPO(
        "MlpPolicy",
        env,
        learning_rate=best_params['learning_rate'],
        n_steps=best_params['batch_size'],
        gae_lambda=best_params['gae_lambda'],
        gamma=best_params['gamma'],
        verbose=1,
        tensorboard_log="logs"
    )

model = create_model()

# Treinamento contínuo
TIME_STEPS = 50000
iters = 0

while True:
    iters += 1
    
    model.learn(total_timesteps=TIME_STEPS, reset_num_timesteps=False, tb_log_name="TRPO_Alt_R1_Opt")
    model.save(f"models/TRPO_Alt_R1_Opt/{iters * TIME_STEPS}")

    #Avaliar o modelo
    mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=10)
    print(f"Iteração {iters} - Recompensa média: {mean_reward:.2f}, Desvio padrão: {std_reward:.2f}")


env.close()