import subprocess
import time
import re
import statistics
import matplotlib.pyplot as plt

# CONFIGURAÇÕES DA SUA BANCADA
SERVER_IP = "192.168.1.100"  # Substitua pelo IP da máquina servidora (iperf3 -s)
TARGET_HOST = "192.168.1.100" # Alvo para o ping
LOAD_LEVELS = ["1M", "5M", "10M", "25M", "50M", "100M"] # Níveis de carga de teste (Mbps)
DURATION = 5  # Duração de cada teste em segundos

results = {
    "load": [],
    "latency": [],
    "loss": []
}

def run_ping(target, duration):
    """Executa o comando ping por um período e retorna a latência média e % de perda."""
    cmd = ["ping", "-c", str(duration), "-i", "0.5", target]
    try:
        output = subprocess.check_output(cmd, universal_newlines=True)
        
        # Extrai porcentagem de perda de pacotes
        loss_match = re.search(r"(\d+)% packet loss", output)
        loss = float(loss_match.group(1)) if loss_match else 0.0
        
        # Extrai rtt (latência min/avg/max/mdev)
        rtt_match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+", output)
        avg_latency = float(rtt_match.group(1)) if rtt_match else 0.0
        
        return avg_latency, loss
    except Exception as e:
        print(f"Erro ao executar o ping: {e}")
        return 0.0, 100.0

print("=== INICIANDO BANCADA DE TESTES DE CARGA ===")
print("Certifique-se de que o 'iperf3 -s' está rodando no servidor isolado!\n")

for load in LOAD_LEVELS:
    print(f"[*] Testando com carga UDP de: {load}...")
    
    # Inicia o iperf3 em background para gerar tráfego de carga
    iperf_cmd = ["iperf3", "-c", SERVER_IP, "-u", "-b", load, "-t", str(DURATION)]
    iperf_process = subprocess.Popen(iperf_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Dá um breve tempo para a carga estabilizar e dispara o ping concomitante
    time.sleep(1)
    latency, loss = run_ping(TARGET_HOST, duration=3)
    
    # Aguarda o término do iperf3
    iperf_process.wait()
    
    # Converte a carga textual (ex: '10M') para número inteiro em Mbps para o gráfico
    numeric_load = int(load.replace('M', ''))
    
    results["load"].append(numeric_load)
    results["latency"].append(latency)
    results["loss"].append(loss)
    
    print(f"    -> Latência Média: {latency} ms | Perda de Pacotes: {loss}%\n")
    time.sleep(2) # Pausa de resfriamento entre os testes

print("=== TESTES CONCLUÍDOS. GERANDO GRÁFICOS... ===")

# Geração dos Gráficos Exigidos na Entrega
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Gráfico 1: Carga vs Atraso (Latência)
ax1.plot(results["load"], results["latency"], marker='o', color='b', linestyle='-')
ax1.set_title("Degradação do Desempenho: Carga vs Atraso")
ax1.set_xlabel("Carga Oferecida (Mbps)")
ax1.set_ylabel("Atraso / Latência Média (ms)")
ax1.grid(True)

# Gráfico 2: Carga vs Perda de Pacotes
ax2.plot(results["load"], results["loss"], marker='s', color='r', linestyle='-')
ax2.set_title("Degradação do Desempenho: Carga vs Perda")
ax2.set_xlabel("Carga Oferecida (Mbps)")
ax2.set_ylabel("Perda de Pacotes (%)")
ax2.grid(True)

plt.tight_layout()
plt.savefig("relatorio_desempenho_rede.png", dpi=300)
print("Gráficos salvos com sucesso como 'relatorio_desempenho_rede.png'!")
plt.show()