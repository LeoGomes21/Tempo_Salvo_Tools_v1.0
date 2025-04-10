from PyQt5.QtWidgets import QInputDialog, QInputDialog, QTreeView, QStyledItemDelegate, QColorDialog, QMenu, QLineEdit, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog, QComboBox, QFrame, QCheckBox, QDoubleSpinBox, QRadioButton, QButtonGroup, QProgressBar, QDialogButtonBox, QGraphicsView, QListWidget, QScrollBar, QDesktopWidget, QGraphicsEllipseItem, QGraphicsScene, QToolTip, QGraphicsPathItem, QGraphicsRectItem, QGraphicsLineItem, QListWidgetItem, QWidget, QListView, QAbstractItemView, QScrollArea, QSizePolicy
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes, QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer, QgsSymbol, Qgis, QgsVectorLayerSimpleLabeling, QgsSimpleLineSymbolLayer, QgsRenderContext, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMessageLog, QgsLayerTreeLayer, QgsSymbolLayer, QgsGeometry, QgsSpatialIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap, QPainter, QColor, QPen, QFont, QBrush, QGuiApplication, QTransform, QCursor, QPainterPath, QPolygonF, QMouseEvent, QWheelEvent
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent, QCoreApplication, QSettings, QItemSelectionModel, QPointF, QSize, QUrl, QVariant, QObject
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from qgis.gui import QgsProjectionSelectionDialog
from PIL import Image, UnidentifiedImageError
import xml.etree.ElementTree as ET
from ezdxf.colors import rgb2int
from qgis.utils import iface
from ezdxf import colors
from io import BytesIO
import processing
import requests
import random
import ezdxf
import time
import math
import os
import re

# Importe a função criar_camada_pontos
from .criar_pontos import criar_camada_pontos

