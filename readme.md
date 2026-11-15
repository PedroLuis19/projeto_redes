# Manual de Instruções: Script de Medição de Carga e Desempenho de Rede

Este documento descreve os pré-requisitos, a configuração do ambiente, o funcionamento detalhado do código em Python e o procedimento de execução para a bancada de testes de tráfego de rede. O script é multiplataforma e pode ser utilizado em distribuições Linux (como Fedora, Ubuntu e Debian) e no Windows.

---

## 1. Visão Geral da Solução

O objetivo do script `load_tester.py` é automatizar a geração de carga de rede incremental e mensurar os impactos causados na latência (atraso) e na perda de pacotes.

* **Gerador de Carga:** `iperf3` (via tráfego UDP em taxas controladas em Mbps).
* **Medidor de Latência e Perda:** Utilitário `ping` nativo do sistema operacional.
* **Processamento e Gráficos:** Python 3 usando as bibliotecas nativas (`subprocess`, `re`, `time`) e a biblioteca `matplotlib` para visualização gráfica.

---

## 2. Pré-requisitos de Software e Instalação

Para garantir a compatibilidade multiplataforma, siga as instruções de configuração conforme o seu Sistema Operacional:

### 2.1. Em Sistemas Linux (Fedora, Ubuntu, Debian, Arch)

1. **Dependências do Sistema:**
   * **Fedora:**
     ```bash
     sudo dnf install iperf3 iputils python3-pip -y
     ```
   * **Ubuntu / Debian:**
     ```bash
     sudo apt update && sudo apt install iperf3 iputils-ping python3-pip -y
     ```

2. **Bibliotecas Python:**
   ```bash
   pip3 install matplotlib
   ```

### 2.2. Em Sistemas Microsoft Windows

