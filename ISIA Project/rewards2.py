from gymnasium import Wrapper

class CustomLunarLander(Wrapper):
    def __init__(self, env):
        super(CustomLunarLander, self).__init__(env)

    def step(self, action):
        obs, reward, done, truncated, info = self.env.step(action)

        if done:
            if obs[0] > -0.3 and obs[0] < 0.3: #Estar na plataforma
                reward += 10 #Recompensa
                if obs[0] > -0.2 and obs[0] < 0.2: #Estar perto do centro
                    reward += 20 #Recompensa 
                    if obs[0] > -0.1 and obs[0] < 0.1: #Estar mesmo no centro
                        reward += 30 #Recompensa 
                
                #Verificar se aterrou 
                if (obs[6] == 1 and obs[7] == 0) or (obs[6] == 0 and obs[7] == 1): #Aterou só com um pé
                    reward += 10 #Recompensa
                if obs[6] == 1 and obs[7] == 1: #Aterrou com os 2 pés
                    reward += 50 #Recompensa

                    #Velocidade Horizontal e Vertical suave  
                    if obs[3] > -0.5 and abs(obs[2]) < 0.3:
                        reward += 50 #Recompensa 
                    else:
                        reward -= 100 #Penalização

                    #Velocidade Angular suave
                    if abs(obs[4]) < 0.1:
                        reward += 50 #Recompensa 
                    else:
                        reward -= 100 #Penalização

                if obs[6] == 0 and obs[7] == 0: #Não aterrar com os 2 pés
                    reward -=100 #Penalização
                

            else: # Não estar no alinhamento horizontal a plataforma
                reward -= 100

        return obs, reward, done, truncated, info