class UiManagerT:
    """
    Gerencia a interface do usuário, interagindo com um QTreeView para listar e gerenciar camadas de pontos no QGIS.
    """
    def __init__(self, iface, dialog):
        """
        Inicializa a instância da classe UiManagerO, responsável por gerenciar a interface do usuário
        que interage com um QTreeView para listar e gerenciar camadas de pontos no QGIS.

        :param iface: Interface do QGIS para interagir com o ambiente.
        :param dialog: Diálogo ou janela que esta classe gerenciará.

        Funções e Ações Desenvolvidas:
        - Configuração inicial das variáveis de instância.
        - Associação do modelo de dados com o QTreeView.
        - Inicialização da configuração do QTreeView.
        - Seleção automática da última camada no QTreeView.
        - Conexão dos sinais do QGIS e da interface do usuário com os métodos correspondentes.
        """
        # Salva as referências para a interface do QGIS e o diálogo fornecidos
        self.iface = iface
        self.dlg = dialog

        # Cria e configura o modelo de dados para o QTreeView
        self.treeViewModel = QStandardItemModel()
        self.dlg.treeViewListaPonto.setModel(self.treeViewModel)

        # Inicializa o QTreeView com as configurações necessárias
        self.init_treeView()

        # Seleciona a última camada adicionada para facilitar a interação do usuário
        self.selecionar_ultima_camada()  # Chama a função após a inicialização da árvore

        # Conecta os sinais do QGIS e da interface do usuário para sincronizar ações e eventos
        self.connect_signals()

        # Adiciona o filtro de eventos ao treeView
        self.tree_view_event_filter = TreeViewEventFilter(self)
        self.dlg.treeViewListaPonto.viewport().installEventFilter(self.tree_view_event_filter)

    def init_treeView(self):
        """
        Configura o QTreeView para listar e gerenciar camadas de pontos. 
        Este método inicializa a visualização da árvore com os itens e configurações necessárias,
        conecta os eventos de interface do usuário e estiliza os componentes visuais.
        
        Funções e Ações Desenvolvidas:
        - Atualização inicial da lista de camadas no QTreeView.
        - Conexão do evento de duplo clique em itens para tratamento.
        - Conexão do evento de alteração em itens para tratamento.
        - Configuração de delegado para customização da apresentação de itens.
        - Configuração do menu de contexto para interações adicionais.
        - Aplicação de estilos CSS para melhor visualização dos itens.
        - Conexão do botão de exportação para ação de exportar dados.
        """
        # Atualiza a visualização da lista de camadas no QTreeView
        self.atualizar_treeView_lista_ponto()

        # Conecta o evento de duplo clique em um item para manipulação de cores da camada
        self.dlg.treeViewListaPonto.doubleClicked.connect(self.on_item_double_clicked)

        # Conecta o evento de mudança em um item para atualizar a visibilidade da camada
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Define e aplica um delegado personalizado para customização da exibição de itens no QTreeView
        self.treeViewDelegate = CircleDelegate(self.dlg.treeViewListaPonto)
        self.dlg.treeViewListaPonto.setItemDelegate(self.treeViewDelegate)

        # Configura a política de menu de contexto para permitir menus personalizados em cliques com o botão direito
        self.dlg.treeViewListaPonto.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dlg.treeViewListaPonto.customContextMenuRequested.connect(self.open_context_menu)

        # Aplica estilos CSS para aprimorar a interação visual com os itens do QTreeView
        self.dlg.treeViewListaPonto.setStyleSheet("""
            QTreeView::item:hover:!selected {
                background-color: #def2fc;
            }
            QTreeView::item:selected {
            }""")

        # Conecta o botão para criar uma camada de pontos ao método que adiciona a camada e atualiza o treeView
        self.dlg.ButtonCriarPonto.clicked.connect(self.adicionar_camada_e_atualizar)

        # Conecta o botão ao novo método do botão cria uma camada como o nome
        self.dlg.ButtonCriarPontoNome.clicked.connect(self.abrir_caixa_nome_camada)

        # Conecta o botão ao método de exportação do KML
        self.dlg.pushButtonExportaKml.clicked.connect(self.exportar_para_kml)
        
        # Conecta o botão ao método de exportação do DXF
        self.dlg.pushButtonExportaDXF.clicked.connect(self.exportar_para_dxf)

        # Conecta o botão para reprojetar a camada
        self.dlg.pushButtonReprojetarT.clicked.connect(self.abrir_dialogo_crs)

    def configurar_tooltip(self, index):
        """
        Configura um tooltip para exibir informações sobre a camada de ponto selecionada no treeView.

        A função extrai informações sobre a camada de ponto, como o tipo de geometria (ex: Point, MultiPoint) 
        e o sistema de referência de coordenadas (SRC) atual da camada. Essas informações são exibidas em 
        um tooltip que aparece quando o usuário passa o mouse sobre o item correspondente no treeView.

        Parâmetros:
        - index: QModelIndex do item atualmente sob o cursor no treeView.
        """
        item = index.model().itemFromIndex(index)  # Obtém o item do modelo de dados com base no índice fornecido
        layer_id = item.data(Qt.UserRole)  # Obtém o ID da camada associada ao item
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if layer:  # Verifica se a camada existe
            tipo_ponto = self.obter_tipo_de_ponto(layer)  # Obtém o tipo de geometria da camada (ex: Point, MultiPoint)
            crs = layer.crs().description() if layer.crs().isValid() else "Sem Georreferenciamento"  # Obtém a descrição do SRC da camada ou "Sem Georreferenciamento" se inválido
            tooltip_text = f"Tipo: {tipo_ponto}\nSRC: {crs}"  # Formata o texto do tooltip com as informações da camada
            QToolTip.showText(QCursor.pos(), tooltip_text)  # Exibe o tooltip na posição atual do cursor

    def obter_tipo_de_ponto(self, layer):
        """
        Retorna uma string que descreve o tipo de geometria da camada fornecida.

        A função obtém o tipo de geometria WKB (Well-Known Binary) da camada e converte esse tipo
        em uma string legível, como 'Point', 'MultiPoint', etc.

        Parâmetros:
        - layer: Objeto QgsVectorLayer representando a camada de onde o tipo de ponto será extraído.

        Retorno:
        - tipo_ponto (str): Uma string que descreve o tipo de geometria da camada.
        """
        geometry_type = layer.wkbType()  # Obtém o tipo de geometria WKB (Well-Known Binary) da camada
        tipo_ponto = QgsWkbTypes.displayString(geometry_type)  # Converte o tipo de geometria em uma string legível
        return tipo_ponto  # Retorna a string que descreve o tipo de geometria

    def adicionar_camada_e_atualizar(self):
        """
        Método chamado ao clicar no botão para criar uma camada de ponto.
        Cria a camada de ponto e atualiza o treeView.
        """
        # Chamada para a função que cria uma nova camada de pontos
        criar_camada_pontos(self.iface)

        # Após adicionar a camada, atualize o treeView
        self.atualizar_treeView_lista_ponto()

    def abrir_caixa_nome_camada(self):
        """
        Esta função cria uma caixa de diálogo que permite ao usuário inserir o nome de uma nova camada.
        A caixa de diálogo contém um campo de texto e dois botões: 'OK' e 'Cancelar'.
        O botão 'OK' é ativado somente quando o campo de texto não está vazio.
        Se o usuário clicar em 'OK', a função 'criar_camada_pontos' é chamada e a árvore de visualização é atualizada.
        """
        dialog = QDialog(self.dlg) # Cria uma nova caixa de diálogo
        dialog.setWindowTitle("Nome da Camada") # Define o título da caixa de diálogo
        layout = QVBoxLayout(dialog) # Define o layout da caixa de diálogo
        layout.addWidget(QLabel("Digite o nome da camada:")) # Adiciona um rótulo ao layout

        lineEdit = QLineEdit() # Cria um novo campo de texto
        lineEdit.setPlaceholderText("Camada Temporária") # Define o texto do espaço reservado para o campo de texto
        layout.addWidget(lineEdit) # Adiciona o campo de texto ao layout

        okButton = QPushButton("OK") # Cria botões OK e Cancelar
        cancelButton = QPushButton("Cancelar") # Cria um novo botão 'Cancelar'

        okButton.clicked.connect(dialog.accept) # Conecta o clique do botão 'OK' à função 'accept' da caixa de diálogo
        cancelButton.clicked.connect(dialog.reject) # Conecta o clique do botão 'Cancelar' à função 'reject' da caixa de diálogo

        okButton.setEnabled(False) # Desativa o botão 'OK' por padrão

        # Ativa o botão 'OK' quando o campo de texto não está vazio
        lineEdit.textChanged.connect(lambda: okButton.setEnabled(bool(lineEdit.text().strip())))

        buttonLayout = QHBoxLayout()  # Cria um novo layout horizontal para os botões
        buttonLayout.addWidget(okButton)  # Adiciona o botão 'OK' ao layout do botão
        buttonLayout.addWidget(cancelButton)  # Adiciona o botão 'Cancelar' ao layout do botão
        layout.addLayout(buttonLayout)  # Adiciona o layout do botão ao layout principal

        # Se a caixa de diálogo for aceita e o campo de texto não estiver vazio, cria uma nova camada e atualiza a árvore de visualização
        if dialog.exec_() == QDialog.Accepted and lineEdit.text().strip():
            nome_camada = lineEdit.text().strip()  # Obtém o nome da camada do campo de texto
            criar_camada_pontos(self.iface, nome_camada)  # Cria uma nova camada de pontos
            self.atualizar_treeView_lista_ponto()  # Atualiza a árvore de visualização

    def connect_signals(self):
        """
        Conecta os sinais do QGIS e do QTreeView para sincronizar a interface com o estado atual do projeto.
        Este método garante que mudanças no ambiente do QGIS se reflitam na interface do usuário e que ações na
        interface desencadeiem reações apropriadas no QGIS.

        Funções e Ações Desenvolvidas:
        - Conexão com sinais de adição e remoção de camadas para atualizar a visualização da árvore.
        - Sincronização do modelo do QTreeView com mudanças de seleção e propriedades das camadas no QGIS.
        - Tratamento da mudança de nome das camadas para manter consistência entre a interface e o estado interno.
        """
        # Conecta sinais do QGIS para lidar com a adição e remoção de camadas no projeto
        QgsProject.instance().layersAdded.connect(self.layers_added)
        QgsProject.instance().layersRemoved.connect(self.atualizar_treeView_lista_ponto)

        # Conecta o evento de mudança em um item do QTreeView para atualizar a visibilidade da camada no QGIS
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Sincroniza o estado das camadas no QGIS com o checkbox do QTreeView sempre que as camadas do mapa mudam
        self.iface.mapCanvas().layersChanged.connect(self.sync_from_qgis_to_treeview)

        # Conecta mudanças na seleção do QTreeView para atualizar a camada ativa no QGIS
        self.dlg.treeViewListaPonto.selectionModel().selectionChanged.connect(self.on_treeview_selection_changed)

        # Sincroniza a seleção no QGIS com a seleção no QTreeView quando a camada ativa no QGIS muda
        self.iface.currentLayerChanged.connect(self.on_current_layer_changed)

        # Inicia a conexão de sinais para tratar a mudança de nome das camadas no projeto
        self.connect_name_changed_signals()

        # Conectando o botão pushButtonFecharT à função que fecha o diálogo
        self.dlg.pushButtonFecharT.clicked.connect(self.close_dialog)

    def close_dialog(self):
        """
        Fecha o diálogo associado a este UiManagerT:
        """
        self.dlg.close()

    def abrir_dialogo_crs(self):
        """
        Abre um diálogo de seleção de CRS e reprojeta a camada de pontos selecionada no treeViewListaPonto.

        A função permite ao usuário escolher um novo sistema de referência de coordenadas (SRC) para a camada 
        selecionada no treeViewListaPonto. Após a seleção, a camada é reprojetada usando o novo SRC, e a nova camada é 
        adicionada ao projeto QGIS com a mesma cor de ícone e rótulo da camada original.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManagerT)

        A função não retorna valores, mas adiciona uma nova camada reprojetada ao projeto QGIS.
        """
        index = self.dlg.treeViewListaPonto.currentIndex()  # Obtém o índice atualmente selecionado no treeViewListaPonto
        if not index.isValid():  # Verifica se o índice é válido (se há uma seleção)
            return  # Sai da função se o índice não for válido
        
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)  # Obtém o ID da camada associada ao item selecionado
        layer = QgsProject.instance().mapLayer(layer_id)  # Recupera a camada correspondente ao ID no projeto QGIS
        if not layer or layer.geometryType() != QgsWkbTypes.PointGeometry:  # Verifica se a camada existe e é de pontos
            self.mostrar_mensagem("Por favor, selecione uma camada de pontos válida.", "Aviso")  # Exibe uma mensagem de aviso
            return  # Sai da função se a camada não for de pontos
        
        # Abre o diálogo de seleção de CRS para que o usuário possa escolher um novo SRC
        dialog = QgsProjectionSelectionDialog(self.dlg)  # Cria uma instância do diálogo de seleção de CRS
        dialog.setCrs(layer.crs())  # Configura o CRS atual da camada como o CRS padrão no diálogo
        if dialog.exec_():  # Exibe o diálogo e verifica se o usuário confirmou a seleção
            novo_crs = dialog.crs()  # Obtém o novo CRS selecionado pelo usuário

            # Usa o processamento do QGIS para reprojetar a camada
            params = {
                'INPUT': layer,  # Define a camada original como entrada
                'TARGET_CRS': novo_crs,  # Define o novo CRS como o CRS alvo
                'OUTPUT': 'memory:'  # Salva o resultado na memória
            }
            resultado = processing.run('qgis:reprojectlayer', params)  # Executa o processo de reprojeção
            nova_camada = resultado['OUTPUT']  # Obtém a nova camada reprojetada a partir dos resultados

            # Verifique se a nova camada tem feições válidas
            if nova_camada and nova_camada.isValid():  # Verifica se a nova camada foi criada corretamente
                # Gerar nome único para a nova camada reprojetada
                novo_nome = self.gerar_nome_unico_rep(layer.name())  # Gera um nome único para evitar duplicidades
                nova_camada.setName(novo_nome)  # Define o nome da nova camada

                # Aplicar as cores do ícone e do rótulo da camada original
                cor_icone = self.obter_cor_icone(layer)  # Obtém a cor do ícone da camada original
                cor_rotulo = self.obter_cor_rotulo(layer)  # Obtém a cor do rótulo da camada original

                # self.aplicar_simbologia_com_cores_qgis(nova_camada, cor_icone, cor_rotulo)  # Aplica a simbologia

                QgsProject.instance().addMapLayer(nova_camada)  # Adiciona a nova camada reprojetada ao projeto

                # Atualiza a camada na tela
                layer.triggerRepaint()  # Recarrega a camada original (caso necessário)
                self.iface.mapCanvas().refresh()  # Atualiza a tela do mapa para refletir a nova camada

                # Exibe uma mensagem informando que a camada foi reprojetada
                texto_mensagem = f"A camada '{layer.name()}' foi reprojetada para {novo_crs.authid()} ({novo_crs.description()}) com o nome '{novo_nome}'."  # Cria a mensagem de sucesso
                self.mostrar_mensagem(texto_mensagem, "Sucesso")  # Exibe a mensagem na barra de mensagens do QGIS
            else:
                self.mostrar_mensagem(f"Erro na reprojeção da camada '{layer.name()}'.", "Erro")  # Exibe uma mensagem de erro se a reprojeção falhar

    def gerar_nome_unico_rep(self, base_nome):
        """
        Gera um nome único para uma nova camada baseada no nome da camada original.

        A função cria um novo nome para a camada reprojetada, adicionando um sufixo incremental 
        (_rep1, _rep2, etc.) ao nome base, garantindo que o novo nome seja único dentro do projeto QGIS.

        Parâmetros:
        - self: Referência à instância atual do objeto. (UiManager)
        - base_nome (str): O nome original da camada, usado como base para gerar o novo nome.

        Retorno:
        - novo_nome (str): Um nome único gerado para a nova camada reprojetada.
        """
        # Cria um conjunto contendo todos os nomes de camadas existentes no projeto QGIS
        existing_names = {layer.name() for layer in QgsProject.instance().mapLayers().values()}

        # Se o nome base ainda não existir no projeto, retorna com o sufixo _rep1
        if base_nome not in existing_names:
            return f"{base_nome}_rep1"
        # Inicia o contador de sufixos em 1
        i = 1
        # Gera o primeiro nome com o sufixo _rep1
        novo_nome = f"{base_nome}_rep{i}"

        # Incrementa o sufixo até encontrar um nome que não exista no projeto
        while novo_nome in existing_names:
            i += 1
            novo_nome = f"{base_nome}_rep{i}"
        # Retorna o nome único gerado
        return novo_nome

    def on_treeview_selection_changed(self, selected, deselected):
        """
        Reage às mudanças de seleção no QTreeView, atualizando a camada ativa no QGIS.
        Este método é chamado sempre que o usuário seleciona ou desseleciona uma camada na lista do QTreeView.
        
        Funções e Ações Desenvolvidas:
        - Obtenção do nome da camada selecionada no QTreeView.
        - Busca da camada correspondente no projeto do QGIS.
        - Atualização da camada ativa no QGIS para corresponder à seleção do usuário.

        :param selected: Índices dos itens que foram selecionados (não utilizado diretamente neste método).
        :param deselected: Índices dos itens que foram desselecionados (não utilizado diretamente neste método).
        """
        # Obtém os índices dos itens selecionados no QTreeView
        indexes = self.dlg.treeViewListaPonto.selectionModel().selectedIndexes()
        if indexes:
            # Extrai o nome da camada do item selecionado no QTreeView
            selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
            # Busca a camada por nome no projeto do QGIS
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            # Se a camada existir, define-a como a camada ativa
            if layers:
                self.iface.setActiveLayer(layers[0])

    def connect_name_changed_signals(self):
        """
        Conecta o sinal de mudança de nome de todas as camadas de ponto existentes no projeto QGIS.
        Este método percorre todas as camadas listadas no QgsLayerTreeRoot e, para cada camada,
        conecta o evento de mudança de nome à função de callback on_layer_name_changed.

        Funções e Ações Desenvolvidas:
        - Busca e iteração por todas as camadas no projeto QGIS.
        - Conexão do sinal de mudança de nome da camada ao método correspondente para tratamento.
        """
        # Acessa a raiz da árvore de camadas do projeto QGIS
        root = QgsProject.instance().layerTreeRoot()
        # Itera por todos os nós de camadas na árvore de camadas
        for layerNode in root.findLayers():
            # Verifica se o nó é uma instância de QgsLayerTreeLayer
            if isinstance(layerNode, QgsLayerTreeLayer):
                # Conecta o sinal de mudança de nome da camada ao método de tratamento on_layer_name_changed
                layerNode.layer().nameChanged.connect(self.on_layer_name_changed)

    def layers_added(self, layers):
        """
        Responde ao evento de adição de camadas no projeto QGIS, atualizando a lista de camadas no QTreeView
        e conectando sinais de mudança de nome para camadas de pontos recém-adicionadas.

        Este método verifica cada camada adicionada para determinar se é uma camada de vetor de pontos.
        Se for, ele atualiza a lista de camadas no QTreeView e conecta o sinal de mudança de nome à função
        de callback apropriada.

        :param layers: Lista de camadas recém-adicionadas ao projeto.

        Funções e Ações Desenvolvidas:
        - Verificação do tipo e da geometria das camadas adicionadas.
        - Atualização da visualização da lista de camadas no QTreeView para incluir novas camadas de pontos.
        - Conexão do sinal de mudança de nome da camada ao método de tratamento correspondente.
        """
        # Itera por todas as camadas adicionadas
        for layer in layers:
            # Verifica se a camada é do tipo vetor e se sua geometria é de ponto
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry:
                # Atualiza a lista de camadas no QTreeView
                self.atualizar_treeView_lista_ponto()
                # Conecta o sinal de mudança de nome da nova camada ao método on_layer_name_changed
                layer.nameChanged.connect(self.on_layer_name_changed)
                # Interrompe o loop após adicionar o sinal à primeira camada de ponto encontrada
                break

    def on_layer_name_changed(self):
        """
        Responde ao evento de mudança de nome de qualquer camada no projeto QGIS. 
        Este método é chamado automaticamente quando o nome de uma camada é alterado,
        e sua função é garantir que a lista de camadas no QTreeView seja atualizada para refletir
        essa mudança.

        Funções e Ações Desenvolvidas:
        - Atualização da lista de camadas no QTreeView para assegurar que os nomes das camadas estejam corretos.
        """
        # Atualiza a lista de camadas no QTreeView para refletir a mudança de nome
        self.atualizar_treeView_lista_ponto()

    def update_treeview_selection_from_qgis(self, layer):
        """
        Sincroniza a seleção no QTreeView com a camada ativa no QGIS. Quando uma camada é selecionada
        diretamente no QGIS, este método atualiza a seleção no QTreeView para refletir essa escolha.

        Este método verifica todas as entradas no QTreeView e seleciona aquela que corresponde ao nome
        da camada ativa no QGIS.

        :param layer: A camada atualmente ativa no QGIS que deve ser refletida na interface do usuário.

        Funções e Ações Desenvolvidas:
        - Limpeza da seleção atual no QTreeView para evitar seleções múltiplas ou desatualizadas.
        - Busca e seleção da camada correspondente no modelo do QTreeView.
        - Scrolling automático para o item selecionado, garantindo sua visibilidade.
        """
        # Limpa a seleção atual no modelo do QTreeView para garantir que não haja itens duplicadamente selecionados
        self.dlg.treeViewListaPonto.selectionModel().clearSelection()

        # Verifica se uma camada foi fornecida
        if layer:
            # Itera por todos os itens no modelo do QTreeView
            for i in range(self.treeViewModel.rowCount()):
                item = self.treeViewModel.item(i)
                # Encontra o item que corresponde ao nome da camada ativa no QGIS
                if item and item.text() == layer.name():
                    # Obtém o índice do item correspondente no modelo
                    index = self.treeViewModel.indexFromItem(item)
                    # Seleciona o item no QTreeView e garante que ele esteja visível para o usuário
                    self.dlg.treeViewListaPonto.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                    self.dlg.treeViewListaPonto.scrollTo(index)
                    break  # Encerra o loop após a seleção ser feita para evitar processamento desnecessário

    def adjust_item_font(self, item, layer):
        """
        Ajusta a fonte do item no QTreeView com base no tipo de fonte de dados da camada associada.
        Este método modifica a fonte para itálico se a camada for temporária (em memória) e para negrito se for permanente.

        A visualização visual das camadas como itálicas ou negritas ajuda o usuário a identificar rapidamente
        o tipo de camada (temporária vs. permanente) diretamente pela interface do usuário.

        :param item: O item no QTreeView que representa uma camada no QGIS.
        :param layer: A camada do QGIS associada ao item no QTreeView.

        :return: Retorna o item com a fonte ajustada.

        Funções e Ações Desenvolvidas:
        - Configuração da fonte para itálico se a fonte de dados da camada for 'memory' (temporária).
        - Configuração da fonte para negrito se a fonte de dados da camada for permanente.
        """
        # Cria um objeto QFont para ajustar a fonte do item
        fonte_item = QFont()

        # Verifica se a camada é temporária (dados em memória) e ajusta a fonte para itálico
        if layer.dataProvider().name() == 'memory':
            fonte_item.setItalic(True)
        # Se não for temporária, ajusta a fonte para negrito, indicando uma camada permanente
        else:
            fonte_item.setBold(True)

        # Aplica a fonte ajustada ao item no QTreeView
        item.setFont(fonte_item)

        # Retorna o item com a fonte ajustada para uso posterior se necessário
        return item

    def atualizar_treeView_lista_ponto(self):
        """
        Esta função atualiza a lista de camadas de pontos no QTreeView. 
        Ela limpa o modelo existente, adiciona um cabeçalho, 
        itera sobre todas as camadas no projeto do QGIS, filtra as camadas de pontos,
        cria itens para essas camadas e ajusta a fonte dos itens conforme necessário.
        Por fim, garante que a última camada esteja selecionada no QTreeView.

        Detalhes:
        - Limpa o modelo do QTreeView.
        - Adiciona um item de cabeçalho ao modelo.
        - Obtém a raiz da árvore de camadas do QGIS e todas as camadas do projeto.
        - Itera sobre todas as camadas do projeto.
            - Filtra para incluir apenas camadas de pontos.
            - Cria um item para cada camada de pontos com nome, verificável e não editável diretamente.
            - Define o estado de visibilidade do item com base no estado do nó da camada.
            - Ajusta a fonte do item com base no tipo de camada (temporária ou permanente).
            - Adiciona o item ao modelo do QTreeView.
        - Seleciona a última camada no QTreeView.
        """
        # Limpa o modelo existente para assegurar que não haja itens desatualizados
        self.treeViewModel.clear()
        
        # Cria e configura um item de cabeçalho para a lista
        headerItem = QStandardItem('Lista de Camadas de Pontos')
        headerItem.setTextAlignment(Qt.AlignCenter)
        self.treeViewModel.setHorizontalHeaderItem(0, headerItem)

        # Acessa a raiz da árvore de camadas do QGIS para obter todas as camadas
        root = QgsProject.instance().layerTreeRoot()
        layers = QgsProject.instance().mapLayers().values()

        # Itera sobre todas as camadas do projeto
        for layer in layers:
            # Filtra para incluir apenas camadas de pontos
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry:
                # Cria um item para a camada com nome, verificável e não editável diretamente
                item = QStandardItem(layer.name())
                item.setCheckable(True)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(layer.id(), Qt.UserRole)

                # Encontra o nó correspondente na árvore de camadas para definir o estado de visibilidade
                layerNode = root.findLayer(layer.id())
                item.setCheckState(Qt.Checked if layerNode and layerNode.isVisible() else Qt.Unchecked)

                # Ajusta a fonte do item com base no tipo de camada (temporária ou permanente)
                self.adjust_item_font(item, layer)

                # Adiciona o item ao modelo do QTreeView
                self.treeViewModel.appendRow(item)
        
        # Seleciona a última camada no QTreeView para garantir que uma camada esteja sempre selecionada
        self.selecionar_ultima_camada()

    def selecionar_ultima_camada(self):
        """
        Esta função garante que uma camada de pontos esteja sempre selecionada no QTreeView.
        Se houver camadas no modelo, seleciona a última camada.
        Se não houver camadas, tenta selecionar a primeira camada disponível.

        Detalhes:
        - Obtém o modelo associado ao QTreeView.
        - Conta o número de linhas (camadas) no modelo.
        - Se houver camadas:
            - Obtém o índice da última camada no modelo.
            - Define a seleção atual para o índice da última camada e garante que esteja visível.
        - Se não houver camadas:
            - Obtém o índice da primeira camada.
            - Se válido, define a seleção atual para o índice da primeira camada e garante que esteja visível.
        """
        # Obtém o modelo associado ao QTreeView
        model = self.dlg.treeViewListaPonto.model()
        
        # Conta o número de linhas (camadas) no modelo
        row_count = model.rowCount()

        # Verifica se há camadas no modelo
        if row_count > 0:
            # Obtém o índice da última camada no modelo
            last_index = model.index(row_count - 1, 0)
            
            # Define a seleção atual para o índice da última camada
            self.dlg.treeViewListaPonto.setCurrentIndex(last_index)
            
            # Garante que a última camada esteja visível no QTreeView
            self.dlg.treeViewListaPonto.scrollTo(last_index)
        else:
            # Obtém o índice da primeira camada no modelo
            first_index = model.index(0, 0)
            
            # Verifica se o índice da primeira camada é válido
            if first_index.isValid():
                # Define a seleção atual para o índice da primeira camada
                self.dlg.treeViewListaPonto.setCurrentIndex(first_index)
                
                # Garante que a primeira camada esteja visível no QTreeView
                self.dlg.treeViewListaPonto.scrollTo(first_index)

    def on_current_layer_changed(self, layer):
        """
        Esta função é chamada quando a camada ativa no QGIS muda.
        Ela verifica se a camada ativa é uma camada de pontos e, se for, 
        atualiza a seleção no QTreeView para corresponder à camada ativa.
        Se a camada ativa não for uma camada de pontos, reverte a seleção 
        para a última camada de pontos selecionada no QTreeView.

        Detalhes:
        - Verifica se a camada ativa existe e se é uma camada de pontos.
        - Se for uma camada de pontos:
            - Obtém o modelo associado ao QTreeView.
            - Itera sobre todas as linhas no modelo para encontrar a camada correspondente.
            - Quando encontrada, seleciona e garante que a camada esteja visível no QTreeView.
        - Se a camada ativa não for uma camada de pontos, seleciona a última camada de pontos no QTreeView.
        """
        # Verifica se a camada ativa existe e se é uma camada de pontos
        if layer and layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry:
            # Obtém o modelo associado ao QTreeView
            model = self.dlg.treeViewListaPonto.model()
            
            # Itera sobre todas as linhas no modelo
            for row in range(model.rowCount()):
                # Obtém o item da linha atual
                item = model.item(row, 0)
                
                # Verifica se o nome do item corresponde ao nome da camada ativa
                if item.text() == layer.name():
                    # Obtém o índice do item correspondente
                    index = model.indexFromItem(item)
                    
                    # Define a seleção atual para o índice do item correspondente
                    self.dlg.treeViewListaPonto.setCurrentIndex(index)
                    
                    # Garante que o item correspondente esteja visível no QTreeView
                    self.dlg.treeViewListaPonto.scrollTo(index)
                    
                    # Interrompe a iteração, pois a camada correspondente foi encontrada
                    break
        else:
            # Se a camada ativa não for uma camada de pontos, seleciona a última camada de pontos no QTreeView
            self.selecionar_ultima_camada()

    def on_layer_was_renamed(self, layerId, newName):
        """
        Responde ao evento de renomeação de uma camada no QGIS, atualizando o nome da camada no QTreeView.
        Este método garante que as mudanças de nome no projeto sejam refletidas na interface do usuário.

        :param layerId: ID da camada que foi renomeada.
        :param newName: Novo nome atribuído à camada.

        Funções e Ações Desenvolvidas:
        - Pesquisa no modelo do QTreeView pelo item que corresponde à camada renomeada.
        - Atualização do texto do item no QTreeView para refletir o novo nome.
        """
        # Itera sobre todos os itens no modelo do QTreeView para encontrar o item correspondente
        for i in range(self.treeViewModel.rowCount()):
            item = self.treeViewModel.item(i)
            layer = QgsProject.instance().mapLayer(layerId)
            # Verifica se o item corresponde à camada que foi renomeada
            if layer and item.text() == layer.name():
                item.setText(newName)  # Atualiza o nome do item no QTreeView
                break  # Sai do loop após atualizar o nome

    def on_item_changed(self, item):
        """
        Responde a mudanças nos itens do QTreeView, especificamente ao estado do checkbox, sincronizando a visibilidade
        da camada correspondente no QGIS. Este método assegura que ações na interface do usuário sejam refletidas no
        estado visual das camadas no mapa.

        :param item: Item do QTreeView que foi alterado (geralmente, uma mudança no estado do checkbox).

        Funções e Ações Desenvolvidas:
        - Busca da camada correspondente no projeto QGIS usando o nome do item.
        - Ajuste da visibilidade da camada na árvore de camadas do QGIS com base no estado do checkbox do item.
        """
        # Encontra a camada correspondente no projeto QGIS pelo nome do item
        layer = QgsProject.instance().mapLayersByName(item.text())
        if not layer:
            return  # Se a camada não for encontrada, interrompe o método

        layer = layer[0]  # Assume a primeira camada encontrada (nomes deveriam ser únicos)

        # Encontra o QgsLayerTreeLayer correspondente na árvore de camadas
        root = QgsProject.instance().layerTreeRoot()
        node = root.findLayer(layer.id())

        if node:
            # Ajusta a visibilidade da camada com base no estado do checkbox do item
            node.setItemVisibilityChecked(item.checkState() == Qt.Checked)

    def sync_from_qgis_to_treeview(self):
        """
        Sincroniza o estado do checkbox no QTreeView com a visibilidade das camadas no QGIS.
        Este método garante que as alterações na visibilidade das camadas, feitas através do QGIS,
        sejam refletidas nos checkboxes correspondentes no QTreeView.

        Funções e Ações Desenvolvidas:
        - Obtenção da lista atual de camadas visíveis no canvas do QGIS.
        - Iteração pelos itens do QTreeView para ajustar o estado do checkbox com base na visibilidade de cada camada.

        Observação: Este método assume que os nomes das camadas são únicos, o que permite a correspondência direta entre
        o item no QTreeView e a camada no QGIS.
        """
        # Acessa a raiz da árvore de camadas do projeto QGIS
        root = QgsProject.instance().layerTreeRoot()
        # Obtém as camadas atualmente visíveis no canvas do QGIS
        layers = self.iface.mapCanvas().layers()
        layer_names = [layer.name() for layer in layers]  # Lista de nomes das camadas visíveis

        # Itera por cada item no modelo do QTreeView
        for i in range(self.treeViewModel.rowCount()):
            item = self.treeViewModel.item(i)
            if item:
                # Busca a camada correspondente no QGIS pelo nome do item
                layerNode = root.findLayer(QgsProject.instance().mapLayersByName(item.text())[0].id())
                if layerNode:
                    # Ajusta o estado do checkbox com base na visibilidade da camada correspondente
                    item.setCheckState(Qt.Checked if layerNode.isVisible() else Qt.Unchecked)

    def on_item_double_clicked(self, index):
        """
        Manipula o evento de duplo clique em um item do QTreeView. Este método é acionado quando um usuário
        efetua um duplo clique em uma camada listada, permitindo que altere as cores de preenchimento e borda da camada.

        Funções e Ações Desenvolvidas:
        - Recuperação da camada associada ao item clicado.
        - Obtenção das cores atuais de preenchimento e borda da camada.
        - Exibição de um diálogo para que o usuário selecione novas cores.
        - Aplicação das cores selecionadas à camada, se novas cores foram escolhidas.

        :param index: QModelIndex que representa o item no modelo que foi duplo clicado.
        """
        # Obtém o ID da camada do item clicado usando o UserRole
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            # Obtém as cores atuais de preenchimento e borda da camada
            current_fill_color, current_border_color = self.get_point_colors(layer)
            # Solicita ao usuário que selecione novas cores para preenchimento e borda
            new_fill_color, new_border_color = self.prompt_for_new_colors(current_fill_color, current_border_color)
            # Se novas cores forem selecionadas, aplica estas cores à camada
            if new_fill_color and new_border_color:
                self.apply_new_colors(layer, new_fill_color, new_border_color)

    def get_point_colors(self, layer):
        """
        Obtém as cores de preenchimento e borda de um ponto a partir da camada especificada.
        Este método acessa o renderizador da camada para extrair as configurações de cor atuais do símbolo do ponto.
        
        Funções e Ações Desenvolvidas:
        - Acesso ao renderizador da camada para obter os símbolos usados na renderização.
        - Extração da cor de preenchimento e da cor da borda do primeiro símbolo de ponto.
        - Retorno das cores obtidas ou (None, None) se as cores não puderem ser determinadas.
        
        :param layer: Camada do QGIS de onde as cores serão obtidas (deve ser uma camada de vetor de ponto).
        
        :return: Uma tupla contendo a cor de preenchimento e a cor da borda do ponto, respectivamente.
                 Retorna (None, None) se não conseguir extrair as cores.
        """
        # Acessa o renderizador da camada para obter a lista de símbolos usados na renderização
        symbols = layer.renderer().symbols(QgsRenderContext())
        if symbols:
            # Extrai a cor de preenchimento do primeiro símbolo (geralmente usado para o preenchimento de pontos)
            fill_color = symbols[0].color()
            # Define uma cor padrão para a borda caso não seja especificada
            border_color = Qt.black  # Cor padrão se não houver contorno definido
            # Verifica se há camadas de símbolo no símbolo do ponto
            if symbols[0].symbolLayerCount() > 0:
                border_layer = symbols[0].symbolLayer(0)
                # Se o símbolo da borda tiver uma propriedade de cor de borda, extrai essa cor
                if hasattr(border_layer, 'strokeColor'):
                    border_color = border_layer.strokeColor()
            # Retorna as cores de preenchimento e borda
            return fill_color, border_color
        # Retorna None para ambos se não houver símbolos ou se as cores não puderem ser determinadas
        return None, None

    def apply_new_colors(self, layer, fill_color, border_color):
        """
        Aplica novas cores de preenchimento e borda à camada especificada. Este método atualiza o renderizador
        da camada com um novo símbolo criado a partir das cores selecionadas, garantindo que as alterações de cor
        sejam visualmente refletidas no mapa do QGIS.

        Funções e Ações Desenvolvidas:
        - Criação de um novo símbolo com as cores de preenchimento e borda especificadas.
        - Configuração de um novo renderizador para a camada usando o símbolo criado.
        - Atualização da camada no QGIS para refletir as novas cores.

        :param layer: Camada do QGIS que terá suas cores alteradas.
        :param fill_color: Nova cor de preenchimento para a camada.
        :param border_color: Nova cor de borda para a camada.
        """
        # Cria um novo símbolo com as cores selecionadas baseado no tipo de geometria da camada
        new_symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        new_symbol.setColor(fill_color)  # Define a cor de preenchimento do novo símbolo
        new_symbol.symbolLayer(0).setStrokeColor(border_color)  # Define a cor da borda no primeiro símbolo da camada

        # Cria um novo renderizador usando o novo símbolo e aplica à camada
        new_renderer = QgsSingleSymbolRenderer(new_symbol)
        layer.setRenderer(new_renderer)  # Atualiza o renderizador da camada

        # Dispara o processo de repintura para atualizar a visualização da camada no mapa
        layer.triggerRepaint()
        # Emite um sinal para notificar que a camada foi adicionada (usado para atualizar interfaces de usuário dependentes)
        QgsProject.instance().layerWasAdded.emit(layer)
        # Refresca a simbologia da camada na árvore de camadas do QGIS para garantir que as mudanças sejam visíveis
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def prompt_for_new_colors(self, current_fill_color, current_border_color):
        """
        Exibe diálogos de seleção de cor para que o usuário escolha novas cores de preenchimento e borda para uma camada.
        Este método usa o QColorDialog para permitir a seleção visual das cores, proporcionando uma interface amigável
        e intuitiva.

        Funções e Ações Desenvolvidas:
        - Exibição de diálogos para seleção de cores para a borda e o preenchimento da camada.
        - Verificação da validade das cores selecionadas.
        - Retorno das novas cores selecionadas, ou cores transparentes se nenhuma cor válida for escolhida.

        :param current_fill_color: Cor atual de preenchimento da camada, usada como valor inicial no diálogo.
        :param current_border_color: Cor atual da borda da camada, usada como valor inicial no diálogo.

        :return: Uma tupla contendo as novas cores de preenchimento e borda. Retorna cores transparentes se o usuário
                 cancelar a seleção ou selecionar uma cor inválida.
        """
        # Inicializa as variáveis de cor como None para verificar se houve seleção
        new_fill_color = None
        new_border_color = None

        # Solicita ao usuário que selecione uma nova cor da borda
        border_color_dialog = QColorDialog.getColor(current_border_color, self.dlg, "Escolha a Cor da Borda")
        if border_color_dialog.isValid():
            new_border_color = border_color_dialog
        else:
            new_border_color = QColor(0, 0, 0, 0)  # Define cor transparente se nenhuma cor válida for selecionada

        # Solicita ao usuário que selecione uma nova cor de preenchimento
        fill_color_dialog = QColorDialog.getColor(current_fill_color, self.dlg, "Escolha a Cor de Preenchimento")
        if fill_color_dialog.isValid():
            new_fill_color = fill_color_dialog
        else:
            new_fill_color = QColor(0, 0, 0, 0)  # Define cor transparente se nenhuma cor válida for selecionada

        # Retorna as novas cores selecionadas
        return new_fill_color, new_border_color

    def abrir_layer_properties(self, index):
        """
        Abre a janela de propriedades da camada selecionada no QTreeView. Este método é chamado quando o usuário deseja
        ver ou editar as propriedades de uma camada específica, como símbolos, campos e outras configurações.

        Funções e Ações Desenvolvidas:
        - Obtenção do ID da camada a partir do item selecionado no QTreeView.
        - Recuperação da camada correspondente no projeto QGIS.
        - Exibição da janela de propriedades da camada se ela for encontrada.

        :param index: O índice do modelo que representa o item selecionado no QTreeView.
        """
        # Obtém o ID da camada do item selecionado no treeView
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        # Se a camada for encontrada, exibe a janela de propriedades da camada
        if layer:
            self.iface.showLayerProperties(layer)

    def open_context_menu(self, position):
        """
        Cria e exibe um menu de contexto para ações específicas em um item selecionado no QTreeView.
        Este método é acionado com um clique do botão direito do mouse sobre um item da lista,
        apresentando opções como abrir propriedades da camada e alterar tamanho dos pontos da camada.

        Funções e Ações Desenvolvidas:
        - Verificação da seleção atual no QTreeView para determinar o item sobre o qual o menu será aberto.
        - Criação das opções do menu para manipulação das propriedades da camada e ajuste o tamanho do ponto.
        - Execução do menu no local do clique e execução da ação selecionada.

        :param position: A posição do cursor no momento do clique, usada para posicionar o menu de contexto.
        """
        # Obtém os índices selecionados no QTreeView
        indexes = self.dlg.treeViewListaPonto.selectedIndexes()
        if indexes:
            # Obter o índice da primeira coluna, que deve conter o ID da camada
            index = indexes[0].sibling(indexes[0].row(), 0)
            # Cria o menu de contexto
            menu = QMenu()
            # Adiciona opção para abrir propriedades da camada
            layer_properties_action = menu.addAction("Abrir Propriedades da Camada")
            # Adiciona opção para alterar a espessura da borda
            change_border_thickness_action = menu.addAction("Tamanho do Ponto")
            # Exibe o menu no local do clique e aguarda ação do usuário
            action = menu.exec_(self.dlg.treeViewListaPonto.viewport().mapToGlobal(position))

            # Executa a ação correspondente à escolha do usuário
            if action == layer_properties_action:
                self.abrir_layer_properties(index)
            elif action == change_border_thickness_action:
                self.prompt_for_new_point_size(index)

    def prompt_for_new_point_size(self, index):
        """
        Exibe um diálogo que permite ao usuário ajustar o tamanho do ponto de uma camada de ponto.
        O método recupera o tamanho atual do ponto, apresenta um QDoubleSpinBox para seleção do novo valor,
        e aplica a alteração se o usuário confirmar.

        Funções e Ações Desenvolvidas:
        - Recuperação da camada associada ao item selecionado no QTreeView.
        - Obtenção do tamanho atual do ponto da camada.
        - Criação de um diálogo com um QDoubleSpinBox para o usuário escolher o novo tamanho.
        - Aplicação do novo tamanho ao ponto da camada se o usuário confirmar a mudança.

        :param index: Índice do item no modelo de onde o ID da camada é extraído.
        """
        # Recupera o ID da camada do item selecionado no QTreeView
        layer_id = index.model().itemFromIndex(index).data(Qt.UserRole)
        # Busca a camada correspondente no projeto QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer:
            # Obtém o tamanho atual do ponto da camada
            current_size = self.get_current_point_size(layer)

            # Cria um diálogo personalizado para ajuste do tamanho
            dlg = QDialog(self.dlg)
            dlg.setWindowTitle("Tamanho do Ponto")
            layout = QVBoxLayout(dlg)

            # Configura um QDoubleSpinBox para escolha do novo tamanho
            spinBox = QDoubleSpinBox(dlg)
            spinBox.setRange(0, 100)  # Define o intervalo de valores
            spinBox.setSingleStep(0.2)  # Define o incremento de ajuste
            spinBox.setValue(current_size)  # Define o valor inicial com o tamanho atual
            spinBox.setDecimals(2)  # Define a precisão decimal
            layout.addWidget(spinBox)

            # Cria botões de OK e Cancelar
            buttonLayout = QHBoxLayout()
            okButton = QPushButton("OK", dlg)
            okButton.clicked.connect(dlg.accept)  # Conecta o botão OK à ação de aceitar o diálogo
            buttonLayout.addWidget(okButton)
            layout.addLayout(buttonLayout)

            # Exibe o diálogo e espera pela ação do usuário
            if dlg.exec_():
                new_size = spinBox.value()  # Obtém o novo valor do tamanho
                # Aplica o novo tamanho ao ponto da camada se o usuário confirmar
                self.apply_new_point_size(layer, new_size)

    def get_current_point_size(self, layer):
        """
        Recupera o tamanho atual do ponto de uma camada específica no QGIS. Este método acessa o renderizador da camada,
        e extrai o tamanho do ponto do primeiro símbolo de ponto encontrado.

        Funções e Ações Desenvolvidas:
        - Acesso ao renderizador da camada para obter os símbolos usados na renderização.
        - Extração do tamanho do ponto do primeiro símbolo de ponto se disponível.
        - Retorno do tamanho atual do ponto ou 0 se não for possível determinar.

        :param layer: Camada do QGIS cujo tamanho do ponto precisa ser obtido.
        :return: Tamanho do ponto da camada ou 0 se não for possível determinar o tamanho.
        """
        # Acessa o renderizador da camada para obter a lista de símbolos utilizados
        symbols = layer.renderer().symbols(QgsRenderContext())
        if symbols and symbols[0].symbolLayerCount() > 0:
            # Extrai o primeiro símbolo de ponto
            point_layer = symbols[0].symbolLayer(0)
            # Verifica se o símbolo do ponto possui um atributo para tamanho
            if hasattr(point_layer, 'size'):
                # Retorna o tamanho do ponto se disponível
                return point_layer.size()
        # Retorna 0 como valor padrão caso o tamanho do ponto não seja acessível ou não esteja definido
        return 0

    def apply_new_point_size(self, layer, size):
        """
        Aplica um novo tamanho de ponto para a camada especificada no QGIS. Este método modifica diretamente
        o símbolo de ponto usado para renderizar a camada, garantindo que as alterações sejam visíveis imediatamente
        no mapa.

        Funções e Ações Desenvolvidas:
        - Acesso ao renderizador da camada para modificar o tamanho do ponto de cada símbolo de ponto.
        - Aplicação do novo tamanho do ponto.
        - Disparo de eventos para atualizar a visualização e a interface do usuário no QGIS.

        :param layer: Camada do QGIS que terá o tamanho do ponto ajustado.
        :param size: Novo tamanho do ponto a ser aplicado.
        """
        # Acessa o renderizador da camada para obter os símbolos usados na renderização
        symbols = layer.renderer().symbols(QgsRenderContext())
        if symbols:
            # Itera sobre cada símbolo na lista de símbolos da camada
            for symbol in symbols:
                # Verifica se há camadas de símbolo disponíveis no símbolo atual
                if symbol.symbolLayerCount() > 0:
                    point_layer = symbol.symbolLayer(0)
                    # Verifica se o símbolo do ponto possui um método para definir o tamanho do ponto
                    if hasattr(point_layer, 'setSize'):
                        # Aplica o novo tamanho do ponto
                        point_layer.setSize(size)
            # Dispara o repintura da camada para atualizar a visualização no mapa
            layer.triggerRepaint()
            # Emite um sinal indicando que a camada foi adicionada para atualizar interfaces de usuário dependentes
            QgsProject.instance().layerWasAdded.emit(layer)
            # Refresca a simbologia da camada na árvore de camadas do QGIS
            self.iface.layerTreeView().refreshLayerSymbology(layer.id())

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
            self.dlg,
            "Salvar Camada",
            nome_completo_proposto,
            tipo_arquivo,
            options=options)

        # Verifica se um nome de arquivo foi escolhido
        if fileName:
            # Atualiza o último diretório usado nas configurações do QGIS
            settings.setValue("lastDir", os.path.dirname(fileName))

            # Assegura que o arquivo tenha a extensão correta
            if not fileName.endswith(extensao):
                fileName += extensao

        return fileName  # Retorna o caminho completo do arquivo escolhido ou None se cancelado

    def iniciar_progress_bar(self, layer):
        """
        Inicia e exibe uma barra de progresso na interface do usuário para o processo de exportação de uma camada para DXF.

        Parâmetros:
        - layer (QgsVectorLayer): A camada para a qual a barra de progresso será exibida, indicando o progresso da exportação.

        Funcionalidades:
        - Cria uma mensagem personalizada na barra de mensagens para acompanhar o progresso.
        - Configura e estiliza uma barra de progresso.
        - Adiciona a barra de progresso à barra de mensagens e a exibe na interface do usuário.
        - Define o valor máximo da barra de progresso com base no número de feições na camada.
        - Retorna os widgets de barra de progresso e de mensagem para que possam ser atualizados durante a exportação.
        """
        # Cria uma mensagem personalizada na barra de progresso
        progressMessageBar = self.iface.messageBar().createMessage("Exportando camada para DXF: " + layer.name())
        progressBar = QProgressBar()  # Cria uma instância da QProgressBar
        progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Alinha a barra de progresso à esquerda e verticalmente ao centro
        progressBar.setFormat("%p% - %v de %m Feições processadas")  # Define o formato da barra de progresso
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

        # Define o valor máximo da barra de progresso com base no número de feições da camada
        feature_count = layer.featureCount()
        progressBar.setMaximum(feature_count)

        # Retorna o progressBar e o progressMessageBar para que possam ser atualizados durante o processo de exportação
        return progressBar, progressMessageBar

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivos=None):
        """
        Exibe uma mensagem na barra de mensagens do QGIS, proporcionando feedback ao usuário baseado nas ações realizadas.
        As mensagens podem ser de erro ou de sucesso, com uma duração configurável e uma opção de abrir uma pasta.

        :param texto: Texto da mensagem a ser exibida.
        :param tipo: Tipo da mensagem ("Erro" ou "Sucesso") que determina a cor e o ícone da mensagem.
        :param duracao: Duração em segundos durante a qual a mensagem será exibida (padrão é 3 segundos).
        :param caminho_pasta: Caminho da pasta a ser aberta ao clicar no botão (padrão é None).
        :param caminho_arquivos: Caminho do arquivo a ser executado ao clicar no botão (padrão é None).
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
            
            # Se o caminho da pasta for fornecido, adiciona um botão para abrir a pasta
            if caminho_pasta:
                botao_abrir_pasta = QPushButton("Abrir Pasta")
                botao_abrir_pasta.clicked.connect(lambda: os.startfile(caminho_pasta))
                msg.layout().insertWidget(1, botao_abrir_pasta)  # Adiciona o botão à esquerda do texto
            
            # Se o caminho do arquivo for fornecido, adiciona um botão para executar o arquivo
            if caminho_arquivos:
                botao_executar = QPushButton("Executar")
                botao_executar.clicked.connect(lambda: os.startfile(caminho_arquivos))
                msg.layout().insertWidget(2, botao_executar)  # Adiciona o botão à esquerda do texto
            
            # Adiciona a mensagem à barra com o nível informativo e a duração especificada
            bar.pushWidget(msg, level=Qgis.Info, duration=duracao)

    def obter_cor_rotulo(self, layer):
        """
        Obtém a cor do rótulo da camada e a converte para o formato de cor KML (AABBGGRR).

        Parâmetros:
        - layer (QgsVectorLayer): A camada de origem para obter a cor do rótulo.

        Funcionalidades:
        - Verifica se os rótulos estão habilitados para a camada.
        - Obtém o renderizador de rótulo e as configurações de texto.
        - Converte a cor do rótulo do formato Qt para o formato KML.
        - Retorna a cor do rótulo em formato hexadecimal (AABBGGRR).
        - Retorna preto como padrão se os rótulos não estiverem habilitados ou configurados.
        """
        # Verifica se os rótulos estão habilitados para a camada
        if layer.labelsEnabled():
            # Obtenha o renderizador de rótulo e as configurações de texto
            labeling = layer.labeling()
            if labeling:
                text_format = labeling.settings().format()
                cor_texto = text_format.color()

                # Converta a cor do Qt para o formato de cor KML (AABBGGRR)
                cor_kml = cor_texto.alpha() << 24 | cor_texto.blue() << 16 | cor_texto.green() << 8 | cor_texto.red()
                cor_kml_hex = format(cor_kml, '08x')
                return cor_kml_hex

        # Retorna preto como padrão se os rótulos não estiverem habilitados ou não configurados
        return 'ff000000'

    def obter_cor_icone(self, layer):
        """
        Obtém a cor do ícone da camada e a converte para o formato de cor KML (AABBGGRR).

        Parâmetros:
        - layer (QgsVectorLayer): A camada de origem para obter a cor do ícone.

        Funcionalidades:
        - Verifica se a geometria da camada é do tipo ponto.
        - Obtém o renderizador de símbolo da camada.
        - Verifica se o renderizador é do tipo 'singleSymbol' e se o símbolo é um marcador.
        - Obtém a cor do símbolo do ícone.
        - Converte a cor do símbolo do formato Qt para o formato KML.
        - Retorna a cor do ícone em formato hexadecimal (AABBGGRR).
        - Retorna branco como padrão se a geometria não for do tipo ponto ou se o símbolo não for um marcador.
        """
        # Verifica se a geometria da camada é do tipo ponto
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            # Obtém o símbolo da camada
            renderer = layer.renderer()
            if renderer and renderer.type() == 'singleSymbol':
                symbol = renderer.symbol()
                if symbol and symbol.type() == QgsSymbol.Marker:
                    # Obtém a cor do símbolo
                    cor_icone = symbol.color()
                    cor_kml = cor_icone.alpha() << 24 | cor_icone.blue() << 16 | cor_icone.green() << 8 | cor_icone.red()
                    cor_kml_hex = format(cor_kml, '08x')
                    return cor_kml_hex

        # Retorna branco como padrão se não for um símbolo de ponto padrão
        return 'ffffffff'

    def url_para_link_html(self, url):
        """
        Converte um URL em um link HTML clicável. A função realiza as seguintes etapas:

        1. Verifica se o texto fornecido é um URL válido.
        2. Se for um URL válido, formata o texto "Link de acesso" como um link HTML com o URL correto.
        3. Se não for um URL, retorna o texto como está.

        Parâmetros:
        - url (str): O texto a ser verificado e possivelmente convertido em um link HTML.

        Funcionalidades:
        - Verificação de validade do URL usando expressão regular.
        - Formatação do texto como link HTML se o URL for válido.
        - Retorno do texto original se não for um URL válido.
        """
        # Verifica se o texto é um URL válido
        if re.match(r'https?://[^\s]+', url):
            # Retorna o texto "Acesso Aqui" formatado como link HTML com o URL correto
            return f"<a href='{url}'>Link de acesso</a>"
        else:
            # Se não for um URL, retorna o texto como está
            return url

    def gerar_cor_suave(self):
        """
        Gera uma cor suave aleatória no formato hexadecimal. A função realiza as seguintes etapas:

        1. Gera valores aleatórios para os componentes RGB dentro do intervalo de cores suaves (180-255).
        2. Formata e retorna a cor como uma string hexadecimal.

        Funcionalidades:
        - Geração de valores aleatórios para os componentes vermelho, verde e azul (RGB).
        - Formatação da cor no formato hexadecimal.

        Retorna:
        - str: A cor gerada no formato hexadecimal (e.g., '#aabbcc').
        """
        # Gera valores aleatórios para os componentes RGB dentro do intervalo de cores suaves
        r = random.randint(180, 255) # Componente vermelho
        g = random.randint(180, 255) # Componente verde
        b = random.randint(180, 255) # Componente azul
        return f'#{r:02x}{g:02x}{b:02x}' # Retorna a cor formatada como uma string hexadecimal

    def exportar_para_kml(self):
        """
        Exporta a camada selecionada para um arquivo KML. A função realiza as seguintes etapas:

        1. Obtém a seleção atual no QTreeView.
        2. Verifica se alguma camada foi selecionada. Se não, exibe uma mensagem de erro.
        3. Obtém o nome da camada selecionada.
        4. Verifica se a camada selecionada está presente no projeto. Se não, exibe uma mensagem de erro.
        5. Verifica se a camada possui feições para exportar. Se não, exibe uma mensagem de erro.
        6. Abre um diálogo para o usuário selecionar o campo de identificação e a URL do ícone.
           - Se o usuário cancelar o diálogo, exibe uma mensagem informativa.
           - Se o usuário aceitar, obtém o campo de identificação, URL do ícone e o estado do checkbox de rótulos.
        7. Obtém o caminho do arquivo para salvar o KML.
           - Se o usuário cancelar a seleção do caminho, exibe uma mensagem informativa.
        8. Inicia a barra de progresso após selecionar o caminho do arquivo.
        9. Mede o tempo de execução da criação do KML e da escrita no arquivo.
           - Cria o conteúdo KML em memória.
           - Escreve o conteúdo KML no arquivo.
        10. Calcula o tempo de execução.
        11. Remove a barra de progresso.
        12. Exibe uma mensagem de sucesso indicando o tempo de execução.

        Funcionalidades:
        - Verificação da seleção e existência da camada.
        - Verificação da presença de feições na camada.
        - Diálogo de seleção de campo de identificação e URL de ícone.
        - Seleção do caminho do arquivo para salvar o KML.
        - Criação e escrita do conteúdo KML.
        - Exibição de mensagens informativas e de erro.
        - Exibição de barra de progresso durante o processo de exportação.
        """
        # Obtém a seleção atual no QTreeView
        indexes = self.dlg.treeViewListaPonto.selectionModel().selectedIndexes()
        if not indexes:
            self.mostrar_mensagem("Selecione uma camada para exportar.", "Erro")
            return

        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        layer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
        if not layer:
            self.mostrar_mensagem("Camada não encontrada.", "Erro")
            return

        # Verifica se há feições na camada
        if layer.featureCount() == 0:
            self.mostrar_mensagem("Nenhuma feição para ser exportada.", "Erro")
            return

        # Obtenha o campo de identificação desejado e a URL do ícone do usuário
        dialog = IconFieldSelectionDialog(layer)
        if dialog.exec_() == QDialog.Accepted:
            campo_id, icon_url, image_url, overlay_url = dialog.get_selections()  # Captura campo, URL do ícone e URL da imagem
            exportar_rotulos = dialog.check_box.isChecked()  # Obtem o estado do checkbox diretamente do diálogo
        else:
            self.mostrar_mensagem("Seleção de ícone cancelada.", "Info")
            return

        # Obtenha o caminho do arquivo para salvar o KML
        nome_padrao = f"{layer.name()}.kml"
        tipo_arquivo = "KML Files (*.kml)"
        caminho_arquivo = self.escolher_local_para_salvar(nome_padrao, tipo_arquivo)
        if not caminho_arquivo:
            self.mostrar_mensagem("Exportação cancelada.", "Info")
            return

        # Inicia a barra de progresso após selecionar o caminho do arquivo
        progressBar, progressMessageBar = self.iniciar_progress_bar(layer)

        # Medir o tempo de execução da criação do KML e da escrita no arquivo
        start_time = time.time()
        kml_element = self.criar_kml_em_memoria(layer, campo_id, icon_url, exportar_rotulos, progressBar, image_url, overlay_url)  # Passa o estado do checkbox como argumento
        tree = ET.ElementTree(kml_element)
        tree.write(caminho_arquivo, xml_declaration=True, encoding='utf-8', method="xml")
        end_time = time.time()

        # Calcula o tempo de execução
        execution_time = end_time - start_time

        # Remove a barra de progresso
        self.iface.messageBar().clearWidgets()

        # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
        self.mostrar_mensagem(
            f"Camada exportada para KMZ em {execution_time:.2f} segundos", 
            "Sucesso", 
            caminho_pasta=os.path.dirname(caminho_arquivo), 
            caminho_arquivos=caminho_arquivo)

    def criar_kml_em_memoria(self, layer, campo_id, icon_url, exportar_rotulos, progressBar, image_url, overlay_url):
        """
        Cria o conteúdo KML em memória para a camada fornecida. A função realiza as seguintes etapas:

        1. Cria o elemento raiz do KML e o elemento Document.
        2. Obtém a cor do ícone e do rótulo da camada.
        3. Verifica se a camada está no sistema de referência de coordenadas WGS84 (EPSG:4326) e, se necessário, prepara a transformação de coordenadas.
        4. Itera sobre cada feição na camada e cria um Placemark para cada uma:
           - Adiciona um nome ao Placemark com o valor do campo ID.
           - Cria a tag Point com as coordenadas da feição.
           - Adiciona ExtendedData com os atributos da feição.
           - Define um estilo para o Placemark, incluindo ícone e rótulo.
        5. Atualiza a barra de progresso durante o processamento.
        6. Retorna o elemento raiz do KML.
        7. Cria um índice espacial para a camada

        Parâmetros:
        - layer (QgsVectorLayer): A camada de origem para a exportação.
        - campo_id (str): O campo de identificação a ser usado como nome dos Placemarks.
        - icon_url (str): A URL do ícone a ser usado para os Placemarks.
        - exportar_rotulos (bool): Indica se os rótulos devem ser exportados.
        - Adiciona um ScreenOverlay ao documento KML.
        - progressBar (QProgressBar): A barra de progresso a ser atualizada durante o processamento.

        Funcionalidades:
        - Criação de KML em memória com elementos e estilos configuráveis.
        - Transformação de coordenadas para WGS84, se necessário.
        - Adição de dados estendidos e estilos personalizados para cada Placemark.
        - Atualização da barra de progresso para informar o progresso do usuário.
        
        Retorna:
        - xml.etree.ElementTree.Element: O elemento raiz do KML criado.
        """
        # Cria um índice espacial para a camada
        spatial_index = QgsSpatialIndex()
        for feature in layer.getFeatures():
            spatial_index.insertFeature(feature)

        # Cria o elemento raiz do KML
        kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, 'Document')
        cor_icone = self.obter_cor_icone(layer)

        # Obtém a cor do rótulo em formato KML e converte para hexadecimal RGB
        cor_rotulo_kml = self.obter_cor_rotulo(layer)
        # Converter de AABBGGRR para RRGGBB para uso em HTML
        cor_rotulo_html = '#' + cor_rotulo_kml[6:] + cor_rotulo_kml[4:6] + cor_rotulo_kml[2:4]

        # Verifica se a camada já está em WGS84 (EPSG:4326)
        if layer.crs().authid() != 'EPSG:4326':
            # Define o sistema de referência de coordenadas para WGS84 (usado pelo KML)
            crsDestino = QgsCoordinateReferenceSystem(4326)  # WGS84
            transform = QgsCoordinateTransform(layer.crs(), crsDestino, QgsProject.instance())
            transformar = True
        else:
            transformar = False

        # Itera sobre cada feição na camada e cria um Placemark
        for i, feature in enumerate(layer.getFeatures(), start=1):
            placemark = ET.SubElement(document, 'Placemark')

            # Adiciona um nome ao Placemark com o valor do campo ID
            name = ET.SubElement(placemark, 'name')
            name.text = str(feature[campo_id])

            # Cria a tag Point com as coordenadas
            point = ET.SubElement(placemark, 'Point')
            coordinates = ET.SubElement(point, 'coordinates')
            geom = feature.geometry()
            # Aplica a transformação de coordenadas se necessário
            if transformar:
                geom.transform(transform)

            coord_text = f"{geom.asPoint().x()},{geom.asPoint().y()},0"  # Adicione altitude se necessário
            coordinates.text = coord_text

            # Adiciona ExtendedData com os atributos da feição
            extended_data = ET.SubElement(placemark, 'ExtendedData')
            for field in layer.fields():
                data = ET.SubElement(extended_data, 'Data', name=field.name())
                value = ET.SubElement(data, 'value')
                value.text = str(feature[field.name()])

            # Define um estilo para o Placemark
            style = ET.SubElement(placemark, 'Style')
            icon_style = ET.SubElement(style, 'IconStyle')
            label_style = ET.SubElement(style, 'LabelStyle')

            self.gerar_balloon_style(feature, campo_id, style, cor_rotulo_html, image_url, overlay_url)

            # Condições para escala do ícone e rótulo
            if icon_url:
                icon = ET.SubElement(icon_style, 'Icon')
                href = ET.SubElement(icon, 'href')
                href.text = icon_url  # Use a URL do ícone escolhido
                color = ET.SubElement(icon_style, 'color')
                color.text = cor_icone  # A cor é usada aqui
                # Escala do ícone quando não há rótulos para exportar
                if not exportar_rotulos:
                    label_scale = ET.SubElement(label_style, 'scale')
                    label_scale.text = '0'  # Esconde o rótulo

            if exportar_rotulos:
                label_scale = ET.SubElement(label_style, 'scale')
                label_scale.text = '1.0'  # Mostra o rótulo
                color = ET.SubElement(label_style, 'color')
                color.text = cor_rotulo_kml  # A cor é usada aqui
                # Escala do ícone quando não há ícone para exportar
                if not icon_url:
                    icon_scale = ET.SubElement(icon_style, 'scale')
                    icon_scale.text = '0'  # Esconde o ícone

            progressBar.setValue(i)  # Atualiza a barra de progresso

        # Adiciona ScreenOverlay apenas se overlay_url for fornecida e não for vazia
        if overlay_url:
            # Redimensiona a imagem obtida a partir do URL
            imagem_redimensionada, nova_largura, nova_altura = self.redimensionar_imagem_proporcional_url(overlay_url, 300, 150)

            if imagem_redimensionada is not None:
                # Adiciona o ScreenOverlay ao KML usando a imagem redimensionada
                screen_overlay = ET.SubElement(document, 'ScreenOverlay') # Cria o elemento ScreenOverlay no documento KML
                name = ET.SubElement(screen_overlay, 'name')  # Define o nome do ScreenOverlay
                name.text = 'logo'

                # Define o ícone do ScreenOverlay, utilizando a URL da imagem fornecida
                icon = ET.SubElement(screen_overlay, 'Icon')
                href = ET.SubElement(icon, 'href')
                href.text = overlay_url

                # Configura a posição e o tamanho do overlay na tela
                overlay_xy = ET.SubElement(screen_overlay, 'overlayXY', x="1", y="1", xunits="fraction", yunits="fraction")
                screen_xy = ET.SubElement(screen_overlay, 'screenXY', x=f"{nova_largura}", y=f"{nova_altura}", xunits="pixels", yunits="pixels")
                rotation_xy = ET.SubElement(screen_overlay, 'rotationXY', x="0", y="0", xunits="fraction", yunits="fraction")
                # Define o tamanho do ScreenOverlay
                size = ET.SubElement(screen_overlay, 'size', x=f"{nova_largura}", y=f"{nova_altura}", xunits="pixels", yunits="pixels")

        # Retorna o elemento raiz do KML
        return kml

    def gerar_balloon_style(self, feature, campo_id, style, cor_rotulo_html, image_url, overlay_url):
        """
        Gera o estilo de balão (BalloonStyle) para uma feição KML. A função realiza as seguintes etapas:

        1. Constrói uma tabela HTML com os atributos da feição.
        2. Adiciona a tabela HTML ao BalloonStyle do KML.

        Parâmetros:
        - feature (QgsFeature): A feição para a qual o BalloonStyle será gerado.
        - campo_id (str): O campo de identificação a ser usado no balão.
        - style (xml.etree.ElementTree.Element): O elemento de estilo do KML onde o BalloonStyle será adicionado.
        - cor_rotulo_html (str): A cor do rótulo em formato hexadecimal RGB para uso em HTML.
        - image_url: A URL da imagem a ser usada como ícone do placemark.
        - overlay_url: A URL da imagem a ser usada como overlay.

        Funcionalidades:
        - Construção de tabela HTML com os atributos da feição.
        - Geração de cores suaves para o fundo das células da tabela.
        - Conversão de URLs em links HTML clicáveis.
        - Adição da tabela HTML ao BalloonStyle do KML.
        - image_url: A URL da imagem a ser usada como ícone do Placemark.
        """
        # Construir a tabela HTML
        tabela_geral_html = '<table border="1" style="border-collapse: collapse; border: 2px solid black; width: 100%;">'
        for field in feature.fields():
            cor_fundo = self.gerar_cor_suave()  # Gera uma cor suave
            field_value = str(feature[field.name()])
            field_value_as_link = self.url_para_link_html(field_value)
            tabela_geral_html += f'<tr><td><table border="0" style="background-color: {cor_fundo}; width: 100%;">'
            tabela_geral_html += f'<tr><td style="text-align: left;"><b>{field.name()}</b></td>'
            tabela_geral_html += f'<td style="text-align: right;">{str(feature[field.name()])}</td></tr></table></td></tr>'
        tabela_geral_html += '</table>'

        # Redimensiona a imagem para 150x75 antes de gerar o HTML
        imagem_html = ""
        if image_url:  # Verifica se a URL da imagem foi fornecida
            imagem_redimensionada, nova_largura, nova_altura = self.redimensionar_imagem_proporcional_url(image_url, 150, 75)
            if imagem_redimensionada:
                # Gera o HTML com a nova largura e altura
                imagem_html = f'<div style="text-align: center; padding: 10px 0;"><img src="{image_url}" alt="Imagem" width="{nova_largura}" height="{nova_altura}"></div>'
            else:
                # Se não foi possível redimensionar, usar dimensões padrão ou uma mensagem de erro
                imagem_html = f'<div style="text-align: center; padding: 10px 0;"><p>Imagem não pôde ser carregada.</p></div>'

        # BalloonStyle com a imagem e a tabela de atributos diretamente
        balloon_style = ET.SubElement(style, 'BalloonStyle')
        text = ET.SubElement(balloon_style, 'text')
        balloon_html = f"""
        {imagem_html}
            <h3 style="margin-bottom:1px;">{campo_id}: {str(feature[campo_id])}</h3>
            <p>Tabela de Informações:</p>
            {tabela_geral_html}
            """
        text.text = balloon_html

    def redimensionar_imagem_proporcional_url(self, url_imagem, largura_max, altura_max):
        """
        Baixa a imagem de um URL e redimensiona proporcionalmente para caber dentro de uma caixa de largura e altura máximas.

        Parâmetros:
        - url_imagem (str): URL da imagem a ser redimensionada.
        - largura_max (int): Largura máxima da caixa.
        - altura_max (int): Altura máxima da caixa.

        Retorna:
        - Uma instância de `PIL.Image.Image` redimensionada proporcionalmente.
        - As novas dimensões da imagem (largura, altura).
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }  # Define o cabeçalho de User-Agent para a solicitação HTTP

        try:
            response = requests.get(url_imagem, headers=headers)  # Faz o download da imagem do URL com o cabeçalho definido
            response.raise_for_status()  # Verifica se o download foi bem-sucedido

            imagem = Image.open(BytesIO(response.content))  # Abre a imagem a partir do conteúdo baixado
            largura_original, altura_original = imagem.size  # Obtém as dimensões originais da imagem

            proporcao_largura = largura_max / largura_original  # Calcula a proporção para a largura
            proporcao_altura = altura_max / altura_original  # Calcula a proporção para a altura
            proporcao_final = min(proporcao_largura, proporcao_altura)  # Usa a menor proporção para manter a imagem dentro da caixa

            nova_largura = int(largura_original * proporcao_final)  # Calcula a nova largura proporcional
            nova_altura = int(altura_original * proporcao_final)  # Calcula a nova altura proporcional

            imagem_redimensionada = imagem.resize((nova_largura, nova_altura), Image.LANCZOS)  # Redimensiona a imagem

            return imagem_redimensionada, nova_largura, nova_altura  # Retorna a imagem redimensionada e as novas dimensões

        except UnidentifiedImageError:
            # Captura o erro se a imagem não puder ser identificada e exibe uma mensagem de erro
            self.mostrar_mensagem("Erro ao abrir a imagem. O arquivo não é uma imagem válida ou está corrompido.", "Erro")
            return None, None, None  # Retorna None se ocorrer um erro

        except Exception as e:
            # Captura qualquer outro erro, exibe uma mensagem de erro e continua
            self.mostrar_mensagem(f"Erro ao processar a imagem: {e}", "Erro")
            return None, None, None  # Retorna None se ocorrer um erro

    def exportar_para_dxf(self):
        """
        Exporta a camada selecionada para um arquivo DXF. A função realiza as seguintes etapas:

        1. Obtém a seleção atual no QTreeView.
        2. Verifica se alguma camada foi selecionada. Se não, exibe uma mensagem de erro.
        3. Obtém o nome da camada selecionada.
        4. Verifica se a camada selecionada está presente no projeto. Se não, exibe uma mensagem de erro.
        5. Obtém os nomes dos campos da camada.
        6. Verifica se os valores dos campos contêm caracteres inválidos.
        7. Se forem encontrados campos inválidos, notifica o usuário e encerra a função.
        8. Cria um novo documento DXF.
        9. Inicializa o diálogo de escolha de blocos e configurações.
        10. Executa o diálogo e obtém as configurações escolhidas pelo usuário.
        11. Chama a função para exportar a camada para DXF com as configurações selecionadas.

        Funcionalidades:
        - Verificação da seleção e existência da camada.
        - Verificação de caracteres inválidos nos valores dos campos.
        - Inicialização e execução de um diálogo de escolha de configurações.
        - Exportação da camada para um arquivo DXF com as configurações selecionadas.
        """
        # Obtém a seleção atual no QTreeView
        indexes = self.dlg.treeViewListaPonto.selectionModel().selectedIndexes()
        if not indexes:
            self.mostrar_mensagem("Selecione uma camada para exportar.", "Erro")
            return

        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        layer = QgsProject.instance().mapLayersByName(selected_layer_name)[0]
        if not layer:
            self.mostrar_mensagem("Camada não encontrada.", "Erro")
            return

        # Obtém os nomes dos campos da camada
        campos = [field.name() for field in layer.fields()]

        # Dicionário para armazenar campos com valores inválidos
        campos_invalidos = {}

        # Definição de quais caracteres são considerados inválidos
        caracteres_invalidos = set("/|\*?%$#@!~'")

        # Função para verificar se o valor é inválido
        def valor_invalido(valor):
            if valor is None or valor == "":  # Checa se o valor é nulo ou vazio
                return True
            if any(char in caracteres_invalidos for char in str(valor)):
                return True
            return False  # Retorna False se o valor for válido
        
        # Verificação de cada feição e cada campo relevante
        for feature in layer.getFeatures():
            for campo in campos:
                valor = feature[campo]
                if valor_invalido(valor):  # Usa a função valor_invalido para verificar
                    if campo not in campos_invalidos:
                        campos_invalidos[campo] = []
                    campos_invalidos[campo].append(feature.id())

        # Se foram encontrados campos inválidos, notifica o usuário e encerra a função
        if campos_invalidos:
            mensagem_erro = "Valores inválidos ou vazios encontrados nos seguintes campos:\n"
            for campo, ids in campos_invalidos.items():
                mensagem_erro += f"{campo} (IDs: {', '.join(map(str, ids))})\n"
            self.mostrar_mensagem(mensagem_erro, "Erro")
            return

        doc = ezdxf.new(dxfversion='R2013')  # Cria um novo documento DXF
        cores = {}  # Inicializa um dicionário de cores
        self.dialogo = BlocoEscolhaDialogo(campos, layer, self.dlg)  # A instância é criada aqui e atribuída a self.dialogo
        dialogo = BlocoEscolhaDialogo(campos, layer, self.dlg)  # Inicializa o diálogo de escolha
        # nomes_blocos = dialogo.criar_blocos(doc, cores)  # Cria blocos no documento DXF

        resultado = dialogo.exec_()  # Executa o diálogo
        if resultado == QDialog.Accepted:
            cores = dialogo.cores  # Atualiza cores com as escolhas do usuário
            nomes_blocos = self.dialogo.criar_blocos(doc, cores)  # Chama o método criar_blocos da instância self.dialogo
            campoEscolhido = dialogo.getCampoEscolhido()  # Obtém o campo escolhido no diálogo
            selecoes = dialogo.getSelecoes()  # Obtém as seleções feitas no diálogo
            camposSelecionados = dialogo.getCamposSelecionados() if hasattr(dialogo, 'camposCheckBoxes') else []  # Obter campos selecionados se existir
            campoZ = dialogo.getCampoZ()  # Obter o campo Z selecionado
            blocoSelecionado = dialogo.getBlocoSelecionado()  # Obter o bloco selecionado

            if campoEscolhido and selecoes:  # Chama a função para exportar a camada para DXF
                self.exportar_camada_para_dxf(layer, campoEscolhido, selecoes, cores, camposSelecionados, campoZ, blocoSelecionado)

    def exportar_camada_para_dxf(self, layer, campoEscolhido, selecoes, cores, camposSelecionados, campoZ, blocoSelecoes):
        """
        Exporta a camada selecionada para um arquivo DXF. A função realiza as seguintes etapas:

        1. Obtém o nome da camada e solicita ao usuário o caminho do arquivo para salvar o DXF.
        2. Cria um novo documento DXF.
        3. Cria camadas no documento DXF com as cores escolhidas.
        4. Inicia a barra de progresso.
        5. Itera sobre cada feição na camada e adiciona pontos, textos e blocos ao documento DXF.
        6. Salva o documento DXF no caminho especificado.
        7. Calcula o tempo de execução.
        8. Remove a barra de progresso e exibe uma mensagem de sucesso.
        9. Cria um índice espacial para a camada antes da exportação.

        Parâmetros:
        - layer (QgsVectorLayer): A camada de origem para a exportação.
        - campoEscolhido (str): O campo de identificação a ser usado como nome dos Placemarks.
        - selecoes (list): As seleções feitas no diálogo de escolha.
        - cores (dict): Dicionário de cores escolhidas.
        - camposSelecionados (list): Lista de campos selecionados para exportar.
        - campoZ (str): Campo Z para coordenadas 3D, se aplicável.
        - blocoSelecoes (dict): Dicionário de blocos selecionados para cada valor de atributo.

        Funcionalidades:
        - Criação de documento DXF com camadas e estilos personalizados.
        - Adição de pontos, textos e blocos ao documento DXF.
        - Atualização da barra de progresso durante o processamento.
        - Cálculo do tempo de execução e exibição de mensagem de sucesso.
        """

        # Cria um índice espacial para a camada
        spatial_index = QgsSpatialIndex()
        for feature in layer.getFeatures():
            spatial_index.insertFeature(feature)

        # Obtém o nome da camada
        nome_camada = layer.name()
        caminho_arquivo = self.escolher_local_para_salvar(f"{nome_camada}.dxf", "DXF Files (*.dxf)")
        if not caminho_arquivo:
            return  # Usuário cancelou a operação

        doc = ezdxf.new(dxfversion='R2013')
        msp = doc.modelspace()

        self.nomes_blocos = self.dialogo.criar_blocos(doc, cores)

        # Criando camadas com as cores escolhidas no documento DXF
        for valor_atributo, cor_rgb in cores.items():
            cor_int = rgb2int(cor_rgb)
            doc.layers.new(name=str(valor_atributo), dxfattribs={'true_color': cor_int})

        altura_texto = 0.5
        deslocamento_y = altura_texto * 1.2  # Ajuste o deslocamento_y para a distância vertical entre as linhas de texto
        deslocamento_x = altura_texto * (-2.7)  # O deslocamento_x é ajustado para centralizar o texto em relação ao ponto

        # Inicia a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(layer)

        start_time = time.time()

        for i, feature in enumerate(layer.getFeatures(), start=1):
            valor_atributo = feature[campoEscolhido]
            if valor_atributo in selecoes:
                geom = feature.geometry()
                if geom is not None:
                    point = geom.asPoint()
                    x, y = point.x(), point.y()
                    z = feature[campoZ] if campoZ else 0  # Usar valor Z se campoZ estiver definido

                    # Adiciona o ponto (em 3D se z estiver definido)
                    if campoZ:
                        msp.add_point((x, y, z), dxfattribs={'layer': str(valor_atributo)})
                    else:
                        msp.add_point((x, y), dxfattribs={'layer': str(valor_atributo)})

                    # Adiciona a referência ao bloco selecionado para este valor de atributo (em 2D)
                    blocoSelecionado = blocoSelecoes.get(valor_atributo)
                    if blocoSelecionado and blocoSelecionado in self.nomes_blocos:
                        msp.add_blockref(blocoSelecionado, (x, y), dxfattribs={
                            'layer': str(valor_atributo),
                            'insert': (x, y),
                            'xscale': 1.0,
                            'yscale': 1.0,
                            'zscale': 1.0,
                            'rotation': 0
                        })

                    # O texto é colocado acima do ponto inicialmente (em 2D)
                    y_offset = y + (altura_texto / 2)
                    x_offset = x - (deslocamento_x / 2)  # Ajusta o X para centralizar o texto
                    for campo in camposSelecionados:
                        texto = feature[campo]
                        msp.add_text(str(texto), dxfattribs={
                            'insert': (x_offset, y_offset),
                            'height': altura_texto,
                            'layer': str(valor_atributo)
                        })
                        y_offset -= deslocamento_y  # Move para baixo para o próximo texto

            progressBar.setValue(i)  # Atualiza a barra de progresso
        
        # Salva o documento DXF no caminho especificado
        doc.saveas(caminho_arquivo)
        end_time = time.time()

        execution_time = end_time - start_time

        # Remove a barra de progresso
        self.iface.messageBar().clearWidgets()

        # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
        self.mostrar_mensagem(
            f"Arquivo DXF salvo com sucesso em {execution_time:.2f} segundos", 
            "Sucesso", 
            caminho_pasta=os.path.dirname(caminho_arquivo), 
            caminho_arquivos=caminho_arquivo)