1. **Instalação do Python:**
   * Faça o download do Python 3 (versão 3.8 ou superior) no site oficial [python.org](https://www.python.org/) e certifique-se de marcar a opção **"Add Python to PATH"** durante a instalação.

2. **Instalação do `iperf3`:**
   * Baixe o binário do `iperf3` compilado para Windows (disponível no repositório do iperf3 ou via iperf.fr).
   * Extraia o arquivo `.exe` e adicione o diretório do `iperf3.exe` às Variáveis de Ambiente do Sistema (PATH) ou coloque o executável dentro da mesma pasta onde executará o código Python.

3. **Bibliotecas Python:**
   Abra o Terminal ou PowerShell e execute:
   ```cmd
   pip install matplotlib
   ```

---

## 3. Topologia da Bancada de Testes (Rede Isolada)

Para atender ao **Requisito E (Ética e Ambiente Controlado)** do projeto, os testes devem ocorrer estritamente em uma rede fechada.

* **Máquina A (Servidor):** Rodando o serviço do `iperf3` em modo de escuta:
  ```bash
  iperf3 -s
  ```
* **Máquina B (Cliente / Gerador de Carga):** Rodando o script `load_tester.py` apontando para o endereço IP da Máquina A.

---

## 4. Script Python Multiplataforma (`load_tester.py`)

Abaixo encontra-se a versão do script ajustada para detectar automaticamente o sistema operacional e adaptar os comandos de rede (`ping` e `iperf3`):

```python
import os
import platform
import re
import subprocess
import time
import matplotlib.pyplot as plt

# ==============================================================================
# CONFIGURAÇÕES DA BANCADA DE TESTES
# ==============================================================================
SERVER_IP = "192.168.1.100"  # Endereço IP do Servidor (Máquina A)
TARGET_HOST = "192.168.1.100" # Endereço IP alvo do Ping (geralmente o mesmo Servidor)
LOAD_LEVELS = ["1M", "5M", "10M", "25M", "50M", "100M"] # Níveis de banda UDP
DURATION = 5  # Duração de cada nível de teste em segundos

results = {
    "load": [],
    "latency": [],
    "loss": []
}

def get_ping_command(target, count):
    """Retorna o comando de ping formatado de acordo com o Sistema Operacional."""
    system_os = platform.system().lower()
    if system_os == "windows":
        # Windows usa -n para contagem e -w para timeout em milissegundos
        return ["ping", "-n", str(count), target]
    else:
        # Linux/Unix usa -c para contagem e -i para intervalo entre pacotes
        return ["ping", "-c", str(count), "-i", "0.5", target]

def parse_ping_output(output, system_os):
    """Extrai latência média (ms) e perda de pacotes (%) da saída do ping."""
    avg_latency = 0.0
    loss = 100.0

    if system_os == "windows":
        # Extrai perda no Windows: (0% loss) ou (0% de perda)
        loss_match = re.search(r"\((\d+)%\s*(?:loss|de perda)\)", output, re.IGNORECASE)
        if loss_match:
            loss = float(loss_match.group(1))

        # Extrai latência no Windows: Average = XXms ou Média = XXms
        lat_match = re.search(r"(?:Average|Média)\s*=\s*(\d+)ms", output, re.IGNORECASE)
        if lat_match:
            avg_latency = float(lat_match.group(1))
    else:
        # Extrai perda no Linux: 0% packet loss
        loss_match = re.search(r"(\d+)% packet loss", output)
        if loss_match:
            loss = float(loss_match.group(1))

        # Extrai latência no Linux: rtt min/avg/max/mdev = min/avg/max/mdev
        rtt_match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+", output)
        if rtt_match:
            avg_latency = float(rtt_match.group(1))

    return avg_latency, loss

def run_ping(target, count=5):
    """Executa o comando ping e retorna (latência_média, perda_porcentagem)."""
    system_os = platform.system().lower()
    cmd = get_ping_command(target, count)
    
    try:
        output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)
        return parse_ping_output(output, system_os)
    except Exception as e:
        print(f"[ERRO] Falha ao executar ping: {e}")
        return 0.0, 100.0

# ==============================================================================
# EXECUÇÃO DOS TESTES DE CARGA
# ==============================================================================
print("=== INICIANDO BANCADA DE TESTES DE CARGA E MEDIÇÃO DE DESEMPENHO ===")
print(f"Sistema Operacional Detectado: {platform.system()}")
print(f"Alvo do Servidor: {SERVER_IP}\n")

for load in LOAD_LEVELS:
    print(f"[*] Aplicando Carga de Tráfego UDP: {load}bps...")
    
    # 1. Inicia o iperf3 em segundo plano (Processo Assíncrono)
    iperf_cmd = ["iperf3", "-c", SERVER_IP, "-u", "-b", load, "-t", str(DURATION)]
    try:
        iperf_process = subprocess.Popen(iperf_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("[ERRO CRÍTICO] O 'iperf3' não foi encontrado no PATH do sistema.")
        break

    # 2. Aguarda a carga estabilizar na interface física/virtual
    time.sleep(1)

    # 3. Executa a amostragem do Ping simultaneamente à carga
    latency, loss = run_ping(TARGET_HOST, count=5)

    # 4. Aguarda a finalização do teste de carga atual do iperf3
    iperf_process.wait()

    # 5. Formata os dados para o gráfico
    numeric_load = int(load.replace('M', '').replace('K', ''))
    results["load"].append(numeric_load)
    results["latency"].append(latency)
    results["loss"].append(loss)

    print(f"    -> Latência Média Obtida: {latency:.2f} ms")
    print(f"    -> Perda de Pacotes Medida: {loss:.1f}%\n")
    
    # Período de resfriamento da rede entre os níveis de carga
    time.sleep(2)

print("=== COLETA CONCLUÍDA. GERANDO GRÁFICOS ANALÍTICOS... ===")

# ==============================================================================
# PLOTAGEM DOS GRÁFICOS COM MATPLOTLIB
# ==============================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Gráfico 1: Impacto da Carga na Latência (Atraso)
ax1.plot(results["load"], results["latency"], marker='o', color='blue', linewidth=2)
ax1.set_title("Degradação de Desempenho: Carga vs Atraso (Latência)")
ax1.set_xlabel("Carga Injetada (Mbps)")
ax1.set_ylabel("Atraso Médio RTT (ms)")
ax1.grid(True, linestyle='--', alpha=0.7)

# Gráfico 2: Impacto da Carga na Perda de Pacotes
ax2.plot(results["load"], results["loss"], marker='s', color='red', linewidth=2)
ax2.set_title("Degradação de Desempenho: Carga vs Perda de Pacotes")
ax2.set_xlabel("Carga Injetada (Mbps)")
ax2.set_ylabel("Perda de Pacotes (%)")
ax2.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
output_filename = "relatorio_desempenho_rede.png"
plt.savefig(output_filename, dpi=300)
print(f"Gráfico gerado com sucesso: '{output_filename}'")
plt.show()
```

---

## 5. Detalhamento Técnico do Código

### A. Detecção de Plataforma (`platform.system()`)
Como o Windows e o Linux utilizam parâmetros de linha de comando diferentes para o utilitário `ping` (`-n` no Windows vs `-c` no Linux), a função `get_ping_command` altera dinamicamente os sinalizadores para evitar incompatibilidades.

### B. Injeção de Carga Concorrente (`subprocess.Popen`)
Para medir o desempenho *sob carga*, a geração de tráfego e a medição do ping precisam ocorrer ao mesmo tempo. O uso de `subprocess.Popen` inicia o `iperf3` em segundo plano sem bloquear o script, permitindo que a função `run_ping` meça a rede enquanto o tráfego de carga está ativo.

### C. Expressões Regulares (`re.search`)
A função `parse_ping_output` utiliza Expressões Regulares (Regex) para parsear os textos de saída retornados pelo sistema operacional. Ela abstrai variações idiomáticas de saída (como "0% loss" em inglês ou "0% de perda" em português).

### D. Métricas em Gráficos (`matplotlib`)
Ao final do loop, os arrays contendo os níveis de carga (em Mbps), a latência média (em ms) e a porcentagem de perda de pacotes são convertidos nos dois gráficos exigidos no **Artefato de Entrega D**:
1. **Carga vs Atraso:** Evidencia o enfileiramento de pacotes (*bufferbloat*) no switch/roteador.
2. **Carga vs Perda:** Evidencia o descarte de pacotes quando a capacidade do enlace atinge $100\%$.

---

## 6. Procedimento de Teste PASSO a PASSO

1. Ligue as duas máquinas (ou Máquinas Virtuais) no ambiente de rede isolado.
2. No **Servidor**, inicie a escuta:
   ```bash
   iperf3 -s
   ```
3. No **Cliente**, configure os IPs no script Python e execute:
   ```bash
   python3 load_tester.py
   ```
