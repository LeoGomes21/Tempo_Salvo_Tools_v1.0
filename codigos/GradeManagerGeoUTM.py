from qgis.core import (QgsProject, QgsVectorLayer, QgsPointXY, QgsField, QgsFeature, QgsGeometry, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsCoordinateReferenceSystem, Qgis, QgsMapLayer, QgsRectangle, QgsWkbTypes)
from qgis.PyQt.QtWidgets import QDialog, QProgressBar, QApplication, QFileDialog, QPushButton
from qgis.PyQt.QtCore import QVariant, Qt, QSettings
from qgis.utils import iface
from qgis.PyQt import uic
import ezdxf
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GradeUtmGeo.ui'))

class GradeManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """
        Construtor da classe GradeManager.

        Parâmetros:
        - parent (QWidget, opcional): O widget pai do diálogo. Se não for especificado, o diálogo não terá um pai.

        Funcionalidades:
        - Inicializa a interface do usuário e as conexões dos botões do diálogo.
        - Define o título da janela do diálogo.
        - Conecta os botões a seus respectivos métodos.
        - Armazena os valores iniciais dos spinBoxes definidos no QtDesigner, que serão usados para resetar os valores posteriormente.

        Retorno:
        - Nenhum. O construtor apenas inicializa o diálogo.
        """

        # Chama o construtor da classe pai (`QDialog`) para inicializar o diálogo
        super(GradeManager, self).__init__(parent)

        # Configura a interface gráfica do usuário (UI) definida no QtDesigner
        self.setupUi(self)

        # Referência para a interface principal do QGIS
        self.iface = iface

        # Define o título do diálogo como "Gerar Grade UTM/GEO"
        self.setWindowTitle("Gerar Grade UTM/GEO")

        # Atualiza imediatamente o estado do botão
        self.updatePushButtonDXFState()

        # Conecta os sinais aos slots
        self.connect_signals()

    def showEvent(self, event):
        """
        Manipula o evento de exibição do diálogo e reseta os valores dos spinBoxes para seus valores iniciais definidos no QtDesigner.

        Parâmetros:
        - event (QEvent): O evento de exibição que é acionado quando o diálogo é mostrado. É um parâmetro do tipo `QEvent`.

        Funcionalidades:
        - Chama a implementação original de `showEvent` da classe pai para garantir o comportamento padrão do evento.
        - Reseta os valores dos spinBoxes (`spinBox_espacamento`, `spinBox_percentual`, `spinBox_segundos`) para os valores iniciais 
          que foram definidos durante a inicialização da interface no QtDesigner.

        Retorno:
        - Nenhum. A função apenas redefine os valores dos spinBoxes quando o diálogo é exibido.
        """

        # Chama o método `showEvent` da classe pai para manter o comportamento padrão do evento
        super(GradeManager, self).showEvent(event)

        # Reseta os valores dos spinBoxes para os valores iniciais definidos no QtDesigner
        # Redefine `spinBox_espacamento` para seu valor inicial
        self.spinBox_espacamento.setValue(self.initial_spinBox_espacamento_value)

        # Redefine `spinBox_percentual` para seu valor inicial
        self.spinBox_percentual.setValue(self.initial_spinBox_percentual_value)

        # Redefine `spinBox_segundos` para seu valor inicial
        self.spinBox_segundos.setValue(self.initial_spinBox_segundos_value)
        
        # Atualiza imediatamente o estado do botão
        self.updatePushButtonDXFState()

    def connect_signals(self):

        # Conecta o botão `pushButtonGradeGeo` ao método que executa a criação da grade geográfica
        self.pushButtonGradeGeo.clicked.connect(self.executar_criar_grade)

        # Conecta o botão `pushButtonGradeUTM` ao método que executa a criação da grade UTM
        self.pushButtonGradeUTM.clicked.connect(self.executar_criar_grade_utm)

        # Conecta o botão `pushButtonFechar` para fechar o diálogo quando clicado
        self.pushButtonFechar.clicked.connect(self.close)

        # Armazena os valores iniciais dos spinBoxes definidos no QtDesigner
        # Armazena o valor inicial de `spinBox_espacamento`
        self.initial_spinBox_espacamento_value = self.spinBox_espacamento.value()

        # Armazena o valor inicial de `spinBox_percentual`
        self.initial_spinBox_percentual_value = self.spinBox_percentual.value()

        # Armazena o valor inicial de `spinBox_segundos`
        self.initial_spinBox_segundos_value = self.spinBox_segundos.value()

        # chamará o método executar_criar_grade_utm_aj
        self.pushButtonGradeAj.clicked.connect(self.executar_criar_grade_utm_aj)

        # Exporta para DXF
        self.pushButtonDXF.clicked.connect(self.exportar_para_dxf)

        # Conecta os sinais do projeto para atualizar quando camadas são adicionadas ou removidas
        QgsProject.instance().layersAdded.connect(self.updatePushButtonDXFState)
        QgsProject.instance().layersRemoved.connect(self.updatePushButtonDXFState)

        # Se disponível, conecte também a mudança de CRS
        try:
            QgsProject.instance().crsChanged.connect(self.updatePushButtonDXFState)
        except Exception:
            # Se o sinal crsChanged não existir, você pode chamá-lo em showEvent
            pass

    def executar_criar_grade(self):
        """
        Executa a criação da grade geográfica com base nos valores definidos no diálogo.

        Funcionalidades:
        - Obtém o valor atual do spinBox de segundos.
        - Chama a função que cria a grade e os pontos geográficos, utilizando o valor de segundos obtido.
        - Exibe os rótulos na camada de pontos criada.

        Parâmetros:
        - Nenhum.

        Retorno:
        - Nenhum. A função é responsável por acionar a criação da grade e exibir os rótulos.
        """

        # Obtém o valor de segundos a partir do spinBox_segundos
        segundos = self.spinBox_segundos.value()

        # Chama o método para criar a grade geográfica e os pontos usando o valor de segundos
        self.criar_grade_e_pontos(segundos)

        # Exibe os rótulos nos pontos da camada criada
        self.exibir_rotulos_na_camada_escolhida()

    def obter_camada_pelo_nome(self, nome):
        """
        Obtém uma camada do projeto QGIS com base no nome fornecido.

        Funcionalidades:
        - Percorre todas as camadas atualmente carregadas no projeto QGIS.
        - Verifica se o nome da camada coincide com o nome fornecido.
        - Retorna a camada correspondente se encontrada, ou `None` se nenhuma camada com o nome especificado for encontrada.

        Parâmetros:
        - nome (str): O nome da camada que se deseja buscar no projeto QGIS.

        Retorno:
        - QgsVectorLayer: A camada correspondente ao nome fornecido, se encontrada.
        - None: Se nenhuma camada com o nome especificado for encontrada.
        """

        # Percorre todas as camadas carregadas no projeto QGIS
        for layer in QgsProject.instance().mapLayers().values():
            # Verifica se o nome da camada corresponde ao nome fornecido
            if layer.name() == nome:
                return layer  # Retorna a camada encontrada

        # Retorna None se nenhuma camada correspondente for encontrada
        return None

    def executar_criar_grade_utm(self):
        """
        Executa a criação da grade UTM com base nos valores definidos no diálogo.

        Funcionalidades:
        - Obtém os valores atuais do spinBox de espaçamento e percentual.
        - Chama a função que cria a grade e os pontos UTM, utilizando os valores de espaçamento e percentual obtidos.
        - Exibe os rótulos na camada de pontos UTM criada.

        Parâmetros:
        - Nenhum.

        Retorno:
        - Nenhum. A função é responsável por acionar a criação da grade UTM e exibir os rótulos.
        """

        # Obtém o valor de espaçamento a partir do spinBox_espacamento
        intervalo = self.spinBox_espacamento.value()

        # Obtém o valor percentual a partir do spinBox_percentual
        percentual = self.spinBox_percentual.value()

        # Chama o método para criar a grade UTM e os pontos usando os valores de espaçamento e percentual
        self.criar_grade_e_pontos_utm(intervalo, percentual)

        # Exibe os rótulos nos pontos da camada UTM criada
        self.exibir_rotulos_na_camada_escolhida_utm()

    def remove_layers_if_exist(self, layer_names):
        """
        Remove camadas do projeto QGIS se elas existirem, baseado nos nomes fornecidos.

        Funcionalidades:
        - Verifica se camadas com os nomes fornecidos estão carregadas no projeto QGIS.
        - Remove as camadas encontradas que correspondem aos nomes fornecidos.

        Parâmetros:
        - layer_names (list): Lista de strings contendo os nomes das camadas a serem removidas.

        Retorno:
        - Nenhum. A função remove as camadas existentes que correspondem aos nomes fornecidos.
        """

        # Itera sobre a lista de nomes de camadas
        for layer_name in layer_names:
            # Obtém as camadas que possuem o nome correspondente
            existing_layers = QgsProject.instance().mapLayersByName(layer_name)

            # Itera sobre as camadas encontradas com o nome correspondente
            for layer in existing_layers:
                # Remove a camada do projeto QGIS com base em seu ID
                QgsProject.instance().removeMapLayer(layer.id())

    def esta_em_utm(self, src_projeto):
        """
        Verifica se o Sistema de Referência de Coordenadas (SRC) do projeto está configurado em UTM.

        Funcionalidades:
        - A função verifica se o Sistema de Referência de Coordenadas (SRC) atual do projeto contém a string 'UTM zone' na sua descrição.
        - Isso é utilizado para determinar se o projeto está configurado para o sistema UTM (Universal Transverse Mercator).

        Parâmetros:
        - src_projeto (QgsCoordinateReferenceSystem): O Sistema de Referência de Coordenadas (SRC) atual do projeto.

        Retorno:
        - bool: Retorna True se o SRC do projeto estiver configurado em UTM, e False caso contrário.
        """

        # Obtém a descrição do SRC (Sistema de Referência de Coordenadas) do projeto
        src_descricao = src_projeto.description()

        # Verifica se a descrição do SRC contém a string 'UTM zone', indicando que o projeto está em UTM
        return 'UTM zone' in src_descricao

    def exibir_rotulos_na_camada_escolhida_geo(self):
        """
        Exibe os rótulos na camada de coordenadas geográficas, se ela estiver presente no projeto.

        Funcionalidades:
        - Verifica se a camada com o nome 'Coordenadas Limites' está carregada no projeto.
        - Caso a camada seja encontrada, os rótulos são configurados para serem exibidos nela.

        Parâmetros:
        - Nenhum. A função utiliza internamente o nome da camada 'Coordenadas Limites'.

        Retorno:
        - Nenhum. A função exibe os rótulos na camada de pontos geográficos selecionada.
        """

        # Nome da camada de pontos geográficos que será verificada
        nome_da_camada_pontos = "Coordenadas Limites"

        # Obtém a camada pelo nome, se ela estiver carregada no projeto
        camada_escolhida_pontos = self.obter_camada_pelo_nome(nome_da_camada_pontos)

        # Se a camada foi encontrada, configura os rótulos para essa camada
        if camada_escolhida_pontos:
            self.configurar_rotulos_na_camada_geo(camada_escolhida_pontos)

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
        progressMessageBar = self.iface.messageBar().createMessage("Criando Grade...")
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

    def criar_grade_e_pontos_utm(self, intervalo, percentual):
        """
        Esta função cria uma grade UTM e uma camada de pontos de interseção no QGIS.

        Função:
        - Remove as camadas existentes chamadas 'Grade UTM' e 'Coordenadas Limites'.
        - Verifica se o sistema de coordenadas do projeto está em UTM.
        - Define os limites da grade, ajusta os valores para serem múltiplos do intervalo fornecido.
        - Cria linhas horizontais e verticais para a grade, com base em um intervalo especificado.
        - Escala a janela central da grade com base em um percentual dado.
        - Gera e adiciona pontos de interseção nas extremidades e bordas da grade.
        - Exibe uma barra de progresso enquanto a grade e os pontos são criados.
        - Exibe uma mensagem de sucesso após a conclusão.

        Parâmetros:
        - intervalo (int): O espaçamento entre as linhas da grade (em metros).
        - percentual (float): Percentual para ajustar a escala da janela central (de 0% a 100%).

        Retorno:
        - Nenhum valor de retorno explícito. A função cria camadas de linhas e pontos diretamente no projeto QGIS.
        """

        # Remove as camadas existentes 'Grade UTM' e 'Coordenadas Limites', se existirem
        self.remove_layers_if_exist(['Grade UTM', 'Coordenadas Limites'])

        # Obtém a extensão atual da tela do mapa e o SRC (Sistema de Referência de Coordenadas) do projeto
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        src_projeto = QgsProject.instance().crs()

        # Check if the project CRS is UTM
        if not self.esta_em_utm(src_projeto):
            self.mostrar_mensagem("O projeto não está configurado com um SRC UTM.", "Erro")
            return

        # Obtém os limites da extensão (xmin, ymin, xmax, ymax)
        xmin, ymin, xmax, ymax = extent.toRectF().getCoords()

        # Adjust grid limits to be multiples of the interval
        xmin = int(xmin) // intervalo * intervalo
        ymin = int(ymin) // intervalo * intervalo
        xmax = int(xmax) // intervalo * intervalo + intervalo
        ymax = int(ymax) // intervalo * intervalo + intervalo

        # Invert the scale of the central window based on the percentual
        escala_janela = (100 - percentual) / 100.0  # Invert scale to make 100% fill the entire area

        # Calcula as dimensões totais da grade (largura e altura)
        largura_total = xmax - xmin
        altura_total = ymax - ymin

         # Define as coordenadas da janela central com base na escala invertida
        largura_janela = largura_total * escala_janela
        altura_janela = altura_total * escala_janela
        xmin_janela = xmin + (largura_total - largura_janela) / 2
        xmax_janela = xmax - (largura_total - largura_janela) / 2
        ymin_janela = ymin + (altura_total - altura_janela) / 2
        ymax_janela = ymax - (altura_total - altura_janela) / 2

        # Calcula o número total de etapas (linhas e pontos) para a barra de progresso
        total_lines = (int(ymax - ymin) // intervalo + 1) * 2  # horizontal lines (including central window)
        total_lines += (int(xmax - xmin) // intervalo + 1) * 2  # vertical lines (including central window)
        total_points = (int((xmax - xmin) / intervalo + 1) * 2) + (int((ymax - ymin) / intervalo + 1) * 2)
        total_steps = total_lines + total_points # Total de etapas (linhas + pontos)

        # Inicia a barra de progresso com o número total de etapas
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)
        current_step = 0  # Contador de etapas iniciado em 0

        # Cria a camada de linhas da grade
        grid_layer = QgsVectorLayer(f'LineString?crs={src_projeto.authid()}', 'Grade UTM', 'memory')
        provider = grid_layer.dataProvider()
        provider.addAttributes([QgsField('ID', QVariant.Int)])  # Adiciona o campo 'ID'
        grid_layer.updateFields() # Atualiza os campos da camada

        # Inicia o ID das linhas em 1
        line_id = 1

        # Adiciona linhas horizontais à camada da grade
        for y in range(int(ymin), int(ymax + intervalo), int(intervalo)):
            if ymin_janela <= y <= ymax_janela:
                coords_inicio = [QgsPointXY(xmin, y), QgsPointXY(xmin_janela, y)]
                coords_fim = [QgsPointXY(xmax_janela, y), QgsPointXY(xmax, y)]
                for coords in [coords_inicio, coords_fim]:
                    line = QgsFeature()
                    line.setGeometry(QgsGeometry.fromPolylineXY(coords))
                    line.setAttributes([line_id]) # Atribui o ID à linha
                    provider.addFeature(line) # Adiciona a linha à camada
                    line_id += 1 # Incrementa o ID da linha

                    # Atualiza a barra de progresso
                    current_step += 1
                    progressBar.setValue(current_step)
            else:
                # Adiciona a linha completa fora da janela central
                line_coords = QgsGeometry.fromPolylineXY([QgsPointXY(xmin, y), QgsPointXY(xmax, y)])
                horizontal_line = QgsFeature()
                horizontal_line.setGeometry(line_coords)
                horizontal_line.setAttributes([line_id])
                provider.addFeature(horizontal_line)
                line_id += 1

                # Atualiza a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)

        # Adiciona linhas verticais à camada da grade
        for x in range(int(xmin), int(xmax + intervalo), int(intervalo)):
            if xmin_janela <= x <= xmax_janela:
                coords_inicio = [QgsPointXY(x, ymin), QgsPointXY(x, ymin_janela)]
                coords_fim = [QgsPointXY(x, ymax_janela), QgsPointXY(x, ymax)]
                for coords in [coords_inicio, coords_fim]:
                    line = QgsFeature()
                    line.setGeometry(QgsGeometry.fromPolylineXY(coords)) # Define a geometria da linha
                    line.setAttributes([line_id]) # Atribui o ID à linha
                    provider.addFeature(line) # Adiciona a linha à camada
                    line_id += 1

                    # Atualiza a barra de progresso
                    current_step += 1
                    progressBar.setValue(current_step)
            else:
                # Adiciona a linha completa fora da janela central
                line_coords = QgsGeometry.fromPolylineXY([QgsPointXY(x, ymin), QgsPointXY(x, ymax)])
                vertical_line = QgsFeature()
                vertical_line.setGeometry(line_coords)
                vertical_line.setAttributes([line_id])
                provider.addFeature(vertical_line)
                line_id += 1

                # Update progress bar
                current_step += 1
                progressBar.setValue(current_step)

        # Adiciona a camada de linhas ao projeto
        QgsProject.instance().addMapLayer(grid_layer)

        # Cria a camada de pontos de interseção
        intersection_points_layer = QgsVectorLayer(f'Point?crs={src_projeto.authid()}', 'Coordenadas Limites', 'memory')
        points_provider = intersection_points_layer.dataProvider()
        points_provider.addAttributes([
            QgsField('ID', QVariant.Int),
            QgsField('X', QVariant.Int),
            QgsField('Y', QVariant.Int)
        ])
        intersection_points_layer.updateFields()

        # Add intersection points only on the boundary lines
        point_id = 1
        # Adiciona pontos de interseção nas bordas verticais (nos extremos superior e inferior)
        for x in range(int(xmin), int(xmax + intervalo), int(intervalo)):
            for y in [ymin, ymax]:
                intersection_point = QgsFeature()
                point_coords = QgsPointXY(x, y)
                intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords)) # Define a geometria do ponto
                intersection_point.setAttributes([point_id, x, y]) # Atribui o ID e coordenadas
                points_provider.addFeature(intersection_point) # Adiciona o ponto à camada
                point_id += 1

                # Atualiza a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)

        # Adiciona pontos de interseção nas bordas horizontais
        for y in range(int(ymin + intervalo), int(ymax), int(intervalo)):
            for x in [xmin, xmax]:
                intersection_point = QgsFeature()
                point_coords = QgsPointXY(x, y)
                intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords)) # Define a geometria do ponto
                intersection_point.setAttributes([point_id, x, y]) # Atribui o ID e coordenadas
                points_provider.addFeature(intersection_point) # Adiciona o ponto à camada
                point_id += 1

                # Update progress bar
                current_step += 1
                progressBar.setValue(current_step)

        # Adiciona a camada de pontos de interseção ao projeto
        QgsProject.instance().addMapLayer(intersection_points_layer)

        # Limpa a barra de progresso após a conclusão
        self.iface.messageBar().clearWidgets()

        # Exibe uma mensagem de sucesso após a criação das camadas
        self.mostrar_mensagem("As camadas 'Grade UTM' e 'Coordenadas Limites' foram criadas com sucesso.", "Sucesso")

    def exibir_rotulos_na_camada_escolhida_utm(self):
        """
        Exibe os rótulos na camada UTM escolhida. 

        A função localiza a camada de pontos de interseção 'Coordenadas Limites' no projeto atual,
        e se a camada for encontrada, os rótulos são configurados e ativados.

        Parâmetros:
        - Nenhum.

        Retorno:
        - Nenhum retorno explícito. A função configura rótulos na camada de pontos encontrada.
        """

        # Nome da camada de pontos que será configurada
        nome_da_camada_pontos = "Coordenadas Limites"

        # Obtém a camada pelo nome
        camada_escolhida_pontos = self.obter_camada_pelo_nome(nome_da_camada_pontos)

        # Verifica se a camada foi encontrada no projeto
        if camada_escolhida_pontos:
            # Se a camada foi encontrada, configura os rótulos na camada
            self.configurar_rotulos_na_camada_utm(camada_escolhida_pontos)

    def configurar_rotulos_na_camada_utm(self, camada_de_vetor):
        """
        Configura os rótulos na camada UTM de vetor, exibindo as coordenadas X ou Y dependendo
        da posição do ponto (extremidade).

        A função usa a configuração de rótulos do QGIS para exibir os valores de coordenadas 
        de acordo com a posição do ponto na camada UTM. Ela é particularmente útil para mostrar 
        valores de coordenadas nas extremidades dos limites de uma grade.

        Parâmetros:
        - camada_de_vetor (QgsVectorLayer): A camada de vetor (camada de pontos) onde os rótulos serão configurados.

        Retorno:
        - Nenhum retorno explícito. A função ativa e configura os rótulos diretamente na camada fornecida.
        """

        # Verifica se a camada fornecida é uma camada de vetor (QgsVectorLayer)
        if not isinstance(camada_de_vetor, QgsVectorLayer):
            return  # Se não for, a função é encerrada

        # Configuração dos rótulos usando QgsPalLayerSettings
        configuracao_de_rotulos = QgsPalLayerSettings()  # Cria uma nova configuração de rótulos
        configuracao_de_rotulos.enabled = True  # Ativa os rótulos
        configuracao_de_rotulos.isExpression = True  # Define que os rótulos serão baseados em uma expressão
        configuracao_de_rotulos.priority = 0  # Define a prioridade dos rótulos (0 é a prioridade mais baixa)
        configuracao_de_rotulos.displayAll = True  # Exibe todos os rótulos, mesmo em feições sobrepostas

        # Criação de uma expressão condicional para verificar a posição dos pontos
        # A expressão CASE verifica se o ponto está na extremidade máxima ou mínima
        # para X ou Y e exibe a coordenada correspondente.
        expr = """CASE 
                    WHEN "Y" = minimum("Y", group_by:=NULL) OR "Y" = maximum("Y", group_by:=NULL) THEN to_string("X")
                    WHEN "X" = minimum("X", group_by:=NULL) OR "X" = maximum("X", group_by:=NULL) THEN to_string("Y")
                  END"""

        # Atribui a expressão como o campo para exibir os rótulos
        configuracao_de_rotulos.fieldName = expr
        
        # Define a configuração simples de rotulagem para a camada de vetor
        rotulacao_simples = QgsVectorLayerSimpleLabeling(configuracao_de_rotulos)
        
        # Aplica a rotulagem configurada à camada de vetor
        camada_de_vetor.setLabeling(rotulacao_simples)
        
        # Ativa os rótulos na camada
        camada_de_vetor.setLabelsEnabled(True)
        
        # Solicita uma nova renderização da camada para garantir que os rótulos sejam exibidos
        camada_de_vetor.triggerRepaint()

    def dec_to_dms(self, valor):
        """
        Converte um valor decimal de coordenadas (graus decimais) em graus, minutos e segundos (DMS).

        A função é usada para converter valores de latitude e longitude no formato decimal para
        o formato de graus, minutos e segundos (DMS).

        Parâmetros:
        - valor (float): O valor de coordenada em graus decimais que será convertido para DMS.

        Retorno:
        - str: O valor convertido no formato DMS (graus, minutos, segundos), retornado como string.
        """

        # Define o sinal negativo se o valor for negativo, ou nenhum sinal se for positivo
        sinal = "-" if valor < 0 else ""

        # Converte o valor para positivo, se necessário, para calcular os graus, minutos e segundos
        valor = abs(valor)

        # Extrai a parte inteira do valor como graus
        graus = int(valor)

        # Calcula os minutos a partir da parte decimal dos graus
        minutos = int((valor - graus) * 60)

        # Calcula os segundos a partir da parte restante após a extração dos minutos
        segundos = (valor - graus - minutos / 60) * 3600

        # Retorna o valor formatado em graus, minutos e segundos com precisão de 2 casas decimais nos segundos
        return f"{sinal}{graus}° {minutos}' {segundos:.2f}\""

    def criar_grade_e_pontos(self, segundos):
        """
        Converte um valor de coordenada em graus decimais (DD) para o formato de graus, minutos e segundos (DMS).

        Essa função é útil para transformar valores de latitude e longitude, que estão em formato decimal,
        em um formato mais legível e convencional, utilizado comumente em navegação e cartografia, conhecido
        como DMS (graus, minutos e segundos). O formato DMS divide os graus decimais em três componentes:
        graus inteiros, minutos (parte decimal convertida para minutos), e segundos (parte residual em segundos).

        Funcionamento:
        - Verifica se o valor é negativo e armazena o sinal apropriado ("-" ou "").
        - Calcula os graus inteiros como a parte inteira do valor absoluto.
        - Calcula os minutos multiplicando a parte decimal restante por 60 e obtendo a parte inteira desse produto.
        - Calcula os segundos convertendo a parte decimal restante após a conversão para minutos em segundos.
        - Combina graus, minutos e segundos em uma string formatada e retorna o valor no formato DMS.

        Parâmetros:
        - valor (float): Um número de coordenada em graus decimais (latitude ou longitude) que será convertido.

        Retorno:
        - str: Uma string representando o valor convertido no formato "graus° minutos' segundos\"".
               O sinal negativo é mantido caso o valor original seja negativo (indica coordenadas ao sul ou oeste).
        """

        # Remover as camadas 'Grade Geografica' e 'Coordenadas Limites' antes de criar novas
        self.remove_layers_if_exist(['Grade Geografica', 'Coordenadas Limites'])

        canvas = iface.mapCanvas()
        extent = canvas.extent()
        src_projeto = QgsProject.instance().crs()

        # Verificar se o sistema de coordenadas é geográfico (latitude e longitude)
        if not src_projeto.isGeographic():
            self.mostrar_mensagem("O sistema de coordenadas não está em coordenadas geográficas.", "Erro")
            return

        xmin, ymin, xmax, ymax = extent.toRectF().getCoords()

        # Verificar se as coordenadas estão dentro dos limites válidos para latitude e longitude
        if not (-180 <= xmin <= 180 and -180 <= xmax <= 180 and -90 <= ymin <= 90 and -90 <= ymax <= 90):
            self.mostrar_mensagem("As coordenadas da grade estão fora dos limites válidos.", "Erro")
            return

        intervalo = segundos / 3600

        # Ajustar coordenadas para múltiplos do intervalo
        xmin = round(xmin / intervalo) * intervalo
        ymin = round(ymin / intervalo) * intervalo
        xmax += intervalo - (xmax - xmin) % intervalo if (xmax - xmin) % intervalo != 0 else 0
        ymax += intervalo - (ymax - ymin) % intervalo if (ymax - ymin) % intervalo != 0 else 0

        grid_layer = QgsVectorLayer(f'LineString?crs={src_projeto.authid()}', 'Grade Geografica', 'memory')
        provider = grid_layer.dataProvider()
        provider.addAttributes([QgsField('ID', QVariant.Int)])
        grid_layer.updateFields()

        line_id = 1
        linhas_horizontais = [round(y, 10) for y in [ymin + i * intervalo for i in range(int((ymax - ymin) / intervalo) + 1)]]

        linhas_verticais = [round(x, 10) for x in [xmin + i * intervalo for i in range(int((xmax - xmin) / intervalo) + 1)]]

        # Calcular o total de etapas para a barra de progresso
        total_lines = len(linhas_horizontais) + len(linhas_verticais)
        total_points = (len(linhas_horizontais) * 2) + (len(linhas_verticais) * 2)
        total_steps = total_lines + total_points  # Total de etapas = linhas + pontos

        # Iniciar a barra de progresso
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)
        current_step = 0  # Inicializar o contador de etapas

        # Verificar se a linha superior (topo) está incluída
        if round(ymax, 10) not in linhas_horizontais:
            linhas_horizontais.append(round(ymax, 10))

        # Criar linhas horizontais
        for y in sorted(linhas_horizontais):
            horizontal_line = QgsFeature()
            line_coords = QgsGeometry.fromPolylineXY([QgsPointXY(xmin, y), QgsPointXY(xmax, y)])
            horizontal_line.setGeometry(line_coords)
            horizontal_line.setAttributes([line_id])
            provider.addFeature(horizontal_line)
            line_id += 1

            # Atualizar a barra de progresso
            current_step += 1
            progressBar.setValue(current_step)

        # Verificar se a linha direita (topo) está incluída
        if round(xmax, 10) not in linhas_verticais:
            linhas_verticais.append(round(xmax, 10))

        # Criar linhas verticais
        for x in sorted(linhas_verticais):
            vertical_line = QgsFeature()
            line_coords = QgsGeometry.fromPolylineXY([QgsPointXY(x, ymin), QgsPointXY(x, ymax)])
            vertical_line.setGeometry(line_coords)
            vertical_line.setAttributes([line_id])
            provider.addFeature(vertical_line)
            line_id += 1

            # Atualizar a barra de progresso
            current_step += 1
            progressBar.setValue(current_step)

        # Adicionar a camada de grade ao projeto
        QgsProject.instance().addMapLayer(grid_layer)

        # Criar a camada de pontos de interseção
        intersection_points_layer = QgsVectorLayer(f'Point?crs={src_projeto.authid()}', 'Coordenadas Limites', 'memory')
        points_provider = intersection_points_layer.dataProvider()
        points_provider.addAttributes([QgsField('ID', QVariant.Int),
                                       QgsField('X', QVariant.Double),
                                       QgsField('Y', QVariant.Double),
                                       QgsField('X_DMS', QVariant.String, len=20),
                                       QgsField('Y_DMS', QVariant.String, len=20)])
        intersection_points_layer.updateFields()

        point_id = 1
        pontos_criados = set()  # Usar um conjunto para verificar pontos duplicados

        # Função para arredondar as coordenadas e verificar duplicidade
        def coordenada_ajustada(x, y, precisao=6):
            return (round(x, precisao), round(y, precisao))

        # Cria pontos nas bordas verticais, exceto nos cantos superiores e inferiores
        for x in [xmin, xmax]:
            for y in [round(y, 10) for y in [ymin + i * intervalo for i in range(1, int((ymax - ymin) / intervalo))]]:
                if coordenada_ajustada(x, y) not in pontos_criados:  # Verificar se o ponto já foi criado
                    intersection_point = QgsFeature()
                    point_coords = QgsPointXY(x, y)
                    intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords))
                    intersection_point.setAttributes([point_id, x, y, self.dec_to_dms(x), self.dec_to_dms(y)])
                    points_provider.addFeature(intersection_point)
                    point_id += 1
                    pontos_criados.add(coordenada_ajustada(x, y))  # Adicionar ponto ao conjunto com precisão ajustada

                    # Atualizar a barra de progresso
                    current_step += 1
                    progressBar.setValue(current_step)

        # Cria pontos nas bordas horizontais, incluindo os cantos superiores e inferiores
        for y in [ymin, ymax]:
            for x in [round(x, 10) for x in [xmin + i * intervalo for i in range(0, int((xmax - xmin) / intervalo) + 1)]]:
                if coordenada_ajustada(x, y) not in pontos_criados:  # Verificar se o ponto já foi criado
                    intersection_point = QgsFeature()
                    point_coords = QgsPointXY(x, y)
                    intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords))
                    intersection_point.setAttributes([point_id, x, y, self.dec_to_dms(x), self.dec_to_dms(y)])
                    points_provider.addFeature(intersection_point)
                    point_id += 1
                    pontos_criados.add(coordenada_ajustada(x, y))  # Adicionar ponto ao conjunto com precisão ajustada

                    # Atualizar a barra de progresso
                    current_step += 1
                    progressBar.setValue(current_step)

        # Verificar e adicionar pontos nas extremidades das linhas horizontais e verticais
        for y in linhas_horizontais:
            # Verificar extremidades esquerda (xmin) e direita (xmax)
            if coordenada_ajustada(xmin, y) not in pontos_criados:
                intersection_point = QgsFeature()
                point_coords = QgsPointXY(xmin, y)
                intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords))
                intersection_point.setAttributes([point_id, xmin, y, self.dec_to_dms(xmin), self.dec_to_dms(y)])
                points_provider.addFeature(intersection_point)
                point_id += 1
                pontos_criados.add(coordenada_ajustada(xmin, y))

                # Atualizar a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)

            if coordenada_ajustada(xmax, y) not in pontos_criados:
                print(f"Adicionando ponto de interseção na extremidade direita em x={xmax}, y={y}")
                intersection_point = QgsFeature()
                point_coords = QgsPointXY(xmax, y)
                intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords))
                intersection_point.setAttributes([point_id, xmax, y, self.dec_to_dms(xmax), self.dec_to_dms(y)])
                points_provider.addFeature(intersection_point)
                point_id += 1
                pontos_criados.add(coordenada_ajustada(xmax, y))

                # Atualizar a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)

        # Verificar extremidades das linhas verticais
        for x in linhas_verticais:
            # Verificar extremidades superior (ymax) e inferior (ymin)
            if coordenada_ajustada(x, ymin) not in pontos_criados:

                intersection_point = QgsFeature()
                point_coords = QgsPointXY(x, ymin)
                intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords))
                intersection_point.setAttributes([point_id, x, ymin, self.dec_to_dms(x), self.dec_to_dms(ymin)])
                points_provider.addFeature(intersection_point)
                point_id += 1
                pontos_criados.add(coordenada_ajustada(x, ymin))

                # Atualizar a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)

            if coordenada_ajustada(x, ymax) not in pontos_criados:
                print(f"Adicionando ponto de interseção na extremidade superior em x={x}, y={ymax}")
                intersection_point = QgsFeature()
                point_coords = QgsPointXY(x, ymax)
                intersection_point.setGeometry(QgsGeometry.fromPointXY(point_coords))
                intersection_point.setAttributes([point_id, x, ymax, self.dec_to_dms(x), self.dec_to_dms(ymax)])
                points_provider.addFeature(intersection_point)
                point_id += 1
                pontos_criados.add(coordenada_ajustada(x, ymax))

                # Atualizar a barra de progresso
                current_step += 1
                progressBar.setValue(current_step)

        QgsProject.instance().addMapLayer(intersection_points_layer)

        # Fechar a barra de progresso
        self.iface.messageBar().clearWidgets()

        self.mostrar_mensagem("As camadas 'Grade Geográfica' e 'Coordenadas Limites' foram criadas com sucesso.", "Sucesso")

    def exibir_rotulos_na_camada_escolhida(self):
        """
        Exibe rótulos para a camada de pontos "Coordenadas Limites", caso ela exista no projeto.

        Parâmetros:
        - Nenhum. A função opera diretamente sobre o estado interno da instância e do QGIS.

        Funcionalidades:
        - Define o nome da camada de pontos que será utilizada para a exibição dos rótulos.
        - Busca a camada chamada "Coordenadas Limites" no projeto QGIS atual.
        - Verifica se a camada foi encontrada:
          - Se a camada é encontrada, a função chama `configurar_rotulos_na_camada` para configurar os rótulos
            de acordo com as especificações (como coordenadas, DMS, etc.).
        - Se a camada não for encontrada, a função não faz nenhuma ação adicional.
        
        Retorno:
        - Nenhum. A função afeta diretamente a camada de pontos no QGIS, exibindo os rótulos configurados.
        """

        # Define o nome da camada de pontos onde os rótulos serão exibidos
        nome_da_camada_pontos = "Coordenadas Limites"

        # Busca a camada de pontos "Coordenadas Limites" no projeto atual
        camada_escolhida_pontos = self.obter_camada_pelo_nome(nome_da_camada_pontos)

        # Verifica se a camada foi encontrada
        if camada_escolhida_pontos:
            # Configura e exibe os rótulos sobre os pontos da camada
            self.configurar_rotulos_na_camada(camada_escolhida_pontos)

    def mostrar_mensagem(self, texto, tipo, duracao=3, caminho_pasta=None, caminho_arquivo=None):
        """
        Exibe uma mensagem na barra de mensagens do QGIS, proporcionando feedback ao usuário baseado nas ações realizadas.

        Parâmetros:
        - texto (str): O texto da mensagem que será exibido.
        - tipo (str): O tipo de mensagem ("Erro" ou "Sucesso") que determina o nível de prioridade da notificação.
        - duracao (int, opcional): O tempo em segundos que a mensagem permanecerá visível. O padrão é 3 segundos.
        - caminho_pasta (str, opcional): Caminho de uma pasta que pode ser aberto diretamente a partir da mensagem.
        - caminho_arquivo (str, opcional): Caminho de um arquivo que pode ser executado diretamente a partir da mensagem.

        Funcionalidades:
        - Exibe uma mensagem de erro ou sucesso com a duração especificada.
        - Se o tipo for "Erro", exibe uma mensagem com nível crítico.
        - Se o tipo for "Sucesso", exibe a mensagem com um botão opcional para abrir uma pasta ou executar um arquivo.
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
            
            # Se o caminho do arquivo for fornecido, adiciona um botão para executar o arquivo
            if caminho_arquivo:
                botao_executar = QPushButton("Executar")
                botao_executar.clicked.connect(lambda: os.startfile(caminho_arquivo))
                msg.layout().insertWidget(2, botao_executar)  # Adiciona o botão à esquerda do texto
            
            # Adiciona a mensagem à barra com o nível informativo e a duração especificada
            bar.pushWidget(msg, level=Qgis.Info, duration=duracao)

    def configurar_rotulos_na_camada(self, camada_de_vetor):
        """
        Configura e exibe rótulos na camada de vetor fornecida, mostrando as coordenadas em formato DMS.

        Parâmetros:
        - camada_de_vetor (QgsVectorLayer): A camada de vetor onde os rótulos serão exibidos.
                                             A camada deve ser do tipo `QgsVectorLayer`.

        Funcionalidades:
        - Verifica se a camada fornecida é válida e do tipo correto (`QgsVectorLayer`).
        - Configura as definições de rótulos para exibir as coordenadas X e Y em formato DMS (graus, minutos e segundos).
        - Define a prioridade dos rótulos e garante que todos os rótulos sejam exibidos.
        - Aplica as configurações de rótulos na camada fornecida e força a atualização da visualização para exibir os rótulos.

        Retorno:
        - Nenhum. A função apenas afeta a visualização da camada no QGIS, exibindo os rótulos sobre os pontos.
        """

        # Verifica se a camada fornecida é do tipo `QgsVectorLayer`
        if not isinstance(camada_de_vetor, QgsVectorLayer):
            return  # Sai da função se a camada não for válida

        # Cria uma instância de configurações de rótulo (QgsPalLayerSettings)
        configuracao_de_rotulos = QgsPalLayerSettings()

        # Habilita a exibição dos rótulos
        configuracao_de_rotulos.enabled = True

        # Define que o campo de rótulo será uma expressão personalizada
        configuracao_de_rotulos.isExpression = True

        # Define a prioridade dos rótulos (0 é o valor mais baixo)
        configuracao_de_rotulos.priority = 0

        # Configura para exibir todos os rótulos, sem filtros
        configuracao_de_rotulos.displayAll = True

        # Define a expressão para exibir as coordenadas X e Y em formato DMS
        expr = 'concat(to_string("X_DMS"), \'\\n\', to_string("Y_DMS"))'

        # Atribui a expressão ao campo de rótulo
        configuracao_de_rotulos.fieldName = expr

        # Cria uma instância de rotulagem simples com as configurações definidas
        rotulacao_simples = QgsVectorLayerSimpleLabeling(configuracao_de_rotulos)

        # Aplica a rotulagem à camada de vetor
        camada_de_vetor.setLabeling(rotulacao_simples)

        # Habilita a exibição de rótulos na camada
        camada_de_vetor.setLabelsEnabled(True)

        # Reforça a atualização da camada para garantir que os rótulos sejam exibidos imediatamente
        camada_de_vetor.triggerRepaint()

    def executar_criar_grade_utm_aj(self):
        """
        Cria uma grade UTM que:
          - Ocupa totalmente a extensão do Map Canvas, arredondada a múltiplos do espaçamento
          - Linhas fechando as extremidades (fora das feições)
          - E também cria uma camada de pontos "Coordenadas Limites (Fora)" nas bordas,
            armazenando X e Y (apenas se estiverem fora das feições)
          - Para camadas lineares e pontuais, usa um buffer de 10% do valor do spinBox_espacamento
          - Se não houver feições (ou não estiver em UTM), exibe mensagem de erro.
          - Configura os rótulos nos pontos, exibindo X ou Y conforme a posição extrema.
        """

        # 1) Verificar se o projeto está em SRC UTM
        crs_projeto = QgsProject.instance().crs()
        if not self.esta_em_utm(crs_projeto):
            self.mostrar_mensagem(
                "O projeto não está em SRC UTM. Defina um SRC UTM antes de continuar.",
                "Erro")
            return

        # 2) Pegar espaçamento no spinBox
        intervalo = self.spinBox_espacamento.value()
        if intervalo <= 0:
            self.mostrar_mensagem("Intervalo inválido. Defina um valor > 0.", "Erro")
            return

        # Buffer de 10% do espaçamento para linhas/pontos
        buffer_para_linhas_pontos = 0.1 * intervalo

        # 3) Remover camadas anteriores
        self.remove_layers_if_exist(['Grade UTM', 'Coordenadas Limites'])

        # 4) Construir a união de todas as geometrias (polygon, buffer de lines/points, raster, mesh)
        union_geom = None

        def unir_geometrias(base_geom, nova_geom):
            if base_geom is None:
                return nova_geom
            else:
                return base_geom.combine(nova_geom)

        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer and layer.isValid():
                # Polígono
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    for feat in layer.getFeatures():
                        geom = feat.geometry()
                        if geom:
                            union_geom = unir_geometrias(union_geom, geom)
                # Linha ou ponto => buffer
                elif layer.geometryType() in (QgsWkbTypes.LineGeometry, QgsWkbTypes.PointGeometry):
                    for feat in layer.getFeatures():
                        geom = feat.geometry()
                        if geom:
                            bufferado = geom.buffer(buffer_para_linhas_pontos, 5)
                            if not bufferado.isEmpty():
                                union_geom = unir_geometrias(union_geom, bufferado)

            elif layer.type() == QgsMapLayer.RasterLayer:
                # Raster => retângulo bounding box
                ext_raster = layer.extent()
                geom_ret = QgsGeometry.fromRect(ext_raster)
                union_geom = unir_geometrias(union_geom, geom_ret)

            elif layer.type() == QgsMapLayer.MeshLayer:
                # Mesh => retângulo bounding box
                ext_mesh = layer.extent()
                geom_ret = QgsGeometry.fromRect(ext_mesh)
                union_geom = unir_geometrias(union_geom, geom_ret)

        # Se não achamos geometrias para union
        if not union_geom or union_geom.isEmpty():
            self.mostrar_mensagem(
                "Não há feições/camadas para restringir a grade.",
                "Erro"
            )
            return

        # 5) Extensão do Map Canvas, arredondada para múltiplos do espaçamento
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        minx = extent.xMinimum()
        miny = extent.yMinimum()
        maxx = extent.xMaximum()
        maxy = extent.yMaximum()

        minx = math.floor(minx / intervalo) * intervalo
        miny = math.floor(miny / intervalo) * intervalo
        maxx = math.ceil(maxx / intervalo) * intervalo
        maxy = math.ceil(maxy / intervalo) * intervalo

        retangulo_geom = QgsGeometry.fromRect(QgsRectangle(minx, miny, maxx, maxy))

        # 6) Polígono externo = retângulo - union_geom
        poligono_externo = retangulo_geom.difference(union_geom)
        if poligono_externo.isEmpty():
            self.mostrar_mensagem(
                "As feições/camadas ocupam toda a área de trabalho. Nada sobra para a grade externa.",
                "Erro")
            return

        # 7) Criar camada de linhas: "Grade UTM Ajustada (Fora)"
        grade_layer = QgsVectorLayer(
            f'LineString?crs={crs_projeto.authid()}',
            'Grade UTM',
            'memory'
        )
        provider_lines = grade_layer.dataProvider()
        provider_lines.addAttributes([QgsField('ID', QVariant.Int)])
        grade_layer.updateFields()

        fid_lines = 1

        # 8) Calcular total para barra de progresso (linhas + pontos)
        qtd_horiz = int((maxy - miny) // intervalo) + 1
        qtd_vert = int((maxx - minx) // intervalo) + 1
        total_linhas = qtd_horiz + qtd_vert

        # Para pontos: cada x => 2 pontos (canto inferior e superior)
        #              cada y => 2 pontos (canto esquerdo e direito)
        total_points = ((qtd_vert) * 2) + ((qtd_horiz) * 2)
        total_steps = total_linhas + total_points

        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)
        steps_done = 0

        # 9) Criar linhas horizontais
        y_atual = miny
        while y_atual <= maxy:
            line_geom = QgsGeometry.fromPolylineXY([
                QgsPointXY(minx, y_atual),
                QgsPointXY(maxx, y_atual)
            ])
            # Intersecta com poligono_externo => somente fora
            linha_fora = line_geom.intersection(poligono_externo)
            if not linha_fora.isEmpty():
                if linha_fora.isMultipart():
                    partes = linha_fora.asMultiPolyline()
                    for parte in partes:
                        feat_line = QgsFeature()
                        feat_line.setGeometry(QgsGeometry.fromPolylineXY(parte))
                        feat_line.setAttributes([fid_lines])
                        provider_lines.addFeature(feat_line)
                        fid_lines += 1
                else:
                    feat_line = QgsFeature()
                    feat_line.setGeometry(linha_fora)
                    feat_line.setAttributes([fid_lines])
                    provider_lines.addFeature(feat_line)
                    fid_lines += 1

            steps_done += 1
            progressBar.setValue(steps_done)
            y_atual += intervalo

        # 10) Criar linhas verticais
        x_atual = minx
        while x_atual <= maxx:
            line_geom = QgsGeometry.fromPolylineXY([
                QgsPointXY(x_atual, miny),
                QgsPointXY(x_atual, maxy)
            ])
            linha_fora = line_geom.intersection(poligono_externo)
            if not linha_fora.isEmpty():
                if linha_fora.isMultipart():
                    partes = linha_fora.asMultiPolyline()
                    for parte in partes:
                        feat_line = QgsFeature()
                        feat_line.setGeometry(QgsGeometry.fromPolylineXY(parte))
                        feat_line.setAttributes([fid_lines])
                        provider_lines.addFeature(feat_line)
                        fid_lines += 1
                else:
                    feat_line = QgsFeature()
                    feat_line.setGeometry(linha_fora)
                    feat_line.setAttributes([fid_lines])
                    provider_lines.addFeature(feat_line)
                    fid_lines += 1

            steps_done += 1
            progressBar.setValue(steps_done)
            x_atual += intervalo

        # Adicionar a camada de linhas ao projeto
        QgsProject.instance().addMapLayer(grade_layer)

        # 11) Criar a camada de pontos: "Coordenadas Limites (Fora)"
        points_layer = QgsVectorLayer(
            f'Point?crs={crs_projeto.authid()}',
            'Coordenadas Limites',
            'memory'
        )
        provider_points = points_layer.dataProvider()
        provider_points.addAttributes([
            QgsField('ID', QVariant.Int),
            QgsField('X', QVariant.Double),
            QgsField('Y', QVariant.Double)
        ])
        points_layer.updateFields()

        fid_points = 1

        # a) Pontos nas bordas verticais (x variando, y = miny ou maxy)
        x_val = minx
        while x_val <= maxx:
            for y_borda in [miny, maxy]:
                pt_geom = QgsGeometry.fromPointXY(QgsPointXY(x_val, y_borda))
                pt_fora = pt_geom.intersection(poligono_externo)
                if not pt_fora.isEmpty():
                    feat_pt = QgsFeature()
                    feat_pt.setGeometry(pt_geom)
                    feat_pt.setAttributes([fid_points, x_val, y_borda])
                    provider_points.addFeature(feat_pt)
                    fid_points += 1
            steps_done += 2
            progressBar.setValue(steps_done)
            x_val += intervalo

        # b) Pontos nas bordas horizontais (y variando, x = minx ou maxx)
        y_val = miny + intervalo
        while y_val < maxy:
            for x_borda in [minx, maxx]:
                pt_geom = QgsGeometry.fromPointXY(QgsPointXY(x_borda, y_val))
                pt_fora = pt_geom.intersection(poligono_externo)
                if not pt_fora.isEmpty():
                    feat_pt = QgsFeature()
                    feat_pt.setGeometry(pt_geom)
                    feat_pt.setAttributes([fid_points, x_borda, y_val])
                    provider_points.addFeature(feat_pt)
                    fid_points += 1
            steps_done += 2
            progressBar.setValue(steps_done)
            y_val += intervalo

        # Adicionar a camada de pontos ao projeto
        QgsProject.instance().addMapLayer(points_layer)

        # Configurar rótulos usando a função solicitada
        self.configurar_rotulos_na_camada_utm(points_layer)

        # 12) Limpar barra e exibir mensagem
        self.iface.messageBar().clearWidgets()
        self.mostrar_mensagem(
            "Grade UTM Ajustada (Fora) e Coordenadas Limites (Fora) criadas com sucesso!",
            "Sucesso")

    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):
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

        # Verifica se um nome de arquivo foi escolhido
        if fileName:
            # Atualiza o último diretório usado nas configurações do QGIS
            settings.setValue("lastDir", os.path.dirname(fileName))

            # Assegura que o arquivo tenha a extensão correta
            if not fileName.endswith(extensao):
                fileName += extensao

        return fileName  # Retorna o caminho completo do arquivo escolhido ou None se cancelado

    def exportar_para_dxf(self):
        """
        Exporta para DXF as camadas "Grade UTM" (linhas) e "Coordenadas Limites" (pontos com rótulos),
        utilizando ezdxf. Os rótulos são exportados como MText, com tamanho igual a 0,5% da escala do mapa,
        e as linhas terão a cor cinza (color 8).
        
        Primeiro, utiliza a função escolher_local_para_salvar para obter o caminho do arquivo.
        Em seguida, procura as camadas pelo nome, converte as geometrias em entidades DXF e salva o arquivo.
        """
        # Seleciona o caminho para salvar (o usuário escolhe o local)
        file_path = self.escolher_local_para_salvar("GradeUTM.dxf", "DXF Files (*.dxf)")
        if not file_path:
            return

        # Obter as camadas pelo nome
        grade_layer = self.obter_camada_pelo_nome("Grade UTM")
        pontos_layer = self.obter_camada_pelo_nome("Coordenadas Limites")
        if not grade_layer or not pontos_layer:
            self.mostrar_mensagem("Camadas 'Grade UTM' e/ou 'Coordenadas Limites' não encontradas.", "Erro")
            return

        # Cria um novo documento DXF (versão R2010)
        doc = ezdxf.new(dxfversion='R2010')
        msp = doc.modelspace()

        # Cria as camadas DXF se ainda não existirem
        if "Grade UTM" not in doc.layers:
            doc.layers.new(name="Grade UTM")
        if "Coordenadas Limites" not in doc.layers:
            doc.layers.new(name="Coordenadas Limites")

        # Exporta as linhas da camada "Grade UTM" como LWPolyline, definindo a cor como cinza (8)
        for feat in grade_layer.getFeatures():
            geom = feat.geometry()
            if geom is None:
                continue
            if geom.isMultipart():
                parts = geom.asMultiPolyline()
                for part in parts:
                    points = [(pt.x(), pt.y()) for pt in part]
                    msp.add_lwpolyline(points, dxfattribs={'layer': "Grade UTM", 'color': 8})
            else:
                part = geom.asPolyline()
                points = [(pt.x(), pt.y()) for pt in part]
                msp.add_lwpolyline(points, dxfattribs={'layer': "Grade UTM", 'color': 8})

        # Calcular o tamanho do texto como 0,5% da escala do mapa
        scale_value = self.iface.mapCanvas().scale()
        char_height = 0.0025 * scale_value

        # Preparar os extremos para definir a lógica dos rótulos dos pontos
        xs = []
        ys = []
        for feat in pontos_layer.getFeatures():
            pt = feat.geometry().asPoint()
            xs.append(pt.x())
            ys.append(pt.y())
        if not xs or not ys:
            self.mostrar_mensagem("Nenhum ponto encontrado na camada 'Coordenadas Limites'.", "Erro")
            return

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        tol = 1e-6

        # Exporta cada ponto como uma entidade MText.
        # Se o ponto estiver na extremidade vertical (Y mínimo ou Y máximo), o rótulo será o valor de X;
        # Se estiver na extremidade horizontal (X mínimo ou X máximo), o rótulo será o valor de Y.
        for feat in pontos_layer.getFeatures():
            pt = feat.geometry().asPoint()
            x = pt.x()
            y = pt.y()
            label = ""
            if abs(y - min_y) < tol or abs(y - max_y) < tol:
                label = str(x)
            elif abs(x - min_x) < tol or abs(x - max_x) < tol:
                label = str(y)
            if label:
                # Adiciona MText com tamanho definido (char_height) e atribui à layer "Coordenadas Limites"
                mtext = msp.add_mtext(label, dxfattribs={'layer': "Coordenadas Limites", 'char_height': char_height})
                # Define a posição de inserção e o alinhamento central (attachment_point = 5)
                mtext.dxf.insert = (x, y)
                mtext.dxf.attachment_point = 5

        try:
            doc.saveas(file_path)
            self.mostrar_mensagem(f"Exportação para DXF concluída: {file_path}", "Sucesso", duracao=3)#, caminho_pasta=os.path.dirname(file_path), caminho_arquivo=file_path)

        except Exception as e:
            self.mostrar_mensagem(f"Erro ao salvar DXF: {e}", "Erro")

    def updatePushButtonDXFState(self):
        """
        Atualiza o estado (habilitado ou não) do pushButtonDXF.
        O botão será habilitado somente se:
          - O projeto estiver em UTM (ou seja, CRS com 'UTM zone' na descrição);
          - As camadas "Grade UTM" e "Coordenadas Limites" existirem no projeto.
        """
        crs = QgsProject.instance().crs()
        # Se o projeto não estiver em UTM ou não houver CRS válido, desabilita o botão.
        if not crs or not self.esta_em_utm(crs):
            self.pushButtonDXF.setEnabled(False)
            return

        # Verifica se as camadas necessárias existem.
        grade_layer = self.obter_camada_pelo_nome("Grade UTM")
        coord_layer = self.obter_camada_pelo_nome("Coordenadas Limites")
        if grade_layer is None or coord_layer is None:
            self.pushButtonDXF.setEnabled(False)
        else:
            self.pushButtonDXF.setEnabled(True)