class TreeViewEventFilter(QObject):
    """
    Filtro de eventos personalizado para detectar movimentos do mouse sobre itens em um treeView.

    Esta classe herda de QObject e implementa um filtro de eventos que detecta quando o mouse se move
    sobre itens específicos em um treeView. Quando o mouse se move sobre um item, a classe chama um 
    método no UiManager para exibir um tooltip com informações sobre o item.

    Parâmetros:
    - ui_manager: Referência à instância do objeto UiManager, que gerencia a interface do usuário.
    """

    def __init__(self, ui_manager):
        """
        Inicializa o filtro de eventos com uma referência ao UiManager.

        Parâmetros:
        - ui_manager: Instância do UiManager que será usada para acessar e manipular a interface do usuário.
        """
        super().__init__()  # Inicializa a classe base QObject
        self.ui_manager = ui_manager  # Armazena a referência ao UiManagerT para uso posterior

    def eventFilter(self, obj, event):
        """
        Filtra os eventos de movimentação do mouse sobre o treeView e exibe tooltips quando aplicável.

        Esta função intercepta eventos que ocorrem no treeView especificado. Se o evento for de movimento
        do mouse (QEvent.MouseMove) e o mouse estiver sobre um item válido no treeView, a função chama
        o método 'configurar_tooltip' do UiManager para exibir um tooltip com informações sobre o item.

        Parâmetros:
        - obj: O objeto que está sendo monitorado (neste caso, o viewport do treeView).
        - event: O evento que está sendo filtrado (como QEvent.MouseMove).

        Retorno:
        - bool: O resultado da chamada à função 'eventFilter' da classe base, indicando se o evento foi processado.
        """
        # Verifica se o objeto é o viewport do treeView e se o evento é de movimento do mouse
        if obj == self.ui_manager.dlg.treeViewListaPonto.viewport() and event.type() == QEvent.MouseMove:
            # Obtém o índice do item no treeView sob o cursor do mouse
            index = self.ui_manager.dlg.treeViewListaPonto.indexAt(event.pos())
            if index.isValid():  # Verifica se o índice é válido (se o mouse está sobre um item)
                self.ui_manager.configurar_tooltip(index)  # Chama o método para configurar e exibir o tooltip
        # Retorna o resultado padrão do filtro de eventos
        return super().eventFilter(obj, event)  # Chama a implementação da classe base para continuar o processamento normal

