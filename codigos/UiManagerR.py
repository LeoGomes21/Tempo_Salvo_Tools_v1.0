from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes, Qgis, QgsVectorLayerSimpleLabeling,  QgsCoordinateReferenceSystem, QgsCoordinateTransform,  QgsLayerTreeLayer, QgsSingleBandPseudoColorRenderer, QgsRasterFileWriter, QgsRectangle, QgsRasterLayer, QgsMapSettings, QgsRasterPipe, QgsLayout, QgsLayoutItemLegend, QgsLayoutSize, QgsLayerTreeGroup, QgsUnitTypes, QgsLegendRenderer, QgsLayerTree, QgsVectorLayer, QgsRaster, QgsApplication
from PyQt5.QtWidgets import QInputDialog, QTreeView, QStyledItemDelegate, QMenu, QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QFileDialog, QStyle, QStyleOptionViewItem, QMessageBox, QProgressBar
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap, QPainter, QColor, QPen, QFont, QPainterPath, QImage
from PyQt5.QtCore import Qt, QRect, QEvent, QCoreApplication, QSettings, QSize, QRectF
import xml.etree.ElementTree as ET
import pyqtgraph.opengl as gl
from qgis.utils import iface
from ezdxf import colors
from osgeo import gdal
import numpy as np
import qgis.utils
import simplekml
import tempfile
import zipfile
import random
import ezdxf
import time
import math
import os

