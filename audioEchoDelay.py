import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import pygame
import time
import os
from concurrent.futures import ThreadPoolExecutor
import glob
from threading import Thread

class AplicacaoEcoAudio:
    """Aplicação para adicionar efeito de eco em arquivos de áudio usando interface gráfica."""

    def __init__(self, root):
        """Inicializa a aplicação com a janela principal e componentes da interface."""
        self.root = root
        self.dados_audio = None  # Dados do áudio carregado (array numpy)
        self.taxa_amostragem = None  # Taxa de amostragem do arquivo de áudio
        self.arquivo_audio = None  # Caminho do arquivo de áudio atual
        self.pasta_impulsos = None  # Pasta contendo arquivos de impulso
        self.configurar_interface()

    def configurar_interface(self):
        """Configura os componentes da interface gráfica."""
        self.root.title("Aplicação de Eco e Delay")
        self.root.geometry("400x400")

        # Registro do suporte para arrastar e soltar
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.ao_soltar)

        # Componentes da Interface
        self.rotulo_arquivo = tk.Label(self.root, 
            text="Arraste um ou mais arquivos de áudio aqui ou clique para carregar")
        self.rotulo_arquivo.pack(pady=10)

        # Botões principais
        botao_abrir = tk.Button(self.root, text="Selecionar Arquivo(s)", command=self.abrir_arquivo)
        botao_abrir.pack(pady=5)

        # Frame para parâmetros
        frame_params = ttk.LabelFrame(self.root, text="Parâmetros")
        frame_params.pack(pady=5, padx=5, fill="x")

        tk.Label(frame_params, text="Atraso (ms)").pack()
        self.entrada_atraso = tk.Entry(frame_params)
        self.entrada_atraso.pack()
        self.entrada_atraso.insert(0, "200")  # Valor padrão

        tk.Label(frame_params, text="Decaimento (0.0 - 1.0)").pack()
        self.entrada_decaimento = tk.Entry(frame_params)
        self.entrada_decaimento.pack()
        self.entrada_decaimento.insert(0, "0.5")  # Valor padrão

        # Frame para resposta de impulso
        frame_impulso = ttk.LabelFrame(self.root, text="Resposta de Impulso")
        frame_impulso.pack(pady=5, padx=5, fill="x")

        self.var_usar_impulso = tk.BooleanVar()
        self.check_impulso = tk.Checkbutton(frame_impulso, text="Usar resposta de impulso", 
                                           variable=self.var_usar_impulso,
                                           command=self.atualizar_estado_ir)
        self.check_impulso.pack(pady=5)

        # Frame para seleção do IR
        frame_selecao_ir = tk.Frame(frame_impulso)
        frame_selecao_ir.pack(fill="x", padx=5)

        botao_impulso = tk.Button(frame_selecao_ir, text="Selecionar Pasta", 
                                 command=self.selecionar_pasta_impulsos)
        botao_impulso.pack(side=tk.LEFT, pady=5)

        # Combobox para seleção do IR
        self.combo_ir = ttk.Combobox(frame_selecao_ir, state='disabled')
        self.combo_ir.pack(side=tk.LEFT, pady=5, padx=5, fill="x", expand=True)
        self.combo_ir.bind('<<ComboboxSelected>>', self.ao_selecionar_ir)

        # Label para mostrar informações do IR
        self.rotulo_ir = tk.Label(frame_impulso, text="Nenhum IR selecionado", font=('Arial', 8))
        self.rotulo_ir.pack(pady=2)

        # Botões de controle
        frame_controles = tk.Frame(self.root)
        frame_controles.pack(pady=10)

        self.botao_tocar = tk.Button(frame_controles, text="Tocar", command=self.tocar_audio, state='disabled')
        self.botao_tocar.pack(side=tk.LEFT, padx=5)

        self.botao_parar = tk.Button(frame_controles, text="Parar", command=self.parar_audio, state='disabled')
        self.botao_parar.pack(side=tk.LEFT, padx=5)

        self.botao_salvar = tk.Button(frame_controles, text="Processar", command=self.processar_arquivos)
        self.botao_salvar.pack(side=tk.LEFT, padx=5)

        # Barra de progresso
        self.barra_progresso = ttk.Progressbar(self.root, mode='determinate')
        self.barra_progresso.pack(pady=10, fill="x", padx=5)

    def carregar_audio(self, caminho_arquivo):
        """
        Carrega um arquivo de áudio na memória para pré-visualização.

        Args:
            caminho_arquivo (str): Caminho do arquivo de áudio a ser carregado.
        """
        try:
            self.dados_audio, self.taxa_amostragem = sf.read(caminho_arquivo)
            self.arquivo_audio = caminho_arquivo
            self.rotulo_arquivo.config(text=f"Arquivo para pré-visualização: {os.path.basename(caminho_arquivo)}")
            # Habilita botões de reprodução
            self.botao_tocar.config(state='normal')
            self.botao_parar.config(state='normal')
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar arquivo: {e}")

    def adicionar_eco(self, dados_audio, atraso_ms, decaimento, taxa_amostragem=None):
        """
        Aplica efeito de eco aos dados de áudio.

        Args:
            dados_audio (numpy.ndarray): Dados do áudio original
            atraso_ms (int): Atraso do eco em milissegundos
            decaimento (float): Fator de decaimento do eco (0.0 a 1.0)
            taxa_amostragem (int, optional): Taxa de amostragem do áudio. 
                                           Se None, usa a taxa do áudio carregado.

        Returns:
            numpy.ndarray: Dados do áudio com efeito de eco aplicado
        """
        if dados_audio is None:
            raise ValueError("Nenhum dado de áudio carregado.")

        # Usa a taxa de amostragem fornecida ou a da classe
        taxa = taxa_amostragem if taxa_amostragem is not None else self.taxa_amostragem

        # Converte atraso de milissegundos para amostras
        amostras_atraso = int((atraso_ms / 1000) * taxa)

        # Se estiver usando resposta de impulso
        if self.var_usar_impulso.get() and self.pasta_impulsos:
            return self.aplicar_resposta_impulso(dados_audio, taxa)

        # Caso contrário, aplica eco normal
        # Cria um array de saída com tamanho suficiente para acomodar o eco
        tamanho_saida = len(dados_audio) + amostras_atraso
        if dados_audio.ndim == 1:  # Áudio mono
            saida = np.zeros(tamanho_saida)
            # Copia o áudio original
            saida[:len(dados_audio)] = dados_audio
            # Adiciona o eco
            for i in range(len(dados_audio)):
                saida[i + amostras_atraso] += decaimento * dados_audio[i]
        else:  # Áudio estéreo
            saida = np.zeros((tamanho_saida, 2))
            # Copia o áudio original
            saida[:len(dados_audio)] = dados_audio
            # Adiciona o eco
            for i in range(len(dados_audio)):
                saida[i + amostras_atraso, 0] += decaimento * dados_audio[i, 0]
                saida[i + amostras_atraso, 1] += decaimento * dados_audio[i, 1]

        return np.clip(saida, -1.0, 1.0)
    
    def validar_parametros(self, atraso_ms, decaimento):
        try:
            atraso = int(atraso_ms)
            if atraso <= 0:
                raise ValueError("O atraso deve ser um número positivo")
                
            decay = float(decaimento)
            if not 0.0 <= decay <= 1.0:
                raise ValueError("O decaimento deve estar entre 0.0 e 1.0")
                
            return atraso, decay
        except ValueError as e:
            messagebox.showerror("Erro de Validação", str(e))
            raise

    def aplicar_resposta_impulso(self, dados_audio, taxa_amostragem=None):
        """
        Aplica a resposta de impulso ao áudio.
        
        Args:
            dados_audio (numpy.ndarray): Dados do áudio original
            taxa_amostragem (int, optional): Taxa de amostragem do áudio

        Returns:
            numpy.ndarray: Áudio processado com a resposta de impulso
        """
        try:
            if not self.combo_ir.get():
                raise ValueError("Nenhum IR selecionado.")

            # Carrega o arquivo de impulso selecionado
            caminho_ir = os.path.join(self.pasta_impulsos, self.combo_ir.get())
            impulso, taxa_impulso = sf.read(caminho_ir)

            # Garante que o impulso seja mono se necessário
            if impulso.ndim > 1:
                impulso = np.mean(impulso, axis=1)

            # Aplica a convolução
            if dados_audio.ndim == 1:  # Áudio mono
                resultado = np.convolve(dados_audio, impulso, mode='full')
            else:  # Áudio estéreo
                resultado_l = np.convolve(dados_audio[:, 0], impulso, mode='full')
                resultado_r = np.convolve(dados_audio[:, 1], impulso, mode='full')
                resultado = np.column_stack((resultado_l, resultado_r))

            # Normaliza o resultado
            return np.clip(resultado / np.max(np.abs(resultado)), -1.0, 1.0)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao aplicar resposta de impulso: {e}")
            return dados_audio

    def selecionar_pasta_impulsos(self):
        """Permite ao usuário selecionar a pasta contendo arquivos de resposta de impulso."""
        pasta = filedialog.askdirectory(title="Selecionar Pasta de Impulsos")
        if pasta:
            self.pasta_impulsos = pasta
            self.atualizar_lista_irs()

    def atualizar_lista_irs(self):
        """Atualiza a lista de IRs disponíveis no combobox."""
        if self.pasta_impulsos:
            arquivos_impulso = glob.glob(os.path.join(self.pasta_impulsos, "*.wav"))
            if arquivos_impulso:
                # Pega apenas os nomes dos arquivos, sem o caminho completo
                nomes_irs = [os.path.basename(f) for f in arquivos_impulso]
                self.combo_ir['values'] = nomes_irs
                self.combo_ir.set(nomes_irs[0])  # Seleciona o primeiro IR
                self.combo_ir.config(state='readonly')
                self.atualizar_info_ir(nomes_irs[0])
            else:
                self.combo_ir.set('')
                self.combo_ir['values'] = []
                self.combo_ir.config(state='disabled')
                self.rotulo_ir.config(text="Nenhum arquivo WAV encontrado na pasta")
                messagebox.showwarning("Aviso", "Nenhum arquivo WAV encontrado na pasta selecionada")

    def ao_selecionar_ir(self, evento):
        """Callback para quando um novo IR é selecionado no combobox."""
        ir_selecionado = self.combo_ir.get()
        self.atualizar_info_ir(ir_selecionado)

    def atualizar_info_ir(self, nome_arquivo):
        """Atualiza as informações exibidas sobre o IR selecionado."""
        if nome_arquivo:
            caminho_completo = os.path.join(self.pasta_impulsos, nome_arquivo)
            try:
                # Carrega o IR para obter informações
                dados, taxa = sf.read(caminho_completo)
                duracao = len(dados) / taxa
                canais = "Estéreo" if dados.ndim > 1 else "Mono"
                self.rotulo_ir.config(
                    text=f"IR: {nome_arquivo} | {canais} | {duracao:.2f}s | {taxa}Hz"
                )
            except Exception as e:
                self.rotulo_ir.config(text=f"Erro ao carregar IR: {str(e)}")
        else:
            self.rotulo_ir.config(text="Nenhum IR selecionado")

    def atualizar_estado_ir(self):
        """Atualiza o estado dos controles de IR baseado no checkbox."""
        if self.var_usar_impulso.get():
            if self.pasta_impulsos:
                self.combo_ir.config(state='readonly')
            else:
                # Se a checkbox for marcada mas não houver pasta selecionada
                self.selecionar_pasta_impulsos()
        else:
            self.combo_ir.config(state='disabled')

    def atualizar_progresso(self, valor):
        """Atualiza a barra de progresso de forma segura"""
        self.barra_progresso['value'] = valor
        self.root.update_idletasks()

    def finalizar_processamento_unico(self, sucesso, erro=None):
        """Finaliza o processamento de arquivo único"""
        # Reabilita botões
        self.botao_salvar.config(state='normal')
        self.botao_tocar.config(state='normal')
        self.botao_parar.config(state='normal')
        
        # Reseta barra de progresso
        self.barra_progresso['value'] = 0
        
        # Mostra mensagem apropriada
        if sucesso:
            messagebox.showinfo("Sucesso", "Arquivo processado com sucesso!")
        else:
            messagebox.showerror("Erro", f"Falha ao processar arquivo: {erro}")

    def processar_arquivos(self):
        """Processa um ou mais arquivos selecionados."""
        if not hasattr(self, 'arquivos_selecionados') or not self.arquivos_selecionados:
            if self.arquivo_audio:
                self.arquivos_selecionados = [self.arquivo_audio]
            else:
                messagebox.showwarning("Aviso", "Nenhum arquivo selecionado para processar")
                return

        total = len(self.arquivos_selecionados)
        
        # Se for apenas um arquivo, pede o nome do arquivo de saída
        if total == 1:
            caminho_saida = filedialog.asksaveasfilename(
                defaultextension=".wav",
                filetypes=[("Arquivos WAV", "*.wav")],
                initialfile=f"{os.path.splitext(os.path.basename(self.arquivos_selecionados[0]))[0]}_processado.wav"
            )
            if not caminho_saida:  # Usuário cancelou
                return

            # Desabilita botões durante o processamento
            self.botao_salvar.config(state='disabled')
            self.botao_tocar.config(state='disabled')
            self.botao_parar.config(state='disabled')

            # Reinicia a barra de progresso
            self.barra_progresso['value'] = 0
            self.root.update_idletasks()

            def processar_unico():
                try:
                    # Leitura do arquivo - 25%
                    dados, taxa = sf.read(self.arquivos_selecionados[0])
                    self.root.after(0, lambda: self.atualizar_progresso(25))

                    # Processamento do eco - 50%
                    try:
                        atraso_ms, decaimento = self.validar_parametros(
                            self.entrada_atraso.get(),
                            self.entrada_decaimento.get()
                        )
                    except ValueError:
                        self.root.after(0, lambda: self.finalizar_processamento_unico(False, "Parâmetros inválidos"))
                        return
                    dados_modificados = self.adicionar_eco(dados, atraso_ms, decaimento, taxa_amostragem=taxa)
                    self.root.after(0, lambda: self.atualizar_progresso(50))

                    # Salvamento do arquivo - 75%
                    sf.write(caminho_saida, dados_modificados, taxa)
                    self.root.after(0, lambda: self.atualizar_progresso(75))

                    # Finalização - 100%
                    self.root.after(0, lambda: self.atualizar_progresso(100))
                    self.root.after(0, lambda: self.finalizar_processamento_unico(True))
                except Exception as e:
                    self.root.after(0, lambda: self.finalizar_processamento_unico(False, str(e)))

            # Inicia o processamento em uma thread separada
            thread_processamento = Thread(target=processar_unico)
            thread_processamento.start()
            return

        # Se forem múltiplos arquivos, pede a pasta de destino
        pasta_destino = filedialog.askdirectory(title="Selecione a pasta para salvar os arquivos processados")
        if not pasta_destino:  # Usuário cancelou
            return

        # Desabilita botões durante o processamento
        self.botao_salvar.config(state='disabled')
        self.botao_tocar.config(state='disabled')
        self.botao_parar.config(state='disabled')

        try:
            atraso_ms, decaimento = self.validar_parametros(
                self.entrada_atraso.get(),
                self.entrada_decaimento.get()
            )
        except ValueError:
            return

        # Variáveis para controle do processamento em lote
        processamento_lote = {
            'total': total,
            'processados': 0,
            'erros': [],
            'params': {
                'atraso_ms': int(self.entrada_atraso.get()),
                'decaimento': float(self.entrada_decaimento.get()),
                'pasta_destino': pasta_destino
            }
        }

        def atualizar_progresso():
            """Atualiza a barra de progresso e verifica se o processamento terminou"""
            progresso = (processamento_lote['processados'] / processamento_lote['total']) * 100
            self.barra_progresso['value'] = progresso
            self.root.update_idletasks()
            
            if processamento_lote['processados'] == processamento_lote['total']:
                # Reabilita botões
                self.botao_salvar.config(state='normal')
                self.botao_tocar.config(state='normal')
                self.botao_parar.config(state='normal')
                
                # Reseta barra de progresso
                self.barra_progresso['value'] = 0
                
                # Mostra mensagem com resultados
                if processamento_lote['erros']:
                    mensagem_erro = "\n".join([f"- {erro}" for erro in processamento_lote['erros'][:5]])
                    if len(processamento_lote['erros']) > 5:
                        mensagem_erro += f"\n(mais {len(processamento_lote['erros']) - 5} erros...)"
                    messagebox.showwarning("Processamento Concluído com Erros",
                                        f"{processamento_lote['processados']} de {processamento_lote['total']} arquivos processados com sucesso.\n\nErros:\n{mensagem_erro}")
                else:
                    messagebox.showinfo("Concluído", 
                                    f"Processamento concluído com sucesso!\nTodos os {processamento_lote['total']} arquivos foram processados.")
            else:
                # Agenda próxima verificação
                self.root.after(100, atualizar_progresso)

        def processar_arquivo(arquivo_entrada):
            try:
                dados, taxa = sf.read(arquivo_entrada)
                dados_modificados = self.adicionar_eco(
                    dados, 
                    processamento_lote['params']['atraso_ms'],
                    processamento_lote['params']['decaimento'],
                    taxa_amostragem=taxa
                )
                
                nome_base = os.path.splitext(os.path.basename(arquivo_entrada))[0]
                arquivo_saida = os.path.join(
                    processamento_lote['params']['pasta_destino'], 
                    f"{nome_base}_processado.wav"
                )
                
                sf.write(arquivo_saida, dados_modificados, taxa)
                processamento_lote['processados'] += 1
                return None
            except Exception as e:
                processamento_lote['processados'] += 1
                return f"Erro ao processar {os.path.basename(arquivo_entrada)}: {str(e)}"

        def processar_lote():
            with ThreadPoolExecutor() as executor:
                for resultado in executor.map(processar_arquivo, self.arquivos_selecionados):
                    if resultado:  # Se houve erro
                        processamento_lote['erros'].append(resultado)

        # Inicia o processamento em uma thread separada
        thread_processamento = Thread(target=processar_lote)
        thread_processamento.start()

        # Inicia a verificação de progresso
        atualizar_progresso()

    def tocar_audio(self):
        """Toca o áudio com o efeito de eco aplicado."""
        try:
            if self.dados_audio is not None:
                try:
                    atraso_ms, decaimento = self.validar_parametros(
                        self.entrada_atraso.get(),
                        self.entrada_decaimento.get()
                    )
                except ValueError:
                    return  # Retorna se houver erro de validação

                dados_modificados = self.adicionar_eco(self.dados_audio, atraso_ms, decaimento)

                # Limpa qualquer arquivo temporário anterior
                for arquivo in os.listdir():
                    if arquivo.startswith("temp_com_eco_") and arquivo.endswith(".wav"):
                        try:
                            os.remove(arquivo)
                        except:
                            pass  # Ignora erros se não conseguir remover

                # Gera um nome de arquivo temporário único
                arquivo_temp = f"temp_com_eco_{int(time.time() * 1000)}.wav"
                sf.write(arquivo_temp, dados_modificados, self.taxa_amostragem)

                # Para qualquer reprodução atual e reinicializa o mixer
                pygame.mixer.quit()
                pygame.mixer.init(frequency=self.taxa_amostragem)
                pygame.mixer.music.load(arquivo_temp)
                pygame.mixer.music.play()

                # Função para tentar remover o arquivo após a reprodução
                def remover_arquivo_temp():
                    try:
                        # Primeiro verifica se a música ainda está tocando
                        if not pygame.mixer.music.get_busy():
                            pygame.mixer.quit()  # Fecha o mixer para liberar o arquivo
                            if os.path.exists(arquivo_temp):
                                os.remove(arquivo_temp)
                        else:
                            # Se ainda está tocando, agenda nova tentativa
                            self.root.after(100, remover_arquivo_temp)
                    except:
                        pass  # Ignora erros na remoção

                # Agenda a primeira tentativa de remoção
                duracao_ms = int(len(dados_modificados) / self.taxa_amostragem * 1000)
                self.root.after(duracao_ms + 100, remover_arquivo_temp)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao reproduzir áudio: {e}")

    def parar_audio(self):
        """Para a reprodução do áudio atual."""
        pygame.mixer.music.stop()

    def abrir_arquivo(self):
        """Abre um diálogo para selecionar arquivo(s) de áudio."""
        arquivos = filedialog.askopenfilenames(
            filetypes=[("Arquivos WAV", "*.wav")]
        )
        
        if arquivos:
            self.arquivos_selecionados = arquivos
            if len(arquivos) == 1:
                # Se for um único arquivo, carrega para preview
                self.carregar_audio(arquivos[0])
                self.rotulo_arquivo.config(
                    text=f"Arquivo selecionado: {os.path.basename(arquivos[0])}"
                )
            else:
                # Se forem múltiplos arquivos, atualiza o rótulo
                self.rotulo_arquivo.config(
                    text=f"{len(arquivos)} arquivos selecionados para processamento"
                )
                # Desabilita botões de reprodução
                self.botao_tocar.config(state='disabled')
                self.botao_parar.config(state='disabled')

    def ao_soltar(self, evento):
        """
        Manipula o carregamento de arquivo por arrastar e soltar.

        Args:
            evento: O evento TkinterDnD de soltar contendo o caminho do arquivo.
        """
        caminhos = evento.data.strip("{}").split("} {")  # Suporta múltiplos arquivos
        self.arquivos_selecionados = caminhos
        
        if len(caminhos) == 1:
            self.carregar_audio(caminhos[0])
            self.rotulo_arquivo.config(
                text=f"Arquivo selecionado: {os.path.basename(caminhos[0])}"
            )
        else:
            self.rotulo_arquivo.config(
                text=f"{len(caminhos)} arquivos selecionados para processamento"
            )
            # Desabilita botões de reprodução para múltiplos arquivos
            self.botao_tocar.config(state='disabled')
            self.botao_parar.config(state='disabled')


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = AplicacaoEcoAudio(root)
    root.mainloop()
