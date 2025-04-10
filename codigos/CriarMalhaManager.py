from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QProgressBar, QComboBox, QGraphicsScene, QFileDialog
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsProcessingFeatureSourceDefinition, QgsProcessing, QgsCoordinateReferenceSystem, QgsProcessingContext, QgsMeshLayer, QgsMapSettings, QgsMapRendererCustomPainterJob
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QPixmap
from qgis.PyQt.QtCore import Qt, QSize, QSettings
from qgis.gui import QgsProjectionSelectionDialog
from qgis.utils import iface
from qgis.PyQt import uic
import processing
import os
import time
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'CriaMalhas.ui'))

class MalhaManager(QDialog, FORM_CLASS):
    def __init__(self, iface, plugin, parent=None):
        """Constructor."""
        super(MalhaManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        self.iface = iface  # Armazena a referência da interface QGIS
        self.plugin = plugin        # Guarda a referência ao plugin principal (CriarVetor)

        # Inicializa a cena gráfica
        self.scene = QGraphicsScene(self)
        self.graphicsViewPontos.setScene(self.scene)

        # Altera o título da janela
        self.setWindowTitle("Criação de Malhas")

        # Preenche o comboBox com camadas de pontos
        self.populate_combo_box()

        # Preenche o comboBox com os campos
        self.populate_combo_box_z()

        # Conecta os sinais aos slots
        self.connect_signals()

        self.display_point_layer()

        self.selection_color = QColor(Qt.yellow)  # Cor personalizável
        
        # Inicializa os LineEdits com valores padrão e estilo
        self.lineEditFeicoes.setReadOnly(True)
        self.lineEditSelecionados.setReadOnly(True)
        self.lineEditFeicoes.setStyleSheet("color: silver;")
        self.lineEditSelecionados.setStyleSheet("color: silver;")
        # self.lineEditFeicoes.setText("Total/Feições: 0")
        # self.lineEditSelecionados.setText("Selecionados: 0")

        self.output_path = None  # Variável para armazenar o caminho

        self.lineEditSalvar.setReadOnly(True)
        self.lineEditSalvar.setText("[Salvar em arquivo temporário]")
        self.lineEditSalvar.setStyleSheet("color: silver;")

    def connect_signals(self):

        # Conecta a mudança de seleção no comboBoxCamada para atualizar o checkBoxSeleciona
        self.comboBoxCamada.currentIndexChanged.connect(self.update_checkBoxSeleciona)

        # Conecta sinais para atualizar contagens de feições
        self.comboBoxCamada.currentIndexChanged.connect(self.update_feature_counts)

        # Conecta sinais do projeto para atualizar comboBox quando camadas forem adicionadas, removidas ou renomeadas
        QgsProject.instance().layersAdded.connect(self.populate_combo_box)
        QgsProject.instance().layersRemoved.connect(self.populate_combo_box)
        QgsProject.instance().layerWillBeRemoved.connect(self.populate_combo_box)

        # Conecta a mudança de seleção no comboBoxCamada para atualizar o comboBoxZ
        self.comboBoxCamada.currentIndexChanged.connect(self.populate_combo_box_z)
        # Conecta a mudança de seleção no comboBoxCamada para atualizar o checkBoxZ
        self.comboBoxCamada.currentIndexChanged.connect(self.update_checkBoxZ)

        # Conecta o clique do botão pushButtonExecutar para executar o cálculo da malha
        self.pushButtonExecutar.clicked.connect(self.execute_mesh_calculation)

        self.comboBoxCamada.currentIndexChanged.connect(self.display_point_layer)

        # Conecta sinais de seleção e modificação de feições
        self.comboBoxCamada.currentIndexChanged.connect(self.update_layer_connections)

        # Conectar o botão para definir o salvamento
        self.pushButtonSalvar.clicked.connect(self.definir_local_salvamento)

        # Conecta sinais para atualizar o estado do botão pushButtonExecutar
        self.comboBoxCamada.currentIndexChanged.connect(self.update_button_state)
        self.comboBoxZ.currentIndexChanged.connect(self.update_button_state)
        QgsProject.instance().layersAdded.connect(self.update_button_state)
        QgsProject.instance().layersRemoved.connect(self.update_button_state)

        # Conecta sinais de adição/remoção de camadas para atualizar o checkBoxZ
        QgsProject.instance().layersAdded.connect(self.update_checkBoxZ)
        QgsProject.instance().layersRemoved.connect(self.update_checkBoxZ)

        # Conecta o sinal stateChanged do checkBoxZ para atualizar o estado do comboBoxZ
        self.checkBoxZ.stateChanged.connect(self.update_combo_box_z_state)

        # Conecta o botão Fechar ao slot de fechar o diálogo
        self.pushButtonFechar.clicked.connect(self.hide)

        # Ao clicar no pushButtonRasterizar, chama o método rasterizar_malha
        self.pushButtonRasterizar.clicked.connect(self.abrir_dialogo_rasterizar)

        # atualiza o botão pushButtonRasterizar cm base na existência de Camadas de malhas
        QgsProject.instance().layersAdded.connect(self.update_rasterizar_button_state)
        QgsProject.instance().layersRemoved.connect(self.update_rasterizar_button_state)
        QgsProject.instance().layerWillBeRemoved.connect(self.update_rasterizar_button_state)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(MalhaManager, self).showEvent(event)

        self.populate_combo_box()  # Atualiza o comboBoxCamada com as camadas disponíveis

        self.update_checkBoxSeleciona()  # Atualiza o estado do checkBoxSeleciona com base nas feições selecionadas

        self.update_layer_connections()  # Conecta os sinais da camada atual

        self.update_checkBoxZ()  # Conecta os sinais da camada com Z

        self.display_point_layer()  # Atualiza a visualização ao abrir

        self.update_feature_counts()  # Atualiza as contagens de feições

        # Atualiza o estado do botão pushButtonExecutar
        self.update_button_state()

        # Atualiza o estado inicial do comboBoxZ com base no checkBoxZ
        self.update_combo_box_z_state()

        # Atualiza o estado do botão pushButtonRasterizar
        self.update_rasterizar_button_state()

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

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivo=None):
        """
        Exibe uma mensagem na barra de mensagens do QGIS, proporcionando feedback ao usuário baseado nas ações realizadas.
        As mensagens podem ser de erro ou de sucesso, com uma duração configurável e uma opção de abrir uma pasta.

        :param texto: Texto da mensagem a ser exibida.
        :param tipo: Tipo da mensagem ("Erro" ou "Sucesso") que determina a cor e o ícone da mensagem.
        :param duracao: Duração em segundos durante a qual a mensagem será exibida (padrão é 3 segundos).
        :param caminho_pasta: Caminho da pasta a ser aberta ao clicar no botão (padrão é None).
        :param caminho_arquivo: Caminho do arquivo a ser executado ao clicar no botão (padrão é None).
        """
        # Obtém a barra de mensagens da interface do QGIS
        bar = self.iface.messageBar()  # Acessa a barra de mensagens da interface do QGIS

        # Exibe a mensagem com o nível apropriado baseado no tipo
        if tipo == "Erro":
            # Mostra uma mensagem de erro na barra de mensagens com um ícone crítico e a duração especificada
            bar.pushMessage("Erro", texto, level=Qgis.Critical, duration=duracao)
        elif tipo == "Sucesso":
            # Cria o item da mensagem
            msg = bar.createMessage("Sucesso", texto)
            
            # Se o caminho da pasta for fornecido, adiciona um botão para abrir a pasta
            if caminho_pasta:
                botao_abrir_pasta = QPushButton("Abrir Pasta")
                botao_abrir_pasta.clicked.connect(lambda: os.startfile(caminho_pasta))
                msg.layout().insertWidget(1, botao_abrir_pasta)  # Adiciona o botão à esquerda do texto

    def update_checkBoxSeleciona(self):
        """
        Atualiza o estado do checkBoxSeleciona com base na seleção de feições da camada atualmente selecionada.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Obtém o ID da camada atualmente selecionada no comboBoxCamada.
        - Se uma camada válida for encontrada, verifica a quantidade de feições selecionadas na camada.
        - Se houver feições selecionadas, o checkBoxSeleciona é ativado.
        - Se não houver feições selecionadas ou a camada não for válida, o checkBoxSeleciona é desativado e desmarcado.
        """
        layer_id = self.comboBoxCamada.currentData()  # Obtém o ID da camada selecionada no comboBoxCamada
        if layer_id:  # Verifica se há uma camada selecionada
            layer = QgsProject.instance().mapLayer(layer_id)  # Obtém a camada correspondente ao ID
            if layer:  # Verifica se a camada existe
                selected_features = layer.selectedFeatureCount()  # Conta o número de feições selecionadas na camada
                if selected_features > 0:  # Se houver feições selecionadas, ativa o checkBoxSeleciona
                    self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(True)
                else:  # Se não houver feições selecionadas, desativa o checkBoxSeleciona e o desmarca
                    self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(False)
                    self.findChild(QCheckBox, 'checkBoxSeleciona').setChecked(False)
            else:  # Se a camada não for válida, desativa o checkBoxSeleciona e o desmarca
                self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(False)
                self.findChild(QCheckBox, 'checkBoxSeleciona').setChecked(False)
        else:  # Se não houver uma camada selecionada, desativa o checkBoxSeleciona e o desmarca
            self.findChild(QCheckBox, 'checkBoxSeleciona').setEnabled(False)
            self.findChild(QCheckBox, 'checkBoxSeleciona').setChecked(False)

    def populate_combo_box(self):
        """
        Popula o comboBoxCamada com as camadas de polígonos disponíveis no projeto e realiza ações relacionadas.

        Parâmetros:
        self : objeto
            Referência à instância atual da classe.

        A função realiza as seguintes ações:
        - Salva a camada atualmente selecionada no comboBoxCamada.
        - Bloqueia temporariamente os sinais do comboBoxCamada para evitar atualizações desnecessárias.
        - Limpa o comboBoxCamada antes de preenchê-lo novamente.
        - Adiciona as camadas de polígonos disponíveis ao comboBoxCamada.
        - Restaura a seleção da camada anterior, se possível.
        - Desbloqueia os sinais do comboBoxCamada após preenchê-lo.
        - Preenche o comboBoxRotulagem com os campos da camada selecionada.
        - Ativa ou desativa o botão pushButtonConverter com base na presença de camadas no comboBoxCamada.
        """
        current_layer_id = self.comboBoxCamada.currentData()  # Salva a camada atualmente selecionada
        self.comboBoxCamada.blockSignals(True)  # Bloqueia os sinais para evitar chamadas desnecessárias a update_poligono_edit_nome
        self.comboBoxCamada.clear()  # Limpa o comboBox antes de preencher

        layer_list = QgsProject.instance().mapLayers().values()
        for layer in layer_list:
            if isinstance(layer, QgsVectorLayer) and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PointGeometry:
                self.comboBoxCamada.addItem(layer.name(), layer.id())
                layer.nameChanged.connect(self.update_combo_box_item)  # Conecta o sinal nameChanged à função update_combo_box_item

        # Restaura a seleção anterior, se possível
        if current_layer_id:
            index = self.comboBoxCamada.findData(current_layer_id) # Tenta encontrar a camada selecionada anteriormente
            if index != -1:
                self.comboBoxCamada.setCurrentIndex(index) # Restaura a seleção anterior

        self.comboBoxCamada.blockSignals(False)  # Desbloqueia os sinais

        self.update_feature_counts()  # Atualiza as contagens após preencher o comboBox

        # Garante que o comboBoxZ seja atualizado mesmo quando não há camadas
        self.populate_combo_box_z()

        self.update_layer_connections()  # Atualiza conexões com a nova camada

        self.display_point_layer()  # Atualiza após mudanças nas camadas

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

    def populate_combo_box_z(self):
        """
        Popula o comboBoxZ com os campos numéricos da camada atualmente selecionada no comboBoxCamada,
        excluindo campos que se referem às coordenadas das feições.
        """
        self.comboBoxZ.clear()  # Limpa o comboBoxZ antes de preencher
        layer_id = self.comboBoxCamada.currentData()  # Obtém o ID da camada selecionada
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                # Lista de nomes de campos que geralmente representam coordenadas
                coordinate_field_names = {'id', 'x', 'y', 'coord_x', 'coord_y', 'xcoord', 'ycoord', 'longitude', 'latitude'}

                # Itera sobre os campos da camada e adiciona apenas os numéricos que não são coordenadas
                for field in layer.fields():
                    if field.isNumeric():
                        # Verifica se o nome do campo está na lista de nomes de coordenadas (case-insensitive)
                        if field.name().lower() not in coordinate_field_names:
                            self.comboBoxZ.addItem(field.name(), field.name())

        # Atualiza o estado do botão após preencher o comboBoxZ
        self.update_button_state()

    def update_checkBoxZ(self):
        """
        Atualiza o estado do checkBoxZ para que fique ativo apenas se a camada de pontos
        selecionada possuir dimensão Z (ou seja, for uma camada 3D).
        """
        layer_id = self.comboBoxCamada.currentData()  # Obtém o ID da camada selecionada
        checkBoxZ = self.findChild(QCheckBox, 'checkBoxZ')
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            # Verifica se a camada existe e se possui dimensão Z
            if layer and QgsWkbTypes.hasZ(layer.wkbType()):
                checkBoxZ.setEnabled(True)
                checkBoxZ.setChecked(False)
            else:
                checkBoxZ.setEnabled(False)
                checkBoxZ.setChecked(False) # Desmarca o checkBoxZ se a camada não tiver geometria Z
        else:
            checkBoxZ.setEnabled(False)
            checkBoxZ.setChecked(False) # Desativa e desmarca o checkBoxZ se nenhuma camada estiver selecionada

    def resizeEvent(self, event):
        super(MalhaManager, self).resizeEvent(event)
        self.display_point_layer()

    def display_point_layer(self):
        """
        Renderiza a camada de pontos com destaque para a seleção do QGIS, sem alterar o estado da seleção.
        """

        # Verifica se o diálogo está visível
        if not self.isVisible():
            return
        
        # Restante do código original
        self.scene.clear()

        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer or not isinstance(layer, QgsVectorLayer):
            return

        # Configurações do mapa com renderização da seleção
        map_settings = QgsMapSettings()
        map_settings.setLayers([layer])  # Usa a camada original
        map_settings.setBackgroundColor(QColor(255, 255, 255))
        map_settings.setDestinationCrs(QgsProject.instance().crs())
        map_settings.setFlag(QgsMapSettings.DrawSelection, True)  # Renderiza seleção do QGIS
        map_settings.setExtent(layer.extent())

        # Define o tamanho da imagem
        width = self.graphicsViewPontos.viewport().width()
        height = self.graphicsViewPontos.viewport().height()
        map_settings.setOutputSize(QSize(width, height))

        # Renderiza a camada com seleção
        image = QImage(width, height, QImage.Format_ARGB32)
        painter = QPainter(image)
        renderer = QgsMapRendererCustomPainterJob(map_settings, painter)
        renderer.start()
        renderer.waitForFinished()
        painter.end()

        # Exibe a imagem no QGraphicsView
        pixmap = QPixmap.fromImage(image)
        self.scene.addPixmap(pixmap)
        self.graphicsViewPontos.setScene(self.scene)
        self.graphicsViewPontos.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def update_layer_connections(self):
        """
        Conecta os sinais da camada para atualizar a visualização em tempo real.
        """

        layer_id = self.comboBoxCamada.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                # Conecta o sinal de seleção para atualizar o graphicsViewPontos
                layer.selectionChanged.connect(self.display_point_layer)
                # Desconecta sinais anteriores (evita múltiplas conexões)
                try:
                    layer.featureAdded.disconnect()
                    layer.featureDeleted.disconnect()
                    layer.attributeValueChanged.disconnect()
                    layer.styleChanged.disconnect()
                except TypeError:
                    pass  # Ignora se não estava conectado

                # Conecta sinais de modificação de feições
                layer.selectionChanged.connect(self.display_point_layer)
                layer.featureAdded.connect(self.update_feature_counts)
                layer.featureDeleted.connect(self.update_feature_counts)
                layer.selectionChanged.connect(self.update_feature_counts)

                # Conecta sinais de modificação da camada
                layer.featureAdded.connect(self.display_point_layer)
                layer.featureDeleted.connect(self.display_point_layer)
                layer.attributeValueChanged.connect(self.display_point_layer)
                layer.styleChanged.connect(self.display_point_layer)

                # Mantém a conexão com seleção (já existente)
                layer.selectionChanged.connect(self.update_checkBoxSeleciona)
                self.update_checkBoxSeleciona()

                # Atualiza imediatamente as contagens
                self.update_feature_counts()

        else:
            self.update_checkBoxSeleciona()
            self.update_feature_counts()  # Limpa os campos se não houver camada

    def update_feature_counts(self):
        """
        Atualiza os valores dos lineEditFeicoes e lineEditSelecionados com base na camada selecionada.
        Configura os campos com prefixos e define a cor do texto como prata.
        """
        # Configura os lineEdits como somente leitura e define a cor do texto como prata
        self.lineEditFeicoes.setReadOnly(True)
        self.lineEditSelecionados.setReadOnly(True)
        self.lineEditFeicoes.setStyleSheet("color: silver;")
        self.lineEditSelecionados.setStyleSheet("color: silver;")

        # Obtém a camada selecionada
        layer_id = self.comboBoxCamada.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer):
                # Total de feições
                total_features = layer.featureCount()
                self.lineEditFeicoes.setText(f"{total_features}")
                
                # Feições selecionadas (apenas para a camada selecionada)
                selected_features = layer.selectedFeatureCount()
                self.lineEditSelecionados.setText(f"{selected_features}")
            else:
                # Limpa os campos se não houver camada válida
                self.lineEditFeicoes.setText("Nenhuma")
                self.lineEditSelecionados.setText("Nenhuma")
        else:
            # Limpa os campos se não houver camada selecionada
            self.lineEditFeicoes.setText("Nenhuma")
            self.lineEditSelecionados.setText("Nenhuma")

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

    def execute_mesh_calculation(self):
        # Validação da camada de pontos
        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            self.mostrar_mensagem("Selecione uma camada de pontos válida.", "Erro")
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer or layer.geometryType() != QgsWkbTypes.PointGeometry:
            self.mostrar_mensagem("Camada inválida ou não é do tipo ponto.", "Erro")
            return

        # Validação de seleção
        use_selected = self.checkBoxSeleciona.isChecked()
        if use_selected and layer.selectedFeatureCount() == 0:
            self.mostrar_mensagem("Não há feições selecionadas.", "Erro")
            return

        # Configuração do uso de Z
        use_z = self.checkBoxZ.isChecked()
        z_field_index = -1  # Valor padrão para usar geometria Z
        if use_z:
            if not QgsWkbTypes.hasZ(layer.wkbType()):
                self.mostrar_mensagem("A camada selecionada não possui dimensão Z.", "Erro")
                return
        else:
            # Se checkBoxZ não está marcado, usa o campo Z do comboBoxZ
            z_field_name = self.comboBoxZ.currentData()
            if z_field_name:
                z_field_index = layer.fields().indexFromName(z_field_name)
            else:
                self.mostrar_mensagem("Selecione um campo Z válido ou marque 'Usar Z da Geometria'.", "Erro")
                return

        # Preparação dos dados
        try:
            # Cria camada temporária para seleção (se necessário)
            temp_layer = None
            if use_selected:
                temp_layer = QgsVectorLayer(f"Point?crs={layer.crs().authid()}", "selected_points", "memory")
                temp_layer.dataProvider().addAttributes(layer.fields())
                temp_layer.updateFields()
                temp_layer.dataProvider().addFeatures([f for f in layer.getSelectedFeatures()])
                temp_layer.updateExtents()

                # Adiciona a camada temporária ao projeto
                QgsProject.instance().addMapLayer(temp_layer)
                source_layer = temp_layer
            else:
                source_layer = layer

            # Configuração da barra de progresso
            progress_bar, progress_msg = self.iniciar_progress_bar(1)

            # Configuração do parâmetro SOURCE_DATA
            source_data = [{
                'source': source_layer.id(),
                'type': 2,  # Pontos para vértices TIN
                'attributeIndex': z_field_index  # Usa -1 para geometria Z ou índice do campo
            }]

            # Execução do algoritmo TIN
            result = processing.run("native:tinmeshcreation", {
                'SOURCE_DATA': source_data,
                'MESH_FORMAT': 0,  # 0 = .mesh, 1 = .vtk
                'CRS_OUTPUT': QgsCoordinateReferenceSystem(),  # CRS vazio
                'OUTPUT_MESH': 'TEMPORARY_OUTPUT'
            })

            # Carrega a malha como camada
            mesh_path = result['OUTPUT_MESH']
            mesh_layer = QgsMeshLayer(mesh_path, "Malha_TIN", "mdal")  # Carrega a malha
            if not mesh_layer.isValid():
                raise Exception("Falha ao carregar a malha gerada")

            # Adiciona ao projeto
            QgsProject.instance().addMapLayer(mesh_layer)
            self.mostrar_mensagem(
                "Malha TIN gerada com sucesso!",
                "Sucesso",
                caminho_pasta=QgsProject.instance().homePath()
            )

        except Exception as e:
            self.mostrar_mensagem(f"Erro: {str(e)}", "Erro")
        finally:
            # Limpeza
            if temp_layer is not None:
                QgsProject.instance().removeMapLayer(temp_layer.id())  # Remove a camada temporária
            if progress_msg is not None:
                self.iface.messageBar().popWidget(progress_msg)

    def definir_local_salvamento(self):
        caminho = self.escolher_local_para_salvar("Malha_TIN.mesh", "MDAL Mesh (*.mesh)")
        if caminho:
            self.lineEditSalvar.setText(caminho)
            self.lineEditSalvar.setStyleSheet("color: black;")
        else:
            self.lineEditSalvar.setText("[Salvar em arquivo temporário]")
            self.lineEditSalvar.setStyleSheet("color: silver;")

    def update_button_state(self):
        """
        Atualiza o estado do botão pushButtonExecutar com base nas condições:
        - A camada deve ter geometria Z ou pelo menos um campo numérico no comboBoxZ.
        """
        # Obtém a camada selecionada
        layer_id = self.comboBoxCamada.currentData()
        if not layer_id:
            self.pushButtonExecutar.setEnabled(False)
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer or not isinstance(layer, QgsVectorLayer):
            self.pushButtonExecutar.setEnabled(False)
            return

        # Verifica se a camada tem geometria Z
        has_z_geometry = QgsWkbTypes.hasZ(layer.wkbType())

        # Verifica se há campos numéricos no comboBoxZ
        has_numeric_fields = self.comboBoxZ.count() > 0

        # Habilita o botão se pelo menos uma das condições for verdadeira
        if has_z_geometry or has_numeric_fields:
            self.pushButtonExecutar.setEnabled(True)
        else:
            self.pushButtonExecutar.setEnabled(False)

    def update_combo_box_z_state(self):
        """
        Atualiza o estado do comboBoxZ com base na seleção do checkBoxZ.
        - Se checkBoxZ estiver marcado, desativa o comboBoxZ.
        - Se checkBoxZ não estiver marcado, ativa o comboBoxZ.
        """
        is_checked = self.checkBoxZ.isChecked()
        self.comboBoxZ.setEnabled(not is_checked)

    # def closeEvent(self, event):
        # """
        # Executa ações de limpeza ao fechar o diálogo.
        # """
        # try:
            # # Desconecta sinais da camada atual
            # layer_id = self.comboBoxCamada.currentData()
            # if layer_id:
                # layer = QgsProject.instance().mapLayer(layer_id)
                # if layer:
                    # # Desconecta todos os sinais relacionados à atualização da visualização
                    # try:
                        # layer.selectionChanged.disconnect(self.display_point_layer)
                        # layer.featureAdded.disconnect(self.display_point_layer)
                        # layer.featureDeleted.disconnect(self.display_point_layer)
                        # layer.attributeValueChanged.disconnect(self.display_point_layer)
                        # layer.styleChanged.disconnect(self.display_point_layer)
                    # except TypeError:
                        # pass  # Ignora se não estava conectado

            # # Remove conexões globais do projeto
            # QgsProject.instance().layersAdded.disconnect(self.populate_combo_box)
            # QgsProject.instance().layersRemoved.disconnect(self.populate_combo_box)
            # QgsProject.instance().layerWillBeRemoved.disconnect(self.populate_combo_box)

            # # Limpa a cena gráfica
            # self.scene.clear()

            # # Libera recursos adicionais, se necessário
            # self.comboBoxCamada.blockSignals(True)
            # self.comboBoxCamada.clear()

            # # Aceita o evento de fechamento
            # event.accept()
            # super(MalhaManager, self).closeEvent(event)
        # except Exception as e:
            # event.ignore()

    def abrir_dialogo_rasterizar(self):
        """
        Chama o método run_rasterizarmalha do plugin principal para abrir o diálogo de Rasterização.
        """
        if hasattr(self.plugin, 'run_rasterizarmalha'):
            self.plugin.run_rasterizarmalha()
        else:
            self.mostrar_mensagem("Não foi possível abrir o diálogo Rasterizar Malha.", "Erro")

    def update_rasterizar_button_state(self):
        """
        Atualiza o estado do botão pushButtonRasterizar.
        O botão será habilitado se existir pelo menos uma camada de malha (QgsMeshLayer) no projeto;
        caso contrário, ficará desativado.
        """
        mesh_exists = False
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsMeshLayer):
                mesh_exists = True
                break
        self.pushButtonRasterizar.setEnabled(mesh_exists)

    def closeEvent(self, event):
        # Em vez de fazer a limpeza completa, apenas oculta o diálogo
        self.hide()
        event.ignore()