class UiManagerR:
    """
    Gerencia a interface do usuário, interagindo com um QTreeView para listar e gerenciar camadas de rasters no QGIS.
    """
    def __init__(self, iface, dialog):
        """
        Inicializa a instância da classe UiManagerO, responsável por gerenciar a interface do usuário
        que interage com um QTreeView para listar e gerenciar camadas de rasters no QGIS.

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
        self.dlg.treeViewListaRaster.setModel(self.treeViewModel)

        # Inicializa o QTreeView com as configurações necessárias
        self.init_treeView()

        # Conecta os sinais do QGIS e da interface do usuário para sincronizar ações e eventos
        self.connect_signals()

    def init_treeView(self):
        """
        Configura o QTreeView para listar e gerenciar camadas de rasters. 
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
        self.atualizar_treeView_lista_raster()

        # Conecta o evento de mudança em um item para atualizar a visibilidade da camada
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Define e aplica um delegado personalizado para customização da exibição de itens no QTreeView
        self.dlg.treeViewListaRaster.setItemDelegate(CustomDelegate(self.dlg.treeViewListaRaster))

        # Configura a política de menu de contexto para permitir menus personalizados em cliques com o botão direito
        self.dlg.treeViewListaRaster.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dlg.treeViewListaRaster.customContextMenuRequested.connect(self.open_context_menu)

        # Aplica estilos CSS para aprimorar a interação visual com os itens do QTreeView
        self.dlg.treeViewListaRaster.setStyleSheet("""
            QTreeView::item:hover:!selected {
                background-color: #def2fc;
            }
            QTreeView::item:selected {
            }""")

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
        QgsProject.instance().layersRemoved.connect(self.atualizar_treeView_lista_raster)

        # Conecta o evento de mudança em um item do QTreeView para atualizar a visibilidade da camada no QGIS
        self.treeViewModel.itemChanged.connect(self.on_item_changed)

        # Sincroniza o estado das camadas no QGIS com o checkbox do QTreeView sempre que as camadas do mapa mudam
        self.iface.mapCanvas().layersChanged.connect(self.sync_from_qgis_to_treeview)

        # Conecta mudanças na seleção do QTreeView para atualizar a camada ativa no QGIS
        self.dlg.treeViewListaRaster.selectionModel().selectionChanged.connect(self.on_treeview_selection_changed)

        # Sincroniza a seleção no QGIS com a seleção no QTreeView quando a camada ativa no QGIS muda
        self.iface.currentLayerChanged.connect(self.on_current_layer_changed)

        # Inicia a conexão de sinais para tratar a mudança de nome das camadas no projeto
        self.connect_name_changed_signals()

        # Conecte o botão pushButtonRasterKML à função export_raster_to_kml
        self.dlg.pushButtonRasterKML.clicked.connect(self.export_raster_to_kml)

        # Conecte o botão pushButtonRasterDXF à função export_raster_to_dxf
        self.dlg.pushButtonRasterDXF.clicked.connect(self.exportar_raster_dxf)

        # Conectando o botão pushButtonFecharR à função que fecha o diálogo
        self.dlg.pushButtonFecharR.clicked.connect(self.close_dialog)

        # Conecta para abrir o Qgis2threejs 
        self.dlg.pushButton3DRaster.clicked.connect(self.abrir_qgis2threejs)

    def close_dialog(self):
        """
        Fecha o diálogo associado a este UiManagerR:
        """
        self.dlg.close()

    def on_treeview_selection_changed(self, selected, deselected):
        """
        Esta função é chamada quando a seleção no QTreeView muda. 
        Ela obtém o índice do item selecionado, extrai o nome da camada, 
        encontra a camada correspondente no projeto QGIS e define essa camada como ativa.

        Detalhes:
        - Obtém os índices dos itens selecionados no QTreeView.
        - Se houver itens selecionados:
            - Extrai o nome da camada do item selecionado.
            - Busca a camada no projeto QGIS pelo nome.
            - Se a camada for encontrada, define-a como a camada ativa no QGIS.
        """
        # Obtém os índices dos itens selecionados no QTreeView
        indexes = self.dlg.treeViewListaRaster.selectionModel().selectedIndexes()
        
        # Verifica se há algum índice selecionado
        if indexes:
            # Extrai o nome da camada do item selecionado no QTreeView
            selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
            
            # Busca a camada por nome no projeto do QGIS
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            
            # Se a camada existir, define-a como a camada ativa
            if layers:
                self.iface.setActiveLayer(layers[0])

    def atualizar_treeView_lista_raster(self):
        """
        Esta função atualiza a lista de camadas raster no QTreeView. 
        Ela limpa o modelo existente, adiciona um cabeçalho, 
        itera sobre todas as camadas no projeto do QGIS, filtra as camadas raster,
        cria itens para essas camadas e ajusta a fonte dos itens conforme necessário.
        Por fim, garante que a última camada esteja selecionada no QTreeView.

        Detalhes:
        - Limpa o modelo do QTreeView.
        - Adiciona um item de cabeçalho ao modelo.
        - Obtém a raiz da árvore de camadas do QGIS e todas as camadas do projeto.
        - Itera sobre todas as camadas do projeto.
            - Filtra para incluir apenas camadas raster.
            - Cria um item para cada camada raster com nome, verificável e não editável diretamente.
            - Define o estado de visibilidade do item com base no estado do nó da camada.
            - Ajusta a fonte do item com base no tipo de camada (temporária ou permanente).
            - Adiciona o item ao modelo do QTreeView.
        - Seleciona a última camada no QTreeView.
        """
        # Limpa o modelo existente para assegurar que não haja itens desatualizados
        self.treeViewModel.clear()
        
        # Cria e configura um item de cabeçalho para a lista
        headerItem = QStandardItem('Lista de Camadas de Rasters')
        headerItem.setTextAlignment(Qt.AlignCenter)
        self.treeViewModel.setHorizontalHeaderItem(0, headerItem)

        # Acessa a raiz da árvore de camadas do QGIS para obter todas as camadas
        root = QgsProject.instance().layerTreeRoot()
        layers = QgsProject.instance().mapLayers().values()

        # Itera sobre todas as camadas do projeto
        for layer in layers:
            # Filtra para incluir apenas camadas raster
            if layer.type() == QgsMapLayer.RasterLayer:
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
        Esta função garante que uma camada raster esteja sempre selecionada no QTreeView.
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
        model = self.dlg.treeViewListaRaster.model()
        
        # Conta o número de linhas (camadas) no modelo
        row_count = model.rowCount()

        # Verifica se há camadas no modelo
        if row_count > 0:
            # Obtém o índice da última camada no modelo
            last_index = model.index(row_count - 1, 0)
            
            # Define a seleção atual para o índice da última camada
            self.dlg.treeViewListaRaster.setCurrentIndex(last_index)
            
            # Garante que a última camada esteja visível no QTreeView
            self.dlg.treeViewListaRaster.scrollTo(last_index)
        else:
            # Obtém o índice da primeira camada no modelo
            first_index = model.index(0, 0)
            
            # Verifica se o índice da primeira camada é válido
            if first_index.isValid():
                # Define a seleção atual para o índice da primeira camada
                self.dlg.treeViewListaRaster.setCurrentIndex(first_index)
                
                # Garante que a primeira camada esteja visível no QTreeView
                self.dlg.treeViewListaRaster.scrollTo(first_index)

    def on_current_layer_changed(self, layer):
        """
        Esta função é chamada quando a camada ativa no QGIS muda.
        Ela verifica se a camada ativa é uma camada raster e, se for, 
        atualiza a seleção no QTreeView para corresponder à camada ativa.
        Se a camada ativa não for uma camada raster, reverte a seleção 
        para a última camada raster selecionada no QTreeView.

        Detalhes:
        - Verifica se a camada ativa existe e se é uma camada raster.
        - Se for uma camada raster:
            - Obtém o modelo associado ao QTreeView.
            - Itera sobre todas as linhas no modelo para encontrar a camada correspondente.
            - Quando encontrada, seleciona e garante que a camada esteja visível no QTreeView.
        - Se a camada ativa não for uma camada raster, seleciona a última camada raster no QTreeView.
        """
        # Verifica se a camada ativa existe e se é uma camada raster
        if layer and layer.type() == QgsMapLayer.RasterLayer:
            # Obtém o modelo associado ao QTreeView
            model = self.dlg.treeViewListaRaster.model()
            
            # Itera sobre todas as linhas no modelo
            for row in range(model.rowCount()):
                # Obtém o item da linha atual
                item = model.item(row, 0)
                
                # Verifica se o nome do item corresponde ao nome da camada ativa
                if item.text() == layer.name():
                    # Obtém o índice do item correspondente
                    index = model.indexFromItem(item)
                    
                    # Define a seleção atual para o índice do item correspondente
                    self.dlg.treeViewListaRaster.setCurrentIndex(index)
                    
                    # Garante que o item correspondente esteja visível no QTreeView
                    self.dlg.treeViewListaRaster.scrollTo(index)
                    
                    # Interrompe a iteração, pois a camada correspondente foi encontrada
                    break
        else:
            # Se a camada ativa não for uma camada raster, seleciona a última camada raster no QTreeView
            self.selecionar_ultima_camada()

    def adjust_item_font(self, item, layer):
        """
        Esta função ajusta a fonte do item no QTreeView com base no tipo de camada.
        Se a camada for temporária (dados em memória), ajusta a fonte para itálico.
        Se a camada for permanente, ajusta a fonte para negrito.

        Detalhes:
        - Cria um objeto QFont para ajustar a fonte do item.
        - Verifica se a camada é temporária usando o método isTemporary().
        - Se a camada for temporária, ajusta a fonte para itálico.
        - Se a camada for permanente, ajusta a fonte para negrito.
        - Aplica a fonte ajustada ao item no QTreeView.
        - Retorna o item com a fonte ajustada para uso posterior, se necessário.
        """
        # Cria um objeto QFont para ajustar a fonte do item
        fonte_item = QFont()

        # Verifica se a camada é temporária (dados em memória) e ajusta a fonte para itálico
        if layer.isTemporary():
            fonte_item.setItalic(True)
        # Se não for temporária, ajusta a fonte para negrito, indicando uma camada permanente
        else:
            fonte_item.setBold(True)

        # Aplica a fonte ajustada ao item no QTreeView
        item.setFont(fonte_item)

        # Retorna o item com a fonte ajustada para uso posterior se necessário
        return item

    def connect_name_changed_signals(self):
        """
        Conecta o sinal de mudança de nome de todas as camadas de raster existentes no projeto QGIS.
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
        e conectando sinais de mudança de nome para camadas de rasters recém-adicionadas.

        Este método verifica cada camada adicionada para determinar se é uma camada de vetor de rasters.
        Se for, ele atualiza a lista de camadas no QTreeView e conecta o sinal de mudança de nome à função
        de callback apropriada.

        :param layers: Lista de camadas recém-adicionadas ao projeto.

        Funções e Ações Desenvolvidas:
        - Verificação do tipo e da geometria das camadas adicionadas.
        - Atualização da visualização da lista de camadas no QTreeView para incluir novas camadas de rasters.
        - Conexão do sinal de mudança de nome da camada ao método de tratamento correspondente.
        """
        # Itera por todas as camadas adicionadas
        for layer in layers:
            # Verifica se a camada é do tipo vetor e se sua geometria é de raster
            if layer.type() == QgsMapLayer.RasterLayer:
                # Atualiza a lista de camadas no QTreeView
                self.atualizar_treeView_lista_raster()
                # Conecta o sinal de mudança de nome da nova camada ao método on_layer_name_changed
                layer.nameChanged.connect(self.on_layer_name_changed)
                # Interrompe o loop após adicionar o sinal à primeira camada de raster encontrada
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
        self.atualizar_treeView_lista_raster()

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

    def open_context_menu(self, position):
        """
        Esta função abre um menu de contexto ao clicar com o botão direito na árvore de visualização (QTreeView).
        Se um item for selecionado, cria e exibe um menu de contexto com a opção de abrir as propriedades da camada.
        
        Detalhes:
        - Obtém os índices dos itens selecionados no QTreeView.
        - Verifica se há algum item selecionado.
        - Se houver um item selecionado:
            - Cria um novo menu de contexto.
            - Adiciona a opção "Abrir Propriedades da Camada" ao menu de contexto.
            - Exibe o menu de contexto na posição do cursor.
            - Executa a ação correspondente se a opção "Abrir Propriedades da Camada" for selecionada.
        """
        # Obtém os índices dos itens selecionados na árvore de visualização
        indexes = self.dlg.treeViewListaRaster.selectedIndexes()
        
        # Verifica se algum item foi selecionado
        if indexes:
            # Cria um novo menu de contexto
            menu = QMenu()
            
            # Adiciona uma ação ao menu de contexto
            layer_properties_action = menu.addAction("Abrir Propriedades da Camada")
            
            # Exibe o menu de contexto na posição do cursor e obtém a ação selecionada pelo usuário
            action = menu.exec_(self.dlg.treeViewListaRaster.viewport().mapToGlobal(position))
            
            # Verifica se a ação selecionada foi "Abrir Propriedades da Camada"
            if action == layer_properties_action:
                # Abre as propriedades da camada para o item selecionado
                self.abrir_layer_properties(indexes[0])

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
            if caminho_arquivo:
                botao_executar = QPushButton("Executar")
                botao_executar.clicked.connect(lambda: os.startfile(caminho_arquivo))
                msg.layout().insertWidget(2, botao_executar)  # Adiciona o botão à esquerda do texto
            
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
        progressMessageBar = self.iface.messageBar().createMessage("Exportando camada para KML")
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

    def export_raster_to_kml(self):
        """
        Exporta uma camada raster selecionada para o formato KMZ (KML + Imagens).

        Passos detalhados:
        1. Captura o tempo de início do processo.
        2. Verifica se uma camada raster está selecionada na treeView.
        3. Obtém o nome da camada selecionada e verifica se a camada existe no projeto.
        4. Inicia a barra de progresso para monitorar o processo de exportação.
        5. Reprojeta a camada raster e exporta as imagens necessárias.
        6. Cria o arquivo KML usando as imagens exportadas.
        7. Escolhe o local para salvar o arquivo KMZ.
        8. Cria o arquivo KMZ (ZIP) contendo o KML e as imagens.
        9. Atualiza a barra de progresso e limpa a barra de mensagem.
        10. Exibe uma mensagem informando o sucesso da exportação e o tempo de execução.

        Retorna:
        - None
        """
        start_time = time.time()  # Capturar o tempo de início

        # Verificar se alguma camada está selecionada na treeView
        indexes = self.dlg.treeViewListaRaster.selectedIndexes()
        if not indexes:
            self.mostrar_mensagem("Nenhuma camada selecionada", "Erro")
            return

        # Obter o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        # Obter a camada pelo nome
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)
        if not layers:
            self.mostrar_mensagem("Camada não encontrada", "Erro")
            return

        layer = layers[0]  # Obter a primeira camada encontrada

        # Iniciar a barra de progresso
        total_steps = 5  # Ajuste o número total de etapas conforme necessário
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)
        step = 0  # Inicializar o contador de etapas

        # Reprojetar a camada raster e exportar as imagens necessárias
        reprojected_layer, transformed_extent, output_image_path, legend_image_path = self.reproject_and_export_raster(layer, progressBar, step)
        if not reprojected_layer:
            return

        step += 2  # Atualizar o contador de etapas
        # Criar o arquivo KML usando as imagens exportadas
        kml_output_path = self.create_kml(reprojected_layer, transformed_extent, output_image_path, legend_image_path, progressBar, step)
        if not kml_output_path:
            return

        step += 2  # Atualizar o contador de etapas
        progressBar.setValue(step)  # Atualizar a barra de progresso

        end_time = time.time()  # Capturar o tempo de fim
        execution_time = end_time - start_time  # Calcular o tempo de execução

        # Escolher local para salvar o arquivo KMZ
        kmz_output_path = self.escolher_local_para_salvar(layer.name() + ".kmz", "Arquivos KMZ (*.kmz)")
        if not kmz_output_path:
            progressBar.reset()
            self.iface.messageBar().clearWidgets()
            
            return

        # Criar o arquivo KMZ (ZIP)
        with zipfile.ZipFile(kmz_output_path, 'w') as kmz:
            kmz.write(kml_output_path, os.path.basename(kml_output_path))
            kmz.write(output_image_path, os.path.basename(output_image_path))
            kmz.write(legend_image_path, os.path.basename(legend_image_path))

        step += 1  # Atualizar o contador de etapas
        progressBar.setValue(step)  # Atualizar a barra de progresso

        self.iface.messageBar().clearWidgets()  # Limpar a barra de mensagem

        # Exibir mensagem de sucesso com o tempo de execução e caminhos dos arquivos
        self.mostrar_mensagem(
            f"Camada exportada para KMZ em {execution_time:.2f} segundos", 
            "Sucesso", 
            caminho_pasta=os.path.dirname(kmz_output_path), 
            caminho_arquivo=kmz_output_path)

    def reproject_and_export_raster(self, layer, progressBar, step):
        """
        Reprojeta uma camada raster para WGS84 e exporta uma imagem PNG da camada e sua legenda.

        Passos detalhados:
        1. Verifica se a camada está em WGS84 (EPSG:4326).
        2. Se não estiver em WGS84, reprojeta a camada para WGS84.
        3. Cria um caminho temporário para salvar o raster reprojetado.
        4. Configura a transformação de coordenadas e transforma a extensão da camada.
        5. Usa o GDAL para reprojetar o raster.
        6. Cria uma nova camada raster a partir do arquivo reprojetado.
        7. Se a camada já estiver em WGS84, usa a camada original.
        8. Atualiza a barra de progresso.
        9. Cria um arquivo temporário para a imagem PNG.
        10. Exporta a imagem raster para PNG, aplicando a renderização configurada.
        11. Atualiza a barra de progresso.
        12. Cria a imagem da legenda da camada.
        13. Retorna a camada reprojetada, a extensão transformada, o caminho da imagem PNG e o caminho da imagem da legenda.

        Retorna:
        - reprojected_layer: Camada raster reprojetada para WGS84.
        - transformed_extent: Extensão transformada da camada.
        - output_image_path: Caminho do arquivo PNG exportado.
        - legend_image_path: Caminho do arquivo de imagem da legenda.
        """
        # Verificar se a camada está em WGS84 (EPSG:4326)
        wgs84_crs = QgsCoordinateReferenceSystem('EPSG:4326')
        if layer.crs() != wgs84_crs:
            # Criar um caminho temporário para o raster reprojetado
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_file:
                reprojected_raster_path = tmp_file.name

            try:
                # Configurar a transformação de coordenadas
                transform = QgsCoordinateTransform(layer.crs(), wgs84_crs, QgsProject.instance())
                extent = layer.extent()
                transformed_extent = transform.transformBoundingBox(extent, QgsCoordinateTransform.ForwardTransform)
                
                # Usar o GDAL para reprojetar o raster
                gdal.Warp(reprojected_raster_path, layer.source(), dstSRS='EPSG:4326')
                
                # Criar uma nova camada raster a partir do arquivo reprojetado
                reprojected_layer = QgsRasterLayer(reprojected_raster_path, layer.name() + '_wgs84')
                if not reprojected_layer.isValid():
                    self.mostrar_mensagem("Erro ao reprojetar a camada para WGS84", "Erro")
                    return None, None, None, None
            except Exception as e:
                self.mostrar_mensagem("Erro ao reprojetar a camada: " + str(e), "Erro")
                return None, None, None, None
        else:
            reprojected_layer = layer  # Usar a camada original se já estiver em WGS84
            transformed_extent = reprojected_layer.extent()  # Obter a extensão transformada

        # Atualizar a barra de progresso
        step += 1  # Incrementar o contador de etapas
        progressBar.setValue(step)  # Atualizar o valor da barra de progresso

        # Criar um arquivo temporário para a imagem PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_png_file:
            output_image_path = tmp_png_file.name  # Obter o caminho do arquivo PNG temporário

        # Exportar a imagem raster para PNG, aplicando a renderização configurada
        pipe = QgsRasterPipe()  # Criar um pipeline de raster
        pipe.set(layer.dataProvider().clone())  # Clonar o provedor de dados da camada
        pipe.set(layer.renderer().clone())  # Clonar o renderizador da camada

        file_writer = QgsRasterFileWriter(output_image_path)  # Criar um escritor de arquivos raster
        file_writer.writeRaster(
            pipe,  # Usar o pipeline de raster
            layer.width(),  # Largura da imagem
            layer.height(),  # Altura da imagem
            layer.extent(),  # Extensão da camada
            layer.crs()  # Sistema de referência de coordenadas da camada
        )

        # Atualizar a barra de progresso
        step += 1  # Incrementar o contador de etapas
        progressBar.setValue(step)  # Atualizar o valor da barra de progresso

        # Criar a imagem da legenda
        legend_image_path = self.gerar_legenda_como_imagem(layer)  # Gerar a imagem da legenda
        if not legend_image_path:
            self.mostrar_mensagem("Erro ao gerar a legenda da camada", "Erro")
            return None, None, None, None

        return reprojected_layer, transformed_extent, output_image_path, legend_image_path  # Retornar os resultados

    def create_kml(self, reprojected_layer, transformed_extent, output_image_path, legend_image_path, progressBar, step):
        """
        Cria um arquivo KML com a camada raster reprojetada e uma imagem de legenda.

        Passos detalhados:
        1. Obtém a extensão da camada transformada.
        2. Cria um arquivo KML temporário.
        3. Cria um KML com GroundOverlay para a imagem raster.
        4. Adiciona a legenda como ScreenOverlay no KML.
        5. Salva o arquivo KML.
        6. Atualiza a barra de progresso.
        7. Retorna o caminho do arquivo KML criado.

        Retorna:
        - kml_output_path: Caminho do arquivo KML criado.
        """
        # Obter a extensão da camada transformada
        bbox = [transformed_extent.xMinimum(), transformed_extent.yMinimum(), transformed_extent.xMaximum(), transformed_extent.yMaximum()]

        # Criar KML com GroundOverlay
        with tempfile.NamedTemporaryFile(suffix='.kml', delete=False) as tmp_kml_file:
            kml_output_path = tmp_kml_file.name  # Obter o caminho do arquivo KML temporário

        kml = simplekml.Kml()  # Criar um objeto KML
        ground = kml.newgroundoverlay(name=reprojected_layer.name())  # Criar um GroundOverlay no KML
        ground.icon.href = os.path.basename(output_image_path)  # Definir o ícone como a imagem raster exportada (apenas o nome do arquivo)
        ground.latlonbox.north = bbox[3]  # Definir o limite norte da extensão
        ground.latlonbox.south = bbox[1]  # Definir o limite sul da extensão
        ground.latlonbox.east = bbox[2]  # Definir o limite leste da extensão
        ground.latlonbox.west = bbox[0]  # Definir o limite oeste da extensão

        # Adicionar a legenda como ScreenOverlay
        screen = kml.newscreenoverlay(name="Legenda")  # Criar um ScreenOverlay no KML para a legenda
        screen.icon.href = os.path.basename(legend_image_path)  # Definir o ícone como a imagem da legenda (apenas o nome do arquivo)
        screen.overlayxy = simplekml.OverlayXY(x=0, y=0, xunits=simplekml.Units.fraction, yunits=simplekml.Units.fraction)  # Definir a posição do overlay
        screen.screenxy = simplekml.ScreenXY(x=0.01, y=0.05, xunits=simplekml.Units.fraction, yunits=simplekml.Units.fraction)  # Definir a posição na tela
        screen.size.x = 0.18  # Definir a largura do overlay
        screen.size.y = 0.18  # Definir a altura do overlay
        screen.size.xunits = simplekml.Units.fraction  # Definir a unidade de largura
        screen.size.yunits = simplekml.Units.fraction  # Definir a unidade de altura

        kml.save(kml_output_path)  # Salvar o arquivo KML

        # Atualizar a barra de progresso
        step += 2  # Incrementar o contador de etapas
        progressBar.setValue(step)  # Atualizar o valor da barra de progresso

        return kml_output_path  # Retornar o caminho do arquivo KML criado

    def gerar_legenda_como_imagem(self, layer, page_width=60, page_height=70):
        """
        Gera uma imagem de legenda para a camada raster especificada.

        Passos detalhados:
        1. Cria um layout temporário.
        2. Adiciona um item de legenda ao layout.
        3. Inclui apenas a camada raster especificada na legenda.
        4. Atualiza a legenda.
        5. Ajusta o tamanho da legenda.
        6. Calcula o tamanho da imagem com base no conteúdo da legenda.
        7. Renderiza a legenda em uma imagem.
        8. Salva a imagem temporária.
        9. Retorna o caminho da imagem da legenda.

        Retorna:
        - legend_image_path: Caminho do arquivo de imagem da legenda.
        """
        # Criar um layout temporário
        project = QgsProject.instance()
        layout = QgsLayout(project)
        layout.initializeDefaults()

        # Adicionar item de legenda ao layout
        legend = QgsLayoutItemLegend(layout)
        legend.setTitle("Legenda")
        legend.setLinkedMap(None)  # Sem mapa associado

        # Incluir apenas a camada raster especificada na legenda
        root = QgsLayerTree()
        root.addLayer(layer)
        legend.model().setRootGroup(root)

        legend.updateLegend()  # Atualizar a legenda

        # Ajustar tamanho da legenda
        layout.addLayoutItem(legend)
        legend.setMinimumSize(QgsLayoutSize(page_width, page_height, QgsUnitTypes.LayoutMillimeters))  # Tamanho configurável
        legend.attemptResize(QgsLayoutSize(page_width, page_height, QgsUnitTypes.LayoutMillimeters))  # Tamanho configurável

        # Calcular o tamanho da imagem com base no conteúdo da legenda
        legend_rect = legend.boundingRect()
        img_width = int(legend_rect.width() * 10)  # Ajustar fator de escala conforme necessário
        img_height = int(legend_rect.height() * 10)

        # Renderizar a legenda em uma imagem
        image = QImage(img_width, img_height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)  # Fundo transparente

        # Configurar o QPainter para renderizar a legenda na imagem
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        layout.render(painter, QRectF(0, 0, img_width, img_height), legend_rect)
        painter.end()

        # Salvar a imagem temporária
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_legend_file:
            legend_image_path = tmp_legend_file.name  # Obter o caminho do arquivo temporário
            image.save(legend_image_path, 'PNG')  # Salvar a imagem no arquivo temporário

        return legend_image_path  # Retornar o caminho da imagem da legenda

    def exportar_raster_dxf(self):
        """
        Exporta uma camada raster para o formato DXF. Dependendo do tipo da camada, 
        realiza uma exportação diferente:
        - Se a camada for um serviço de mapa (WMS/XYZ), exporta a visualização da área de trabalho.
        - Caso contrário, exporta a camada raster comum.

        Passos:
        1. Obtém a camada selecionada pelo usuário.
        2. Verifica se a camada é um serviço de mapa.
        3. Se for um serviço de mapa, exporta a visualização da área de trabalho.
        4. Se for uma camada raster comum, exporta a camada raster comum.

        """
        # Obtém os índices das camadas selecionadas na interface do usuário
        indexes = self.dlg.treeViewListaRaster.selectedIndexes()
        if not indexes:  # Verifica se alguma camada foi selecionada
            self.mostrar_mensagem("Nenhuma camada selecionada", "Erro")  # Mostra mensagem de erro
            return  # Encerra a função se nenhuma camada foi selecionada
        
        # Obtém o nome da camada selecionada
        selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
        
        # Obtém a camada pelo nome
        layers = QgsProject.instance().mapLayersByName(selected_layer_name)
        if not layers:  # Verifica se a camada foi encontrada
            self.mostrar_mensagem("Camada não encontrada", "Erro")  # Mostra mensagem de erro
            return  # Encerra a função se a camada não foi encontrada
        
        layer = layers[0]  # Obtém a primeira camada encontrada

        # Verificação para camadas de serviço de mapas
        if layer.providerType() in ['wms', 'xyz']:  # Verifica se a camada é um serviço de mapa (WMS/XYZ)
            self.exportar_visualizacao_para_dxf(layer)  # Exporta a visualização da área de trabalho
        else:  # Caso contrário
            self.exportar_raster_comum_para_dxf(layer)  # Exporta a camada raster comum

    def exportar_visualizacao_para_dxf(self, layer):
        """
        Exporta a visualização da área de trabalho do QGIS para o formato DXF.

        Passos:
        1. Inicia a barra de progresso.
        2. Captura a visualização do canvas do QGIS como uma imagem.
        3. Salva a imagem capturada como PNG.
        4. Solicita ao usuário o local para salvar o arquivo DXF.
        5. Cria um documento DXF e insere a imagem PNG.
        6. Salva o arquivo DXF.
        7. Atualiza a barra de progresso e mostra uma mensagem de sucesso.

        Parâmetros:
        - layer: A camada para a qual a visualização será exportada.
        """
        start_time = time.time()  # Inicia a contagem do tempo de execução
        total_steps = 5  # Define o número total de etapas para a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)  # Inicia a barra de progresso
        
        canvas = self.iface.mapCanvas()  # Obtém o canvas do QGIS
        rect = canvas.extent()  # Obtém a extensão da visualização
        width = canvas.size().width()  # Obtém a largura do canvas
        height = canvas.size().height()  # Obtém a altura do canvas
        image = QImage(width, height, QImage.Format_ARGB32)  # Cria uma imagem com as dimensões do canvas
        painter = QPainter(image)  # Cria um pintor para a imagem
        canvas.render(painter)  # Renderiza o canvas na imagem
        painter.end()  # Finaliza o pintor

        progressBar.setValue(1)  # Atualiza a barra de progresso

        # Salvar a imagem capturada
        temp_image_path = self.escolher_local_para_salvar("visualizacao_qgis.png", "Image Files (*.png)")  # Solicita o caminho para salvar a imagem
        if not temp_image_path:  # Verifica se o caminho foi fornecido
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se o caminho não foi fornecido
        if not image.save(temp_image_path):  # Salva a imagem como PNG
            self.mostrar_mensagem("Erro ao salvar a imagem capturada", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se ocorrer um erro

        progressBar.setValue(2)  # Atualiza a barra de progresso

        # Escolher local para salvar o arquivo DXF
        dxf_file_path = self.escolher_local_para_salvar("visualizacao_qgis.dxf", "DXF Files (*.dxf)")  # Solicita o caminho para salvar o DXF
        if not dxf_file_path:  # Verifica se o caminho foi fornecido
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se o caminho não foi fornecido

        progressBar.setValue(3)  # Atualiza a barra de progresso

        # Converter a imagem para DXF
        doc = ezdxf.new(dxfversion='R2013')  # Cria um novo documento DXF
        msp = doc.modelspace()  # Obtém o espaço do modelo
        image_def = doc.add_image_def(filename=os.path.abspath(temp_image_path), size_in_pixel=(width, height))  # Adiciona a definição da imagem
        insert_point = (rect.xMinimum(), rect.yMinimum())  # Define o ponto de inserção
        msp.add_image(insert=insert_point,  # Adiciona a imagem ao espaço do modelo
                      size_in_units=(rect.width(), rect.height()),  # Define o tamanho da imagem em unidades
                      image_def=image_def,  # Define a imagem
                      rotation=0)  # Define a rotação

        progressBar.setValue(4)  # Atualiza a barra de progresso

        # Salvar o arquivo DXF
        doc.saveas(dxf_file_path)  # Salva o documento DXF

        progressBar.setValue(5)  # Atualiza a barra de progresso

        end_time = time.time()  # Calcula o tempo de execução
        execution_time = end_time - start_time  # Calcula o tempo total de execução
        self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
        self.mostrar_mensagem(  # Mostra mensagem de sucesso
            f"Visualização da área de trabalho exportada para DXF em {execution_time:.2f} segundos",
            "Sucesso",
            caminho_pasta=os.path.dirname(dxf_file_path),
            caminho_arquivo=dxf_file_path)

    def exportar_raster_comum_para_dxf(self, layer):
        """
        Exporta uma camada raster comum para o formato DXF.
        
        Passos:
        1. Inicia a barra de progresso.
        2. Solicita ao usuário para salvar o arquivo raster como TIFF.
        3. Solicita ao usuário para salvar o arquivo DXF.
        4. Configura os parâmetros do raster, incluindo resolução e extensão.
        5. Cria e salva o arquivo TIFF.
        6. Converte o TIFF para PNG.
        7. Deleta o arquivo TIFF.
        8. Cria um documento DXF e insere a imagem PNG.
        9. Salva o arquivo DXF.
        10. Atualiza a barra de progresso e mostra uma mensagem de sucesso.

        Parâmetros:
        - layer: A camada raster a ser exportada.
        """
        start_time = time.time()  # Inicia a contagem do tempo de execução
        total_steps = 100  # Define o número total de etapas para a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)  # Inicia a barra de progresso

        progressBar.setValue(10)  # Atualiza a barra de progresso
        raster_file_path_tif = self.escolher_local_para_salvar(f"{layer.name()}.tif", "Image Files (*.tif)")  # Solicita o caminho para salvar o TIFF
        if not raster_file_path_tif:  # Verifica se o caminho foi fornecido
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se o caminho não foi fornecido
        
        progressBar.setValue(20)  # Atualiza a barra de progresso
        dxf_file_path = self.escolher_local_para_salvar(f"{layer.name()}.dxf", "DXF Files (*.dxf)")  # Solicita o caminho para salvar o DXF
        if not dxf_file_path:  # Verifica se o caminho foi fornecido
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se o caminho não foi fornecido
        
        progressBar.setValue(30)  # Atualiza a barra de progresso
        resolution_multiplier = 8  # Define o multiplicador de resolução
        provider = layer.dataProvider()  # Obtém o provedor de dados da camada
        extent = layer.extent()  # Obtém a extensão da camada
        width = layer.width() * resolution_multiplier  # Calcula a largura com base no multiplicador de resolução
        height = layer.height() * resolution_multiplier  # Calcula a altura com base no multiplicador de resolução
        file_writer = QgsRasterFileWriter(raster_file_path_tif)  # Cria o escritor de arquivos raster
        pipe = QgsRasterPipe()  # Cria o pipe raster
        if not pipe.set(provider.clone()):  # Clona o provedor de dados do raster
            self.mostrar_mensagem("Erro ao clonar o provedor de dados do raster", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se ocorrer um erro
        if not pipe.set(layer.renderer().clone()):  # Clona o renderizador do raster
            self.mostrar_mensagem("Erro ao clonar o renderizador do raster", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se ocorrer um erro
        if file_writer.writeRaster(pipe, width, height, extent, layer.crs()) != QgsRasterFileWriter.NoError:  # Escreve o raster no arquivo TIFF
            self.mostrar_mensagem("Erro ao salvar o arquivo raster", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se ocorrer um erro
        
        progressBar.setValue(50)  # Atualiza a barra de progresso
        if not os.path.exists(raster_file_path_tif):  # Verifica se o arquivo TIFF foi salvo
            self.mostrar_mensagem("Erro ao salvar o arquivo raster", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se o arquivo não foi salvo
        
        # Converter TIFF para PNG
        raster_file_path_png = raster_file_path_tif.replace(".tif", ".png")  # Define o caminho do arquivo PNG
        image = QImage()  # Cria uma instância de QImage
        if not image.load(raster_file_path_tif):  # Carrega o arquivo TIFF
            self.mostrar_mensagem("Erro ao carregar o arquivo TIFF para conversão", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se ocorrer um erro
        progressBar.setValue(60)  # Atualiza a barra de progresso durante o carregamento da imagem
        
        if not image.save(raster_file_path_png, "PNG"):  # Salva a imagem como PNG
            self.mostrar_mensagem("Erro ao salvar o arquivo como PNG", "Erro")  # Mostra mensagem de erro
            self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
            return  # Encerra a função se ocorrer um erro
        progressBar.setValue(70)  # Atualiza a barra de progresso durante a conversão para PNG
        
        # Deletar o arquivo TIFF
        os.remove(raster_file_path_tif)  # Deleta o arquivo TIFF
        
        progressBar.setValue(80)  # Atualiza a barra de progresso após a exclusão do TIFF
        doc = ezdxf.new(dxfversion='R2010')  # Cria um novo documento DXF
        msp = doc.modelspace()  # Obtém o espaço do modelo
        image_def = doc.add_image_def(filename=os.path.abspath(raster_file_path_png), size_in_pixel=(width, height))  # Adiciona a definição da imagem
        insert_point = (extent.xMinimum(), extent.yMinimum())  # Define o ponto de inserção
        msp.add_image(insert=insert_point,  # Adiciona a imagem ao espaço do modelo
                      size_in_units=(extent.width(), extent.height()),  # Define o tamanho da imagem em unidades
                      image_def=image_def,  # Define a imagem
                      rotation=0)  # Define a rotação
        
        progressBar.setValue(90)  # Atualiza a barra de progresso durante a criação do DXF
        doc.saveas(dxf_file_path)  # Salva o documento DXF
        progressBar.setValue(100)  # Atualiza a barra de progresso após salvar o DXF
        
        end_time = time.time()  # Calcula o tempo de execução
        execution_time = end_time - start_time  # Calcula o tempo total de execução
        self.iface.messageBar().clearWidgets()  # Limpa a barra de mensagens
        self.mostrar_mensagem(  # Mostra mensagem de sucesso
            f"Camada exportada para DXF em {execution_time:.2f} segundos",
            "Sucesso",
            caminho_pasta=os.path.dirname(dxf_file_path),
            caminho_arquivo=dxf_file_path)

    def abrir_qgis2threejs(self):
        """
        Aproxima para a camada selecionada no QTreeView e abre o plugin Qgis2threejs.
        Se o plugin não estiver instalado, oferece a opção de instalá-lo.
        """

        # Verifica se há uma camada selecionada no QTreeView
        indexes = self.dlg.treeViewListaRaster.selectedIndexes()
        if indexes:
            selected_layer_name = self.treeViewModel.itemFromIndex(indexes[0]).text()
            layers = QgsProject.instance().mapLayersByName(selected_layer_name)
            
            if layers:
                selected_layer = layers[0]  # Obtém a camada selecionada
                self.iface.mapCanvas().setExtent(selected_layer.extent())  # Ajusta o zoom para a camada
                self.iface.mapCanvas().refresh()  # Atualiza o mapa

        # Agora, verificamos e abrimos o plugin Qgis2threejs normalmente
        plugin_nome = "Qgis2threejs"
        plugin_dir = os.path.join(QgsApplication.qgisSettingsDirPath(), "python", "plugins", plugin_nome)

        if os.path.exists(plugin_dir):
            if plugin_nome in qgis.utils.plugins:
                # O plugin está carregado corretamente, então chamamos a interface
                try:
                    qgis.utils.plugins[plugin_nome].openExporter()
                except Exception as e:
                    QMessageBox.critical(self.dlg, "Erro ao abrir Qgis2threejs", f"Erro: {str(e)}")
            else:
                # O plugin existe, mas não está carregado – tentamos carregá-lo e iniciar
                try:
                    qgis.utils.loadPlugin(plugin_nome)
                    qgis.utils.startPlugin(plugin_nome)
                    qgis.utils.plugins[plugin_nome].openExporter()
                except Exception as e:
                    QMessageBox.critical(self.dlg, "Erro ao carregar Qgis2threejs", f"Erro ao tentar carregar o plugin:\n{str(e)}")
        else:
            # O plugin não está instalado, perguntar se o usuário deseja instalá-lo
            resposta = QMessageBox.question(
                self.dlg,
                "Plugin não encontrado",
                f"O complemento '{plugin_nome}' não está instalado.\nDeseja instalá-lo agora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if resposta == QMessageBox.Yes:
                self.iface.actionManagePlugins().trigger()
            else:
                self.mostrar_mensagem(
                    f"O complemento '{plugin_nome}' é necessário para esta funcionalidade.",
                    "Erro",
                    duracao=5
                )

class CustomDelegate(QStyledItemDelegate):
    """
    Esta classe `CustomDelegate` personaliza a aparência dos itens no QTreeView, 
    especialmente para camadas raster, desenhando ícones específicos baseados no tipo de renderização.

    Detalhes:
    - O método `paint` personaliza a pintura dos itens no QTreeView.
        - Inicializa a opção de estilo do item.
        - Usa o estilo do widget pai.
        - Calcula a posição e o tamanho do ícone de seleção.
        - Obtém a camada correspondente pelo nome e verifica seu tipo de renderização.
        - Desenha um quadrado dividido em 4 partes com cores baseadas no tipo de renderização da camada.
        - Desenha o item padrão após personalização.
    - O método `sizeHint` ajusta o tamanho do item para acomodar o ícone personalizado.
    - O método `is_false_color` verifica se a camada usa renderização de falsa cor.

    Métodos:
    - `__init__(self, parent=None)`: Inicializa a classe com o pai opcional.
    - `paint(self, painter, option, index)`: Personaliza a pintura dos itens no QTreeView.
    - `sizeHint(self, option, index)`: Ajusta o tamanho do item para acomodar o ícone personalizado.
    - `is_false_color(self, layer)`: Verifica se a camada usa renderização de falsa cor.
    """
    def __init__(self, parent=None):
        super().__init__(parent) # Inicializa a classe base com o pai opcional

    def paint(self, painter, option, index):
        # Inicializa a opção de estilo do item
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        # Usa o estilo do widget pai
        style = option.widget.style()
        
        checkBoxRect = style.subElementRect(QStyle.SE_ItemViewItemCheckIndicator, options, option.widget)
        iconSize = QSize(14, 14)
        iconRect = QRect(checkBoxRect.left() - 20, checkBoxRect.top(), iconSize.width(), iconSize.height())
        
        # Obter a camada correspondente pelo nome
        layer_name = index.data()
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            if self.is_false_color(layer):
                # Desenha o quadrado dividido em 4 partes com cores de falsa cor
                colors = [QColor(255, 0, 255), QColor(255, 0, 0), QColor(0, 255, 0), QColor(255, 255, 0)]
            else:
                # Desenha o quadrado dividido em 4 partes em escala de cinza
                colors = [QColor(200, 200, 200), QColor(50, 50, 50), QColor(120, 120, 120), QColor(150, 150, 150)]
            
            size = iconRect.width() // 2
            for i in range(2):
                for j in range(2):
                    partRect = QRect(iconRect.left() + i*size, iconRect.top() + j*size, size, size)
                    painter.fillRect(partRect, colors[i + j*2])
        
        # Desenha o item padrão
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        """
        Ajusta o tamanho do item para acomodar o ícone personalizado.
        
        Detalhes:
        - Chama o método base `sizeHint` para obter o tamanho padrão.
        - Aumenta a largura para acomodar o ícone personalizado.
        
        Retorna:
        - `QSize`: O tamanho ajustado do item.
        """
        size = super().sizeHint(option, index)
        size.setWidth(size.width() + 15)  # Ajusta o tamanho para o ícone
        return size

    def is_false_color(self, layer):
        """
        Verifica se a camada usa renderização de falsa cor.
        
        Detalhes:
        - Verifica se a camada é do tipo Raster.
        - Obtém o renderizador da camada e verifica se é uma instância de `QgsSingleBandPseudoColorRenderer`.
        
        Retorna:
        - `bool`: `True` se a camada usar renderização de falsa cor, caso contrário `False`.
        """
        # Método auxiliar para verificar se a camada usa renderização de falsa cor
        if layer.type() == QgsMapLayer.RasterLayer:
            renderer = layer.renderer()
            if isinstance(renderer, QgsSingleBandPseudoColorRenderer):
                return True
        return False

