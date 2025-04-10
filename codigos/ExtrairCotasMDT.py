from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QComboBox, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLineEdit, QMessageBox, QProgressBar
from qgis.core import QgsProject, QgsRasterLayer, QgsMapSettings, QgsMapRendererCustomPainterJob, Qgis, QgsMessageLog, QgsRasterLayer, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapSettings, QgsMessageLog, QgsColorRampShader, QgsRendererRange, QgsGraduatedSymbolRenderer, QgsFillSymbol, Qgis, QgsField, QgsField, QgsPointXY, QgsRaster, QgsPoint, QgsFeature, QgsGeometry, QgsRectangle
from qgis.PyQt.QtGui import QImage, QPainter, QPixmap, QColor
from qgis.PyQt.QtCore import Qt, QRectF, QPointF, QSize, QVariant
from qgis.gui import QgsMapCanvas
from qgis.utils import iface
from qgis.PyQt import uic
import time
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ExtrairCotasMDT.ui'))

class CotasManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """
        Inicializa a janela de extração de cotas de um raster.
        
        Parâmetros:
        - parent (opcional): O widget pai desta janela de diálogo, se houver.
        
        Funcionalidades:
        - Configura a interface do usuário (UI) criada no Designer.
        - Ajusta a janela e os campos de entrada com placeholders.
        - Conecta botões e sinais a funções.
        - Inicializa o ComboBox com as camadas raster do projeto atual.
        """
        super(CotasManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        self.iface = iface

        # Altera o título da janela
        self.setWindowTitle("Extrair Cotas de Raster")

        # Cria uma cena gráfica para o QGraphicsView
        self.scene = QGraphicsScene()
        self.graphicsViewRaster.setScene(self.scene)

        self.lineEditSistemaReferencia.setPlaceholderText("Sistema de referência:")  # Texto de placeholder
        self.lineEditSistemaReferencia.setReadOnly(True)  # Campo somente leitura

        self.lineEditResolucao.setPlaceholderText("Resolução do Pixel:")  # Texto de placeholder
        self.lineEditResolucao.setReadOnly(True)  # Campo somente leitura

        self.lineEditQuantidade.setPlaceholderText("Total de Pixel:")  # Texto de placeholder
        self.lineEditQuantidade.setReadOnly(True)  # Campo somente leitura

        # Conecta para executar a extração das cotas do Raster
        self.okButton.clicked.connect(self.extrair_cotas)

        self.cancelButton.clicked.connect(self.reject)  # Conecta o clique do botão à função reject

        # Inicializa o ComboBox de Raster
        self.init_combo_box_raster()

        # Conecta os sinais aos slots
        self.connect_signals()

    def limpar_informacoes_camada(self):
        """
        Limpa os campos de entrada relacionados às informações da camada raster (resolução, total de pixels e sistema de referência).

        Funcionalidades:
        - Limpa o texto exibido nos campos de entrada para resolução, total de pixels e sistema de referência.
        - Remove o estilo customizado dos campos de entrada, voltando ao padrão.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Limpa o campo de texto da resolução do pixel e redefine o estilo
        self.lineEditResolucao.clear()  # Remove o texto da linha de edição de resolução
        self.lineEditResolucao.setStyleSheet("")  # Remove qualquer estilo aplicado (cor, bordas, etc.)

        # Limpa o campo de texto do total de pixels e redefine o estilo
        self.lineEditQuantidade.clear()  # Remove o texto da linha de edição do total de pixels
        self.lineEditQuantidade.setStyleSheet("")  # Remove qualquer estilo aplicado

        # Limpa o campo de texto do sistema de referência e redefine o estilo
        self.lineEditSistemaReferencia.clear()  # Remove o texto da linha de edição do sistema de referência
        self.lineEditSistemaReferencia.setStyleSheet("")  # Remove qualquer estilo aplicado

    def init_combo_box_raster(self):
        """
        Inicializa o ComboBox com as camadas raster disponíveis no projeto atual.

        Funcionalidades:
        - Obtém todas as camadas carregadas no projeto e filtra apenas as camadas raster.
        - Limpa o ComboBox e o preenche com os nomes e IDs das camadas raster.
        - Seleciona automaticamente a primeira camada raster disponível (se houver) e exibe a visualização da mesma.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """
        # Obtém todas as camadas do projeto atual
        layers = QgsProject.instance().mapLayers().values()
        
        # Filtra apenas camadas raster
        raster_layers = [layer for layer in layers if layer.type() == layer.RasterLayer]
        
        # Limpa o ComboBox antes de adicionar itens
        self.comboBoxRaster.clear()
        
        # Adiciona as camadas raster ao ComboBox
        for raster_layer in raster_layers:
            self.comboBoxRaster.addItem(raster_layer.name(), raster_layer.id())

        # Seleciona a primeira camada raster, se existir
        if raster_layers:
            self.comboBoxRaster.setCurrentIndex(0) # Seleciona o primeiro item da lista no ComboBox
            self.display_raster() # Chama a função para exibir a visualização da camada selecionada

    def connect_signals(self):
        """
        Conecta os sinais de eventos da interface gráfica aos seus respectivos slots (funções) para gerenciar o comportamento
        da aplicação quando eventos específicos ocorrem.

        Funcionalidades:
        - Conecta a mudança de índice do ComboBox às funções de atualização da visualização raster.
        - Conecta os sinais de adição, remoção e alteração de camadas no projeto QGIS à atualização do ComboBox.
        - Conecta as mudanças de estado dos checkboxes à função que habilita ou desabilita o botão "OK".

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Conecta o evento de mudança de índice do ComboBox (quando o usuário escolhe outra camada) à função de exibir o raster correspondente
        self.comboBoxRaster.currentIndexChanged.connect(self.display_raster)

        # Conecta o sinal de remoção de camada ao método que atualiza o ComboBox
        QgsProject.instance().layersRemoved.connect(self.update_combo_box)

        # Conecta o sinal de adição de camada ao método que lida com a adição de novas camadas
        QgsProject.instance().layersAdded.connect(self.handle_layers_added)

        # Para cada camada no projeto, conecta o sinal de mudança de nome ao método que atualiza o ComboBox
        for layer in QgsProject.instance().mapLayers().values():
            layer.nameChanged.connect(self.update_combo_box)

        # Conecta o evento de mudança de índice do ComboBox novamente a uma função que atualiza informações específicas da camada raster
        self.comboBoxRaster.currentIndexChanged.connect(self.on_combo_box_raster_changed)

        # Conecta as mudanças de estado dos checkboxes (marcado/desmarcado) à função que verifica se o botão "OK" deve ser habilitado
        self.checkboxPontos.stateChanged.connect(self.verificar_estado_componentes_checkboxes)
        self.checkboxPoligonos.stateChanged.connect(self.verificar_estado_componentes_checkboxes)
        self.checkboxEstilizada.stateChanged.connect(self.verificar_estado_componentes_checkboxes)
        self.checkboxAtribuida.stateChanged.connect(self.verificar_estado_componentes_checkboxes)

    def update_combo_box(self):
        """
        Atualiza o ComboBox de camadas raster quando há mudanças no projeto, como adição, remoção ou renomeação de camadas.
        
        Funcionalidades:
        - Atualiza o ComboBox para refletir as camadas raster disponíveis no projeto.
        - Restaura a seleção anterior no ComboBox, se possível.
        - Caso a camada anteriormente selecionada tenha sido removida, seleciona a primeira camada disponível.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Armazena o índice atual do ComboBox e o ID da camada selecionada para restaurar depois da atualização
        current_index = self.comboBoxRaster.currentIndex()  # Índice atual do ComboBox
        current_layer_id = self.comboBoxRaster.itemData(current_index)  # ID da camada raster atualmente selecionada

        # Atualiza o ComboBox com as camadas raster disponíveis (recarrega o ComboBox)
        self.init_combo_box_raster()

        # Tenta restaurar a seleção anterior com base no ID da camada
        if current_layer_id:
            index = self.comboBoxRaster.findData(current_layer_id)  # Encontra o índice do item que corresponde ao ID da camada anterior
            if index != -1:
                self.comboBoxRaster.setCurrentIndex(index)  # Se o índice for encontrado, restaura a seleção anterior
            else:
                # Se a camada anteriormente selecionada não existir mais, seleciona a primeira camada disponível no ComboBox
                if self.comboBoxRaster.count() > 0:
                    self.comboBoxRaster.setCurrentIndex(0)  # Seleciona o primeiro item do ComboBox
                    self.display_raster()  # Exibe o raster correspondente à nova seleção

    def display_raster(self):
        """
        Exibe a camada raster selecionada no QGraphicsView, renderizando uma visualização do raster.

        Funcionalidades:
        - Limpa a cena gráfica antes de adicionar um novo item.
        - Obtém o ID da camada raster selecionada no ComboBox.
        - Configura as definições de mapa e renderiza a camada raster como uma imagem.
        - Adiciona a imagem renderizada ao QGraphicsView e ajusta a visualização para manter a proporção.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """
        # Limpa a cena antes de adicionar um novo item
        self.scene.clear()  # Remove todos os itens da cena atual

        # Obtém o ID da camada raster selecionada no ComboBox
        selected_raster_id = self.comboBoxRaster.currentData()  # Coleta o ID da camada raster selecionada

        # Busca a camada raster no projeto pelo seu ID
        selected_layer = QgsProject.instance().mapLayer(selected_raster_id)  # Localiza a camada raster no projeto

        # Verifica se a camada selecionada é uma camada raster
        if isinstance(selected_layer, QgsRasterLayer):
            # Define as informações da camada e verifica o estado dos checkboxes
            self.set_informacoes_camada(selected_layer)

            # Configura as definições do mapa
            map_settings = QgsMapSettings()  # Cria uma instância de QgsMapSettings para configurar a renderização do mapa
            map_settings.setLayers([selected_layer])  # Define a camada raster como a única camada a ser renderizada
            map_settings.setBackgroundColor(QColor(255, 255, 255))  # Define a cor de fundo como branco

            # Define o tamanho da imagem a ser renderizada com base no tamanho da área de visualização (QGraphicsView)
            width = self.graphicsViewRaster.viewport().width()  # Largura da área de visualização
            height = self.graphicsViewRaster.viewport().height()  # Altura da área de visualização
            map_settings.setOutputSize(QSize(width, height))  # Define o tamanho da imagem a ser gerada

            # Define a extensão do mapa para corresponder à extensão da camada raster
            map_settings.setExtent(selected_layer.extent())  # Ajusta a extensão da visualização para cobrir a área do raster

            # Cria uma imagem transparente para renderizar o raster
            image = QImage(width, height, QImage.Format_ARGB32)  # Cria uma imagem no formato ARGB (com transparência)
            image.fill(Qt.transparent)  # Preenche a imagem com transparência

            # Configura o pintor (QPainter) para renderizar a imagem
            painter = QPainter(image)  # Cria um pintor para desenhar na imagem
            render_job = QgsMapRendererCustomPainterJob(map_settings, painter)  # Define um trabalho de renderização personalizado

            # Executa o trabalho de renderização
            render_job.start()  # Inicia a renderização da imagem
            render_job.waitForFinished()  # Aguarda a conclusão da renderização
            painter.end()  # Finaliza o pintor

            # Cria um QPixmap a partir da imagem renderizada
            pixmap = QPixmap.fromImage(image)  # Converte a imagem renderizada para um QPixmap
            pixmap_item = QGraphicsPixmapItem(pixmap)  # Cria um item gráfico para o pixmap

            # Adiciona o item à cena gráfica
            self.scene.addItem(pixmap_item)  # Insere o pixmap na cena do QGraphicsView

            # Ajusta a cena ao QGraphicsView, garantindo que a proporção seja preservada
            self.graphicsViewRaster.setSceneRect(pixmap_item.boundingRect())  # Define os limites da cena com base no tamanho do pixmap
            self.graphicsViewRaster.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)  # Ajusta a visualização para manter a proporção da imagem

    def showEvent(self, event):
        """
        Evento chamado quando a janela de diálogo é mostrada.
        
        Funcionalidades:
        - Reseta os componentes do diálogo para o estado inicial.
        - Ajusta a visualização do raster selecionado no QGraphicsView.
        - Verifica o estado inicial dos checkboxes e do botão "OK".
        - Atualiza as informações da camada selecionada no ComboBox.

        Parâmetros:
        - event: O evento de exibição da janela, do tipo QShowEvent.

        Retorna:
        - None.
        """

        # Chama o método da classe base (QDialog) para garantir que o evento seja tratado corretamente
        super(CotasManager, self).showEvent(event)

        # Reseta os componentes (checkboxes, campos de texto, etc.) ao mostrar o diálogo
        self.resetar_componentes()

        # Ajusta a visualização do raster quando o diálogo é mostrado
        self.display_raster()

        # Verifica o estado inicial dos checkboxes e habilita/desabilita componentes conforme necessário
        self.verificar_estado_inicial()

        # Atualiza as informações da camada selecionada no ComboBox, garantindo que os dados estejam corretos
        self.on_combo_box_raster_changed()

    def update_combo_box(self):
        """
        Atualiza o ComboBox de camadas raster quando há mudanças no projeto, como adição, remoção ou renomeação de camadas.
        
        Funcionalidades:
        - Atualiza o ComboBox para refletir as camadas raster disponíveis no projeto.
        - Restaura a seleção anterior no ComboBox, se possível.
        - Caso a camada anteriormente selecionada tenha sido removida, seleciona a primeira camada disponível.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Armazena o índice atual do ComboBox e o ID da camada selecionada para restaurar depois da atualização
        current_index = self.comboBoxRaster.currentIndex()  # Armazena o índice atual do ComboBox
        current_layer_id = self.comboBoxRaster.itemData(current_index)  # Armazena o ID da camada selecionada atualmente

        # Atualiza o ComboBox com as camadas raster disponíveis (recarrega o ComboBox)
        self.init_combo_box_raster()  # Recarrega o ComboBox com as camadas raster presentes no projeto

        # Tenta restaurar a seleção anterior com base no ID da camada
        if current_layer_id:
            index = self.comboBoxRaster.findData(current_layer_id)  # Encontra o índice do item que corresponde ao ID da camada anterior
            if index != -1:
                self.comboBoxRaster.setCurrentIndex(index)  # Se o índice for encontrado, restaura a seleção anterior
            else:
                # Se a camada anteriormente selecionada não existir mais, seleciona a primeira camada disponível no ComboBox
                if self.comboBoxRaster.count() > 0:
                    self.comboBoxRaster.setCurrentIndex(0)  # Seleciona o primeiro item do ComboBox
                    self.display_raster()  # Exibe o raster correspondente à nova seleção

    def handle_layers_added(self, layers):
        """
        Manipula o evento de adição de novas camadas ao projeto QGIS.

        Funcionalidades:
        - Quando novas camadas são adicionadas ao projeto, o ComboBox de camadas raster é atualizado automaticamente.

        Parâmetros:
        - layers: Lista de camadas que foram adicionadas ao projeto.

        Retorna:
        - None.
        """

        # Chama a função de atualização do ComboBox quando novas camadas são adicionadas
        self.update_combo_box()

    def closeEvent(self, event):
        """
        Evento chamado quando a janela de diálogo é fechada.

        Funcionalidades:
        - Define a variável `cotas_dlg` do pai (se existir) como `None`, indicando que o diálogo foi fechado.
        - Chama o método `closeEvent` da classe base para garantir o fechamento adequado da janela.

        Parâmetros:
        - event: O evento de fechamento da janela, do tipo QCloseEvent.

        Retorna:
        - None.
        """

        # Obtém o widget pai do diálogo
        parent = self.parent()  # Obtém o pai (se existir)

        # Se o pai existir, define o atributo cotas_dlg do pai como None
        if parent:
            parent.cotas_dlg = None  # Sinaliza que o diálogo de cotas foi fechado

        # Chama o método closeEvent da classe base (QDialog) para continuar o processo padrão de fechamento
        super(CotasManager, self).closeEvent(event)

    def mostrar_mensagem(self, texto, tipo, duracao=3):
        """
        Exibe uma mensagem na barra de mensagens da interface do QGIS, proporcionando feedback ao usuário.

        Funcionalidades:
        - Exibe uma mensagem de erro ou sucesso na barra de mensagens com um nível e duração apropriados.
        - A mensagem pode ser de dois tipos: "Erro" (nível crítico) ou "Sucesso" (nível informativo).
        - O tempo de exibição da mensagem pode ser ajustado.

        Parâmetros:
        - texto: O texto da mensagem a ser exibida.
        - tipo: O tipo da mensagem ("Erro" ou "Sucesso") que determina o estilo e ícone da mensagem.
        - duracao: Duração em segundos durante a qual a mensagem será exibida (padrão é 3 segundos).

        Retorna:
        - None.
        """
        # Obtém a barra de mensagens da interface do QGIS
        bar = iface.messageBar()  # Acessa a barra de mensagens da interface do QGIS

        # Exibe a mensagem com o nível apropriado baseado no tipo
        if tipo == "Erro":
            # Mostra uma mensagem de erro na barra de mensagens com um ícone crítico e a duração especificada
            bar.pushMessage("Erro", texto, level=Qgis.Critical, duration=duracao)
        elif tipo == "Sucesso":
            # Cria o item da mensagem
            msg = bar.createMessage("Sucesso", texto)
            
            # Adiciona a mensagem à barra com o nível informativo e a duração especificada
            bar.pushWidget(msg, level=Qgis.Info, duration=duracao)

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
        progressMessageBar = self.iface.messageBar().createMessage("Extraindo cotas do Raster")
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

    def set_informacoes_camada(self, layer):
        """
        Define a camada e verifica os checkboxes.

        Passos detalhados:
        1. Define a camada selecionada como um atributo da instância.

        Parâmetros:
        - layer: Camada selecionada.
        """
        self.layer = layer  # Define a camada selecionada como um atributo da instância

        # Conectar o sinal de mudança de renderização à função display_raster
        self.layer.rendererChanged.connect(self.display_raster)

    def atualizar_informacoes_camada(self):
        """
        Atualiza as informações da camada raster selecionada, como resolução do pixel, total de pixels e sistema de referência.
        
        Funcionalidades:
        - Verifica se a camada é válida e se tem dimensões adequadas.
        - Calcula a resolução do pixel em X e Y.
        - Verifica se a camada está em coordenadas geográficas e realiza transformações, se necessário.
        - Atualiza os campos de texto na interface com a resolução do pixel, total de pixels e sistema de referência.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """
        if not self.layer:
            return  # Ou mostre uma mensagem de erro para o usuário

        provider = self.layer.dataProvider()  # Obtém o provedor de dados da camada
        extent = self.layer.extent()  # Obtém a extensão da camada
        width = provider.xSize()  # Calcula a largura da camada raster em pixels
        height = provider.ySize()  # Calcula a altura da camada raster em pixels

        # Chama a função para habilitar ou desabilitar checkboxes e botão "OK"
        self.verificar_estado_componentes(width, height)

        if width == 0 or height == 0:
            return  # Sai da função, já que a camada é inválida

        # Verifica se a camada está em coordenadas geográficas
        if self.layer.crs().isGeographic():
            # Cria uma transformação de coordenadas para um sistema de coordenadas projetadas (por exemplo, UTM)
            target_crs = QgsCoordinateReferenceSystem(3857)  # EPSG:3857 - Pseudo-Mercator
            transform = QgsCoordinateTransform(self.layer.crs(), target_crs, QgsProject.instance())
            transformed_extent = transform.transformBoundingBox(extent)
            pixelSizeX = transformed_extent.width() / width  # Calcula a resolução do pixel em X
            pixelSizeY = transformed_extent.height() / height  # Calcula a resolução do pixel em Y
        else:
            pixelSizeX = extent.width() / width  # Calcula a resolução do pixel em X
            pixelSizeY = extent.height() / height  # Calcula a resolução do pixel em Y

        # Atualiza o campo de texto da resolução do pixel
        self.lineEditResolucao.setText(f"{pixelSizeX:.3f} x {pixelSizeY:.3f} Pixels")
        self.lineEditResolucao.setStyleSheet("color: green;")  # Define a cor do texto como verde

        # Atualiza o campo de texto do total de pixels
        self.lineEditQuantidade.setText(f"{width * height} Pixels")
        self.lineEditQuantidade.setStyleSheet("color: red;")  # Define a cor do texto como vermelho

        crs = self.layer.crs()  # Obtém o sistema de referência da camada
        crs_description = f"{crs.authid()} - {crs.description()}"  # Obtém a descrição completa do sistema de referência
        # Atualiza o campo de texto do sistema de referência
        self.lineEditSistemaReferencia.setText(crs_description)
        self.lineEditSistemaReferencia.setStyleSheet("color: blue;")  # Define a cor do texto como azul

    def verificar_estado_componentes(self, width, height):
        """
        Verifica o estado da camada selecionada e habilita ou desabilita os checkboxes e o botão "OK"
        com base no tamanho da camada raster (width e height).

        Funcionalidades:
        - Se a camada tiver tamanho inválido (width ou height = 0), limpa os campos de texto e desabilita os checkboxes e o botão "OK".
        - Se a camada for válida, habilita os checkboxes e controla o botão "OK" com base no estado dos checkboxes.

        Parâmetros:
        - width: Largura da camada raster em pixels.
        - height: Altura da camada raster em pixels.

        Retorna:
        - None.
        """

        # Verifica se a largura ou altura da camada é 0 (camada inválida)
        if width == 0 or height == 0:
            # Limpa os campos de texto e remove qualquer estilo customizado
            self.lineEditResolucao.clear()  # Limpa o campo de resolução de pixel
            self.lineEditResolucao.setStyleSheet("")  # Remove o estilo customizado do campo de resolução
            self.lineEditQuantidade.clear()  # Limpa o campo de quantidade de pixels
            self.lineEditQuantidade.setStyleSheet("")  # Remove o estilo customizado do campo de quantidade
            self.lineEditSistemaReferencia.clear()  # Limpa o campo do sistema de referência
            self.lineEditSistemaReferencia.setStyleSheet("")  # Remove o estilo customizado do campo de sistema de referência

            # Desativa os checkboxes e desmarca todos
            self.checkboxPontos.setChecked(False)  # Desmarca o checkbox de pontos
            self.checkboxPoligonos.setChecked(False)  # Desmarca o checkbox de polígonos
            self.checkboxEstilizada.setChecked(False)  # Desmarca o checkbox de estilo
            self.checkboxAtribuida.setChecked(False)  # Desmarca o checkbox de atribuição
            self.checkboxPontos.setEnabled(False)  # Desativa o checkbox de pontos
            self.checkboxPoligonos.setEnabled(False)  # Desativa o checkbox de polígonos
            self.checkboxEstilizada.setEnabled(False)  # Desativa o checkbox de estilo
            self.checkboxAtribuida.setEnabled(False)  # Desativa o checkbox de atribuição

            # Desativa o botão "OK"
            self.okButton.setEnabled(False)  # Desativa o botão "OK"
        
        else:
            # Habilita todos os checkboxes, já que a camada é válida
            self.checkboxPontos.setEnabled(True)  # Habilita o checkbox de pontos
            self.checkboxPoligonos.setEnabled(True)  # Habilita o checkbox de polígonos
            self.checkboxEstilizada.setEnabled(True)  # Habilita o checkbox de estilo
            self.checkboxAtribuida.setEnabled(True)  # Habilita o checkbox de atribuição

            # Ativa o botão "OK" apenas se pelo menos um checkbox estiver marcado
            if (self.checkboxPontos.isChecked() or 
                self.checkboxPoligonos.isChecked() or 
                self.checkboxEstilizada.isChecked() or 
                self.checkboxAtribuida.isChecked()):
                self.okButton.setEnabled(True)  # Ativa o botão "OK" se algum checkbox estiver marcado
            else:
                self.okButton.setEnabled(False)  # Desativa o botão "OK" se nenhum checkbox estiver marcado

    def verificar_estado_componentes_checkboxes(self):
        """
        Verifica se pelo menos um checkbox está marcado para ativar o botão "OK".
        
        Funcionalidades:
        - Ativa o botão "OK" se qualquer um dos checkboxes estiver marcado.
        - Desativa o botão "OK" se nenhum checkbox estiver marcado.
        
        Este método deve ser chamado sempre que o estado de um checkbox mudar, 
        para garantir que o botão "OK" só esteja ativo quando há uma opção selecionada.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Verifica se pelo menos um dos checkboxes está marcado
        if (self.checkboxPontos.isChecked() or  # Verifica se o checkbox de pontos está marcado
            self.checkboxPoligonos.isChecked() or  # Verifica se o checkbox de polígonos está marcado
            self.checkboxEstilizada.isChecked() or  # Verifica se o checkbox de estilização está marcado
            self.checkboxAtribuida.isChecked()):  # Verifica se o checkbox de atribuição está marcado
            self.okButton.setEnabled(True)  # Ativa o botão "OK" se qualquer um dos checkboxes estiver marcado
        else:
            self.okButton.setEnabled(False)  # Desativa o botão "OK" se nenhum checkbox estiver marcado

    def on_combo_box_raster_changed(self):
        """
        Atualiza a camada raster selecionada e suas informações associadas quando o ComboBox é alterado.
        
        Funcionalidades:
        - Obtém a camada raster selecionada com base no ID atual do ComboBox.
        - Atualiza as informações associadas à camada (como resolução, sistema de referência, etc.).
        
        Este método é chamado sempre que o usuário seleciona uma nova camada raster no ComboBox.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Obtém o ID da camada raster atualmente selecionada no ComboBox
        selected_layer_id = self.comboBoxRaster.currentData()  # Coleta o ID da camada selecionada no ComboBox

        # Atualiza a camada selecionada no projeto com base no ID
        self.layer = QgsProject.instance().mapLayer(selected_layer_id)  # Obtém a camada raster associada ao ID no projeto

        # Atualiza as informações associadas à camada selecionada (resolução, total de pixels, sistema de referência, etc.)
        self.atualizar_informacoes_camada()  # Chama o método para atualizar as informações da camada

    def verificar_estado_inicial(self):
        """
        Verifica o estado inicial da camada selecionada no diálogo e ajusta os componentes (checkboxes e botão "OK").

        Funcionalidades:
        - Obtém a camada raster selecionada no ComboBox ao iniciar o diálogo.
        - Verifica as dimensões da camada (largura e altura).
        - Habilita ou desabilita os checkboxes e o botão "OK" com base nas dimensões da camada.
        - Se não houver camada selecionada, desativa os componentes.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Obtém o ID da camada raster selecionada no ComboBox
        selected_layer_id = self.comboBoxRaster.currentData()  # Coleta o ID da camada selecionada no ComboBox

        # Obtém a camada raster associada ao ID selecionado
        self.layer = QgsProject.instance().mapLayer(selected_layer_id)  # Carrega a camada raster no projeto com base no ID

        # Verifica se a camada existe
        if self.layer:
            # Obtém o provedor de dados da camada
            provider = self.layer.dataProvider()  # Coleta o provedor de dados da camada raster

            # Obtém a largura e altura da camada raster em pixels
            width = provider.xSize()  # Obtém a largura em pixels da camada raster
            height = provider.ySize()  # Obtém a altura em pixels da camada raster

            # Habilita ou desabilita os checkboxes e o botão "OK" com base nas dimensões da camada
            self.verificar_estado_componentes(width, height)  # Chama a função para verificar o estado dos componentes
        else:
            # Se não houver uma camada selecionada, desativa todos os componentes
            self.verificar_estado_componentes(0, 0)  # Passa dimensões 0 para desativar os componentes

    def resetar_componentes(self):
        """
        Reseta o estado dos checkboxes e do botão "OK" ao abrir o diálogo.
        
        Funcionalidades:
        - Desmarca todos os checkboxes.
        - Desativa todos os checkboxes.
        - Desativa o botão "OK".
        
        Esse método é útil para garantir que, ao abrir o diálogo, os componentes estejam em seu estado inicial.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Desmarca todos os checkboxes
        self.checkboxPontos.setChecked(False)  # Desmarca o checkbox de pontos
        self.checkboxPoligonos.setChecked(False)  # Desmarca o checkbox de polígonos
        self.checkboxEstilizada.setChecked(False)  # Desmarca o checkbox de estilo
        self.checkboxAtribuida.setChecked(False)  # Desmarca o checkbox de atribuição

        # Desativa todos os checkboxes
        self.checkboxPontos.setEnabled(False)  # Desativa o checkbox de pontos
        self.checkboxPoligonos.setEnabled(False)  # Desativa o checkbox de polígonos
        self.checkboxEstilizada.setEnabled(False)  # Desativa o checkbox de estilo
        self.checkboxAtribuida.setEnabled(False)  # Desativa o checkbox de atribuição

        # Desativa o botão "OK"
        self.okButton.setEnabled(False)  # Desativa o botão "OK"

    def aplicar_estilo_poligono(self, camada_poligono, colormap):
        """
        Aplica um estilo graduado a uma camada de polígonos com base em uma colormap.

        Passos detalhados:
        1. Cria uma lista para armazenar os intervalos de renderização.
        2. Itera sobre os itens da colormap para criar símbolos e intervalos de renderização.
        3. Adiciona o primeiro intervalo com valor mínimo infinito.
        4. Adiciona os intervalos subsequentes com base nos valores anteriores e atuais.
        5. Remove o intervalo adicional de infinito, se presente.
        6. Cria um renderizador graduado com base nos intervalos de valores e aplica à camada de polígonos.

        Parâmetros:
        - camada_poligono: Camada de polígonos a ser estilizada.
        - colormap: Lista de itens da colormap contendo valores e cores.

        Retorna:
        - None
        """
        ranges = []  # Lista para armazenar os intervalos de renderização

        for i in range(len(colormap)):  # Itera sobre os itens da colormap
            item = colormap[i]  # Obtém o item atual da colormap
            if i == 0:
                # Primeiro intervalo
                symbol = QgsFillSymbol.createSimple({'color': item.color.name(), 'outline_color': item.color.name()})  # Cria um símbolo de preenchimento
                renderer_range = QgsRendererRange(float('-inf'), item.value, symbol, f"<= {item.value:.3f}")  # Cria um intervalo de renderização
            else:
                prev_item = colormap[i - 1]  # Obtém o item anterior da colormap
                symbol = QgsFillSymbol.createSimple({'color': item.color.name(), 'outline_color': item.color.name()})  # Cria um símbolo de preenchimento
                renderer_range = QgsRendererRange(prev_item.value, item.value, symbol, f"{prev_item.value:.3f} - {item.value:.3f}")  # Cria um intervalo de renderização

            ranges.append(renderer_range)  # Adiciona o intervalo de renderização à lista

        # Remover o intervalo adicional de "inf"
        if len(ranges) > 1 and ranges[-1].upperValue == float('inf'):  # Verifica se há um intervalo adicional de infinito
            ranges.pop()  # Remove o intervalo adicional

        renderer = QgsGraduatedSymbolRenderer('Value', ranges)  # Cria um renderizador graduado com base nos intervalos de valores
        camada_poligono.setRenderer(renderer)  # Aplica o renderizador à camada de polígonos

    def gerar_colormap_cinza(self, min_value, max_value, num_graduacoes=10):
        """
        Gera uma colormap em escala de cinza para um intervalo de valores.

        Passos detalhados:
        1. Inicializa uma lista para armazenar os itens da colormap.
        2. Calcula o tamanho do passo entre cada graduação de valor.
        3. Itera sobre o número de graduações para gerar valores e cores em escala de cinza.
        4. Cria itens da colormap com valores e cores correspondentes.
        5. Adiciona um item final para cobrir valores maiores que o valor máximo, com cor cinza clara.
        6. Retorna a lista de itens da colormap.

        Parâmetros:
        - min_value: Valor mínimo do intervalo.
        - max_value: Valor máximo do intervalo.
        - num_graduacoes: Número de graduações na colormap (padrão é 10).

        Retorna:
        - colormap: Lista de itens da colormap em escala de cinza.
        """
        colormap = []  # Inicializa a lista para armazenar os itens da colormap
        step = (max_value - min_value) / (num_graduacoes - 1)  # Calcula o tamanho do passo entre cada graduação de valor
        for i in range(num_graduacoes):  # Itera sobre o número de graduações
            value = min_value + i * step  # Calcula o valor atual
            gray_value = int(255 * (i / (num_graduacoes - 1)))  # Valor em escala de cinza entre 0 e 255
            color = QColor(gray_value, gray_value, gray_value)  # Cria a cor correspondente em escala de cinza
            colormap.append(QgsColorRampShader.ColorRampItem(value, color))  # Adiciona o item à colormap

        # Adicionar um último item para cobrir valores maiores que o valor máximo
        gray_value = 240  # Última cor em escala de cinza (totalmente branca)
        color = QColor(gray_value, gray_value, gray_value)  # Cria a cor cinza clara
        colormap[-1] = QgsColorRampShader.ColorRampItem(max_value, color)  # Substitui o último item na colormap

        return colormap  # Retorna a lista de itens da colormap

    def aplicar_estilo_atribuido(self, camada_poligono):
        """
        Aplica um estilo de coloração atribuído a uma camada de polígonos baseado nos valores dos pixels.

        Passos detalhados:
        1. Cria uma lista para armazenar os intervalos de renderização.
        2. Cria símbolos de preenchimento para pixels positivos, negativos e nulos.
        3. Adiciona intervalos de renderização para cada tipo de símbolo.
        4. Cria um renderizador graduado com base nos intervalos de valores.
        5. Aplica o renderizador à camada de polígonos.

        Parâmetros:
        - camada_poligono: Camada de polígonos a ser estilizada.

        Retorna:
        - None
        """
        ranges = []  # Cria uma lista para armazenar os intervalos de renderização

        # Cria símbolos de preenchimento para pixels positivos, negativos e nulos
        symbol_positive = QgsFillSymbol.createSimple({'color': 'blue', 'outline_color': 'blue'})  # Azul para pixels positivos
        symbol_negative = QgsFillSymbol.createSimple({'color': 'red', 'outline_color': 'red'})  # Vermelho para pixels negativos
        symbol_zero = QgsFillSymbol.createSimple({'color': 'gray', 'outline_color': 'gray'})  # Cinza para pixels nulos

        # Adiciona intervalos de renderização para cada tipo de símbolo
        ranges.append(QgsRendererRange(0.0001, float('inf'), symbol_positive, "> 0"))  # Intervalo para pixels positivos
        ranges.append(QgsRendererRange(float('-inf'), -0.0001, symbol_negative, "< 0"))  # Intervalo para pixels negativos
        ranges.append(QgsRendererRange(-0.0001, 0.0001, symbol_zero, "= 0"))  # Intervalo para pixels nulos

        renderer = QgsGraduatedSymbolRenderer('Value', ranges)  # Cria um renderizador graduado com base nos intervalos de valores
        camada_poligono.setRenderer(renderer)  # Aplica o renderizador à camada de polígonos

    def criar_camadas_poligonos_unicas(self, raster_layer):
        """
        Cria uma camada de polígonos única com um nome exclusivo, adicionando sufixos numéricos, se necessário.

        Parâmetros:
        - raster_layer: A camada raster de origem para criar a camada de polígonos.

        Retorna:
        - A camada de polígonos criada.
        """
        # Base do nome da camada
        base_name = raster_layer.name() + "_Poligonos"
        layer_name = base_name

        # Verificar se uma camada com o mesmo nome já existe
        layers = QgsProject.instance().mapLayersByName(layer_name)
        count = 1
        while layers:
            layer_name = f"{base_name}_{count}"
            layers = QgsProject.instance().mapLayersByName(layer_name)
            count += 1

        # Criar a camada de polígonos com um nome exclusivo
        camada_poligono = QgsVectorLayer(f"Polygon?crs={raster_layer.crs().authid()}", layer_name, "memory")
        return camada_poligono

    def processar_cotas_poligonos(self, raster_layer, estilizar=False, atribuir=False):
        """
        Processa uma camada raster para extrair cotas em polígonos e cria uma camada de polígonos no QGIS.

        Passos detalhados:
        1. Captura o tempo de início do processo.
        2. Obtém o provedor de dados da camada raster.
        3. Calcula a extensão e dimensões da camada raster.
        4. Cria uma camada de polígonos com os campos necessários.
        5. Itera sobre cada pixel no raster.
        6. Calcula a resolução do pixel em X e Y.
        7. Inicia a barra de progresso.
        8. Para cada pixel, calcula a coordenada do centro do pixel.
        9. Obtém o valor do pixel.
        10. Cria um novo polígono e adiciona à camada se o valor do pixel não for nulo.
        11. Atualiza a barra de progresso periodicamente.
        12. Atualiza a camada de polígonos e a adiciona ao projeto QGIS.
        13. Aplica o estilo atribuído se necessário.
        14. Captura o tempo de fim e calcula o tempo de execução.
        15. Remove a barra de progresso.
        16. Exibe uma mensagem de sucesso com o tempo de execução.

        Parâmetros:
        - raster_layer: Camada raster a ser processada.
        - estilizar: Indica se a camada deve ser estilizada.
        - atribuir: Indica se a camada deve ter estilos atribuídos.

        Retorna:
        - None
        """
        start_time = time.time()  # Capturar o tempo de início

        provider = raster_layer.dataProvider()  # Obter o provedor de dados da camada raster
        extent = provider.extent()  # Obter a extensão da camada raster
        width = provider.xSize()  # Obter a largura da camada raster
        height = provider.ySize()  # Obter a altura da camada raster

        # Criar a camada de polígonos com um nome exclusivo
        camada_poligono = self.criar_camadas_poligonos_unicas(raster_layer)

        pr = camada_poligono.dataProvider()  # Obter o provedor de dados da camada de polígonos
        pr.addAttributes([QgsField("ID", QVariant.Int), QgsField("Value", QVariant.Double)])  # Adicionar campos
        camada_poligono.updateFields()  # Atualizar os campos da camada de polígonos

        pixelSizeX = provider.extent().width() / width  # Calcular a resolução do pixel em X
        pixelSizeY = provider.extent().height() / height  # Calcular a resolução do pixel em Y

        total_steps = width * height  # Número total de pixels
        progress_bar, progress_message_bar = self.iniciar_progress_bar(total_steps)  # Inicia a barra de progresso

        ID = 0
        update_interval = 1000  # Atualizar a barra de progresso a cada 1000 pixels

        valores_pixel = []  # Lista para armazenar os valores dos pixels

        for row in range(height):
            for col in range(width):
                ID += 1

                # Atualizar a barra de progresso a cada 1000 pixels
                if ID % update_interval == 0:
                    progress_bar.setValue(ID)

                # Encontrar a coordenada do centro do pixel
                x = extent.xMinimum() + col * pixelSizeX + pixelSizeX / 2
                y = extent.yMaximum() - row * pixelSizeY - pixelSizeY / 2
                ponto = QgsPointXY(x, y)
                valor_pixel = provider.identify(ponto, QgsRaster.IdentifyFormatValue).results().get(1)

                if valor_pixel is not None:  # Ignorar pixels NoData
                    xMin = extent.xMinimum() + col * pixelSizeX
                    xMax = extent.xMinimum() + (col + 1) * pixelSizeX
                    yMax = extent.yMaximum() - row * pixelSizeY
                    yMin = extent.yMaximum() - (row + 1) * pixelSizeY

                    poligono = QgsGeometry.fromRect(QgsRectangle(xMin, yMin, xMax, yMax))  # Criar um polígono a partir do retângulo

                    feature = QgsFeature()  # Criar uma nova feature
                    feature.setGeometry(poligono)  # Definir a geometria da feature
                    feature.setAttributes([ID, valor_pixel])  # Definir os atributos da feature
                    pr.addFeature(feature)  # Adicionar a feature à camada de polígonos

                    valores_pixel.append(valor_pixel)  # Adicionar o valor do pixel à lista

        # Adicionar a camada de polígono ao projeto
        QgsProject.instance().addMapLayer(camada_poligono)

        # Obter a colormap da camada raster e aplicar o estilo graduado
        renderer = raster_layer.renderer()
        colormap = []
        if hasattr(renderer, 'shader'):
            shader = renderer.shader()
            color_ramp_shader = shader.rasterShaderFunction()
            colormap = color_ramp_shader.colorRampItemList() if isinstance(color_ramp_shader, QgsColorRampShader) else []

        # Gerar colormap cinza se não for encontrado
        if estilizar and not colormap:
            min_value = min(valores_pixel)
            max_value = max(valores_pixel)
            colormap = self.gerar_colormap_cinza(min_value, max_value, 10)

        # Aplicar o estilo graduado baseado na colormap se estilizar for True
        if estilizar:
            self.aplicar_estilo_poligono(camada_poligono, colormap)

        # Aplicar o estilo atribuído se necessário
        if atribuir:
            self.aplicar_estilo_atribuido(camada_poligono)

        # Atualizar a barra de progresso para 100% no final
        progress_bar.setValue(total_steps)

        execution_time = time.time() - start_time  # Calcular o tempo de execução

        # Remove a barra de progresso
        self.iface.messageBar().clearWidgets()

        # Exibir mensagem de sucesso com o tempo de execução
        self.mostrar_mensagem(f"Camada de Polígonos Criadas com sucesso em {execution_time:.2f} segundos.", "Sucesso")

    def processar_cotas_pontos(self, raster_layer):
        """
        Processa uma camada raster para extrair cotas em pontos e cria uma camada de pontos no QGIS.

        Passos detalhados:
        1. Captura o tempo de início do processo.
        2. Obtém o SRC (Sistema de Referência de Coordenadas) do raster.
        3. Cria uma camada de pontos com os campos necessários.
        4. Itera sobre cada pixel no raster.
        5. Calcula a resolução do pixel em X e Y.
        6. Inicia a barra de progresso.
        7. Para cada pixel, calcula a coordenada do centro do pixel.
        8. Obtém o valor do pixel.
        9. Cria um novo ponto e adiciona à camada se o valor do pixel não for nulo.
        10. Atualiza a barra de progresso periodicamente.
        11. Atualiza a camada de pontos e a adiciona ao projeto QGIS.
        12. Captura o tempo de fim e calcula o tempo de execução.
        13. Remove a barra de progresso.
        14. Exibe uma mensagem de sucesso com o tempo de execução.

        Retorna:
        - None
        """
        start_time = time.time()  # Capturar o tempo de início

        # Obtenha o SRC do raster
        raster_crs = raster_layer.crs().authid()

        # Crie a camada de pontos com os campos necessários
        camada_pontos = QgsVectorLayer(f"PointZ?crs={raster_layer.crs().authid()}", raster_layer.name() + "_Pontos", "memory")
        pr = camada_pontos.dataProvider()
        pr.addAttributes([QgsField("ID", QVariant.Int),
                          QgsField("X", QVariant.Double),
                          QgsField("Y", QVariant.Double),
                          QgsField("Z", QVariant.Double)])
        camada_pontos.updateFields()

        # Iterar sobre cada pixel no raster
        provider = raster_layer.dataProvider()
        extent = raster_layer.extent()
        width = provider.xSize()
        height = provider.ySize()

        xres = extent.width() / width  # Calcula a resolução do pixel em X
        yres = extent.height() / height  # Calcula a resolução do pixel em Y

        total_steps = width * height  # Número total de pixels
        progress_bar, progress_message_bar = self.iniciar_progress_bar(total_steps)  # Inicia a barra de progresso

        id = 0
        update_interval = 1000  # Atualizar a barra de progresso a cada 1000 pixels

        for row in range(height):
            for col in range(width):
                id += 1

                # Atualizar a barra de progresso a cada 1000 pixels
                if id % update_interval == 0:
                    progress_bar.setValue(id)

                # Encontrar a coordenada do centro do pixel
                x = extent.xMinimum() + xres * (col + 0.5)
                y = extent.yMinimum() + yres * (row + 0.5)

                # Pegar o valor do pixel
                result = provider.identify(QgsPointXY(x, y), QgsRaster.IdentifyFormatValue)
                z = result.results()[1]

                if z is not None:  # Verifica se o valor do pixel não é nulo
                    # Criar um novo ponto e adicionar à camada
                    x = round(x, 3)  # Arredonda a coordenada X para 3 casas decimais
                    y = round(y, 3)  # Arredonda a coordenada Y para 3 casas decimais
                    z = round(z, 5)  # Arredonda o valor Z para 5 casas decimais

                    # Criar um novo ponto e adicionar à camada
                    pt = QgsPoint(x, y, z)

                    # Criar a feature e preencher os campos
                    feature = QgsFeature()
                    feature.setGeometry(QgsGeometry.fromWkt(pt.asWkt()))  # Usamos fromWkt e asWkt aqui
                    feature.setAttributes([id, pt.x(), pt.y(), z])

                    # Adicionar a feature à camada
                    pr.addFeature(feature)

        # Atualizar a barra de progresso para 100% no final
        progress_bar.setValue(total_steps)

        # Atualizar a camada de pontos e adicioná-la ao projeto
        camada_pontos.updateExtents()
        QgsProject.instance().addMapLayer(camada_pontos)

        execution_time = time.time() - start_time  # Calcular o tempo de execução

        # Remove a barra de progresso
        self.iface.messageBar().clearWidgets()

        # Exibir mensagem de sucesso com o tempo de execução
        self.mostrar_mensagem(f"Camada de Pontos Criadas com sucesso em {execution_time:.2f} segundos.", "Sucesso")

    def extrair_cotas(self):
        """
        Executa a extração de cotas (pontos ou polígonos) de uma camada raster selecionada no ComboBox.

        Funcionalidades:
        - Verifica se há uma camada raster selecionada e válida.
        - Executa a extração de cotas de pontos se o checkbox de pontos estiver marcado.
        - Executa a extração de cotas de polígonos, simples, estilizada ou atribuída, se os checkboxes correspondentes estiverem marcados.

        Parâmetros:
        - Nenhum.

        Retorna:
        - None.
        """

        # Verifica se alguma camada está selecionada no ComboBox
        selected_raster_id = self.comboBoxRaster.currentData()  # Obtém o ID da camada raster selecionada
        if not selected_raster_id:
            # Se não houver camada selecionada, exibe uma mensagem de erro e interrompe o processo
            self.mostrar_mensagem("Nenhuma camada raster selecionada.", "Erro")
            return  # Sai da função se não houver camada

        # Obtém a camada selecionada no projeto usando o ID do ComboBox
        layer = QgsProject.instance().mapLayer(selected_raster_id)  # Obtém a camada raster associada ao ID
        if not layer:
            # Se a camada for inválida, exibe uma mensagem de erro e interrompe o processo
            self.mostrar_mensagem("Camada raster inválida.", "Erro")
            return  # Sai da função se a camada for inválida

        # Processa a extração de cotas de pontos se o checkbox de pontos estiver marcado
        if self.checkboxPontos.isChecked():
            self.processar_cotas_pontos(layer)  # Chama o método para processar cotas de pontos

        # Processa a extração de cotas de polígonos (simples, estilizada ou atribuída) conforme o estado dos checkboxes
        if self.checkboxPoligonos.isChecked() or self.checkboxEstilizada.isChecked() or self.checkboxAtribuida.isChecked():
            estilizar = self.checkboxEstilizada.isChecked()  # Verifica se o checkbox de estilo está marcado
            atribuir = self.checkboxAtribuida.isChecked()  # Verifica se o checkbox de atribuição está marcado
            self.processar_cotas_poligonos(layer, estilizar=estilizar, atribuir=atribuir)  # Chama o método para processar cotas de polígonos