class BlocoEscolhaDialogo(QDialog):
    """
    Diálogo para escolher campos e valores para exportação de pontos. Este diálogo permite ao usuário selecionar campos,
    definir cores, e escolher blocos para exportação em um formato específico.

    Parâmetros:
    - campos (list): Lista de nomes de campos disponíveis na camada.
    - layer (QgsVectorLayer): A camada de origem.
    - nomes_blocos (list): Lista de nomes de blocos disponíveis.
    - parent (QWidget): Widget pai do diálogo (opcional).

    Funcionalidades:
    - Seleção de campos de texto para exportação.
    - Definição de cores aleatórias para os valores selecionados.
    - Seleção de blocos específicos para cada valor.
    - Verificação de condições para habilitar/desabilitar o botão de exportação.
    """
    def __init__(self, campos, layer, parent=None):
        """
        Inicializa uma instância do diálogo BlocoEscolhaDialogo.
        
        Funções principais:
        - Configura a interface do usuário do diálogo.
        - Inicializa variáveis e estruturas de dados para armazenar informações sobre os campos e cores selecionados.
        - Configura e organiza os layouts e widgets do diálogo.

        Etapas detalhadas:
        1. Inicializa a superclasse QDialog.
        2. Armazena os parâmetros `campos` e `layer`.
        3. Cria um dicionário para armazenar as cores selecionadas.
        4. Inicializa um dicionário para armazenar checkboxes dos campos.
        5. Chama o método `criar_blocos` para inicializar os blocos.
        6. Inicializa um dicionário para armazenar o estado dos campos, todos desmarcados.
        7. Inicializa o QButtonGroup para botões de rádio.
        8. Configura o título, tamanho mínimo e máximo do diálogo.
        9. Configura o layout principal do diálogo.
        10. Configura e organiza widgets e layouts adicionais dentro do diálogo.
        11. Configura a lista de widgets para exibir valores de campos.
        12. Adiciona botões de controle (OK e Cancelar) ao diálogo.
        13. Inicializa o QListWidget com os valores do campo string.
        14. Embaralha uma lista de cores vibrantes.
        15. Verifica as condições para habilitar/desabilitar o botão Executar.
        16. Conecta sinais de checkboxes às funções de atualização de estado.

        Parâmetros:
        - campos (list): Lista de nomes dos campos.
        - layer (QgsVectorLayer): Camada de vetor do QGIS.
        - parent (QWidget): Widget pai opcional.
        """
        super().__init__(parent)
        self.campos = campos # Armazena os campo
        self.layer = layer # Armazena a camada
        self.cores = {}  # Dicionário para armazenar as cores selecionadas
        self.camposCheckBoxes = {} # Dicionário para armazenar checkboxes dos campos
        # Inicialização dos blocos  # Adicionando a lista de nomes de blocos
        self.nomes_blocos = self.criar_blocos(ezdxf.new(dxfversion='R2013'), {})
        self.estadoCampos = {campo: False for campo in campos}  # Inicializa todos os campos como desmarcados
        
        # Inicialize radioGroup no construtor
        self.radioGroup = QButtonGroup(self)        

        self.setWindowTitle('Escolha o Campo e o Valor para os Pontos') # Define o título da janela
        self.setMinimumSize(325, 400)  # Define o tamanho mínimo do diálogo
        self.setMaximumSize(325, 600)  # Define o tamanho máximo do diálogo

        layout = QVBoxLayout(self) # Layout principal vertical

        self.frame = QFrame(self) # Cria um frame
        self.frame.setFrameShape(QFrame.StyledPanel) # Define o formato do frame
        self.frame.setLineWidth(int(0.6)) # Define a largura da linha do frame
        frameLayout = QVBoxLayout(self.frame) # Layout vertical para o frame

        self.comboBoxLayout = QHBoxLayout() # Layout horizontal para o comboBox
        self.label = QLabel('Selecione o campo:') # Label para o comboBox
        self.comboBoxLayout.addWidget(self.label) # Adiciona o label ao layout

        self.comboBox = QComboBox(self.frame) # Cria o comboBox
        # Adicionar apenas campos do tipo string ao comboBox
        for campo in self.campos:
            field = self.layer.fields().field(campo)  # Obtém o campo
            # Verifica se o campo é do tipo string
            if field.type() in (QVariant.String, QVariant.StringList): 
                self.comboBox.addItem(campo)
        self.comboBox.setStyleSheet("""
        QComboBox { combobox-popup: 0; }
        QComboBox QAbstractItemView {
            min-height: 80px; /* 10 itens */
            max-height: 80px; /* 10 itens */
            min-width: 100px; /* Ajuste conforme necessário */
        }
        """) # Define o estilo do comboBox

        # Conecta o sinal de mudança de índice à função atualizarListWidget
        self.comboBox.currentIndexChanged.connect(self.atualizarListWidget)
        self.comboBoxLayout.addWidget(self.comboBox) # Adiciona o comboBox ao layout
        frameLayout.addLayout(self.comboBoxLayout) # Adiciona o layout do comboBox ao layout do frame

        # Layout horizontal para o checkbox e o botão de cores aleatórias
        topLayout = QHBoxLayout() # Layout horizontal para o topo
        frameLayout.addLayout(topLayout) # Adiciona o layout ao frame

        # Adiciona QCheckBox para selecionar todos
        self.selectAllCheckBox = QCheckBox("Selecionar Camadas") # Cria o checkbox para selecionar todos
        self.selectAllCheckBox.setChecked(False) # Define o estado inicial como desmarcado
        # Conecta o sinal de mudança de estado à função selecionarTodos
        self.selectAllCheckBox.stateChanged.connect(self.selecionarTodos)
        topLayout.addWidget(self.selectAllCheckBox) # Adiciona o checkbox ao layout

        # Layout horizontal para os botões "Rótulos" e "3D"
        buttonsLayout = QHBoxLayout() # Layout horizontal para os botões
        frameLayout.addLayout(buttonsLayout) # Adiciona o layout ao frame

        # Adiciona botão para abrir a lista de campos numéricos para 3D
        self.btn3D = QPushButton("Altimetria") # Cria o botão "Altimetria"
        # Conecta o sinal de clique à função mostrarCamposNumericos
        self.btn3D.clicked.connect(self.mostrarCamposNumericos)
        buttonsLayout.addWidget(self.btn3D) # Adiciona o botão ao layout

        # Botão "Rótulos"
        self.camposButton = QPushButton("Rótulos")
        # Conecta o sinal de clique à função mostrarCampos
        self.camposButton.clicked.connect(self.mostrarCampos) 
        buttonsLayout.addWidget(self.camposButton) # Adiciona o botão ao layout

        # Adiciona botão para definir cores aleatórias
        self.randomColorButton = QPushButton("Cores Aleatórias")
        # Conecta o sinal de clique à função definirCoresAleatorias
        self.randomColorButton.clicked.connect(self.definirCoresAleatorias)
        topLayout.addWidget(self.randomColorButton) # Adiciona o botão ao layout

        # Layout para o QLineEdit e o novo botão
        lineEditLayout = QHBoxLayout() # Layout horizontal para o QLineEdit
        self.lineEdit = QLineEdit(self.frame) # Cria o QLineEdit
        self.lineEdit.setReadOnly(True)  # Torna o QLineEdit somente leitura
        self.lineEdit.setPlaceholderText("Feições: Selecione!") # Define o texto de espaço reservado
        self.lineEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed) # Define a política de tamanho
        lineEditLayout.addWidget(self.lineEdit) # Adiciona o QLineEdit ao layout

        # Criação do botão "Bloco Aleatório"
        self.blocoAleatorioButton = QPushButton("Bloco Aleatório")
        # Conecta o sinal de clique à função definirBlocoAleatorio
        self.blocoAleatorioButton.clicked.connect(self.definirBlocoAleatorio)
        lineEditLayout.addWidget(self.blocoAleatorioButton) # Adiciona o botão ao layout

        # Adicionando o layout do QLineEdit e botão ao layout principal
        frameLayout.addLayout(lineEditLayout)

        self.listWidget = QListWidget(self.frame) # Cria o QListWidget
        self.listWidget.setMinimumSize(200, 220) # Define o tamanho mínimo do QListWidget
        # Conecta o sinal de mudança de seleção à função atualizarLineEdit
        self.listWidget.itemSelectionChanged.connect(self.atualizarLineEdit)
        frameLayout.addWidget(self.listWidget)  # Adiciona o QListWidget ao frame

        # Adiciona os botões OK e Cancelar
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setText("Exportar")  # Altera o texto do botão OK para Exportar
        self.buttonBox.accepted.connect(self.accept)  # Se Exportar for clicado, aceita o diálogo
        self.buttonBox.rejected.connect(self.reject)  # Se Cancelar for clicado, rejeita o diálogo

        # Centraliza o buttonBox no layout
        frameLayout.addWidget(self.buttonBox, 0, Qt.AlignCenter)  # Adiciona o buttonBox ao layout com alinhamento centralizado

        layout.addWidget(self.frame) # Adiciona o frame ao layout principal

        # Isto carregará os valores do campo string no QListWidget
        self.atualizarListWidget(0)

        # Embaralha uma lista de cores vibrantes
        self.cores_vibrantes_embaralhadas = self.embaralhar_cores_vibrantes()

        self.verificarCondicoesParaExecutar()  # Chama a função verificarCondicoesParaExecutar

        # Conecta o sinal de mudança de estado à função atualizarEstadoBotaoExportar
        self.selectAllCheckBox.stateChanged.connect(self.atualizarEstadoBotaoExportar)
        # Conecta o sinal de mudança de estado à função verificarCondicoesParaExecutar
        self.selectAllCheckBox.stateChanged.connect(self.verificarCondicoesParaExecutar)

    def definirBlocoAleatorio(self):
        """
        Define um bloco aleatório para cada item no QListWidget. A função realiza as seguintes etapas:

        1. Cria uma cópia da lista de blocos disponíveis.
        2. Inicializa uma lista para armazenar os blocos já utilizados.
        3. Percorre cada item do QListWidget:
           - Obtém o texto do QLabel e o QComboBox associados ao item.
           - Verifica se o texto do label corresponde a algum nome de bloco.
           - Se houver correspondência, seleciona o bloco correspondente e o remove da lista de blocos disponíveis.
           - Se não houver correspondência, escolhe um bloco aleatório dos disponíveis.
           - Atualiza as listas de controle de blocos disponíveis e utilizados.

        Funcionalidades:
        - Seleção automática de blocos para itens em uma lista.
        - Evita a repetição de blocos até que todos tenham sido utilizados.
        """
        blocos_disponiveis = self.nomes_blocos.copy()  # Cria uma cópia da lista de blocos disponíveis
        blocos_utilizados = []  # Lista para armazenar os blocos já utilizados

        # Percorre cada item do QListWidget
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            label = widget.findChild(QLabel).text()  # Obtém o texto do QLabel
            combo = widget.findChild(QComboBox)
            
            # Verifica se o nome no label corresponde a algum nome de bloco
            bloco_correspondente = next((bloco for bloco in self.nomes_blocos if bloco.lower() == label.lower()), None)

            if bloco_correspondente:
                # Se houver correspondência, seleciona o bloco correspondente
                combo.setCurrentText(bloco_correspondente)
                # Remove o bloco correspondente da lista de disponíveis, se necessário
                if bloco_correspondente in blocos_disponiveis:
                    blocos_disponiveis.remove(bloco_correspondente)
                    blocos_utilizados.append(bloco_correspondente)
            else:
                # Se não houver blocos disponíveis, reinicia a lista
                if not blocos_disponiveis:
                    blocos_disponiveis = blocos_utilizados.copy()
                    blocos_utilizados.clear()

                # Escolhe um bloco aleatoriamente dos disponíveis
                bloco_aleatorio = random.choice(blocos_disponiveis)
                combo.setCurrentText(bloco_aleatorio)
                # Atualiza as listas de controle
                blocos_disponiveis.remove(bloco_aleatorio)
                blocos_utilizados.append(bloco_aleatorio)

    def atualizarEstadoBotaoExportar(self):
        """
        Atualiza o estado do botão Exportar com base no estado do checkbox Selecionar Camadas.
        A função realiza as seguintes etapas:

        1. Verifica o estado do checkbox Selecionar Camadas.
        2. Habilita ou desabilita o botão Exportar de acordo com o estado do checkbox.

        Funcionalidades:
        - Habilitação e desabilitação dinâmica do botão Exportar.
        """
        # Atualiza o estado do botão Exportar com base no checkbox Selecionar Camadas
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(self.selectAllCheckBox.isChecked())

    def verificarCondicoesParaExecutar(self):
        """
        Verifica se todas as condições necessárias para habilitar o botão Executar são satisfeitas.
        A função realiza as seguintes etapas:

        1. Verifica se a camada possui feições.
        2. Verifica se a camada possui campos.
        3. Verifica se o checkbox "Selecionar Camadas" está marcado.
        4. Habilita o botão Executar somente se todas as condições forem verdadeiras.

        Funcionalidades:
        - Verificação da presença de feições na camada.
        - Verificação da presença de campos na camada.
        - Verificação do estado do checkbox "Selecionar Camadas".
        - Habilitação do botão Executar apenas quando todas as condições são atendidas.
        """
        # Verifica se a camada possui feições
        tem_feicoes = self.layer.featureCount() > 0

        # Verifica se a camada possui campos
        tem_campos = len(self.campos) > 0

        # Verifica se o checkBox "Selecionar Camadas" está marcado
        selecao_ativa = self.selectAllCheckBox.isChecked()

        # Habilita o botão Executar somente se todas as condições forem verdadeiras
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(tem_feicoes and tem_campos and selecao_ativa)

    def mostrarCamposNumericos(self):
        """
        Exibe um diálogo para selecionar campos numéricos para altimetria. A função realiza as seguintes etapas:

        1. Cria e configura o diálogo.
        2. Adiciona botões de rádio para campos numéricos da camada.
        3. Configura a área de rolagem para acomodar muitos campos.
        4. Adiciona botões OK e Cancelar ao diálogo.
        5. Atualiza o texto do botão "3D" com base na seleção de campos numéricos.
        6. Exibe o diálogo.

        Funcionalidades:
        - Seleção de campos numéricos para altimetria.
        - Atualização dinâmica do texto do botão "3D".
        """

        # Cria o diálogo para seleção de campos numéricos
        self.campos3DDialog = QDialog(self)
        self.campos3DDialog.setWindowTitle("Campos para Altimetria")
        self.campos3DDialog.resize(150, 150)  # Define o tamanho do diálogo
        
        dialogLayout = QVBoxLayout(self.campos3DDialog)  # Layout vertical para o diálogo

        campos3DWidget = QWidget()  # Cria um widget para conter os campos numéricos
        campos3DLayout = QVBoxLayout(campos3DWidget)  # Layout vertical para os campos numéricos

        # Adiciona botões de rádio para cada campo numérico na camada
        for campo in self.campos:
            if self.layer.fields().field(campo).isNumeric():  # Verifica se o campo é numérico
                radioButton = QRadioButton(campo)  # Cria um botão de rádio para o campo
                self.radioGroup.addButton(radioButton)  # Adiciona o botão de rádio ao grupo de botões
                campos3DLayout.addWidget(radioButton)  # Adiciona o botão de rádio ao layout de campos numéricos
                # Conecta o sinal toggled de cada radioButton ao método de atualização
                radioButton.toggled.connect(self.atualizarTextoBotao3D)  # Conecta o sinal toggled ao método de atualização do texto do botão 3D

        scrollArea = QScrollArea(self.campos3DDialog)  # Cria uma área de rolagem para o diálogo
        scrollArea.setWidgetResizable(True)  # Define a área de rolagem como redimensionável
        scrollArea.setWidget(campos3DWidget)  # Define o widget de campos numéricos como o widget da área de rolagem
        dialogLayout.addWidget(scrollArea)  # Adiciona a área de rolagem ao layout do diálogo

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self.campos3DDialog)  # Cria botões OK e Cancelar para o diálogo
        buttonBox.accepted.connect(self.campos3DDialog.accept)  # Conecta o botão OK ao método de aceitação do diálogo
        buttonBox.rejected.connect(self.campos3DDialog.reject)  # Conecta o botão Cancelar ao método de rejeição do diálogo
        dialogLayout.addWidget(buttonBox)  # Adiciona o buttonBox ao layout do diálogo

        # Atualiza o texto do botão "3D" ao exibir o diálogo
        self.atualizarTextoBotao3D()  # Atualiza o texto do botão 3D com base na seleção atual de campos numéricos

        self.campos3DDialog.exec_()  # Exibe o diálogo

    def atualizarTextoBotao3D(self):
        """
        Atualiza o texto e o estilo do botão "Altimetria" com base na seleção de campos numéricos.
        A função realiza as seguintes etapas:

        1. Verifica se algum botão de rádio no grupo está selecionado.
        2. Se algum botão estiver selecionado, altera o texto do botão para "Altimetria ✓" e muda a cor para verde.
        3. Se nenhum botão estiver selecionado, retorna o texto e o estilo do botão ao padrão.

        Funcionalidades:
        - Atualização dinâmica do texto e estilo do botão "Altimetria" com base na seleção de campos numéricos.
        """

        # Verifica se algum botão está selecionado e atualiza o texto do botão "3D"
        if any(button.isChecked() for button in self.radioGroup.buttons()):
            self.btn3D.setText("Altimetria ✓")  # Altera o texto do botão para indicar seleção
            self.btn3D.setStyleSheet("color: blue;")  # Muda a cor do texto do botão para verde
        else:
            self.btn3D.setText("Altimetria")  # Retorna o texto do botão ao padrão
            self.btn3D.setStyleSheet("")  # Retorna o estilo do botão ao padrão

    def atualizarEstadoCampos(self, campo, checked):
        """
        Atualiza o estado de seleção de um campo específico.

        Parâmetros:
        - campo (str): O nome do campo cujo estado está sendo atualizado.
        - checked (bool): O novo estado do campo (True se selecionado, False se desmarcado).

        Funcionalidades:
        - Atualiza o dicionário self.estadoCampos com o novo estado do campo.
        """

        # Atualiza o estado de seleção do campo específico
        self.estadoCampos[campo] = checked

    def mostrarCampos(self):
        """
        Exibe um diálogo para selecionar campos da tabela de atributos. A função realiza as seguintes etapas:

        1. Cria e configura o diálogo.
        2. Adiciona checkboxes para cada campo da camada, restaurando o estado anterior de seleção.
        3. Configura a área de rolagem para acomodar muitos campos.
        4. Adiciona botões OK e Cancelar ao diálogo.
        5. Exibe o diálogo.

        Funcionalidades:
        - Seleção de campos para exportação.
        - Atualização do estado dos checkboxes com base na seleção anterior.
        - Verificação dinâmica da seleção de checkboxes.
        """

        # Cria o diálogo para seleção de campos
        self.camposDialog = QDialog(self)
        self.camposDialog.setWindowTitle("Campos da Tabela de Atributos")  # Define o título do diálogo
        self.camposDialog.resize(150, 150)  # Define o tamanho do diálogo
        
        dialogLayout = QVBoxLayout(self.camposDialog)  # Layout vertical para o diálogo

        camposWidget = QWidget()  # Cria um widget para conter os checkboxes
        camposLayout = QVBoxLayout(camposWidget)  # Layout vertical para os checkboxes

        self.camposCheckBoxes = {}  # Dicionário para armazenar os checkboxes
        for campo in self.campos:
            checkBox = QCheckBox(campo)  # Cria um checkbox para cada campo
            checkBox.setChecked(self.estadoCampos[campo])  # Restaura o estado anterior de seleção
            checkBox.stateChanged.connect(lambda checked, c=campo: self.atualizarEstadoCampos(c, checked))  # Conecta o estado do checkbox ao método de atualização de estado
            checkBox.stateChanged.connect(self.verificarSelecao)  # Conecta o estado do checkbox ao método de verificação de seleção
            self.camposCheckBoxes[campo] = checkBox  # Armazena o checkbox no dicionário
            camposLayout.addWidget(checkBox)  # Adiciona o checkbox ao layout de campos

        scrollArea = QScrollArea(self.camposDialog)  # Cria uma área de rolagem para o diálogo
        scrollArea.setWidgetResizable(True)  # Define a área de rolagem como redimensionável
        scrollArea.setWidget(camposWidget)  # Define o widget de campos como o widget da área de rolagem
        dialogLayout.addWidget(scrollArea)  # Adiciona a área de rolagem ao layout do diálogo

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self.camposDialog)  # Cria botões OK e Cancelar para o diálogo
        buttonBox.accepted.connect(self.camposDialog.accept)  # Conecta o botão OK ao método de aceitação do diálogo
        buttonBox.rejected.connect(self.camposDialog.reject)  # Conecta o botão Cancelar ao método de rejeição do diálogo
        dialogLayout.addWidget(buttonBox)  # Adiciona o buttonBox ao layout do diálogo

        self.camposDialog.exec_()  # Exibe o diálogo

    def verificarSelecao(self):
        """
        Verifica a seleção dos checkboxes representando os campos de atributos na interface gráfica.
        A função realiza as seguintes etapas:

        1. Calcula a quantidade de checkboxes selecionados.
        2. Atualiza o texto e a cor do botão 'Rótulos' com base na quantidade de seleções.
        3. Desabilita checkboxes não selecionados se três ou mais campos estiverem selecionados.
        4. Habilita todos os checkboxes se menos de três campos estiverem selecionados.

        Funcionalidades:
        - Verificação dinâmica da seleção de checkboxes.
        - Atualização visual do botão 'Rótulos' com base na seleção.
        - Gerenciamento do estado (habilitado/desabilitado) dos checkboxes com base na quantidade de seleções.
        """
        # Calcula a quantidade de checkboxes selecionados
        selecionados = sum(checkBox.isChecked() for checkBox in self.camposCheckBoxes.values())
        # Atualiza o texto e a cor do botão 'Rótulos' com base na quantidade de seleções
        if selecionados > 0:
            self.camposButton.setText("Rótulos ✓") # Adiciona um checkmark se houver seleção
            self.camposButton.setStyleSheet("QPushButton { color: green; }") # Muda a cor para verde
        else:
            self.camposButton.setText("Rótulos")  # Texto padrão sem seleção
            self.camposButton.setStyleSheet("")  # Retorna ao estilo padrão

        # Se três ou mais campos estão selecionados, desabilita os checkboxes não selecionados
        if selecionados >= 3:
            for checkBox in self.camposCheckBoxes.values():
                if not checkBox.isChecked():
                    checkBox.setDisabled(True) # Desabilita checkboxes não selecionados
        else:
            # Se menos de três campos estão selecionados, habilita todos os checkboxes
            for checkBox in self.camposCheckBoxes.values():
                checkBox.setEnabled(True) # Habilita todos os checkboxes
    @staticmethod
    def embaralhar_cores_vibrantes():
        """
        Embaralha uma lista de cores vibrantes. A função realiza as seguintes etapas:

        1. Define uma lista de cores vibrantes usando objetos QColor.
        2. Embaralha aleatoriamente a lista de cores.
        3. Retorna a lista embaralhada de cores.

        Funcionalidades:
        - Criação de uma lista de cores vibrantes predefinidas.
        - Embaralhamento aleatório da lista de cores.
        - Retorno da lista de cores embaralhadas.

        Retorna:
        - list: Lista de cores vibrantes embaralhadas.
        """

        cores_vibrantes = [
            QColor(255, 0, 0),  # Vermelho
            QColor(0, 255, 0),  # Verde
            QColor(0, 0, 255),  # Azul
            QColor(255, 255, 0),  # Amarelo
            QColor(0, 255, 255),  # Ciano
            QColor(255, 0, 255),  # Magenta
            QColor(255, 165, 0),  # Laranja
            QColor(128, 0, 128),  # Roxo
            # Adicione mais cores conforme necessário
        ]
        random.shuffle(cores_vibrantes)  # Embaralha a lista de cores
        return cores_vibrantes  # Retorna a lista embaralhada

    def definirCoresAleatorias(self):
        # Embaralha uma lista de cores vibrantes
        cores_vibrantes = self.embaralhar_cores_vibrantes()
        cores_iter = iter(cores_vibrantes)  # Cria um iterador para a lista de cores

        # Percorre cada item no QListWidget
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            
            # Encontrando o botão e o label no widget
            button = widget.findChildren(QPushButton)[0]
            label = widget.findChildren(QLabel)[0]
            
            try:
                cor_aleatoria = next(cores_iter)  # Obtém a próxima cor do iterador
            except StopIteration:
                # Se chegar ao final da lista de cores, comece novamente
                cores_iter = iter(cores_vibrantes)
                cor_aleatoria = next(cores_iter)

            # Definindo a cor do botão e do texto do label
            button.setStyleSheet(f"QPushButton {{ background-color: {cor_aleatoria.name()}; }}")
            label.setStyleSheet(f"QLabel {{ color: {cor_aleatoria.name()}; font-weight: bold; font-style: italic; background-color: white; border: 1px solid gray; }}")

            valor = button.property('valor_atributo')  # Obtém o valor do atributo associado ao botão
            self.cores[valor] = (cor_aleatoria.red(), cor_aleatoria.green(), cor_aleatoria.blue())  # Armazena a cor selecionada

            # Atualiza o bloco gráfico com a nova cor
            combo = widget.findChildren(QComboBox)[0]  # Encontra o QComboBox no widget do item
            self.atualizarBlocoGrafico(widget, combo, button)

    def selecionarTodos(self, state):
        """
        Seleciona ou desmarca todos os checkboxes no QListWidget com base no estado do checkbox "Selecionar Todos".
        A função realiza as seguintes etapas:

        1. Itera sobre todos os itens no QListWidget.
        2. Para cada item, obtém o widget associado e encontra o QCheckBox.
        3. Define o estado do QCheckBox com base no estado do checkbox "Selecionar Todos".
        4. Atualiza o estado do botão Exportar.

        Funcionalidades:
        - Seleção ou desmarcação de todos os checkboxes no QListWidget.
        - Atualização do estado do botão Exportar com base na seleção.

        Parâmetros:
        - state (Qt.CheckState): O estado do checkbox "Selecionar Todos" (Qt.Checked ou Qt.Unchecked).
        """

        # Itera sobre todos os itens no QListWidget
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            checkbox = widget.findChild(QCheckBox)  # Encontra o QCheckBox no widget do item
            checkbox.setChecked(state == Qt.Checked)  # Define o estado do QCheckBox com base no estado do checkbox "Selecionar Todos"
        
        # Chama a função para atualizar o estado do botão Exportar sempre que selecionar todos é alterado
        self.atualizarEstadoBotaoExportar()

    def selecionarCor(self, button, label):
        """
        Abre um diálogo de seleção de cor e aplica a cor escolhida ao botão e ao label.
        A função realiza as seguintes etapas:

        1. Abre um diálogo de seleção de cor.
        2. Verifica se uma cor válida foi selecionada.
        3. Se uma cor válida foi selecionada:
           - Define a cor de fundo do botão com a cor selecionada.
           - Define a cor do texto e o estilo do label com a cor selecionada.
           - Armazena a cor selecionada em um dicionário de cores.
           - Atualiza a cor do bloco gráfico correspondente.

        Funcionalidades:
        - Seleção de cor pelo usuário.
        - Aplicação da cor selecionada a um botão e um label.
        - Armazenamento da cor selecionada para referência futura.
        - Atualização da cor do bloco gráfico.

        Parâmetros:
        - button (QPushButton): O botão cuja cor de fundo será alterada.
        - label (QLabel): O label cujo texto e estilo serão alterados.
        """

        color = QColorDialog.getColor()  # Abre o diálogo de seleção de cor
        if color.isValid():  # Verifica se uma cor foi selecionada
            button.setStyleSheet(f"QPushButton {{ background-color: {color.name()}; }}")  # Define a cor de fundo do botão
            label.setStyleSheet(f"QLabel {{ color: {color.name()}; font-weight: bold; font-style: italic; background-color: white; border: 1px solid gray; }}")  # Define a cor do texto e o estilo do label
            valor = button.property('valor_atributo')  # Obtém o valor do atributo associado ao botão
            # Armazena a cor como uma tupla RGB
            self.cores[valor] = (color.red(), color.green(), color.blue())  # Armazena a cor selecionada

            # Atualiza a cor do bloco gráfico
            item_widget = button.parentWidget()
            combo = item_widget.findChild(QComboBox)
            self.atualizarBlocoGrafico(item_widget, combo, button)

    def atualizarLineEdit(self):
        """
        Atualiza o texto do QLineEdit com a contagem total de feições do item selecionado no QListWidget.
        A função realiza as seguintes etapas:

        1. Obtém os itens selecionados no QListWidget.
        2. Se houver itens selecionados:
           - Recupera o texto do primeiro item selecionado.
           - Obtém a contagem de feições para o valor selecionado.
           - Atualiza o texto do QLineEdit com a contagem total de feições.
        3. Se não houver itens selecionados, limpa o texto do QLineEdit.

        Funcionalidades:
        - Atualização dinâmica do QLineEdit com informações sobre o item selecionado.
        - Limpeza do QLineEdit quando nenhum item está selecionado.
        """

        selectedItems = self.listWidget.selectedItems()  # Obtém os itens selecionados no QListWidget
        if selectedItems:
            valor = selectedItems[0].text()  # Recupera o texto do primeiro item selecionado
            contagem = self.valorContagem.get(valor, 0)  # Obtém a contagem para esse valor
            self.lineEdit.setText(f"Total de Feições: {contagem}")  # Atualiza o QLineEdit com a contagem total de feições
        else:
            self.lineEdit.clear()  # Limpa o texto do QLineEdit

    def verificarCheckBoxes(self):
        """
        Verifica o estado dos checkboxes e atualiza o estado do checkbox "Selecionar Todos" e do botão Exportar.
        A função realiza as seguintes etapas:

        1. Verifica se todos os checkboxes estão selecionados.
        2. Verifica se algum checkbox está selecionado.
        3. Atualiza o estado do checkbox "Selecionar Todos" com base nas seleções dos checkboxes.
        4. Habilita o botão Exportar apenas se algum item estiver selecionado.

        Funcionalidades:
        - Verificação dinâmica da seleção de todos os checkboxes.
        - Atualização do estado do checkbox "Selecionar Todos".
        - Habilitação do botão Exportar com base na seleção dos checkboxes.
        """

        # Verifica se todos os checkboxes estão selecionados
        todos_selecionados = all(
            checkbox.isChecked() for i in range(self.listWidget.count())
            for checkbox in [self.listWidget.itemWidget(self.listWidget.item(i)).findChild(QCheckBox)]
        )

        # Verifica se algum checkbox está selecionado
        algum_selecionado = any(
            checkbox.isChecked() for i in range(self.listWidget.count())
            for checkbox in [self.listWidget.itemWidget(self.listWidget.item(i)).findChild(QCheckBox)]
        )

        self.selectAllCheckBox.blockSignals(True)  # Bloqueia sinais para evitar loops de sinal
        self.selectAllCheckBox.setChecked(todos_selecionados or algum_selecionado)  # Atualiza o estado do checkbox "Selecionar Todos"
        self.selectAllCheckBox.setTristate(algum_selecionado and not todos_selecionados)  # Define o estado tri-state
        self.selectAllCheckBox.blockSignals(False)  # Desbloqueia sinais

        # Habilita o botão Exportar apenas se algum item estiver selecionado
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(algum_selecionado)

    def atualizarListWidget(self, index):
        """
        Atualiza o QListWidget com os valores únicos do campo selecionado no comboBox.
        
        Funções principais:
        - Obtém os valores únicos do campo selecionado na camada.
        - Conta as ocorrências de cada valor.
        - Atualiza o QListWidget com os valores únicos.
        - Configura widgets adicionais (QLabel, QCheckBox, QPushButton, QComboBox, QGraphicsView) para cada item.
        - Conecta sinais para interações dos widgets.
        - Desenha o bloco inicial e configura a atualização dos gráficos.

        Etapas detalhadas:
        1. Obtém o nome do campo selecionado no comboBox.
        2. Verifica se o campo selecionado é válido.
        3. Itera sobre as feições da camada para obter os valores únicos e suas contagens.
        4. Limpa o QListWidget.
        5. Adiciona cada valor único ao QListWidget.
        6. Cria e configura widgets adicionais para cada item.
        7. Desenha o bloco inicial e configura a atualização dos gráficos.
        8. Conecta sinais de checkboxes à função de verificação de checkboxes.

        Parâmetros:
        - index (int): Índice do campo selecionado no comboBox.
        """
        # Obtém o nome do campo selecionado no comboBox
        campoSelecionado = self.comboBox.itemText(index)
        if not campoSelecionado:  # Verifica se campoSelecionado é uma string vazia
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)  # Desativa o botão Executar
            return  # Encerra a função para evitar mais execuções

        valoresUnicos = set()  # Conjunto para armazenar valores únicos
        self.valorContagem = {}  # Dicionário para contar as ocorrências de cada valor

        # Itera sobre as feições da camada para obter os valores únicos e suas contagens
        for feature in self.layer.getFeatures():
            valor = feature[campoSelecionado]
            valoresUnicos.add(str(valor))
            self.valorContagem[str(valor)] = self.valorContagem.get(str(valor), 0) + 1

        self.listWidget.clear() # Limpa o QListWidget

        # Adiciona cada valor único ao QListWidget
        for valor in sorted(valoresUnicos):
            item = QListWidgetItem(valor)
            item.setForeground(QBrush(QColor(255, 255, 255))) # Define a cor do texto do item
            self.listWidget.addItem(item)

            item_widget = QWidget()  # Cria um widget para conter o layout do item
            item_layout = QHBoxLayout(item_widget)  # Layout horizontal para o item
            item_layout.setSpacing(5)  # Define o espaçamento entre os widgets do layout
            item_layout.setContentsMargins(2, 1, 2, 1)  # Define as margens do layout

            # Primeiro, o QLabel com o texto
            label = QLabel(valor)
            label.setStyleSheet("font-weight: bold; font-style: italic; background-color: white; border: 1px solid gray;")
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            item_layout.addWidget(label)

            # O checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(self.selectAllCheckBox.isChecked())
            checkbox.stateChanged.connect(self.verificarCheckBoxes)  # Conecta o sinal stateChanged à função
            item_layout.addWidget(checkbox)

            # O botão de cor
            button = QPushButton('Cor')
            button.setFixedSize(50, 20)
            button.clicked.connect(lambda checked, b=button, l=label: self.selecionarCor(b, l))
            item_layout.addWidget(button)

            # O combobox
            combo = QComboBox()
            combo.setMaxVisibleItems(5)  # Define o número máximo de itens visíveis
            combo.setStyleSheet("""
            QComboBox { 
                combobox-popup: 0; 
            }
            QComboBox QAbstractItemView {
                min-height: 140px; /* 10 itens */
                max-height: 140px; /* 10 itens */
                min-width: 100px; /* ajuste conforme necessário */
                max-width: 100px; /* ajuste conforme necessário */
            }
            """) # Define o estilo do comboBox

            for nome_bloco in self.nomes_blocos:
                combo.addItem(nome_bloco)  # Adiciona os nomes dos blocos ao QComboBox
            combo.setFixedSize(80, 20)  # Define o tamanho fixo do QComboBox
            item_layout.addWidget(combo)  # Adiciona o QComboBox ao layout do item

            # Adicionando QGraphicsView
            graphics_view = QGraphicsView()
            # Habilita o antialiasing e suavização de transformações
            graphics_view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            graphics_view.setFixedSize(20, 20) # Define o tamanho fixo do QGraphicsView
            scene = QGraphicsScene()
            graphics_view.setScene(scene) # Define a cena do QGraphicsView
            item_layout.addWidget(graphics_view) # Adiciona o QGraphicsView ao layout

            button.setProperty('valor_atributo', valor)  # Define uma propriedade personalizada no QPushButton

            item_widget.setLayout(item_layout)  # Define o layout do item_widget
            item.setSizeHint(item_widget.sizeHint())  # Define o tamanho do item com base no tamanho do item_widget
            self.listWidget.setItemWidget(item, item_widget)  # Define o widget personalizado para o item

            # Chama a função atualizarBlocoGrafico para desenhar o bloco inicial
            self.atualizarBlocoGrafico(item_widget, combo, button)

            # Conecta o sinal de mudança de índice à função atualizarBlocoGrafico
            combo.currentIndexChanged.connect(lambda index, w=item_widget, c=combo, b=button: self.atualizarBlocoGrafico(w, c, b))

            # Conecta o sinal stateChanged de cada QCheckBox ao método verificarCheckBoxes
            checkbox.stateChanged.connect(self.verificarCheckBoxes)

        # Chama a função verificarCheckBoxes para definir o estado inicial do botão Exportar
        self.verificarCheckBoxes()

    def atualizarBlocoGrafico(self, item_widget, combo, button):
        """
        Atualiza o gráfico do bloco no QGraphicsView com base na seleção do QComboBox e na cor do QPushButton.
        
        Funções principais:
        - Limpa a cena atual no QGraphicsView.
        - Desenha o bloco correspondente à seleção atual do QComboBox.
        - Aplica a cor selecionada ao bloco.
        - Centraliza o bloco na cena do QGraphicsView.
        
        Etapas detalhadas:
        1. Encontra o QGraphicsView no item_widget.
        2. Limpa a cena atual do QGraphicsView.
        3. Obtém o nome do bloco selecionado no QComboBox.
        4. Obtém a cor do QPushButton associado.
        5. Desenha o bloco na cena com a cor selecionada.
        6. Centraliza a cena e ajusta a visualização.

        Parâmetros:
        - item_widget (QWidget): O widget do item contendo o QGraphicsView.
        - combo (QComboBox): O QComboBox com a seleção do bloco.
        - button (QPushButton): O QPushButton com a cor selecionada.
        """
        graphics_view = item_widget.findChild(QGraphicsView)  # Encontra o QGraphicsView no item_widget
        scene = graphics_view.scene()  # Obtém a cena do QGraphicsView
        scene.clear()  # Limpa a cena atual

        nome_bloco = combo.currentText()  # Obtém o nome do bloco selecionado no QComboBox
        cor = button.palette().button().color()  # Obtém a cor do botão
        if nome_bloco:
            self.desenharBloco(scene, nome_bloco, cor)  # Desenha o bloco na cena com a cor selecionada

        # Centralizar a cena
        rect = scene.itemsBoundingRect()  # Obtém o retângulo delimitador dos itens na cena
        scene.setSceneRect(rect)  # Define o retângulo delimitador como o retângulo da cena
        graphics_view.setSceneRect(rect)  # Define o retângulo delimitador como o retângulo da visualização
        graphics_view.fitInView(rect, Qt.KeepAspectRatio)  # Ajusta a visualização para manter a proporção do retângulo

    def desenharBloco(self, scene, nome_bloco, cor):
        """
        Desenha um bloco específico na cena fornecida com base no nome do bloco e na cor fornecida.
        
        Funções principais:
        - Define a cor e a largura da caneta para desenhar.
        - Ajusta a escala dos blocos.
        - Desenha diferentes formas geométricas (círculos, linhas, polígonos) para representar vários blocos.
        
        Etapas detalhadas:
        1. Define a cor e a largura da caneta.
        2. Define um fator de escala para ajustar os blocos ao tamanho desejado.
        3. Desenha o bloco específico com base no nome do bloco fornecido.
        4. Cada bloco é desenhado com as formas geométricas apropriadas (círculos, linhas, polígonos).

        Parâmetros:
        - scene (QGraphicsScene): A cena onde o bloco será desenhado.
        - nome_bloco (str): O nome do bloco a ser desenhado.
        - cor (QColor): A cor para desenhar o bloco.
        """

        pen = QPen(cor)  # Define a cor da caneta
        pen.setWidth(int(0.80))  # Define a largura da caneta
        scale_factor = 1  # Escala para ajustar os blocos ao tamanho desejado

        if nome_bloco == 'CirculoX':
            # Desenha um círculo com um X dentro
            scene.addEllipse(-0.5 * scale_factor, -0.5 * scale_factor, 1.0 * scale_factor, 1.0 * scale_factor, pen)
            scene.addLine(-0.35 * scale_factor, -0.35 * scale_factor, 0.35 * scale_factor, 0.35 * scale_factor, pen)
            scene.addLine(-0.35 * scale_factor, 0.35 * scale_factor, 0.35 * scale_factor, -0.35 * scale_factor, pen)

        elif nome_bloco == 'CirculoCruz':
            # Desenha um círculo com uma cruz dentro
            scene.addEllipse(-0.5 * scale_factor, -0.5 * scale_factor, 1.0 * scale_factor, 1.0 * scale_factor, pen)
            scene.addLine(-0.5 * scale_factor, 0, 0.5 * scale_factor, 0, pen)
            scene.addLine(0, -0.5 * scale_factor, 0, 0.5 * scale_factor, pen)

        elif nome_bloco == 'CirculoTraço':
            # Desenha um círculo com um traço vertical no centro
            scene.addEllipse(-0.5 * scale_factor, -0.5 * scale_factor, 1.0 * scale_factor, 1.0 * scale_factor, pen)
            scene.addLine(0, 0, 0, -0.6 * scale_factor, pen)

        elif nome_bloco == 'CirculoPonto':
            # Desenha um círculo com um ponto no centro
            scene.addEllipse(-0.5 * scale_factor, -0.5 * scale_factor, 1.0 * scale_factor, 1.0 * scale_factor, pen)
            scene.addEllipse(-0.05 * scale_factor, -0.05 * scale_factor, 0.1 * scale_factor, 0.1 * scale_factor, pen)

        elif nome_bloco == 'Árvore':
            # Desenha a copa da árvore com elipses e o tronco com uma linha
            scene.addEllipse(-0.4 * scale_factor, -0.1 * scale_factor, 0.8 * scale_factor, 0.6 * scale_factor, pen)
            scene.addEllipse(-0.3 * scale_factor, -0.3 * scale_factor, 0.6 * scale_factor, 0.7 * scale_factor, pen)
            scene.addEllipse(-0.2 * scale_factor, -0.2 * scale_factor, 0.4 * scale_factor, 0.7 * scale_factor, pen)
            scene.addLine(0, 0.5 * scale_factor, 0, 1.0 * scale_factor, pen)

        elif nome_bloco == 'Poste':
            # Desenha o poste principal e suas travessas e fios
            scene.addLine(0, 0, 0, -2.4 * scale_factor, pen)
            # Desenha a travessa superior
            scene.addLine(-0.4 * scale_factor, -2.0 * scale_factor, 0.4 * scale_factor, -2.0 * scale_factor, pen)
            # Desenha a travessa inferior
            scene.addLine(-0.8 * scale_factor, -1.6 * scale_factor, 0.8 * scale_factor, -1.6 * scale_factor, pen)
            # Desenha os fios inclinados
            scene.addLine(0, -1.6 * scale_factor, -0.5656 * scale_factor, -1.0344 * scale_factor, pen)
            scene.addLine(0, -1.6 * scale_factor, 0.5656 * scale_factor, -1.0344 * scale_factor, pen)

        elif nome_bloco == 'Bandeira':
            # Desenha a haste da bandeira e um triângulo como bandeira
            scene.addLine(0, 0, 0, -1.5 * scale_factor, pen)

            # Desenha a bandeira como um triângulo maior à esquerda
            base_triangular = -0.85 * scale_factor
            altura_triangular = 0.75 * scale_factor
            pontos_bandeira = [(0, -1.5 * scale_factor), 
                               (base_triangular, -1.5 * scale_factor + altura_triangular / 2), 
                               (0, -1.5 * scale_factor + altura_triangular), 
                               (0, -1.5 * scale_factor)]
            scene.addPolygon(QPolygonF([QPointF(p[0], p[1]) for p in pontos_bandeira]), pen)

            # Desenha a linha horizontal maior na base da haste
            scene.addLine(-0.5 * scale_factor, 0, 0.5 * scale_factor, 0, pen)

        elif nome_bloco == 'Bandeira 2':
            # Desenha a haste da bandeira e um retângulo como bandeira
            scene.addLine(0, 0, 0, -1.5 * scale_factor, pen)

            # Desenha a bandeira como um retângulo à esquerda
            largura_bandeira = -0.75 * scale_factor
            altura_bandeira = 0.6 * scale_factor
            topo_bandeira = -1.5 * scale_factor
            base_bandeira = topo_bandeira + altura_bandeira
            pontos_bandeira = [
                (0, topo_bandeira),
                (largura_bandeira, topo_bandeira),
                (largura_bandeira, base_bandeira),
                (0, base_bandeira),
                (0, topo_bandeira)  # Fecha o ponto voltando ao ponto inicial
            ]
            scene.addPolygon(QPolygonF([QPointF(p[0], p[1]) for p in pontos_bandeira]), pen)

            # Desenha a linha horizontal na base da haste
            scene.addLine(-0.25 * scale_factor, 0, 0.25 * scale_factor, 0, pen)

        elif nome_bloco == 'Cerca':
            # Desenha postes verticais e painéis horizontais para a cerca
            altura_poste = 0.8 * scale_factor  # Altura dos postes da cerca
            largura_painel = 0.1 * scale_factor  # Largura dos painéis horizontais
            numero_postes = 3  # Número de postes na cerca

            # Desenha os postes verticais e os painéis horizontais
            for i in range(numero_postes):
                x_pos = i * largura_painel * 2
                # Desenha o poste vertical
                scene.addLine(x_pos, 0, x_pos, -altura_poste, pen)

                # Desenha os painéis horizontais conectando os postes
                if i < numero_postes - 1:
                    scene.addLine(x_pos, -altura_poste / 2, x_pos + largura_painel * 2, -altura_poste / 2, pen)
                    scene.addLine(x_pos, -altura_poste / 4, x_pos + largura_painel * 2, -altura_poste / 4, pen)
                    scene.addLine(x_pos, -altura_poste * 3 / 4, x_pos + largura_painel * 2, -altura_poste * 3 / 4, pen)

        elif nome_bloco == 'Rocha':
            # Desenha a rocha como uma forma poligonal
            pontos_rocha = [
                (-0.5 * scale_factor, 0),
                (-0.3 * scale_factor, 0.3 * scale_factor),
                (0, 0.5 * scale_factor),
                (0.3 * scale_factor, 0.3 * scale_factor),
                (0.5 * scale_factor, 0),
                (0.3 * scale_factor, -0.3 * scale_factor),
                (0, -0.5 * scale_factor),
                (-0.3 * scale_factor, -0.3 * scale_factor),
                (-0.5 * scale_factor, 0)
            ]
            scene.addPolygon(QPolygonF([QPointF(p[0], p[1]) for p in pontos_rocha]), pen)

        elif nome_bloco == 'Bueiro':
            # Desenha dois círculos concêntricos e uma cruz no centro para representar um bueiro
            scene.addEllipse(-0.5 * scale_factor, -0.5 * scale_factor, 1.0 * scale_factor, 1.0 * scale_factor, pen)
            scene.addEllipse(-0.4 * scale_factor, -0.4 * scale_factor, 0.8 * scale_factor, 0.8 * scale_factor, pen)

            # Adiciona uma cruz pequena no centro
            cruz_tamanho = 0.1 * scale_factor
            scene.addLine(-cruz_tamanho, 0, cruz_tamanho, 0, pen)
            scene.addLine(0, -cruz_tamanho, 0, cruz_tamanho, pen)

        elif nome_bloco == 'QuadradoX':
            # Desenha um quadrado com um X dentro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor)
            ]), pen)

            # Desenha um X dentro do quadrado
            scene.addLine(-0.5 * scale_factor, -0.5 * scale_factor, 0.5 * scale_factor, 0.5 * scale_factor, pen)
            scene.addLine(0.5 * scale_factor, -0.5 * scale_factor, -0.5 * scale_factor, 0.5 * scale_factor, pen)

        elif nome_bloco == 'QuadradoTraço':
            # Desenha um quadrado com um traço vertical no centro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor)
            ]), pen)

            # Desenha um traço vertical no centro do quadrado, se estendendo um pouco acima
            scene.addLine(0, 0 * scale_factor, 0, -0.6 * scale_factor, pen)

        elif nome_bloco == 'QuadradoCruz':
            # Desenha um quadrado com uma cruz dentro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor)
            ]), pen)

            # Desenha uma cruz dentro do quadrado
            scene.addLine(-0.4 * scale_factor, 0, 0.4 * scale_factor, 0, pen)
            scene.addLine(0, -0.4 * scale_factor, 0, 0.4 * scale_factor, pen)

        elif nome_bloco == 'TrianguloX':
            # Desenha um triângulo com um X dentro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0, -0.577 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor)
            ]), pen)

            # Desenha o X, centralizado no ponto (0, 0)
            x_size = 0.20 * scale_factor
            y_size = 0.289 * scale_factor
            scene.addLine(-x_size, -y_size, x_size, y_size, pen)
            scene.addLine(-x_size, y_size, x_size, -y_size, pen)

        elif nome_bloco == 'QuadradoPonto':
            # Desenha um quadrado com um ponto no centro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, 0.5 * scale_factor),
                QPointF(0.5 * scale_factor, -0.5 * scale_factor),
                QPointF(-0.5 * scale_factor, -0.5 * scale_factor)
            ]), pen)
            # Desenha um ponto no centro do quadrado
            brush = QBrush(cor)
            scene.addEllipse(-0.05 * scale_factor, -0.05 * scale_factor, 0.1 * scale_factor, 0.1 * scale_factor, pen, brush)

        elif nome_bloco == 'TrianguloPonto':
            # Desenha um triângulo com um ponto no centro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0, -0.577 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor)
            ]), pen)
            # Desenha o ponto
            brush = QBrush(cor)
            scene.addEllipse(-0.05 * scale_factor, -0.05 * scale_factor, 0.1 * scale_factor, 0.1 * scale_factor, pen, brush)

        elif nome_bloco == 'TrianguloTraço':
            # Desenha um triângulo com um traço vertical no centro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0, -0.577 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor)
            ]), pen)
            # Desenha o traço vertical no centro do triângulo
            scene.addLine(0, 0, 0, -0.577 * scale_factor, pen)

        elif nome_bloco == 'Casa':
            # Desenha a base da casa e o telhado
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, 0.25 * scale_factor),
                QPointF(-0.5 * scale_factor, -0.25 * scale_factor),
                QPointF(0.5 * scale_factor, -0.25 * scale_factor),
                QPointF(0.5 * scale_factor, 0.25 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.25 * scale_factor)
            ]), pen)
            # Desenha o telhado
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, -0.25 * scale_factor),
                QPointF(0, -0.5 * scale_factor),
                QPointF(0.5 * scale_factor, -0.25 * scale_factor)
            ]), pen)

        elif nome_bloco == 'TrianguloCruz':
            # Desenha um triângulo com uma cruz dentro
            scene.addPolygon(QPolygonF([
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0.5 * scale_factor, 0.289 * scale_factor),
                QPointF(0 * scale_factor, -0.577 * scale_factor),
                QPointF(-0.5 * scale_factor, 0.289 * scale_factor)
            ]), pen)
            # Desenha a cruz centralizada
            scene.addLine(0, -0.289 * scale_factor, 0, 0.289 * scale_factor, pen)
            scene.addLine(-0.289 * scale_factor, 0, 0.289 * scale_factor, 0, pen)

        elif nome_bloco == 'Topografia GPS':
            # Desenha o tripé e o GPS no topo
            altura_tripe = 1.5 * scale_factor
            largura_base = 0.8 * scale_factor
            largura_gps = 0.2 * scale_factor
            altura_gps = 0.1 * scale_factor
            offset = altura_tripe / 2

            # Desenha as pernas do tripé apontando para baixo
            scene.addLine(0, -offset, -largura_base / 2, offset, pen)
            scene.addLine(0, -offset, largura_base / 2, offset, pen)
            scene.addLine(0, -offset, 0, -offset + 0.2 * scale_factor, pen)

            # Desenha a linha vertical no centro para simular um tripé
            scene.addLine(0, -offset, 0, offset, pen)

            # Desenha o retângulo para representar o GPS no topo do tripé
            scene.addPolygon(QPolygonF([
                QPointF(-largura_gps, -offset + altura_gps),
                QPointF(-largura_gps, -offset - altura_gps),
                QPointF(largura_gps, -offset - altura_gps),
                QPointF(largura_gps, -offset + altura_gps),
                QPointF(-largura_gps, -offset + altura_gps)
            ]), pen)

            # Adiciona um detalhe no GPS, como um pequeno círculo (botão)
            scene.addEllipse(-0.02 * scale_factor, -offset - 0.02 * scale_factor, 0.04 * scale_factor, 0.04 * scale_factor, pen)

    def criar_blocos(self, doc, cores):
        """
        Cria e adiciona blocos predefinidos ao documento DXF. A função realiza as seguintes etapas:

        1. Verifica se cada bloco predefinido já existe no documento DXF.
        2. Se o bloco não existir, cria o bloco usando a função correspondente.
        3. Adiciona o nome do bloco criado à lista de nomes de blocos.

        Parâmetros:
        - doc (ezdxf.document): O documento DXF onde os blocos serão adicionados.
        - cores (dict): Dicionário de cores escolhidas.

        Funcionalidades:
        - Criação de vários tipos de blocos predefinidos (círculos, quadrados, triângulos, etc.).
        - Verificação da existência dos blocos antes de criá-los.
        - Retorno de uma lista com os nomes dos blocos criados.

        Retorna:
        - list: Lista com os nomes dos blocos criados.
        """
        nomes_blocos = []

        # Verifica se os blocos já existem antes de criar novos
        if 'CirculoX' not in doc.blocks:
            nome_bloco_x = self.criar_bloco_circulo_com_linhas(doc, 'CirculoX', cores, [((-0.35, -0.35), (0.35, 0.35)), ((-0.35, 0.35), (0.35, -0.35))])
            nomes_blocos.append(nome_bloco_x)

        if 'CirculoCruz' not in doc.blocks:
            nome_bloco_cruz = self.criar_bloco_circulo_com_linhas(doc, 'CirculoCruz', cores, [((-0.5, 0), (0.5, 0)), ((0, -0.5), (0, 0.5))])
            nomes_blocos.append(nome_bloco_cruz)

        if 'CirculoTraço' not in doc.blocks:
            nome_bloco_traco_vertical = self.criar_bloco_circulo_com_linhas(doc, 'CirculoTraço', cores, [((0, 0), (0, 0.6))])
            nomes_blocos.append(nome_bloco_traco_vertical)

        # Criação do bloco CirculoComPontoCentral
        if 'CirculoPonto' not in doc.blocks:
            nome_bloco_ponto_central = self.criar_bloco_circulo_com_ponto(doc, 'CirculoPonto', cores)
            nomes_blocos.append(nome_bloco_ponto_central)

        # Criação do bloco ÁRVORE
        if 'Árvore' not in doc.blocks:
            nome_bloco_arvore = self.criar_bloco_arvore(doc, 'Árvore', cores)
            nomes_blocos.append(nome_bloco_arvore)

        # Criação do bloco POSTE
        if 'Poste' not in doc.blocks:
            nome_bloco_poste = self.criar_bloco_poste(doc, 'Poste', cores)
            nomes_blocos.append(nome_bloco_poste)

        # Criação do bloco BANDEIRA
        if 'Bandeira' not in doc.blocks:
            nome_bloco_bandeira = self.criar_bloco_bandeira(doc, 'Bandeira', cores)
            nomes_blocos.append(nome_bloco_bandeira)

        # Criação do bloco BANDEIRA 2
        if 'Bandeira 2' not in doc.blocks:
            nome_bloco_bandeira_Q = self.criar_bloco_bandeira_Q(doc, 'Bandeira 2', cores)
            nomes_blocos.append(nome_bloco_bandeira_Q)

        # Criação do bloco CERCA
        if 'Cerca' not in doc.blocks:
            nome_bloco_cerca = self.criar_bloco_cerca(doc, 'Cerca', cores)
            nomes_blocos.append(nome_bloco_cerca)

        # Verifica e cria o bloco de rocha
        if 'Rocha' not in doc.blocks:
            nome_bloco_rocha = self.criar_bloco_rocha(doc, 'Rocha', cores)
            nomes_blocos.append(nome_bloco_rocha)

        # Verifica e cria o bloco de bueiro
        if 'Bueiro' not in doc.blocks:
            nome_bloco_bueiro = self.criar_bloco_bueiro(doc, 'Bueiro', cores)
            nomes_blocos.append(nome_bloco_bueiro)

        # Criação do o bloco QuadradoComX 
        if 'QuadradoX' not in doc.blocks:
            nome_bloco_QuadradoComX = self.criar_bloco_quadrado_com_x(doc, 'QuadradoX', cores)
            nomes_blocos.append(nome_bloco_QuadradoComX)

        # Criação do bloco QuadradoComCruz
        if 'QuadradoCruz' not in doc.blocks:
            nome_bloco_QuadradoComCruz = self.criar_bloco_quadrado_com_cruz(doc, 'QuadradoCruz', cores)
            nomes_blocos.append(nome_bloco_QuadradoComCruz)

        # Criação do bloco QuadradoComTraco
        if 'QuadradoTraço' not in doc.blocks:
            nome_bloco_QuadradoComTraco = self.criar_bloco_quadrado_com_traco(doc, 'QuadradoTraço', cores)
            nomes_blocos.append(nome_bloco_QuadradoComTraco)

        # Criação do bloco QuadradoComPonto
        if 'QuadradoPonto' not in doc.blocks:
            nome_bloco_QuadradoComPonto = self.criar_bloco_quadrado_com_ponto(doc, 'QuadradoPonto', cores)
            nomes_blocos.append(nome_bloco_QuadradoComPonto)

        # Criação do bloco TrianguloComX
        if 'TrianguloX' not in doc.blocks:
            nome_bloco_triangulo_com_X = self.criar_bloco_triangulo_com_x(doc, 'TrianguloX', cores)
            nomes_blocos.append(nome_bloco_triangulo_com_X)

        # Criação do bloco TrianguloComCruz
        if 'TrianguloCruz' not in doc.blocks:
            nome_bloco_triangulo_cruz = self.criar_bloco_triangulo_com_cruz(doc, 'TrianguloCruz', cores)
            nomes_blocos.append(nome_bloco_triangulo_cruz)

        # Criação do bloco TrianguloComPonto
        if 'TrianguloPonto' not in doc.blocks:
            nome_bloco_ponto = self.criar_bloco_triangulo_com_ponto(doc, 'TrianguloPonto', cores)
            nomes_blocos.append(nome_bloco_ponto)

        # Criação do bloco TrianguloComTraco
        if 'TrianguloTraço' not in doc.blocks:
            nome_bloco_traco = self.criar_bloco_triangulo_com_traco(doc, 'TrianguloTraço', cores)
            nomes_blocos.append(nome_bloco_traco)

        # Criação do bloco Casa
        if 'Casa' not in doc.blocks:
            nome_bloco_casa = self.criar_bloco_casa(doc, 'Casa', cores)
            nomes_blocos.append(nome_bloco_casa)

        # Criação do bloco Topografia
        if 'Topografia GPS' not in doc.blocks:
            nome_bloco_gps = self.criar_bloco_gps_tripe(doc, 'Topografia GPS', cores)
            nomes_blocos.append(nome_bloco_gps)

            return nomes_blocos

    def criar_bloco_gps_tripe(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_tripe = cores.get('cor_tripe', (0, 0, 0))  # Cor padrão preta para o tripé
        cor_gps = cores.get('cor_gps', (0, 0, 0))  # Cor padrão 
        cor_detalhe = cores.get('cor_detalhe', (0, 0, 0))  # Cor padrão 

        # Altura e largura do tripé
        altura_tripe = 1.5
        largura_base = 0.8

        # Desenha as pernas do tripé apontando para baixo
        bloco.add_line(start=(0, altura_tripe), end=(-largura_base / 2, 0), dxfattribs={'color': rgb2int(cor_tripe)})
        bloco.add_line(start=(0, altura_tripe), end=(largura_base / 2, 0), dxfattribs={'color': rgb2int(cor_tripe)})
        bloco.add_line(start=(0, altura_tripe), end=(0, 0.2), dxfattribs={'color': rgb2int(cor_tripe)})

        # Desenha o retângulo para representar o GPS no topo do tripé
        largura_gps = 0.2
        altura_gps = 0.1
        bloco.add_lwpolyline([(0 - largura_gps / 2, altura_tripe + altura_gps / 2), 
                              (0 - largura_gps / 2, altura_tripe - altura_gps / 2),
                              (0 + largura_gps / 2, altura_tripe - altura_gps / 2), 
                              (0 + largura_gps / 2, altura_tripe + altura_gps / 2), 
                              (0 - largura_gps / 2, altura_tripe + altura_gps / 2)], 
                              dxfattribs={'color': rgb2int(cor_gps)})

        # Adiciona um detalhe no GPS, como um pequeno círculo (botão)
        bloco.add_circle(center=(0, altura_tripe), radius=0.02, dxfattribs={'color': rgb2int(cor_detalhe)})

        return nome_bloco

    def criar_bloco_casa(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (128, 0, 0))  # Cor padrão vermelha para a edificação

        # Desenha a base da casa
        bloco.add_lwpolyline([(-0.5, -0.25), (-0.5, 0.25), (0.5, 0.25), (0.5, -0.25), (-0.5, -0.25)], dxfattribs={'color': rgb2int(cor_linha)})

        # Desenha o telhado
        bloco.add_lwpolyline([(-0.5, 0.25), (0, 0.5), (0.5, 0.25)], dxfattribs={'color': rgb2int(cor_linha)})

        return nome_bloco

    def criar_bloco_rocha(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (105, 105, 105))  # Cor padrão cinza

        # Ajustando os pontos para que o ponto esteja centralizado no ponto (0,0)
        pontos_rocha = [(-0.5, 0), (-0.3, 0.3), (0, 0.5), (0.3, 0.3), (0.5, 0), (0.3, -0.3), (0, -0.5), (-0.3, -0.3), (-0.5, 0)]
        bloco.add_lwpolyline(pontos_rocha, dxfattribs={'color': rgb2int(cor_linha)})

        return nome_bloco

    def criar_bloco_bueiro(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (0, 0, 0))  # Cor padrão preta para o bueiro

        # Adiciona dois círculos concêntricos para representar a parte superior do bueiro
        bloco.add_circle(center=(0, 0), radius=0.5, dxfattribs={'color': rgb2int(cor_linha)})
        bloco.add_circle(center=(0, 0), radius=0.4, dxfattribs={'color': rgb2int(cor_linha)})

        # Adiciona uma cruz pequena no centro
        cruz_tamanho = 0.1
        bloco.add_line(start=(-cruz_tamanho, 0), end=(cruz_tamanho, 0), dxfattribs={'color': rgb2int(cor_linha)})
        bloco.add_line(start=(0, -cruz_tamanho), end=(0, cruz_tamanho), dxfattribs={'color': rgb2int(cor_linha)})

        return nome_bloco

    def criar_bloco_triangulo_com_x(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (0, 0, 0))  # Cor padrão preta
        # Desenha o triângulo
        bloco.add_lwpolyline([(-0.5, -0.289), (0.5, -0.289), (0, 0.577), (-0.5, -0.289)], dxfattribs={'color': rgb2int(cor_linha)})
        # Desenha o X, centralizado no ponto (0, 0.192)
        x_center = 0
        y_center = 0
        x_size = 0.35
        y_size = 0.54 # A altura de um triângulo menor que seria formado pelo X
        bloco.add_line(start=(x_center - x_size / 2, y_center - y_size / 2), end=(x_center + x_size / 2, y_center + y_size / 2), dxfattribs={'color': rgb2int(cor_linha)})
        bloco.add_line(start=(x_center - x_size / 2, y_center + y_size / 2), end=(x_center + x_size / 2, y_center - y_size / 2), dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_triangulo_com_cruz(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (0, 0, 0))
        # Desenha o triângulo
        bloco.add_lwpolyline([(-0.5, -0.289), (0.5, -0.289), (0, 0.577), (-0.5, -0.289)], dxfattribs={'color': rgb2int(cor_linha)})
        # Desenha a cruz
        bloco.add_line(start=(0, -0.1156), end=(0, 0.404), dxfattribs={'color': rgb2int(cor_linha)})
        bloco.add_line(start=(-0.3, 0.1442), end=(0.3, 0.1442), dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_triangulo_com_ponto(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (0, 0, 0))
        # Desenha o triângulo
        bloco.add_lwpolyline([(-0.5, -0.289), (0.5, -0.289), (0, 0.577), (-0.5, -0.289)], dxfattribs={'color': rgb2int(cor_linha)})
        # Desenha o ponto
        bloco.add_circle(center=(0, 0), radius=0.05, dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_triangulo_com_traco(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get(nome_bloco, (0, 0, 0))
        # Desenha o triângulo
        bloco.add_lwpolyline([(-0.5, -0.289), (0.5, -0.289), (0, 0.577), (-0.5, -0.289)], dxfattribs={'color': rgb2int(cor_linha)})

        bloco.add_line(start=(0, 0), end=(0, 0.677), dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_quadrado_com_x(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get('cor_linha', (0, 0, 0))  # Cor padrão preta
        # Desenha o quadrado centralizado
        bloco.add_lwpolyline([(-0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)], dxfattribs={'color': rgb2int(cor_linha)})
        # Desenha um X dentro do quadrado
        bloco.add_line(start=(-0.5, -0.5), end=(0.5, 0.5), dxfattribs={'color': rgb2int(cor_linha)})
        bloco.add_line(start=(0.5, -0.5), end=(-0.5, 0.5), dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_quadrado_com_cruz(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get('cor_linha', (0, 0, 0))
        # Desenha o quadrado centralizado
        bloco.add_lwpolyline([(-0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)], dxfattribs={'color': rgb2int(cor_linha)})
        # Desenha uma cruz dentro do quadrado
        bloco.add_line(start=(-0.4, 0), end=(0.4, 0), dxfattribs={'color': rgb2int(cor_linha)})
        bloco.add_line(start=(0, -0.4), end=(0, 0.4), dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_quadrado_com_traco(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_linha = cores.get('cor_linha', (0, 0, 0))
        # Desenha o quadrado centralizado
        bloco.add_lwpolyline([(-0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)], dxfattribs={'color': rgb2int(cor_linha)})
        # Desenha um traço vertical no centro do quadrado, se estendendo um pouco acima
        bloco.add_line(start=(0, 0), end=(0, 0.6), dxfattribs={'color': rgb2int(cor_linha)})
        return nome_bloco

    def criar_bloco_quadrado_com_ponto(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_ponto = cores.get('cor_ponto', (0, 0, 0))
        # Desenha o quadrado centralizado
        bloco.add_lwpolyline([(-0.5, -0.5), (-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)], dxfattribs={'color': rgb2int(cor_ponto)})
        # Desenha um ponto no centro do quadrado
        bloco.add_point((0, 0), dxfattribs={'color': rgb2int(cor_ponto)})
        return nome_bloco

    def criar_bloco_cerca(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)

        # Define a cor para a cerca
        cor_cerca = cores.get('cor_cerca', (139, 69, 19))  # Cor padrão marrom para a cerca

        # Parâmetros para o desenho da cerca
        altura_poste = 0.8  # Altura dos postes da cerca
        largura_painel = 0.1  # Largura dos painéis horizontais
        numero_postes = 3  # Número de postes na cerca

        # Desenha os postes verticais e os painéis horizontais
        for i in range(numero_postes):
            x_pos = i * largura_painel * 2
            # Desenha o poste vertical
            bloco.add_line(start=(x_pos, 0), end=(x_pos, altura_poste), dxfattribs={'color': rgb2int(cor_cerca)})

            # Desenha os painéis horizontais conectando os postes
            if i < numero_postes - 1:
                bloco.add_line(start=(x_pos, altura_poste / 2), end=(x_pos + largura_painel * 2, altura_poste / 2), dxfattribs={'color': rgb2int(cor_cerca)})
                bloco.add_line(start=(x_pos, altura_poste / 4), end=(x_pos + largura_painel * 2, altura_poste / 4), dxfattribs={'color': rgb2int(cor_cerca)})
                bloco.add_line(start=(x_pos, altura_poste * 3 / 4), end=(x_pos + largura_painel * 2, altura_poste * 3 / 4), dxfattribs={'color': rgb2int(cor_cerca)})

        return nome_bloco

    def criar_bloco_bandeira(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        
        # Define as cores
        cor_haste = cores.get('cor_haste', (105, 105, 105))  # Cor padrão cinza para a haste
        cor_bandeira = cores.get('cor_bandeira', (255, 0, 0))  # Cor padrão vermelha para a bandeira

        # Adiciona uma linha vertical para representar a haste da bandeira
        altura_haste = 1.5
        bloco.add_line(start=(0, 0), end=(0, altura_haste), dxfattribs={'color': rgb2int(cor_haste)})

        # Adiciona um triângulo maior para representar a bandeira à esquerda
        base_triangular = -0.85  # Agora negativo para ir à esquerda
        altura_triangular = 0.75
        pontos_bandeira = [(0, altura_haste), (base_triangular, altura_haste - altura_triangular / 2), (0, altura_haste - altura_triangular), (0, altura_haste)]
        bloco.add_lwpolyline(points=pontos_bandeira, dxfattribs={'color': rgb2int(cor_bandeira)})

        # Adiciona uma linha horizontal maior na base da haste
        bloco.add_line(start=(-0.5, 0), end=(0.5, 0), dxfattribs={'color': rgb2int(cor_haste)})

        return nome_bloco

    def criar_bloco_bandeira_Q(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        
        # Define as cores
        cor_haste = cores.get('cor_haste', (105, 105, 105))  # Cor padrão cinza para a haste
        cor_bandeira = cores.get('cor_bandeira', (255, 0, 0))  # Cor padrão vermelha para a bandeira

        # Adiciona uma linha vertical para representar a haste da bandeira
        altura_haste = 1.5
        bloco.add_line(start=(0, 0), end=(0, altura_haste), dxfattribs={'color': rgb2int(cor_haste)})

        # Adiciona um retângulo para representar a bandeira no topo da haste e à esquerda
        largura_bandeira = -0.75  # Largura negativa para a esquerda
        altura_bandeira = 0.6
        topo_bandeira = altura_haste
        base_bandeira = topo_bandeira - altura_bandeira
        bloco.add_lwpolyline([
            (0, topo_bandeira),
            (largura_bandeira, topo_bandeira),
            (largura_bandeira, base_bandeira),
            (0, base_bandeira),
            (0, topo_bandeira)  # Fecha o ponto voltando ao ponto inicial
        ], dxfattribs={'color': rgb2int(cor_bandeira)})

        # Adiciona uma linha horizontal na base da haste
        bloco.add_line(start=(-0.25, 0), end=(0.25, 0), dxfattribs={'color': rgb2int(cor_haste)})

        return nome_bloco

    def criar_bloco_poste(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_poste = cores.get('cor_poste', (0, 0, 0))

        # Poste principal (linha vertical)
        bloco.add_line(start=(0, 0), end=(0, 2.4), dxfattribs={'color': rgb2int(cor_poste)})

        # Travessa superior (linha horizontal menor)
        bloco.add_line(start=(-0.4, 2.0), end=(0.4, 2.0), dxfattribs={'color': rgb2int(cor_poste)})

        # Travessa inferior (linha horizontal maior)
        bloco.add_line(start=(-0.8, 1.6), end=(0.8, 1.6), dxfattribs={'color': rgb2int(cor_poste)})

        # Fio inclinado esquerdo (a partir da interseção da linha vertical com a linha horizontal mais baixa)
        bloco.add_line(start=(0, 1.6), end=(-0.5656, 1.0344), dxfattribs={'color': rgb2int(cor_poste)})

        # Fio inclinado direito (a partir da interseção da linha vertical com a linha horizontal mais baixa)
        bloco.add_line(start=(0, 1.6), end=(0.5656, 1.0344), dxfattribs={'color': rgb2int(cor_poste)})

        return nome_bloco

    def criar_bloco_arvore(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        
        # Define as cores
        cor_copa = cores.get('cor_copa', (34, 139, 34))  # Cor padrão verde escuro para a copa
        cor_tronco = cores.get('cor_tronco', (139, 69, 19))  # Cor padrão marrom para o tronco

        # Adiciona as elipses para representar a copa da árvore
        # Primeira elipse
        bloco.add_ellipse(center=(0, 1), major_axis=(0.4, 0), ratio=0.6, start_param=0, end_param=2 * math.pi, dxfattribs={'color': rgb2int(cor_copa)})

        # Segunda elipse, rotacionada
        bloco.add_ellipse(center=(0.2, 0.8), major_axis=(0.3, 0), ratio=0.7, start_param=0, end_param=2 * math.pi, dxfattribs={'color': rgb2int(cor_copa)})

        # Terceira elipse, também rotacionada
        bloco.add_ellipse(center=(-0.2, 0.8), major_axis=(0.3, 0), ratio=0.7, start_param=0, end_param=2 * math.pi, dxfattribs={'color': rgb2int(cor_copa)})

        # Adiciona uma linha para representar o tronco da árvore
        bloco.add_line(start=(0, 0), end=(0, 0.6), dxfattribs={'color': rgb2int(cor_tronco)})

        return nome_bloco

    def criar_bloco_circulo_com_linhas(self, doc, nome_bloco, cores, linhas):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_bloco = cores.get(nome_bloco, (255, 0, 0))  # Cor padrão vermelha
        cor_int = rgb2int(cor_bloco)

        # Adiciona um círculo ao bloco
        bloco.add_circle(center=(0, 0), radius=0.5, dxfattribs={'color': cor_int})

        # Adiciona linhas específicas ao bloco
        for linha in linhas:
            bloco.add_line(start=linha[0], end=linha[1], dxfattribs={'color': cor_int})

        return nome_bloco

    def criar_bloco_circulo_com_ponto(self, doc, nome_bloco, cores):
        bloco = doc.blocks.new(name=nome_bloco)
        cor_bloco = cores.get(nome_bloco, (255, 0, 0))  # Cor padrão vermelha
        cor_int = rgb2int(cor_bloco)

        # Adiciona um círculo ao bloco
        bloco.add_circle(center=(0, 0), radius=0.5, dxfattribs={'color': cor_int})

        # Adiciona um ponto no centro
        bloco.add_point((0, 0), dxfattribs={'color': cor_int})

        return nome_bloco

    def getCampoEscolhido(self):
        """
        Retorna o campo atualmente selecionado no comboBox.
        
        Funcionalidades:
        - Recupera o texto do campo selecionado no comboBox.

        Retorna:
        - str: O texto do campo atualmente selecionado no comboBox.
        """
        
        return self.comboBox.currentText()  # Retorna o texto do campo selecionado no comboBox

    def getSelecoes(self):
        """
        Retorna um conjunto com os valores dos atributos selecionados pelo usuário.
        A função realiza as seguintes etapas:

        1. Cria um conjunto vazio para armazenar as seleções.
        2. Itera sobre todos os itens no QListWidget.
        3. Para cada item, obtém o widget associado e encontra o QCheckBox.
        4. Se o QCheckBox estiver marcado, adiciona o texto do item ao conjunto de seleções.
        5. Retorna o conjunto de seleções.

        Funcionalidades:
        - Recuperação dos valores dos atributos selecionados pelo usuário no QListWidget.

        Retorna:
        - set: Conjunto com os valores dos atributos selecionados.
        """

        selecoes = set()  # Cria um conjunto vazio para armazenar as seleções
        for i in range(self.listWidget.count()):  # Itera sobre todos os itens no QListWidget
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            checkbox = widget.findChild(QCheckBox)  # Encontra o QCheckBox no widget do item
            if checkbox.isChecked():  # Verifica se o QCheckBox está marcado
                selecoes.add(item.text())  # Adiciona o valor do atributo ao conjunto
        return selecoes  # Retorna o conjunto de seleções

    def getCamposSelecionados(self):
        """
        Retorna uma lista com os nomes dos campos selecionados pelo usuário.
        A função realiza as seguintes etapas:

        1. Cria uma lista vazia para armazenar os campos selecionados.
        2. Verifica se o objeto possui o atributo 'camposCheckBoxes'.
        3. Itera sobre os itens no dicionário 'camposCheckBoxes'.
        4. Para cada campo, verifica se o checkbox está marcado.
        5. Se o checkbox estiver marcado, adiciona o nome do campo à lista de campos selecionados.
        6. Retorna a lista de campos selecionados.

        Funcionalidades:
        - Recuperação dos nomes dos campos selecionados pelo usuário.

        Retorna:
        - list: Lista com os nomes dos campos selecionados.
        """

        camposSelecionados = []  # Cria uma lista vazia para armazenar os campos selecionados
        if hasattr(self, 'camposCheckBoxes'):  # Verifica se o objeto possui o atributo 'camposCheckBoxes'
            for campo, checkbox in self.camposCheckBoxes.items():  # Itera sobre os itens no dicionário 'camposCheckBoxes'
                if checkbox.isChecked():  # Verifica se o checkbox está marcado
                    camposSelecionados.append(campo)  # Adiciona o nome do campo à lista de campos selecionados
        return camposSelecionados  # Retorna a lista de campos selecionados

    def getCampoZ(self):
        """
        Retorna o campo selecionado para a dimensão Z.
        A função realiza as seguintes etapas:

        1. Obtém o botão de rádio selecionado no grupo de botões de rádio.
        2. Verifica se um botão de rádio está selecionado.
        3. Se um botão de rádio estiver selecionado, retorna o texto do botão.
        4. Se nenhum botão de rádio estiver selecionado, retorna None.

        Funcionalidades:
        - Recuperação do nome do campo selecionado para a dimensão Z.

        Retorna:
        - str or None: O nome do campo selecionado para a dimensão Z, ou None se nenhum campo estiver selecionado.
        """

        selecionado = self.radioGroup.checkedButton()  # Obtém o botão de rádio selecionado
        return selecionado.text() if selecionado else None  # Retorna o texto do botão selecionado ou None

    def getBlocoSelecionado(self):
        """
        Retorna um dicionário com os valores dos atributos e os blocos selecionados pelo usuário.
        A função realiza as seguintes etapas:

        1. Cria um dicionário vazio para armazenar as seleções de blocos.
        2. Itera sobre todos os itens no QListWidget.
        3. Para cada item, obtém o valor do atributo e o widget associado.
        4. Encontra o QComboBox no widget do item.
        5. Se o QComboBox existir, adiciona o valor do atributo e o texto do bloco selecionado ao dicionário.
        6. Retorna o dicionário de seleções de blocos.

        Funcionalidades:
        - Recuperação dos blocos selecionados pelo usuário para cada valor de atributo.

        Retorna:
        - dict: Dicionário com os valores dos atributos como chaves e os blocos selecionados como valores.
        """

        blocoSelecoes = {}  # Cria um dicionário vazio para armazenar as seleções de blocos
        for i in range(self.listWidget.count()):  # Itera sobre todos os itens no QListWidget
            item = self.listWidget.item(i)
            valor = item.text()  # Obtém o valor do atributo
            widget = self.listWidget.itemWidget(item)
            combo = widget.findChild(QComboBox)  # Encontra o QComboBox no widget do item
            if combo:
                blocoSelecoes[valor] = combo.currentText()  # Adiciona o valor do atributo e o texto do bloco selecionado ao dicionário
        return blocoSelecoes  # Retorna o dicionário de seleções de blocos

class IconFieldSelectionDialog(QDialog):
    icon_cache = {}  # Dicionário de cache de ícones como atributo da classe
    # Atributos de classe para armazenar os URLs
    ultimoTextoUrl = ""
    ultimoTextoUrl2 = ""
    def __init__(self, layer, parent=None):
        """
        Inicializa o diálogo de seleção de campo e ícone.

        Parâmetros:
        - layer: A camada para a qual os campos e ícones serão selecionados.
        - parent: O widget pai do diálogo.
        """
        super(IconFieldSelectionDialog, self).__init__(parent)
        self.setWindowTitle("Escolher Campo e Ícone")

        self.setMinimumWidth(300)  # Define a largura mínima do diálogo
        self.setMaximumWidth(300)  # Define a largura máxima do diálogo

        self.layer = layer # Armazena a camada GIS
        self.selected_icon_url = None # URL do ícone selecionado
        self.selected_field = None # Campo selecionado
        self.network_manager = QNetworkAccessManager() # Gerenciador de rede para baixar ícones
        
        layout = QVBoxLayout(self) # Layout vertical principal do diálogo

        # Parte para escolha do campo e CheckBox
        field_layout = QHBoxLayout()  # Layout horizontal para o ComboBox e o CheckBox

        field_layout.addWidget(QLabel("Campo de identificação:"))
        self.combo_box = QComboBox() # ComboBox para selecionar o campo
        for field in self.layer.fields():
            self.combo_box.addItem(field.name()) # Adiciona os nomes dos campos ao ComboBox
        field_layout.addWidget(self.combo_box) # Adiciona o ComboBox ao layout

        self.check_box = QCheckBox("Rótulos")  # Criar o CheckBox
        self.check_box.setChecked(True)  # Marque por padrão, desmarque se não quiser exportar rótulos
        field_layout.addWidget(self.check_box)  # Adicionar o CheckBox ao layout horizontal

        layout.addLayout(field_layout)  # Adicionar o layout horizontal ao layout principal

        # Parte para escolha do ícone
        layout.addWidget(QLabel("Selecione um ícone:"))
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(30, 30))  # Ajusta o tamanho do ícone
        self.list_widget.setViewMode(QListView.IconMode)  # Exibe os itens em modo de ícone
        self.list_widget.setSpacing(5)  # Adiciona espaço entre os ícones
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)  # Modo de seleção única
        self.list_widget.setDragEnabled(False)  # Desativa o arrastar-e-soltar

        # Limita a largura do QListWidget para forçar os ícones a se organizarem em múltiplas linhas
        self.list_widget.setMaximumWidth(280)  # Ajuste este valor conforme necessário

        # Configura a folha de estilos para alterar a aparência dos itens selecionados
        self.list_widget.setStyleSheet("""
        QListWidget::item:selected {
            border: 2px solid #0563c1;
            background-color: #d8eaff;
        }
        QListWidget::item:hover {
            background-color: #b8daff;
        }
        """)
        self.setup_icon_list() # Configura a lista de ícones
        layout.addWidget(self.list_widget) # Adiciona o QListWidget ao layout principal

        # Adicione um atributo para rastrear o item anteriormente selecionado
        self.previous_selected_item = None  
        # Conecte o sinal itemClicked ao slot que irá desselecionar o ícone se ele já estiver selecionado
        self.list_widget.itemClicked.connect(self.toggle_icon_selection)

        # Criação do QFrame para conter os campos de URL
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)  # Define a forma do frame como uma caixa
        frame.setFrameShadow(QFrame.Raised)  # Define o estilo Raised
        frame.setLineWidth(1)  # Define a largura da borda

        # Layout para o QFrame
        frame_layout = QVBoxLayout(frame)

        # Primeiro QLineEdit e QPushButton para o URL da imagem
        self.labelImageUrl = QLabel("URL da Imagem para a Tabela:")
        frame_layout.addWidget(self.labelImageUrl)

        urlLayout1 = QHBoxLayout()
        self.lineEditImageUrl = QLineEdit()
        self.lineEditImageUrl.setPlaceholderText("Colar o URL da IMG para a Tabela: Opcional")
        self.lineEditImageUrl.setClearButtonEnabled(True)  # Habilita o botão de limpeza
        self.btnAbrirImagem = QPushButton("Colar")
        self.btnAbrirImagem.setMaximumWidth(35)
        urlLayout1.addWidget(self.lineEditImageUrl)
        urlLayout1.addWidget(self.btnAbrirImagem)

        frame_layout.addLayout(urlLayout1)   # Adiciona layout de URL da imagem ao layout do frame

        self.btnAbrirImagem.clicked.connect(self.colarTexto) # Conecta botão para colar texto

        # Segundo QLineEdit e QPushButton para o URL da imagem
        self.labelImageUrl2 = QLabel("URL para ScreenOverlay:")
        frame_layout.addWidget(self.labelImageUrl2)

        urlLayout2 = QHBoxLayout()
        self.lineEditImageUrl2 = QLineEdit()
        self.lineEditImageUrl2.setPlaceholderText("Colar o URL para o ScreenOverlay: Opcional")
        self.lineEditImageUrl2.setClearButtonEnabled(True)  # Habilita o botão de limpeza
        self.btnAbrirImagem2 = QPushButton("Colar")
        self.btnAbrirImagem2.setMaximumWidth(35)
        urlLayout2.addWidget(self.lineEditImageUrl2)
        urlLayout2.addWidget(self.btnAbrirImagem2)
        frame_layout.addLayout(urlLayout2)

        self.btnAbrirImagem2.clicked.connect(self.colarTexto2)

        # Setar o texto dos QLineEdit com os últimos valores usados
        self.lineEditImageUrl.setText(self.ultimoTextoUrl)
        self.lineEditImageUrl2.setText(self.ultimoTextoUrl2)

        # Conecta o sinal textChanged a um novo método para lidar com a atualização do texto
        self.lineEditImageUrl.textChanged.connect(self.verificarTexto)
        self.lineEditImageUrl2.textChanged.connect(self.verificarTexto2)

        layout.addWidget(frame)  # Adiciona o QFrame ao layout principal

        # Botões de Exportar e Cancelar
        buttons_layout = QHBoxLayout()
        self.button_ok = QPushButton("Exportar")
        self.button_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(self.button_ok)

        button_cancel = QPushButton("Cancelar")
        button_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(button_cancel)

        # Conecta a mudança de índice do ComboBox ao método validate_ok_button_state
        self.combo_box.currentIndexChanged.connect(self.validate_ok_button_state)

        # Conecta a mudança de estado do CheckBox ao método validate_ok_button_state
        self.check_box.stateChanged.connect(self.validate_ok_button_state)
        # Conecta a mudança de seleção do QListWidget ao método validate_ok_button_state
        self.list_widget.itemSelectionChanged.connect(self.validate_ok_button_state)

        layout.addLayout(buttons_layout) # Adiciona o layout dos botões ao layout principal

        self.validate_ok_button_state() # Valida o estado inicial do botão OK

    def verificarValidadeURL(self, url):
        """
        Verifica se a string fornecida é uma URL válida usando uma expressão regular.

        Parâmetros:
        - url (str): A URL a ser validada.

        Funcionalidades:
        - Compila uma expressão regular que valida URLs de forma abrangente, cobrindo protocolos, domínios, IPs, portas, caminhos, query strings e fragmentos.
        - Verifica se a URL fornecida corresponde à expressão regular.

        Retorno:
        - Retorna True se a URL for válida, False caso contrário.

        Utilização:
        - Utilizada para garantir que as URLs inseridas para imagens ou links em campos de URL sejam válidas antes de serem utilizadas para evitar erros na aplicação ou na visualização do KML.
        """
        # Expressão regular atualizada para validar URLs de forma mais abrangente.
        padrao_url = re.compile(
            r'^(https?:\/\/)?'  # http:// ou https://
            r'((([a-z\d]([a-z\d-]*[a-z\d])*)\.)+[a-z]{2,}|'  # domínio
            r'((\d{1,3}\.){3}\d{1,3}))'  # ou ip
            r'(\:\d+)?(\/[-a-z\d%_.~+]*)*'  # porta e caminho
            r'(\?[;&a-z\d%_.~+=-]*)?'  # query string
            r'(\#[-a-z\d_]*)?$', re.IGNORECASE)  # fragmento
        return re.match(padrao_url, url) is not None

    def colarTexto(self):
        """
        Obtém o texto do clipboard e insere no campo QLineEdit destinado ao URL da imagem, 
        se o texto for uma URL válida.

        Funcionalidades:
        - Acessa o conteúdo do clipboard do sistema.
        - Verifica se o texto é uma URL válida.
        - Insere a URL válida no campo de texto se for válida.

        Utilização:
        - Usado para facilitar a inserção de URLs por meio do uso de clipboard, evitando a necessidade de digitação manual, 
          aumentando a eficiência do usuário e reduzindo a chance de erro de entrada.
        """
        # Acessa o clipboard do sistema
        clipboard = QGuiApplication.clipboard() # Obtém o objeto clipboard do sistema
        texto = clipboard.text() # Lê o texto atualmente armazenado no clipboard
        
        # Verifica se o texto copiado é uma URL válida
        if self.verificarValidadeURL(texto): # Chama o método para verificar a validade da URL
            self.lineEditImageUrl.setText(texto) # Insere o texto no QLineEdit se for uma URL válida

    def colarTexto2(self):
        """
        Obtém o texto do clipboard e insere no campo QLineEdit destinado ao URL para ScreenOverlay,
        se o texto for uma URL válida.

        Funcionalidades:
        - Acessa o conteúdo do clipboard do sistema.
        - Verifica se o texto é uma URL válida.
        - Insere a URL válida no campo de texto destinado ao ScreenOverlay se for válida.

        Utilização:
        - Usado para facilitar a inserção de URLs de ScreenOverlay por meio do uso de clipboard, 
          evitando a necessidade de digitação manual e melhorando a eficiência do usuário.
        """
        # Acessa o clipboard do sistema
        clipboard = QGuiApplication.clipboard() # Obtém o objeto clipboard do sistema
        texto = clipboard.text() # Lê o texto atualmente armazenado no clipboard

        # Verifica se o texto copiado é uma URL válida
        if self.verificarValidadeURL(texto): # Chama o método para verificar a validade da URL
            self.lineEditImageUrl2.setText(texto) # Insere o texto no QLineEdit destinado ao ScreenOverlay se for uma URL válida

    def verificarValidadeURLImagem(self, url):
        """
        Verifica se a URL fornecida termina com uma extensão de arquivo de imagem aceitável. 
        Este método é usado para garantir que URLs inseridas para imagens sejam de formatos compatíveis para visualização.

        Parâmetros:
        - url (str): A URL da imagem a ser validada.

        Funcionalidades:
        - Define uma lista de extensões de arquivo de imagem que são aceitáveis.
        - Verifica se a URL fornecida termina com uma dessas extensões.

        Retorno:
        - Retorna True se a URL terminar com uma extensão de arquivo de imagem válida, False caso contrário.

        Utilização:
        - Utilizada para validar URLs de imagens, assegurando que os links fornecidos apontem para arquivos de imagem reais que podem ser carregados e exibidos corretamente no KML.
        """
        # Define as extensões de arquivo de imagem que são aceitáveis
        extensoes_validas = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp']
        # Verifica se a URL termina com alguma das extensões válidas
        return any(url.lower().endswith(ext) for ext in extensoes_validas) # Verifica se a URL corresponde a uma extensão válida

    def verificarTexto(self):
        """
        Verifica o conteúdo do campo de entrada para URL da imagem, ajusta a cor do texto baseada na validade da URL
        e atualiza o último texto de URL válido armazenado. Este método é usado para fornecer feedback visual imediato 
        sobre a validade da URL inserida.

        Funcionalidades:
        - Obtém o texto atual do campo QLineEdit destinado à URL da imagem.
        - Verifica se o texto é uma URL válida e se corresponde a uma extensão de arquivo de imagem aceitável.
        - Atualiza o armazenamento do último texto válido ou o limpa se o texto atual não for válido.
        - Altera a cor do texto do QLineEdit para azul se a URL for válida, para vermelho se for inválida, e retorna para a cor padrão se o campo estiver vazio.

        Utilização:
        - Essencial para fornecer uma resposta visual instantânea ao usuário sobre a validade da URL inserida, 
          facilitando a correção de erros e garantindo que apenas URLs válidas sejam utilizadas.
        """
        # Obtém o texto atual do QLineEdit
        texto = self.lineEditImageUrl.text() # Lê o texto da caixa de entrada de URL da imagem
        
        # Verifica a validade da URL e se a URL é uma imagem
        if self.verificarValidadeURL(texto) and self.verificarValidadeURLImagem(texto):
            IconFieldSelectionDialog.ultimoTextoUrl = texto # Atualiza o último texto válido se a URL for válida
            self.lineEditImageUrl.setStyleSheet("QLineEdit { color: blue; }") # Muda a cor do texto para azul
        else:
            IconFieldSelectionDialog.ultimoTextoUrl = "" # Limpa o último texto válido se a URL for inválida
            if texto.strip() != "": # Verifica se o campo não está vazio
                self.lineEditImageUrl.setStyleSheet("QLineEdit { color: red; }") # Muda a cor do texto para vermelho se houver texto inválido
            else:
                self.lineEditImageUrl.setStyleSheet("") # Retorna a cor do texto para o padrão se o campo estiver vazio

    def verificarTexto2(self):
        """
        Verifica o conteúdo do campo de entrada para o URL do ScreenOverlay, ajusta a cor do texto baseada na validade da URL,
        e atualiza o último texto de URL válido armazenado. Este método é usado para fornecer feedback visual imediato 
        sobre a validade da URL inserida.

        Funcionalidades:
        - Obtém o texto atual do campo QLineEdit destinado ao URL do ScreenOverlay.
        - Verifica se o texto é uma URL válida e se corresponde a uma extensão de arquivo de imagem aceitável.
        - Atualiza o armazenamento do último texto válido ou o limpa se o texto atual não for válido.
        - Altera a cor do texto do QLineEdit para azul se a URL for válida, para vermelho se for inválida, e retorna para a cor padrão se o campo estiver vazio.

        Utilização:
        - Essencial para fornecer uma resposta visual instantânea ao usuário sobre a validade da URL inserida para o ScreenOverlay,
          facilitando a correção de erros e garantindo que apenas URLs válidas sejam utilizadas para o ScreenOverlay.
        """
        # Obtém o texto atual do QLineEdit destinado ao URL do ScreenOverlay
        texto = self.lineEditImageUrl2.text()  # Lê o texto da caixa de entrada de URL para o ScreenOverlay

        # Verifica a validade da URL e se a URL é uma imagem
        if self.verificarValidadeURL(texto) and self.verificarValidadeURLImagem(texto):
            IconFieldSelectionDialog.ultimoTextoUrl2 = texto # Atualiza o último texto válido se a URL for válida
            self.lineEditImageUrl2.setStyleSheet("QLineEdit { color: blue; }") # Muda a cor do texto para azul
        else:
            IconFieldSelectionDialog.ultimoTextoUrl2 = "" # Limpa o último texto válido se a URL for inválida
            if texto.strip() != "": # Verifica se o campo não está vazio
                self.lineEditImageUrl2.setStyleSheet("QLineEdit { color: red; }") # Muda a cor do texto para vermelho se houver texto inválido
            else:
                self.lineEditImageUrl2.setStyleSheet("") # Retorna a cor do texto para o padrão se o campo estiver vazio

    def toggle_icon_selection(self, item):
        """
        Alterna a seleção de um ícone na lista de ícones. Se o ícone já estiver selecionado,
        ele será desmarcado. Caso contrário, ele será selecionado.

        Ações executadas pela função:
        1. Verifica se o item clicado é o mesmo que o item anteriormente selecionado.
        2. Se for o mesmo item, desmarca-o, limpa a URL do ícone selecionado e
           reseta a referência ao item anteriormente selecionado.
        3. Se for um item diferente, seleciona o novo item, atualiza a URL do ícone
           selecionado e a referência ao item anteriormente selecionado.
        4. Valida o estado do botão OK após a alteração na seleção.

        Parâmetros:
        - item: O item clicado na lista de ícones.
        """
        # Verifique se o item clicado já está selecionado
        if self.previous_selected_item == item:
            # Se for o mesmo item que o anteriormente selecionado, deselecione-o
            self.list_widget.clearSelection() # Limpa a seleção na lista de ícones
            self.selected_icon_url = None # Reseta a URL do ícone selecionado
            self.previous_selected_item = None  # Limpa o item anteriormente selecionado
        else:
            # Se for um item diferente, selecione-o e atualize o item anteriormente selecionado
            self.list_widget.setCurrentItem(item)  # Define o item atual na lista de ícones
            self.selected_icon_url = item.data(Qt.UserRole) # Obtém a URL do ícone selecionado
            self.previous_selected_item = item  # Atualiza o item anteriormente selecionado

        # Após a alteração na seleção, valide o estado do botão OK
        self.validate_ok_button_state()

    def validate_ok_button_state(self):
        """
        Valida o estado do botão OK no diálogo.

        Ações executadas pela função:
        1. Verifica se algum ícone está selecionado na lista de ícones.
        2. Verifica se o checkbox está marcado.
        3. Verifica se o ComboBox não está vazio.
        4. Habilita o botão OK apenas se:
           - Algum ícone estiver selecionado OU o checkbox estiver marcado,
           E
           - O ComboBox não estiver vazio.

        Linhas de código explicadas:
        """
        # Verifica se algum ícone está selecionado
        has_icon_selected = any(item.isSelected() for item in self.list_widget.selectedItems())
        # Verifica se o checkbox está marcado
        is_checkbox_checked = self.check_box.isChecked()
        # Verifica se o QComboBox não está vazio
        is_combobox_not_empty = self.combo_box.count() > 0

        # O botão "OK" só será habilitado se houver ícones selecionados OU o checkbox estiver marcado,
        # E o QComboBox não estiver vazio.
        self.button_ok.setEnabled((is_checkbox_checked or has_icon_selected) and is_combobox_not_empty)

    def setup_icon_list(self):
        """
        Configura a lista de ícones no diálogo.

        Ações executadas pela função:
        1. Define uma lista de URLs de ícones a serem baixados.
        2. Itera sobre cada URL na lista.
        3. Chama a função `download_icon` para cada URL para baixar e exibir o ícone na lista de ícones (`QListWidget`).

        Linhas de código explicadas:
        """
        # Define uma lista de URLs de ícones a serem baixados
        icon_urls = [
            "http://maps.google.com/mapfiles/kml/shapes/triangle.png",
            "http://maps.google.com/mapfiles/kml/shapes/parks.png",
            "http://maps.google.com/mapfiles/kml/shapes/campground.png",
            "http://maps.google.com/mapfiles/kml/shapes/info-i.png",
            "http://maps.google.com/mapfiles/kml/shapes/square.png",
            "http://maps.google.com/mapfiles/kml/shapes/placemark_square.png",
            "http://maps.google.com/mapfiles/kml/shapes/man.png",
            "http://maps.google.com/mapfiles/kml/shapes/arrow.png",
            "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
            "http://maps.google.com/mapfiles/kml/paddle/wht-circle.png",
            "http://maps.google.com/mapfiles/kml/paddle/wht-diamond.png",
            "http://maps.google.com/mapfiles/kml/paddle/wht-square.png",
            "http://maps.google.com/mapfiles/kml/paddle/wht-stars.png",
            "http://maps.google.com/mapfiles/kml/shapes/cabs.png",
            "http://maps.google.com/mapfiles/kml/shapes/airports.png",
            "http://maps.google.com/mapfiles/kml/shapes/caution.png",
            "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png",
            "http://maps.google.com/mapfiles/kml/shapes/flag.png",
            "http://maps.google.com/mapfiles/kml/pal5/icon13.png",
            "http://mw1.google.com/mw-ocean/ocean/media/swc/en/icons/swc.png",
            "http://maps.google.com/mapfiles/kml/shapes/picnic.png",
            "http://maps.google.com/mapfiles/kml/shapes/church.png",
        ]
        for url in icon_urls:
            # Chama a função download_icon para baixar e exibir o ícone na lista de ícones
            self.download_icon(url)

    def download_icon(self, url):
        """
        Baixa um ícone a partir de uma URL e o adiciona à lista de ícones.

        Ações executadas pela função:
        1. Verifica se a URL do ícone já está no cache.
        2. Se estiver no cache, usa o ícone armazenado.
        3. Se não estiver no cache, faz uma requisição de rede para baixar o ícone.
        4. Conecta o sinal de término do download a uma função que processa o ícone baixado.

        Linhas de código explicadas:
        """
        if url in IconFieldSelectionDialog.icon_cache:
            # Se o ícone já estiver no cache, use-o
            self.add_icon_to_list(url, IconFieldSelectionDialog.icon_cache[url])
        else:
            # Se não estiver no cache, baixe-o
            req = QNetworkRequest(QUrl(url)) # Cria uma requisição de rede com a URL do ícone
            reply = self.network_manager.get(req) # Envia a requisição e obtém a resposta
            # Conecta o sinal finished à função lambda que chama on_download_finished
            reply.finished.connect(lambda: self.on_download_finished(reply))

    def on_download_finished(self, reply):
        """
        Processa a resposta do download de um ícone.

        Ações executadas pela função:
        1. Verifica se houve erro na resposta.
        2. Se houver erro, limpa a resposta e retorna.
        3. Obtém a URL da resposta.
        4. Carrega os dados da resposta em um QPixmap.
        5. Armazena o ícone no cache.
        6. Adiciona o ícone à lista de ícones.
        7. Limpa a resposta.

        Linhas de código explicadas:
        """
        if reply.error():
            reply.deleteLater()  # Limpa a resposta se houver erro
            return

        url = reply.url().toString()  # Obtém a URL da resposta
        pixmap = QPixmap()
        if pixmap.loadFromData(reply.readAll()):  # Carrega os dados da resposta em um QPixmap
            IconFieldSelectionDialog.icon_cache[url] = pixmap  # Armazena o ícone no cache
            self.add_icon_to_list(url, pixmap)  # Adiciona o ícone à lista de ícones
        reply.deleteLater()  # Limpa a resposta

    def add_icon_to_list(self, url, pixmap):
        """
        Adiciona um ícone à lista de ícones no QListWidget.

        Ações executadas pela função:
        1. Cria um objeto QIcon a partir do QPixmap fornecido.
        2. Cria um item de QListWidget sem texto.
        3. Define o ícone do item de lista para o QIcon criado.
        4. Armazena a URL do ícone no item de lista usando Qt.UserRole.
        5. Adiciona o item de lista ao QListWidget.

        Linhas de código explicadas:
        """
        icon = QIcon(pixmap)  # Cria um objeto QIcon a partir do QPixmap fornecido
        item = QListWidgetItem()  # Cria um item de lista sem texto
        item.setIcon(icon)  # Define o ícone do item
        item.setData(Qt.UserRole, url)  # Armazena a URL do ícone no item de lista usando Qt.UserRole
        self.list_widget.addItem(item)  # Adiciona o item de lista ao QListWidget

    def accept(self):
        """
        Aceita o diálogo e salva as seleções feitas pelo usuário.

        Ações executadas pela função:
        1. Obtém o campo selecionado no QComboBox e armazena em self.selected_field.
        2. Obtém o item atualmente selecionado no QListWidget.
        3. Se um item estiver selecionado, obtém a URL do ícone associada e armazena em self.selected_icon_url.
        4. Chama o método accept da classe base QDialog para fechar o diálogo.

        Linhas de código explicadas:
        """
        self.selected_field = self.combo_box.currentText()  # Obtém o campo selecionado no QComboBox e armazena em self.selected_field
        current_item = self.list_widget.currentItem()  # Obtém o item atualmente selecionado no QListWidget
        if current_item:
            self.selected_icon_url = current_item.data(Qt.UserRole)  # Se um item estiver selecionado, obtém a URL do ícone associada e armazena em self.selected_icon_url
        self.selected_image_url = self.lineEditImageUrl.text()  # Captura o texto (URL) inserido no lineEditImageUrl
        self.selected_image_url2 = self.lineEditImageUrl2.text() # Captura o texto (URL) inserido no lineEditImageUr2
        super(IconFieldSelectionDialog, self).accept()  # Chama o método accept da classe base QDialog para fechar o diálogo

    def get_selections(self):
        """
        Retorna as seleções feitas pelo usuário.

        Ações executadas pela função:
        1. Retorna o campo selecionado no QComboBox e a URL do ícone selecionado.

        Retornos:
        - Uma tupla contendo o campo selecionado (self.selected_field) e a URL do ícone selecionado (self.selected_icon_url).
        """
        # Retorna o campo selecionado, a URL do ícone e o URL da imagem
        return self.selected_field, self.selected_icon_url, self.selected_image_url, self.selected_image_url2

class CircleDelegate(QStyledItemDelegate):
    """
    Delegate para desenhar um círculo colorido ao lado de cada item em uma lista de itens.
    
    Ações executadas pela função:
    1. Desenha um círculo colorido ao lado do item, com cor e borda configuráveis.
    2. Ajusta a posição do texto do item para não sobrepor o círculo.
    3. Busca a camada no projeto do QGIS usando o ID e tenta obter as cores do símbolo da camada.
    """
    def paint(self, painter, option, index):
        """
        Sobrescreve o método paint para desenhar um círculo ao lado do item.
        
        Parâmetros:
        - painter (QPainter): O objeto de pintura usado para desenhar o item.
        - option (QStyleOptionViewItem): Opções de estilo para o item.
        - index (QModelIndex): Índice do item no modelo.
        """
        super().paint(painter, option, index)

        # Obtém o ID da camada do item do modelo
        layer_id = index.data(Qt.UserRole)
        if not layer_id:
            layer_id = index.model().itemFromIndex(index).data()

        # Busca a camada no projeto do QGIS usando o ID
        layer = QgsProject.instance().mapLayer(layer_id)

        # Define as cores padrão para o círculo e a borda
        circle_color = Qt.white
        border_color = Qt.black
        border_width = 2  # Definindo a espessura da borda

        # Tenta obter as cores do símbolo da camada, se disponível
        if layer:
            symbols = layer.renderer().symbols(QgsRenderContext())
            if symbols:
                circle_color = symbols[0].color()
                # Verifica se existe um contorno e obtém a cor do contorno
                if symbols[0].symbolLayerCount() > 0:
                    border_layer = symbols[0].symbolLayer(0)
                    if hasattr(border_layer, 'strokeColor'):
                        border_color = border_layer.strokeColor()
 
        # Calcula a posição e o tamanho do círculo
        offset = -15
        radius = 6
        # Assegurando que os valores passados para QRect sejam inteiros
        x = int(option.rect.left() + offset)
        y = int(option.rect.top() + (option.rect.height() - radius * 2) / 2)
        diameter = int(radius * 2)
        circleRect = QRect(x, y, diameter, diameter) # Retângulo que define o círculo

        painter.setBrush(QBrush(circle_color)) # Define a cor de preenchimento e a borda para o círculo
        painter.setPen(QPen(border_color, border_width))  # Configurando a cor e a espessura da borda
        painter.drawEllipse(circleRect) # Desenha o círculo

        # Ajusta a posição do texto no item para não sobrepor o círculo
        option.rect.setLeft(option.rect.left() + offset + radius*2 + 8)
