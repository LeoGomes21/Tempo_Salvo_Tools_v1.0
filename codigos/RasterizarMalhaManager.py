from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QProgressBar, QComboBox, QGraphicsScene, QFileDialog, QGraphicsPixmapItem, QPushButton
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsProcessing, QgsCoordinateReferenceSystem, QgsProcessingContext, QgsMeshLayer, QgsMapSettings, QgsMapRendererCustomPainterJob, QgsProcessingFeedback, QgsRasterLayer, QgsProcessingUtils
from qgis.PyQt.QtCore import Qt, QSize, QSettings, QTimer
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QPixmap
from qgis.utils import iface
from qgis.PyQt import uic
import processing
import tempfile
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'RasterizarMalhas.ui'))

class RasterizarManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(RasterizarManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        self.iface = iface  # Armazena a referência da interface QGIS

        # Inicializa a cena gráfica
        self.scene = QGraphicsScene(self)
        self.graphicsViewMalhas.setScene(self.scene)

        # Altera o título da janela
        self.setWindowTitle("Rasterizar Malhas")

        # Preenche o comboBox com camadas de pontos
        self.populate_combo_box()

        # Conecta os sinais aos slots
        self.connect_signals()

        self.output_path = None  # Variável para armazenar o caminho

        self.lineEditSalvar.setReadOnly(True)
        self.lineEditSalvar.setText("[Salvar em arquivo temporário]")
        self.lineEditSalvar.setStyleSheet("color: silver;")

    def connect_signals(self):

        # Conecta sinais do projeto para atualizar comboBox quando camadas forem adicionadas, removidas ou renomeadas
        QgsProject.instance().layersAdded.connect(self.populate_combo_box)
        QgsProject.instance().layersRemoved.connect(self.populate_combo_box)
        QgsProject.instance().layerWillBeRemoved.connect(self.populate_combo_box)

        # Conecta o clique do botão pushButtonExecutar para executar o cálculo da malha
        self.pushButtonExecutar.clicked.connect(self.execute_Rasterizar)

        self.comboBoxCamada.currentIndexChanged.connect(self.display_mesh_layer)

        # Conectar o botão para definir o salvamento
        self.pushButtonSalvar.clicked.connect(self.definir_local_salvamento)

        # Conecta sinais para atualizar o estado do botão pushButtonExecutar
        self.comboBoxCamada.currentIndexChanged.connect(self.update_button_state)
        QgsProject.instance().layersAdded.connect(self.update_button_state)
        QgsProject.instance().layersRemoved.connect(self.update_button_state)
        self.doubleSpinBoxPixel.valueChanged.connect(self.update_button_state)

        # Conecta o botão Fechar ao slot de fechar o diálogo
        self.pushButtonFechar.clicked.connect(self.close)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(RasterizarManager, self).showEvent(event)

        self.populate_combo_box()  # Atualiza o comboBoxCamada com as camadas disponíveis

        self.display_mesh_layer()  # Atualiza a visualização ao abrir

        # Atualiza o estado do botão pushButtonExecutar
        self.update_button_state()

    def _log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, 'Malha', level=level)

    def iniciar_progress_bar(self, total_steps):
        """
        Inicia e exibe uma barra de progresso na interface do usuário para o processo de exportação.

        Parâmetros:
        - total_steps (int): O número total de etapas a serem concluídas no processo de exportação.

        Funcionalidades:
        - Cria uma mensagem personalizada na barra de mensagens para acompanhar o progresso.
        - Configura e estiliza uma barra de progresso.
        - Adiciona a barra de progresso à barra de mensagens e a exibe na interface do usuário.
        - Define o valor máximo da barra de progresso com base no número total de etapas.
        - Retorna os widgets de barra de progresso e de mensagem para que possam ser atualizados durante a exportação.
        """
        progressMessageBar = self.iface.messageBar().createMessage("Gerando a Camada de Malha")
        progressBar = QProgressBar()  # Cria uma instância da QProgressBar
        progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Alinha a barra de progresso à esquerda e verticalmente ao centro
        progressBar.setFormat("%p% - %v de %m etapas concluídas")  # Define o formato da barra de progresso
        progressBar.setMinimumWidth(300)  # Define a largura mínima da barra de progresso

        # Estiliza a barra de progresso
        progressBar.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 2px;
                background-color: #cddbde;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #55aaff;
                width: 5px;
                margin: 1px;
            }
            QProgressBar {
                min-height: 5px;}""")

        # Adiciona a progressBar ao layout da progressMessageBar e exibe na interface
        progressMessageBar.layout().addWidget(progressBar)
        self.iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)

        # Define o valor máximo da barra de progresso com base no número total de etapas
        progressBar.setMaximum(total_steps)

        return progressBar, progressMessageBar

    def update_combo_box_item(self):
        """
        Atualiza o texto dos itens no comboBoxCamada com base nos nomes atuais das camadas no projeto.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Itera sobre os itens no comboBoxCamada.
        - Para cada item, obtém o ID da camada correspondente.
        - Atualiza o nome exibido no comboBoxCamada com o nome atual da camada, caso a camada ainda exista.
        - Atualiza o campo de nome do polígono (lineEditNome) após atualizar o comboBox.
        """
        
        for i in range(self.comboBoxCamada.count()):  # Itera sobre todos os itens no comboBoxCamada
            layer_id = self.comboBoxCamada.itemData(i)  # Obtém o ID da camada para o item atual
            layer = QgsProject.instance().mapLayer(layer_id)  # Obtém a camada correspondente ao ID
            if layer:  # Verifica se a camada existe
                self.comboBoxCamada.setItemText(i, layer.name())  # Atualiza o texto do item com o nome atual da camada

    def populate_combo_box(self):
        """
        Popula o comboBoxCamada com as camadas de malhas disponíveis no projeto e realiza ações relacionadas.

        A função realiza as seguintes ações:
        - Salva a camada atualmente selecionada no comboBoxCamada.
        - Bloqueia temporariamente os sinais do comboBoxCamada para evitar atualizações desnecessárias.
        - Limpa o comboBoxCamada antes de preenchê-lo novamente.
        - Adiciona as camadas de malhas disponíveis ao comboBoxCamada.
        - Restaura a seleção da camada anterior, se possível.
        - Desbloqueia os sinais do comboBoxCamada após preenchê-lo.
        """
        current_layer_id = self.comboBoxCamada.currentData()  # Salva a camada atualmente selecionada
        self.comboBoxCamada.blockSignals(True)  # Bloqueia os sinais para evitar chamadas desnecessárias
        self.comboBoxCamada.clear()  # Limpa o comboBox antes de preencher

        layer_list = QgsProject.instance().mapLayers().values()
        for layer in layer_list:
            if isinstance(layer, QgsMeshLayer):  # Adiciona somente camadas de malhas
                self.comboBoxCamada.addItem(layer.name(), layer.id())
                layer.nameChanged.connect(self.update_combo_box_item)  # Conecta o sinal nameChanged à função update_combo_box_item

        # Restaura a seleção anterior, se possível
        if current_layer_id:
            index = self.comboBoxCamada.findData(current_layer_id)  # Tenta encontrar a camada selecionada anteriormente
            if index != -1:
                self.comboBoxCamada.setCurrentIndex(index)  # Restaura a seleção anterior

        self.comboBoxCamada.blockSignals(False)  # Desbloqueia os sinais

        self.display_mesh_layer()  # Atualiza após mudanças nas camadas
 
    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):
        """
        Permite ao usuário escolher um local e um nome de arquivo para salvar uma camada, usando uma caixa de diálogo.
        O método também gerencia nomes de arquivos para evitar sobreposição e lembra o último diretório utilizado.

        Funções e Ações Desenvolvidas:
        - Recuperação do último diretório utilizado através das configurações do QGIS.
        - Geração de um nome de arquivo único para evitar sobreposição.
        - Exibição de uma caixa de diálogo para escolha do local de salvamento.
        - Atualização do último diretório utilizado nas configurações do QGIS.

        :param nome_padrao: Nome padrão proposto para o arquivo a ser salvo.
        :param tipo_arquivo: Descrição do tipo de arquivo para a caixa de diálogo (ex. "Arquivos DXF (*.dxf)").

        :return: O caminho completo do arquivo escolhido para salvar ou None se nenhum arquivo foi escolhido.
        """
        # Acessa as configurações do QGIS para recuperar o último diretório utilizado
        settings = QSettings()
        lastDir = settings.value("lastDir", "")  # Usa uma string vazia como padrão se não houver último diretório

        # Configura as opções da caixa de diálogo para salvar arquivos
        options = QFileDialog.Options()
        
        # Gera um nome de arquivo com um sufixo numérico caso o arquivo já exista
        base_nome_padrao, extensao = os.path.splitext(nome_padrao)
        numero = 1
        nome_proposto = base_nome_padrao
        
        # Incrementa o número no nome até encontrar um nome que não exista
        while os.path.exists(os.path.join(lastDir, nome_proposto + extensao)):
            nome_proposto = f"{base_nome_padrao}_{numero}"
            numero += 1

        # Propõe o nome completo no último diretório utilizado
        nome_completo_proposto = os.path.join(lastDir, nome_proposto + extensao)

        # Exibe a caixa de diálogo para salvar arquivos com o nome proposto
        fileName, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Camada",
            nome_completo_proposto,
            tipo_arquivo,
            options=options)

        # Adicionar verificação de permissão de escrita
        if fileName and not os.access(os.path.dirname(fileName), os.W_OK):
            self.mostrar_mensagem(f"Sem permissão para escrever em: {os.path.dirname(fileName)}", "Erro")
            return None

        return fileName  # Retorna o caminho completo do arquivo escolhido ou None se cancelado

    def definir_local_salvamento(self):
        caminho = self.escolher_local_para_salvar("Tiff_TIN", "Raster (*.tiff)")
        if caminho:
            self.lineEditSalvar.setText(caminho)
            self.lineEditSalvar.setStyleSheet("color: black;")
        else:
            self.lineEditSalvar.setText("[Salvar em arquivo temporário]")
            self.lineEditSalvar.setStyleSheet("color: silver;")

    def update_button_state(self):
        """
        Atualiza o estado do botão pushButtonExecutar.
        O botão será desativado se:
          - Nenhuma camada estiver selecionada, ou
          - O valor de doubleSpinBoxPixel for 0.
        """
        layer_id = self.comboBoxCamada.currentData()
        pixel_value = self.doubleSpinBoxPixel.value()
        if not layer_id or pixel_value <= 0:
            self.pushButtonExecutar.setEnabled(False)
        else:
            self.pushButtonExecutar.setEnabled(True)

    def display_mesh_layer(self):
        """
        Exibe a camada de malha selecionada no QGraphicsView, renderizando uma visualização da malha.

        Funcionalidades:
        - Limpa a cena gráfica antes de adicionar um novo item.
        - Obtém o ID da camada de malha selecionada no ComboBox.
        - Configura as definições de mapa e renderiza a camada de malha como uma imagem.
        - Adiciona a imagem renderizada ao QGraphicsView e ajusta a visualização para manter a proporção.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """
        # Limpa a cena antes de adicionar um novo item
        self.scene.clear()  # Remove todos os itens da cena atual

        # Obtém o ID da camada de malha selecionada no ComboBox
        selected_mesh_id = self.comboBoxCamada.currentData()

        # Busca a camada de malha no projeto pelo seu ID
        selected_layer = QgsProject.instance().mapLayer(selected_mesh_id)

        # Verifica se a camada selecionada é de fato uma camada de malha
        if isinstance(selected_layer, QgsMeshLayer):

            # Exemplo: caso você queira exibir informações sobre a malha
            # self.set_informacoes_malha(selected_layer)

            # Configura as definições do mapa
            map_settings = QgsMapSettings()
            map_settings.setLayers([selected_layer])  # Define a camada de malha como a única camada a ser renderizada
            map_settings.setBackgroundColor(QColor(255, 255, 255))  # Define a cor de fundo (branco)

            # Define o tamanho da imagem com base no tamanho da área de visualização
            width = self.graphicsViewMalhas.viewport().width()
            height = self.graphicsViewMalhas.viewport().height()
            map_settings.setOutputSize(QSize(width, height))

            # Ajusta a extensão para a extensão da malha
            map_settings.setExtent(selected_layer.extent())

            # Cria uma imagem transparente para renderizar a camada de malha
            image = QImage(width, height, QImage.Format_ARGB32)
            image.fill(Qt.transparent)

            # Configura o QPainter para renderizar a imagem
            painter = QPainter(image)
            render_job = QgsMapRendererCustomPainterJob(map_settings, painter)

            # Executa o trabalho de renderização
            render_job.start()
            render_job.waitForFinished()
            painter.end()  # Finaliza o pintor

            # Converte a imagem renderizada para QPixmap e cria um item gráfico
            pixmap = QPixmap.fromImage(image)
            pixmap_item = QGraphicsPixmapItem(pixmap)

            # Adiciona o item à cena gráfica
            self.scene.addItem(pixmap_item)

            # Ajusta a cena ao QGraphicsView, mantendo a proporção
            self.graphicsViewMalhas.setSceneRect(pixmap_item.boundingRect())
            self.graphicsViewMalhas.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        else:
            # Se a camada não for uma malha, opcionalmente você pode mostrar uma mensagem
            # ou simplesmente não fazer nada.
            pass

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivo=None):
        """
        Exibe uma mensagem na barra de mensagens do QGIS, proporcionando feedback ao usuário.
        Se um caminho de pasta ou arquivo for informado, um botão para abri-lo será adicionado.
        
        A mensagem será removida automaticamente após 'duracao' segundos.
        
        :param texto: Texto da mensagem.
        :param tipo: "Erro" ou "Sucesso".
        :param duracao: Duração da mensagem (em segundos).
        :param caminho_pasta: Caminho da pasta a ser aberta (somente se definido pelo usuário).
        :param caminho_arquivo: Caminho do arquivo a ser aberto.
        """
        bar = self.iface.messageBar()

        if tipo == "Erro":
            bar.pushMessage("Erro", texto, level=Qgis.Critical, duration=duracao)
        elif tipo == "Sucesso":
            msg = bar.createMessage("Sucesso", texto)
            layout = msg.layout()
            if caminho_pasta:
                botao_abrir_pasta = QPushButton("Abrir Pasta")
                botao_abrir_pasta.clicked.connect(lambda: os.startfile(caminho_pasta))
                layout.addWidget(botao_abrir_pasta)
            if caminho_arquivo:
                botao_abrir_arquivo = QPushButton("Abrir Arquivo")
                botao_abrir_arquivo.clicked.connect(lambda: os.startfile(caminho_arquivo))
                layout.addWidget(botao_abrir_arquivo)
            bar.pushWidget(msg, Qgis.Info)
            # Fecha a mensagem automaticamente após 'duracao' segundos
            QTimer.singleShot(duracao * 1000, lambda: bar.clearWidgets())

    def execute_Rasterizar(self):
        """
        Executa a rasterização da camada de malha selecionada e adiciona o raster resultante ao projeto.
        
        A função realiza as seguintes operações:
        
        - Inicia uma barra de progresso com 5 etapas para fornecer feedback visual do processo.
        - Valida se uma camada de malha (QgsMeshLayer) foi selecionada e se ela é válida.
        - Verifica se a camada de malha contém dados (grupos de dataset) para rasterizar.
        - Obtém e valida o valor do tamanho do pixel a partir do doubleSpinBoxPixel.
        - Gera um nome de arquivo base utilizando o nome da camada de malha.
          - Se o usuário não definir um caminho de salvamento, utiliza um diretório temporário.
          - Se o usuário definir um caminho, garante que o nome termine com a extensão ".tif".
          - Caso já exista um arquivo com o mesmo nome, acrescenta sufixos (_1, _2, etc.) para garantir um nome único.
        - Prepara os parâmetros para o algoritmo "native:meshrasterize", incluindo:
          - A camada de malha de entrada.
          - O grupo de dataset (fixado como [0]).
          - O dataset time definido como estático.
          - A extensão da camada.
          - O tamanho do pixel.
          - O CRS de saída (igual ao da camada de entrada).
          - O caminho de saída para o raster.
        - Executa o algoritmo de processamento "native:meshrasterize".
        - Verifica se o arquivo de saída foi criado corretamente.
        - Gera um nome único para a camada raster a ser adicionada ao projeto, acrescentando sufixos se necessário.
        - Carrega o raster resultante como uma QgsRasterLayer e adiciona-o ao projeto, se for válido.
        - Exibe uma mensagem de sucesso (com um botão "Abrir Pasta" se o usuário tiver definido um caminho) por 3 segundos.
        - Em caso de erro, exibe uma mensagem de erro e tenta remover o arquivo de saída, se existir.
        - Atualiza a barra de progresso em 5 etapas e a fecha automaticamente após 1 segundo.
        
        :return: None
        """
        def get_unique_filename(directory, base_filename):
            candidate = os.path.join(directory, base_filename)
            if not os.path.exists(candidate):
                return candidate
            else:
                i = 1
                name, ext = os.path.splitext(base_filename)
                while True:
                    candidate = os.path.join(directory, f"{name}_{i}{ext}")
                    if not os.path.exists(candidate):
                        return candidate
                    i += 1

        total_steps = 5  # definindo total de etapas para a barra de progresso
        progress_bar, progress_message = self.iniciar_progress_bar(total_steps)

        # Etapa 1: Iniciando
        progress_bar.setValue(1)

        layer_id = self.comboBoxCamada.currentData()
        layer = QgsProject.instance().mapLayer(layer_id)
        
        if not isinstance(layer, QgsMeshLayer) or not layer.isValid():
            self.mostrar_mensagem("Selecione uma camada de malha válida!", "Erro")
            self.iface.messageBar().clearWidgets()
            return

        if layer.datasetGroupCount() == 0:
            self.mostrar_mensagem("A malha não contém dados para rasterizar!", "Erro")
            self.iface.messageBar().clearWidgets()
            return

        pixel_size = self.doubleSpinBoxPixel.value()
        if pixel_size <= 0:
            self.mostrar_mensagem("Tamanho de pixel inválido", "Erro")
            self.iface.messageBar().clearWidgets()
            return

        mesh_name = layer.name()
        default_filename = f"{mesh_name}.tif"

        output_path_text = self.lineEditSalvar.text().strip()
        if not output_path_text or output_path_text == "[Salvar em arquivo temporário]":
            temp_dir = QgsProcessingUtils.tempFolder()
            output_path = os.path.join(temp_dir, default_filename)
        else:
            if not output_path_text.lower().endswith('.tif'):
                output_path_text += '.tif'
            output_path = output_path_text

        output_dir = os.path.dirname(output_path)
        if not os.access(output_dir, os.W_OK):
            self.mostrar_mensagem(f"Sem permissão de escrita em: {output_dir}", "Erro")
            self.iface.messageBar().clearWidgets()
            return

        output_path = get_unique_filename(output_dir, os.path.basename(output_path))

        # Etapa 2: Preparação dos parâmetros concluída
        progress_bar.setValue(2)

        parameters = {
            'INPUT': layer,
            'DATASET_GROUPS': [0],
            'DATASET_TIME': {'type': 'static'},
            'EXTENT': layer.extent(),
            'PIXEL_SIZE': pixel_size,
            'CRS_OUTPUT': layer.crs(),
            'OUTPUT': output_path
        }

        # Etapa 3: Executando o processamento
        progress_bar.setValue(3)
        try:
            result = processing.run("native:meshrasterize", parameters)
            
            if not os.path.exists(result['OUTPUT']):
                raise Exception("Arquivo de saída não foi criado")

            # Etapa 4: Carregando o raster
            progress_bar.setValue(4)
            
            base_layer_name = mesh_name
            candidate_name = base_layer_name
            i = 1
            existing_layers = [l.name() for l in QgsProject.instance().mapLayers().values()]
            while candidate_name in existing_layers:
                candidate_name = f"{base_layer_name}_{i}"
                i += 1

            output_layer = QgsRasterLayer(result['OUTPUT'], candidate_name, "gdal")
            if output_layer.isValid():
                QgsProject.instance().addMapLayer(output_layer)
                if self.lineEditSalvar.text().strip() not in ["", "[Salvar em arquivo temporário]"]:
                    self.mostrar_mensagem("Raster criado com sucesso!", "Sucesso", duracao=3, caminho_pasta=output_dir)
                else:
                    self.mostrar_mensagem("Raster criado com sucesso!", "Sucesso", duracao=3)
            else:
                raise Exception("Falha ao carregar camada raster")

            # Etapa 5: Finalizado
            progress_bar.setValue(5)
            
        except Exception as e:
            self.mostrar_mensagem(f"Erro: {str(e)}", "Erro")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            self.iface.messageBar().clearWidgets()
            return

        # Fecha automaticamente a barra de progresso após um breve intervalo
        QTimer.singleShot(1000, lambda: self.iface.messageBar().clearWidgets())

