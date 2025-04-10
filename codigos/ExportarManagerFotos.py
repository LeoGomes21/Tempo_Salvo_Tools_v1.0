from qgis.PyQt.QtWidgets import QDialog, QCheckBox, QPushButton, QFileDialog, QTableView, QAbstractItemView, QProgressBar, QLineEdit, QStyledItemDelegate, QHeaderView, QMessageBox, QGraphicsScene, QFileDialog, QGraphicsPixmapItem, QGraphicsItem, QDialogButtonBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPixmap, QIcon, QPainter, QColor, QBrush, QPen
from PyQt5.QtCore import QDir, Qt, QSize, QEvent, QRect, QPoint, QItemSelectionModel, QSettings, QRectF
from qgis.core import Qgis, QgsMessageLog
from PyQt5 import QtCore, QtWidgets
from PIL.ExifTags import TAGS
from qgis.utils import iface
from qgis.PyQt import uic
from PyQt5 import QtGui
import pandas as pd
import PIL.ExifTags
import PIL.Image
import simplekml
import requests
import zipfile
import time
import os
import re

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'fotos_kmz.ui'))

class FotosManager(QDialog, FORM_CLASS):
    """
    Classe que gerencia a interface de exportação de fotos para KMZ.

    Atributos de classe:
    - autor_texto: str - Texto do autor para exibição.
    - exibir_texto: str - Texto padrão para exibição, usado para definir a largura das imagens.
    - nomes_imagens: dict - Dicionário para armazenar os nomes das imagens carregadas.
    - icones_imagens: dict - Dicionário para armazenar os ícones selecionados para cada imagem.
    - info_imagens: dict - Dicionário para armazenar todas as informações EXIF das imagens carregadas.
    - ultima_pasta: str - Caminho da última pasta usada para selecionar imagens.

    Atributos de instância e métodos são definidos no restante da classe.
    """
    
    autor_texto = ""  # Variável de classe para armazenar o texto do autor
    exibir_texto = "1400"  # Variável de classe para armazenar o texto de exibição padrão
    nomes_imagens = {}  # Dicionário de classe para armazenar os nomes das imagens
    icones_imagens = {}  # Dicionário de classe para armazenar os ícones selecionados
    info_imagens = {}  # Dicionário de classe para armazenar todas as informações das imagens
    ultima_pasta = QDir.homePath()  # Variável de classe para armazenar o caminho da última pasta usada

    def closeEvent(self, event):
        parent = self.parent()
        if parent:
            parent.fotos_kmz_dlg = None
        super(FotosManager, self).closeEvent(event)

    def __init__(self, parent=None):
        """
        Construtor da classe FotosManager. Inicializa a interface do usuário e configura os elementos gráficos e as conexões de sinal.
        
        Parâmetros:
        parent: QWidget (opcional) - O widget pai, se houver.
        
        Funções:
        - Inicializa a interface do usuário a partir do Designer.
        - Define o título da janela.
        - Inicializa a cena para o QGraphicsView onde os ícones serão exibidos.
        - Conecta os sinais dos widgets aos slots correspondentes.
        - Restaura os textos dos QLineEdits para os valores armazenados.
        - Configura os placeholders dos QLineEdits.
        - Inicialmente desativa certos widgets que dependem da presença de imagens carregadas.
        """
        
        super(FotosManager, self).__init__(parent)  # Chama o construtor da classe base QDialog
        self.setupUi(self)  # Configura a interface do usuário a partir do Designer

        self.setWindowTitle("Exporta Fotos para KMZ")  # Define o título da janela

        self.icon_scene = QGraphicsScene(self)  # Inicializa a cena para o graphicsViewIcones
        self.graphicsViewIcones.setScene(self.icon_scene)  # Define a cena no QGraphicsView

        self.connect_signals()  # Conecta os sinais aos slots

        # Restaura os textos dos line edits
        self.lineEdit_Autor.setText(FotosManager.autor_texto)  # Restaura o texto do autor
        self.lineEditExibir.setText(FotosManager.exibir_texto if FotosManager.exibir_texto != "1400" else "")  # Restaura o texto do tempo de exibição
        self.lineEditExibir.setPlaceholderText("1400")  # Define o texto placeholder para lineEditExibir
        self.lineEditExibir2.setPlaceholderText("Automático")  # Define o texto placeholder para lineEditExibir2
        self.lineEditExibir2.setEnabled(False)  # Desativa lineEditExibir2

        # Inicialmente desativa os itens que dependem de imagens carregadas
        self.lineEdit_Nome.setEnabled(False)  # Desativa lineEdit_Nome
        self.comboBoxLinks.setEnabled(False)  # Desativa comboBoxLinks
        self.graphicsViewIcones.setEnabled(False)  # Desativa graphicsViewIcones
        self.pushButtonKMZ.setEnabled(False)  # Desativa pushButtonKMZ

        # Armazena os estados iniciais dos componentes que precisam ser resetados
        self.lineEdit_Nome_texto_inicial = self.lineEdit_Nome.text()
        self.lineEdit_Autor_texto_inicial = FotosManager.autor_texto
        self.lineEditExibir_texto_inicial = self.lineEditExibir.text()
        # Armazena o estilo padrão do botão de cor
        self.pushButton_Screen_default_style = self.pushButton_Screen.styleSheet()
        # Armazena um modelo vazio para resetar a tableViewFotos
        self.tableViewFotos_modelo_inicial = QStandardItemModel()

    def resetar_componentes(self):
        """
        Reseta os componentes do diálogo para o estado inicial.

        Este método realiza as seguintes ações:
        1. Restaura o texto dos campos de entrada (lineEdits) para os valores iniciais ou salvos.
        2. Reseta o modelo de dados da tabela de fotos para o modelo inicial.
        3. Limpa e reseta a cena gráfica que exibe os ícones.
        4. Exibe o primeiro ícone disponível na lista de ícones.
        5. Restaura o botão de overlay (ScreenOverlay) para o estado padrão.
        6. Desativa os componentes que devem ser inativos até que novas ações sejam realizadas.
        7. Atualiza o estado dos itens baseando-se nas condições atuais.

        Funções principais:
        - `self.lineEdit_Nome.setText(self.lineEdit_Nome_texto_inicial)`: Restaura o texto do campo Nome.
        - `self.lineEdit_Autor.setText(FotosManager.autor_texto)`: Restaura o texto do campo Autor.
        - `self.lineEditExibir.setText(self.lineEditExibir_texto_inicial)`: Restaura o texto do campo Exibir.
        - `self.tableViewFotos.setModel(self.tableViewFotos_modelo_inicial)`: Reseta o modelo da tabela de fotos.
        - `self.icon_scene.clear()`: Limpa a cena gráfica que exibe os ícones.
        - `self.pushButton_Screen.setText("ScreenOverlay")`: Reseta o texto do botão de overlay para o valor inicial.
        - `self.pushButton_Screen.setStyleSheet(self.pushButton_Screen_default_style)`: Reseta o estilo do botão de overlay.
        - `self.lineEdit_Nome.setEnabled(False)`: Desativa o campo Nome até que uma nova pasta seja carregada.
        - `self.atualizar_estado_itens()`: Atualiza o estado de todos os itens.

        """

        # Reseta o texto do lineEdit_Nome para o valor inicial
        self.lineEdit_Nome.setText(self.lineEdit_Nome_texto_inicial)
        
        # Reseta o texto do lineEdit_Autor para o valor salvo inicialmente
        self.lineEdit_Autor.setText(FotosManager.autor_texto)
        
        # Reseta o texto do lineEditExibir para o valor inicial
        self.lineEditExibir.setText(self.lineEditExibir_texto_inicial)
        
        # Reseta o modelo da tableViewFotos para um modelo vazio
        self.tableViewFotos.setModel(self.tableViewFotos_modelo_inicial)
        
        # Limpa a cena do graphicsViewIcones
        self.icon_scene.clear()
        
        # Exibe o primeiro ícone da lista no graphicsViewIcones
        if self.comboBoxLinks.count() > 0:
            self.comboBoxLinks.setCurrentIndex(0)  # Seleciona o primeiro item do comboBox
            self.exibir_icone()  # Exibe o ícone selecionado

        # Reseta o estado do pushButton_Screen
        self.pushButton_Screen.setText("ScreenOverlay")  # Reseta o texto para o valor inicial
        self.pushButton_Screen.setStyleSheet(self.pushButton_Screen_default_style)  # Reseta o estilo para o padrão
        self.screen_overlay_data = {}  # Limpa qualquer dado associado ao ScreenOverlay

        # Desativa novamente os itens até que uma nova pasta seja carregada
        self.lineEdit_Nome.setEnabled(False)  # Desativa o campo Nome
        self.comboBoxLinks.setEnabled(False)  # Desativa o comboBox de Links
        self.graphicsViewIcones.setEnabled(False)  # Desativa o gráfico de ícones
        self.pushButtonKMZ.setEnabled(False)  # Desativa o botão de exportação para KMZ

        self.clear_line_edits() # Resetar os campos de informações

        # Reseta qualquer outra configuração adicional necessária
        self.atualizar_estado_itens()  # Atualiza o estado dos itens baseando-se nas condições atuais

    def showEvent(self, event):
        """
        Evento disparado ao mostrar o diálogo.

        Este método garante que, ao ser exibido, o diálogo seja resetado para seu estado inicial,
        restaurando todos os componentes a partir do método `resetar_componentes`.
        """
        super(FotosManager, self).showEvent(event)
        self.resetar_componentes()  # Chama o método para resetar os componentes

    def connect_signals(self):
        """
        Conecta os sinais dos widgets aos slots correspondentes e configura as propriedades dos QLineEdits e QComboBox.
        
        Funções:
        - Conecta os botões a funções específicas.
        - Configura os QLineEdits para serem apenas leitura, permitindo seleção e cópia.
        - Conecta os sinais de alteração de texto dos QLineEdits para armazenar e validar os valores.
        - Centraliza o texto nos QLineEdits.
        - Limita o número de caracteres nos QLineEdits e filtra caracteres inválidos.
        - Carrega os links no comboBoxLinks.
        - Conecta a mudança de índice do comboBoxLinks a funções específicas.
        - Configura o estilo do comboBoxLinks.
        """
        
        self.pushButtonAbrir.clicked.connect(self.abrir_pasta)  # Conecta o botão Abrir à função abrir_pasta
        self.pushButton_Screen.clicked.connect(self.abrir_screen_overlay)  # Conecta o botão Screen à função abrir_screen_overlay
        self.pushButtonFecha.clicked.connect(self.close_dialog)  # Conecta o botão para fechar o diálogo
        self.pushButtonKMZ.clicked.connect(self.exportar_para_kmz)  # Conecta o botão para exportar KMZ

        # Configurar QLineEdit para serem apenas leitura e permitir seleção e cópia
        line_edits = [
            self.lineEditLatitude, self.lineEditLongitude, self.lineEditAltitude,
            self.lineEditResolucao, self.lineEditData, self.lineEditHorario
        ]
        for line_edit in line_edits:
            line_edit.setReadOnly(True)  # Define os QLineEdits como apenas leitura

        # Conectar sinais de alteração de texto dos line edits para armazenar os valores
        self.lineEdit_Autor.textChanged.connect(lambda texto: self.atualizar_texto('autor_texto', texto))  # Conecta a mudança de texto do autor
        self.lineEditExibir.textChanged.connect(lambda texto: self.validar_formatar_exibir('exibir_texto', texto, self.lineEditExibir))  # Conecta a mudança de texto do exibir

        # Centralizar o texto em lineEditExibir e lineEditExibir2
        self.lineEditExibir.setAlignment(Qt.AlignCenter)  # Centraliza o texto em lineEditExibir
        self.lineEditExibir2.setAlignment(Qt.AlignCenter)  # Centraliza o texto em lineEditExibir2

        # Limitar o número de caracteres e filtrar caracteres inválidos
        self.lineEdit_Autor.setMaxLength(32)  # Limita o número de caracteres no lineEdit_Autor
        self.lineEdit_Nome.setMaxLength(32)  # Limita o número de caracteres no lineEdit_Nome
        self.lineEdit_Nome.textChanged.connect(self.filtrar_caracteres_invalidos)  # Conecta a mudança de texto no lineEdit_Nome para filtrar caracteres inválidos

        self.lineEdit_Nome.textChanged.connect(self.atualizar_nome_imagem)  # Conecta a mudança de texto no lineEdit_Nome para atualizar o nome da imagem

        # Carregar os links no comboBoxLinks
        self.carregar_links_comboBox()  # Chama a função para carregar os links no comboBoxLinks

        self.comboBoxLinks.currentIndexChanged.connect(self.exibir_icone)  # Conecta a mudança de índice do comboBoxLinks à função exibir_icone
        self.comboBoxLinks.currentIndexChanged.connect(self.atualizar_icones)  # Conecta a mudança de índice do comboBoxLinks à função atualizar_icones

        # Chamar exibir_icone uma vez para carregar o ícone inicial
        self.exibir_icone()  # Chama a função exibir_icone para carregar o ícone inicial

        # Configurar estilo do comboBoxLinks
        self.comboBoxLinks.setStyleSheet("""
            QComboBox {combobox-popup: 0;}
            QComboBox QAbstractItemView {
                min-height: 140px; /* 10 itens */
                max-height: 140px; /* 10 itens */
                min-width: 90px; /* ajuste conforme necessário */
                max-width: 90px; /* ajuste conforme necessário */}
            """)  # Define o estilo do comboBox

    def filtrar_caracteres_invalidos(self, texto):
        """
        Filtra caracteres inválidos no texto do QLineEdit lineEdit_Nome.
        
        Parâmetros:
        texto: str - O texto inserido no QLineEdit lineEdit_Nome.
        
        Funções:
        - Remove caracteres inválidos do texto.
        - Atualiza o texto do lineEdit_Nome se houver alterações.
        """
        
        caracteres_invalidos = r'\/:*?"\'|'  # Define os caracteres inválidos
        texto_filtrado = ''.join(c for c in texto if c not in caracteres_invalidos)  # Filtra os caracteres inválidos

        # Atualiza o texto do lineEdit_Nome apenas se houver alterações
        if texto != texto_filtrado:  # Verifica se o texto foi alterado após o filtro
            self.lineEdit_Nome.setText(texto_filtrado)  # Atualiza o texto do lineEdit_Nome com o texto filtrado

    def atualizar_estado_itens(self):
        """
        Atualiza o estado dos widgets dependendo da presença de imagens no tableViewFotos.
        
        Funções:
        - Verifica se há imagens no modelo do tableViewFotos.
        - Habilita ou desabilita os widgets lineEdit_Nome, comboBoxLinks, graphicsViewIcones e pushButtonKMZ com base na presença de imagens.
        """
        
        tem_imagens = self.tableViewFotos.model() is not None and self.tableViewFotos.model().rowCount() > 0  # Verifica se há imagens no modelo do tableViewFotos
        self.lineEdit_Nome.setEnabled(tem_imagens)  # Habilita/desabilita lineEdit_Nome
        self.comboBoxLinks.setEnabled(tem_imagens)  # Habilita/desabilita comboBoxLinks
        self.graphicsViewIcones.setEnabled(tem_imagens)  # Habilita/desabilita graphicsViewIcones
        self.pushButtonKMZ.setEnabled(tem_imagens)  # Habilita/desabilita pushButtonKMZ

    def close_dialog(self):
        """
        Fecha o diálogo atual.
        
        Funções:
        - Fecha a janela de diálogo.
        """
        
        self.close()  # Fecha o diálogo

    def abrir_screen_overlay(self):
        """
        Abre um diálogo para adicionar ou editar um ScreenOverlay.
        
        Funções:
        - Cria uma instância do diálogo ScreenOverlay com a janela atual como pai.
        - Executa o diálogo de maneira modal.
        """
        
        dialog = ScreenOverlay(self)  # Cria uma instância do diálogo ScreenOverlay
        dialog.exec_()  # Executa o diálogo de maneira modal

    def atualizar_texto(self, line_edit_name, texto):
        """
        Atualiza o texto armazenado de um QLineEdit específico.

        Parâmetros:
        line_edit_name: str - O nome do atributo de classe que armazena o texto do QLineEdit.
        texto: str - O novo texto a ser armazenado.

        Funções:
        - Usa setattr para atualizar o valor do atributo de classe correspondente ao nome do QLineEdit.
        """
        
        setattr(FotosManager, line_edit_name, texto)  # Atualiza o valor do atributo de classe correspondente ao nome do QLineEdit

    def validar_formatar_exibir(self, attr_name, texto, line_edit):
        """
        Valida e formata o texto inserido no QLineEdit, garantindo que seja numérico e dentro de um limite específico.

        Parâmetros:
        attr_name: str - O nome do atributo de classe que armazena o texto validado.
        texto: str - O texto inserido no QLineEdit.
        line_edit: QLineEdit - O QLineEdit a ser atualizado.

        Funções:
        - Remove todos os caracteres não numéricos do texto.
        - Limita o texto a 4 dígitos.
        - Converte o texto para inteiro e verifica se está dentro do valor máximo permitido (4000).
        - Atualiza o QLineEdit com o texto validado e formatado.
        - Armazena o texto validado no atributo de classe correspondente.
        """
        
        # Remove todos os caracteres não numéricos
        texto = ''.join(filter(str.isdigit, texto))  # Filtra caracteres não numéricos

        # Limita a 4 dígitos
        if len(texto) > 4:
            texto = texto[:4]  # Limita o texto a 4 dígitos

        # Converte para inteiro e verifica o valor máximo
        if texto:
            valor = int(texto)  # Converte o texto para inteiro
            if valor > 4000:
                valor = 4000  # Limita o valor máximo a 4000
            texto = str(valor)  # Converte o valor de volta para string

        # Atualiza o line edit com o texto validado e formatado
        line_edit.setText(texto)  # Atualiza o QLineEdit com o texto validado
        setattr(FotosManager, attr_name, texto)  # Armazena o texto validado no atributo de classe correspondente

    def abrir_pasta(self):
        """
        Abre um diálogo para selecionar uma pasta, carrega imagens da pasta selecionada e atualiza a interface do usuário.

        Funções:
        - Abre um diálogo para selecionar a pasta, usando a última pasta acessada.
        - Atualiza a última pasta usada.
        - Registra o tempo de início do processo de carregamento de imagens.
        - Gera uma lista de caminhos completos das imagens na pasta selecionada, com extensões suportadas.
        - Inicializa uma barra de progresso para o processo de carregamento de imagens.
        - Carrega as imagens no TableView com barra de progresso.
        - Remove a barra de progresso ao finalizar.
        - Calcula o tempo de execução do processo de carregamento de imagens.
        - Mostra uma mensagem de sucesso ou erro, dependendo do resultado.
        """
        
        # Abre um diálogo para selecionar a pasta, usando a última pasta acessada
        pasta = QFileDialog.getExistingDirectory(self, "Selecione a pasta com as imagens", FotosManager.ultima_pasta)

        if pasta:
            # Atualiza a última pasta usada
            FotosManager.ultima_pasta = pasta

            # Registra o tempo de início
            tempo_inicio = time.time()

            # Lista de extensões de imagem suportadas
            extensoes = ['.png', '.jpg', '.jpeg', '.bmp']
            # Lista de caminhos completos das imagens
            caminhos_imagens = [os.path.join(pasta, arquivo) for arquivo in os.listdir(pasta)
                                if any(arquivo.lower().endswith(ext) for ext in extensoes)]

            # Inicializa a barra de progresso
            progressBar, progressMessageBar = self.iniciar_progress_bar(len(caminhos_imagens))

            # Carrega as imagens no TableView com barra de progresso
            self.carregar_imagens_no_tableview(caminhos_imagens, progressBar)

            # Remove a barra de progresso ao finalizar
            iface.messageBar().popWidget(progressMessageBar)

            # Calcula o tempo de execução
            tempo_execucao = time.time() - tempo_inicio

            # Mostra uma mensagem de sucesso
            self.mostrar_mensagem(f"Imagens carregadas em {tempo_execucao:.2f} segundos.", "Sucesso")
        else:
            # Mostra uma mensagem de erro se nenhuma pasta foi selecionada
            self.mostrar_mensagem("Nenhuma pasta foi selecionada.", "Erro")

    def iniciar_progress_bar(self, total_steps):
        """
        Inicializa e estiliza uma barra de progresso para indicar o carregamento de imagens.

        Parâmetros:
        total_steps: int - O número total de etapas que a barra de progresso representará.

        Funções:
        - Cria uma mensagem de progresso na barra de mensagens do QGIS.
        - Cria e configura uma instância de QProgressBar.
        - Estiliza a barra de progresso.
        - Adiciona a barra de progresso ao layout da barra de mensagens e exibe na interface.
        - Define o valor máximo da barra de progresso com base no número total de etapas.
        - Retorna a barra de progresso e a mensagem de progresso para atualização futura.
        """
        
        progressMessageBar = iface.messageBar().createMessage("Carregando imagens")  # Cria uma mensagem de progresso na barra de mensagens do QGIS
        progressBar = QProgressBar()  # Cria uma instância da QProgressBar
        progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Alinha a barra de progresso à esquerda e verticalmente ao centro
        progressBar.setFormat("%p% - %v de %m Imagens Carregadas")  # Define o formato da barra de progresso
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
                min-height: 5px;
            }""")

        # Adiciona a progressBar ao layout da progressMessageBar e exibe na interface
        progressMessageBar.layout().addWidget(progressBar)  # Adiciona a barra de progresso ao layout da mensagem de progresso
        iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)  # Exibe a mensagem de progresso na barra de mensagens do QGIS

        # Define o valor máximo da barra de progresso com base no número total de etapas
        progressBar.setMaximum(total_steps)  # Define o valor máximo da barra de progresso

        return progressBar, progressMessageBar  # Retorna a barra de progresso e a mensagem de progresso

    def mostrar_mensagem(self, texto, tipo, duracao=3):
        """
        Exibe uma mensagem na barra de mensagens da interface do QGIS.

        Parâmetros:
        texto: str - O texto da mensagem a ser exibida.
        tipo: str - O tipo da mensagem, que pode ser "Erro" ou "Sucesso".
        duracao: int - A duração da mensagem em segundos (padrão é 3 segundos).

        Funções:
        - Obtém a barra de mensagens da interface do QGIS.
        - Exibe uma mensagem de erro ou sucesso com o nível apropriado baseado no tipo fornecido.
        """
        
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

    def mostrar_coordenadas(self):
        """
        Exibe as coordenadas, altitude, resolução, data e horário da imagem selecionada no TableView.

        Funções:
        - Obtém a seleção atual do TableView.
        - Se não houver seleção, retorna sem fazer nada.
        - Obtém o caminho da imagem selecionada e atualiza o lineEdit_Nome.
        - Lê os dados EXIF da imagem, se disponíveis.
        - Obtém e converte os valores de latitude, longitude e altitude dos dados EXIF.
        - Converte as coordenadas para o formato DMS (graus, minutos, segundos).
        - Atualiza os QLineEdits correspondentes com as coordenadas, altitude, resolução, data e horário.
        - Em caso de erro, define os QLineEdits como "Erro".

        Exceções:
        - Lança uma ValueError se não houver dados EXIF.
        - Lança uma Exception genérica para outros erros.
        """

        # Obtém a seleção atual do TableView
        indexes = self.tableViewFotos.selectedIndexes()
        if not indexes:  # Se não houver seleção, retorna
            return

        # Obtém o caminho da imagem selecionada
        index = indexes[0]
        caminho_imagem = index.data(Qt.UserRole)
        self.lineEdit_Nome.setText(FotosManager.nomes_imagens.get(caminho_imagem, "N/A"))  # Atualiza o lineEdit_Nome

        # Lê os dados EXIF da imagem
        try:
            with PIL.Image.open(caminho_imagem) as imagem:  # Abre a imagem usando PIL
                exif_data = imagem._getexif()  # Obtém os dados EXIF
                if not exif_data:
                    raise ValueError("Sem dados EXIF")  # Lança um erro se não houver dados EXIF

                exif = {
                    TAGS.get(k, k): v
                    for k, v in exif_data.items()
                    if k in TAGS
                }  # Converte os dados EXIF para um dicionário legível

                # Obtém os valores de latitude, longitude e altitude dos dados EXIF
                gps_info = exif.get("GPSInfo")
                if gps_info:
                    lat = self._get_gps_coordinate(gps_info, 2, gps_info.get(1))  # Obtém a latitude
                    lon = self._get_gps_coordinate(gps_info, 4, gps_info.get(3))  # Obtém a longitude
                    alt = self._get_gps_altitude(gps_info)  # Obtém a altitude

                    # Converter coordenadas para DMS
                    lat_ref = gps_info.get(1, 'N')  # Obtém a referência de latitude
                    lon_ref = gps_info.get(3, 'E')  # Obtém a referência de longitude
                    lat_dms = self.decimal_to_dms(lat, lat_ref)  # Converte a latitude para DMS
                    lon_dms = self.decimal_to_dms(lon, lon_ref)  # Converte a longitude para DMS

                    # Define os valores nos QLineEdits correspondentes
                    self.lineEditLatitude.setText(lat_dms)
                    self.lineEditLongitude.setText(lon_dms)
                    self.lineEditAltitude.setText(f"{alt:.2f} m" if isinstance(alt, float) else str(alt))
                else:
                    self.lineEditLatitude.setText("N/A")
                    self.lineEditLongitude.setText("N/A")
                    self.lineEditAltitude.setText("N/A")

                # Mostrar resolução, data e horário
                self.mostrar_resolucao_data_horario(caminho_imagem, exif)

        except Exception as e:
            # self.mostrar_mensagem(f"Erro ao ler dados EXIF: {str(e)}")
            self.lineEditLatitude.setText("Erro")
            self.lineEditLongitude.setText("Erro")
            self.lineEditAltitude.setText("Erro")
            self.lineEditResolucao.setText("Erro")
            self.lineEditData.setText("Erro")
            self.lineEditHorario.setText("Erro")

    def _get_gps_coordinate(self, gps_info, ref_index, ref):
        """
        Converte os valores GPS em coordenadas decimais.

        Parâmetros:
        gps_info: dict - O dicionário contendo as informações GPS extraídas dos dados EXIF.
        ref_index: int - O índice da coordenada específica (latitude ou longitude) nos dados GPS.
        ref: str - A referência da coordenada (N, S, E, W).

        Retorna:
        float - A coordenada convertida em decimal ou "N/A" em caso de erro.

        Funções:
        - Obtém a coordenada GPS do dicionário gps_info usando o índice fornecido.
        - Verifica se a coordenada e a referência estão presentes.
        - Converte a coordenada de graus, minutos e segundos para decimal.
        - Ajusta o sinal da coordenada com base na referência (N, S, E, W).
        - Retorna a coordenada decimal ou "N/A" em caso de erro.
        """
        
        try:
            # Converte os valores GPS em coordenadas decimais
            coord = gps_info.get(ref_index)  # Obtém a coordenada GPS do dicionário gps_info
            if not coord or not ref:  # Verifica se a coordenada e a referência estão presentes
                return "N/A"

            coord = [float(x) for x in coord]  # Converte os valores da coordenada para float
            coord = coord[0] + coord[1] / 60 + coord[2] / 3600  # Converte a coordenada de graus, minutos e segundos para decimal

            if ref in ['S', 'W']:  # Ajusta o sinal da coordenada com base na referência
                coord = -coord

            return coord  # Retorna a coordenada decimal
        except Exception as e:
            self.mostrar_mensagem(f"Erro ao converter coordenadas: {str(e)}")
            return "N/A"  # Retorna "N/A" em caso de erro

    def _get_gps_altitude(self, gps_info):
        """
        Obtém a altitude dos dados GPS dos dados EXIF.

        Parâmetros:
        gps_info: dict - O dicionário contendo as informações GPS extraídas dos dados EXIF.

        Retorna:
        float - A altitude em metros ou "N/A" em caso de erro.

        Funções:
        - Obtém a altitude dos dados GPS usando a chave 6.
        - Verifica se a altitude está presente.
        - Converte a altitude para float.
        - Verifica a referência da altitude (acima ou abaixo do nível do mar) usando a chave 5.
        - Ajusta o valor da altitude se a referência for abaixo do nível do mar.
        - Retorna a altitude ou "N/A" em caso de erro.
        """
        
        try:
            # A chave para altitude nos dados EXIF é geralmente 6
            alt = gps_info.get(6)  # Obtém a altitude dos dados GPS
            if not alt:  # Verifica se a altitude está presente
                return "N/A"
            altitude = float(alt)  # Converte a altitude para float

            # Verificar a referência da altitude (acima ou abaixo do nível do mar)
            alt_ref = gps_info.get(5, 0)  # Obtém a referência da altitude usando a chave 5
            if alt_ref == 1:  # Ajusta o valor da altitude se a referência for abaixo do nível do mar
                altitude = -altitude

            return altitude  # Retorna a altitude
        except Exception as e:
            return "N/A"  # Retorna "N/A" em caso de erro

    def mostrar_resolucao_data_horario(self, caminho_imagem, exif):
        """
        Exibe a resolução, data e horário da imagem nos QLineEdits correspondentes.

        Parâmetros:
        caminho_imagem: str - O caminho da imagem a ser aberta.
        exif: dict - O dicionário contendo as informações EXIF extraídas dos dados da imagem.

        Funções:
        - Abre a imagem usando PIL e obtém a resolução.
        - Define a resolução nos QLineEdits correspondentes.
        - Obtém a data e a hora em que a foto foi tirada a partir dos dados EXIF.
        - Formata a data e a hora e define nos QLineEdits correspondentes.
        - Em caso de erro, define os QLineEdits como "Erro".
        """
        
        try:
            with PIL.Image.open(caminho_imagem) as imagem:  # Abre a imagem usando PIL
                # Obtém a resolução da imagem
                width, height = imagem.size  # Obtém a largura e altura da imagem
                self.lineEditResolucao.setText(f"{width}x{height}")  # Define a resolução no QLineEdit correspondente

                # Obtém a data e a hora em que a foto foi tirada
                data_hora = exif.get("DateTimeOriginal")  # Obtém a data e hora dos dados EXIF
                if data_hora:
                    data, hora = data_hora.split(" ")  # Separa a data e a hora
                    ano, mes, dia = data.split(":")  # Separa ano, mês e dia
                    self.lineEditData.setText(f"{dia}/{mes}/{ano}")  # Define a data no QLineEdit correspondente
                    self.lineEditHorario.setText(hora)  # Define a hora no QLineEdit correspondente
                else:
                    self.lineEditData.setText("N/A")  # Define "N/A" no QLineEdit se não houver data
                    self.lineEditHorario.setText("N/A")  # Define "N/A" no QLineEdit se não houver hora
        except Exception as e:
            self.lineEditResolucao.setText("Erro")  # Define "Erro" no QLineEdit em caso de exceção
            self.lineEditData.setText("Erro")  # Define "Erro" no QLineEdit em caso de exceção
            self.lineEditHorario.setText("Erro")  # Define "Erro" no QLineEdit em caso de exceção

    def atualizar_nome_imagem(self, texto):
        """
        Atualiza o nome da imagem selecionada no dicionário nomes_imagens da classe FotosManager.

        Parâmetros:
        texto: str - O novo nome da imagem a ser atualizado.

        Funções:
        - Obtém a seleção atual do TableView.
        - Se não houver seleção, retorna sem fazer nada.
        - Obtém o caminho da imagem selecionada.
        - Atualiza o dicionário nomes_imagens com o novo nome para a imagem selecionada.
        """
        
        indexes = self.tableViewFotos.selectedIndexes()  # Obtém a seleção atual do TableView
        if not indexes:  # Se não houver seleção, retorna
            return

        index = indexes[0]  # Obtém o primeiro índice selecionado
        caminho_imagem = index.data(Qt.UserRole)  # Obtém o caminho da imagem do índice selecionado
        FotosManager.nomes_imagens[caminho_imagem] = texto  # Atualiza o dicionário nomes_imagens com o novo nome

    def remover_imagem(self, caminho_imagem):
        """
        Remove a imagem especificada do TableView e atualiza a interface do usuário.

        Parâmetros:
        caminho_imagem: str - O caminho da imagem a ser removida.

        Funções:
        - Obtém o modelo do TableView.
        - Encontra e remove a linha correspondente à imagem especificada.
        - Remove a imagem do dicionário nomes_imagens.
        - Limpa os QLineEdits após remover a imagem.
        - Seleciona a próxima imagem no TableView, se disponível.
        - Atualiza o estado dos widgets dependentes da presença de imagens no TableView.
        """
        
        modelo = self.tableViewFotos.model()  # Obtém o modelo do TableView
        current_index = None
        for row in range(modelo.rowCount()):  # Itera pelas linhas do modelo
            item = modelo.item(row)
            if item.data(Qt.UserRole) == caminho_imagem:  # Encontra a linha correspondente à imagem especificada
                current_index = row
                modelo.removeRow(row)  # Remove a linha do modelo
                break
        if caminho_imagem in FotosManager.nomes_imagens:
            del FotosManager.nomes_imagens[caminho_imagem]  # Remove a imagem do dicionário nomes_imagens
        
        # Limpar os line edits após remover a imagem
        self.clear_line_edits()  # Limpa os QLineEdits

        # Selecionar a próxima imagem, se disponível
        if current_index is not None:  # Verifica se uma linha foi removida
            if current_index < modelo.rowCount():
                next_index = modelo.index(current_index, 0)  # Seleciona a próxima linha
            else:
                next_index = modelo.index(current_index - 1, 0)  # Seleciona a linha anterior
            
            if next_index.isValid():
                self.tableViewFotos.selectionModel().select(next_index, QItemSelectionModel.SelectCurrent)  # Seleciona a próxima imagem
                self.mostrar_coordenadas()  # Exibe as coordenadas da próxima imagem

        # Atualizar o estado dos itens
        self.atualizar_estado_itens()  # Atualiza o estado dos widgets

    def clear_line_edits(self):
        """
        Limpa o texto de todos os QLineEdits relacionados às informações da imagem.

        Funções:
        - Limpa os QLineEdits para latitude, longitude, altitude, resolução, data, horário e nome da imagem.
        """
        
        self.lineEditLatitude.clear()  # Limpa o QLineEdit para latitude
        self.lineEditLongitude.clear()  # Limpa o QLineEdit para longitude
        self.lineEditAltitude.clear()  # Limpa o QLineEdit para altitude
        self.lineEditResolucao.clear()  # Limpa o QLineEdit para resolução
        self.lineEditData.clear()  # Limpa o QLineEdit para data
        self.lineEditHorario.clear()  # Limpa o QLineEdit para horário
        self.lineEdit_Nome.clear()  # Limpa o QLineEdit para o nome da imagem

    def carregar_links_comboBox(self):
        """
        Carrega uma lista de URLs de ícones no comboBoxLinks, associando cada URL com um nome.

        Funções:
        - Define uma lista de URLs de ícones.
        - Para cada URL na lista, extrai o nome do arquivo sem extensão.
        - Adiciona o nome e a URL ao comboBoxLinks.
        """
        
        icon_urls = [  # Define uma lista de URLs de ícones
            "http://maps.google.com/mapfiles/kml/paddle/go.png",
            "http://maps.google.com/mapfiles/kml/shapes/parks.png",
            "http://maps.google.com/mapfiles/kml/shapes/water.png",
            "http://maps.google.com/mapfiles/kml/shapes/campground.png",
            "http://maps.google.com/mapfiles/kml/shapes/man.png",
            "http://maps.google.com/mapfiles/kml/shapes/woman.png",
            "http://maps.google.com/mapfiles/kml/shapes/flag.png",
            "http://maps.google.com/mapfiles/kml/shapes/info.png",
            "http://maps.google.com/mapfiles/kml/shapes/airports.png",
            "http://maps.google.com/mapfiles/kml/shapes/poi.png",
            "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png",
            "http://maps.google.com/mapfiles/kml/paddle/ylw-diamond.png",
            "http://maps.google.com/mapfiles/kml/paddle/red-stars.png",
            "http://maps.google.com/mapfiles/kml/paddle/ltblu-square.png",
            "http://maps.google.com/mapfiles/kml/paddle/orange-circle.png",
            "http://maps.google.com/mapfiles/kml/shapes/ranger_station.png",
            "http://earth.google.com/images/kml-icons/track-directional/track-8.png",
            "http://maps.google.com/mapfiles/kml/shapes/gas_stations.png",
            "https://www.gstatic.com/earth/images/stockicons/190201-2016-animal-paw_4x.png",
        ]
        for url in icon_urls:  # Para cada URL na lista
            name = os.path.splitext(os.path.basename(url))[0]  # Extrai o nome do arquivo sem extensão
            self.comboBoxLinks.addItem(name, url)  # Adiciona o nome e a URL ao comboBoxLinks

    def atualizar_icone_selecionado(self):
        """
        Atualiza o ícone selecionado no comboBoxLinks com base na imagem atualmente selecionada no TableView.

        Funções:
        - Obtém a seleção atual do TableView.
        - Se não houver seleção, retorna sem fazer nada.
        - Obtém o caminho da imagem selecionada.
        - Se a imagem selecionada estiver no dicionário icones_imagens, atualiza o comboBoxLinks para o ícone correspondente.
        - Bloqueia e desbloqueia sinais para evitar loops de sinal.
        - Chama a função exibir_icone para atualizar a exibição do ícone no graphicsViewIcones.
        """
        
        indexes = self.tableViewFotos.selectedIndexes()  # Obtém a seleção atual do TableView
        if not indexes:  # Se não houver seleção, retorna
            return

        index = indexes[0]  # Obtém o primeiro índice selecionado
        caminho_imagem = index.data(Qt.UserRole)  # Obtém o caminho da imagem do índice selecionado
        if caminho_imagem in FotosManager.icones_imagens:  # Verifica se a imagem está no dicionário icones_imagens
            icon_url = FotosManager.icones_imagens[caminho_imagem]  # Obtém a URL do ícone
            self.comboBoxLinks.blockSignals(True)  # Bloqueia sinais para evitar loops
            self.comboBoxLinks.setCurrentIndex(self.comboBoxLinks.findData(icon_url))  # Atualiza o índice do comboBoxLinks
            self.comboBoxLinks.blockSignals(False)  # Desbloqueia sinais
            self.exibir_icone()  # Chama a função para atualizar a exibição do ícone no graphicsViewIcones

    def escolher_local_para_salvar(self, nome_padrao, tipo_arquivo):
        """
        Exibe uma caixa de diálogo para salvar arquivos, sugerindo um nome e local com base no último diretório utilizado.

        Parâmetros:
        nome_padrao: str - O nome padrão sugerido para o arquivo a ser salvo.
        tipo_arquivo: str - O tipo de arquivo (extensão) a ser salvo, ex: "KMZ files (*.kmz)".

        Retorna:
        str - O caminho completo do arquivo escolhido ou None se cancelado.

        Funções:
        - Acessa as configurações do QGIS para recuperar o último diretório utilizado.
        - Configura as opções da caixa de diálogo para salvar arquivos.
        - Gera um nome de arquivo único com um sufixo numérico se o arquivo já existir.
        - Exibe a caixa de diálogo para salvar arquivos com o nome proposto.
        - Atualiza o último diretório usado nas configurações do QGIS se um nome de arquivo foi escolhido.
        - Assegura que o arquivo tenha a extensão correta.
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

        # Verifica se um nome de arquivo foi escolhido
        if fileName:
            # Atualiza o último diretório usado nas configurações do QGIS
            settings.setValue("lastDir", os.path.dirname(fileName))

            # Assegura que o arquivo tenha a extensão correta
            if not fileName.endswith(extensao):
                fileName += extensao

        return fileName  # Retorna o caminho completo do arquivo escolhido ou None se cancelado

    def gms_to_decimal(self, gms, direction):
        """
        Converte coordenadas em formato GMS (graus, minutos, segundos) para decimal.

        Parâmetros:
        gms: str - A coordenada em formato GMS, ex: "50°30'30".
        direction: str - A direção da coordenada ('N', 'S', 'E', 'W').

        Retorna:
        float - A coordenada em formato decimal.

        Funções:
        - Divide a string GMS em graus, minutos e segundos.
        - Converte graus, minutos e segundos para float.
        - Calcula a coordenada em decimal.
        - Ajusta o sinal da coordenada com base na direção (N, S, E, W).
        """
        
        parts = gms.split('°')  # Divide a string GMS em partes
        degrees = float(parts[0])  # Converte a parte dos graus para float
        minutes = float(parts[1].split("'")[0])  # Converte a parte dos minutos para float
        seconds = float(parts[1].split("'")[1].replace('"', ''))  # Converte a parte dos segundos para float

        decimal = degrees + minutes / 60 + seconds / 3600  # Calcula a coordenada em decimal

        if direction in ['S', 'W']:  # Ajusta o sinal da coordenada com base na direção
            decimal = -decimal

        return decimal  # Retorna a coordenada em formato decimal

    def gerar_excel(self, excel_file_path, imagens_para_incluir):
        """
        Gera um arquivo Excel contendo informações sobre as imagens incluídas.

        O método realiza as seguintes operações:
        1. Itera sobre a lista de caminhos das imagens fornecida em `imagens_para_incluir`.
        2. Para cada imagem, obtém as informações associadas, como nome, latitude, longitude, altitude, data e horário.
        3. Organiza esses dados em uma lista de listas, onde cada sublista contém as informações de uma imagem.
        4. Converte a lista de dados em um DataFrame do pandas, com colunas nomeadas.
        5. Salva o DataFrame em um arquivo Excel no caminho especificado por `excel_file_path`, sem incluir um índice.

        Parâmetros:
        - excel_file_path (str): O caminho completo onde o arquivo Excel será salvo.
        - imagens_para_incluir (list): Lista de caminhos de imagens a serem incluídas no Excel.
        """

        data = []  # Inicializa uma lista para armazenar os dados das imagens

        for caminho_imagem in imagens_para_incluir:  # Itera sobre os caminhos das imagens fornecidos
            info = FotosManager.info_imagens.get(caminho_imagem, {})  # Obtém as informações da imagem do dicionário info_imagens
            nome_imagem = FotosManager.nomes_imagens.get(caminho_imagem, os.path.splitext(os.path.basename(caminho_imagem))[0])  # Obtém o nome da imagem ou usa o nome do arquivo como fallback
            latitude = info.get("latitude", "N/A")  # Obtém a latitude da imagem ou "N/A" se não estiver disponível
            longitude = info.get("longitude", "N/A")  # Obtém a longitude da imagem ou "N/A" se não estiver disponível
            altitude = info.get("altitude", "N/A")  # Obtém a altitude da imagem ou "N/A" se não estiver disponível
            data_imagem = info.get("data", "N/A")  # Obtém a data da imagem ou "N/A" se não estiver disponível
            hora = info.get("hora", "N/A")  # Obtém o horário da imagem ou "N/A" se não estiver disponível
            data.append([nome_imagem, latitude, longitude, altitude, data_imagem, hora])  # Adiciona uma lista com as informações da imagem à lista de dados

        # Converte a lista de dados em um DataFrame do pandas com as colunas nomeadas
        df = pd.DataFrame(data, columns=["Nome", "Latitude", "Longitude", "Altitude", "Data", "Horário"])

        # Salva o DataFrame em um arquivo Excel no caminho especificado, sem incluir um índice
        df.to_excel(excel_file_path, index=False)

    def exportar_para_kmz(self):
        """
        Exporta os dados das imagens para um arquivo KMZ, incluindo KML e Excel.

        Funções:
        - Seleciona o local para salvar o arquivo KMZ.
        - Gera o conteúdo KML e obtém a lista de imagens a serem incluídas.
        - Adiciona conteúdo ScreenOverlay ao KML, se disponível.
        - Escreve o conteúdo KML em um arquivo temporário.
        - Cria um arquivo KMZ, incluindo o KML e as imagens.
        - Remove o arquivo KML temporário.
        - Gera um arquivo Excel com os dados das imagens.
        - Exibe uma mensagem de sucesso com o tempo de execução.
        - Abre o arquivo KMZ gerado, se houver imagens incluídas.
        - Exibe mensagens de erro, se ocorrerem.
        """
        
        QgsMessageLog.logMessage("Iniciando exportação para KMZ", 'FotosEdit', level=Qgis.Critical)
        fileName = self.escolher_local_para_salvar("FOTOS.kmz", "KMZ files (*.kmz)")

        if not fileName:  # Se nenhum nome de arquivo for escolhido, retorna
            return

        kml_content, imagens_para_incluir = self.gerar_conteudo_kml()  # Gera o conteúdo KML e obtém a lista de imagens

        if not kml_content:  # Se o conteúdo KML não for gerado, exibe uma mensagem de erro
            self.mostrar_mensagem("Erro ao gerar conteúdo KML.", "Erro")
            return

        # Adiciona conteúdo ScreenOverlay ao KML, se disponível
        if hasattr(self, 'screen_overlay_data') and isinstance(self.screen_overlay_data, dict) and self.screen_overlay_data.get("image_path"):
            screen_overlay_content = self.gerar_conteudo_screenoverlay(self.screen_overlay_data)
            kml_content = kml_content.replace('</Document>', screen_overlay_content + '</Document>')

        kml_path = os.path.splitext(fileName)[0] + ".kml"
        
        # Registrar o tempo de início
        tempo_inicio = time.time()

        # Inicializar a barra de progresso
        total_steps = len(imagens_para_incluir) + 2  # +2 para incluir a etapa de escrever o KML e criar o arquivo Excel
        progressBar, progressMessageBar = self.iniciar_progress_bar(total_steps)

        try:
            with open(kml_path, 'w', encoding='utf-8') as kml_file:  # Escreve o conteúdo KML em um arquivo temporário
                kml_file.write(kml_content)
            progressBar.setValue(1)  # Atualizar a barra de progresso para a etapa de escrever o KML

            try:
                with zipfile.ZipFile(fileName, 'w', zipfile.ZIP_DEFLATED) as kmz:  # Cria um arquivo KMZ
                    kmz.write(kml_path, os.path.basename(kml_path))
                    for i, caminho_imagem in enumerate(imagens_para_incluir):  # Adiciona cada imagem ao KMZ

                        kmz.write(caminho_imagem, 'files/' + os.path.basename(caminho_imagem))
                        progressBar.setValue(i + 2)  # Atualizar a barra de progresso para cada imagem

                    # Adiciona a imagem ScreenOverlay ao KMZ, se disponível
                    if hasattr(self, 'screen_overlay_data') and isinstance(self.screen_overlay_data, dict) and self.screen_overlay_data.get("image_path"):
                        kmz.write(self.screen_overlay_data["image_path"], 'files/' + os.path.basename(self.screen_overlay_data["image_path"]))

                os.remove(kml_path)  # Remove o arquivo KML temporário
                
                # Gerar o arquivo Excel
                excel_file_path = os.path.splitext(fileName)[0] + ".xlsx"
                self.gerar_excel(excel_file_path, imagens_para_incluir)
                progressBar.setValue(total_steps)  # Atualizar a barra de progresso para a etapa de criar o arquivo Excel

                # Calcular o tempo de execução
                tempo_execucao = time.time() - tempo_inicio

                # Exibir mensagem de sucesso com o tempo de execução
                self.mostrar_mensagem(f"KMZ exportado com sucesso para {fileName} em {tempo_execucao:.2f} segundos.", "Sucesso")

                # Abrir o arquivo KMZ gerado
                if len(imagens_para_incluir) > 0:
                    os.startfile(fileName)

            except Exception as e:  # Captura exceções durante a criação do KMZ
                self.mostrar_mensagem(f"Erro ao criar o arquivo KMZ: {str(e)}", "Erro")

        finally:
            if os.path.exists(kml_path):  # Remove o arquivo KML temporário, se existir
                os.remove(kml_path)
            # Remover a barra de progresso
            iface.messageBar().popWidget(progressMessageBar)

    def gerar_conteudo_screenoverlay(self, screen_overlay_data):
        """
        Gera o conteúdo KML para o ScreenOverlay.

        Parâmetros:
        screen_overlay_data: dict - O dicionário contendo os dados do ScreenOverlay.

        Retorna:
        str - O conteúdo KML gerado para o ScreenOverlay.

        Funções:
        - Gera o conteúdo KML para o ScreenOverlay com base nos dados fornecidos.
        - Adiciona o elemento ScreenOverlay com suas propriedades ao KML.
        - Retorna o conteúdo KML como uma string.
        """

        # Cria a lista de strings que compõem o conteúdo do ScreenOverlay em KML
        screen_overlay_content = [
            '<ScreenOverlay>',  # Abre o elemento ScreenOverlay
            '<name>logo</name>',  # Define o nome do ScreenOverlay
            '<Icon>',  # Abre o elemento Icon
            f'<href>files/{os.path.basename(screen_overlay_data["image_path"])}</href>',  # Define o caminho do ícone
            '</Icon>',  # Fecha o elemento Icon
            f'<overlayXY x="{screen_overlay_data["overlayXY"][0]}" y="{screen_overlay_data["overlayXY"][1]}" xunits="fraction" yunits="fraction"/>',  # Define as coordenadas overlayXY
            f'<screenXY x="{screen_overlay_data["screenXY"][0]}" y="{screen_overlay_data["screenXY"][1]}" xunits="pixels" yunits="pixels"/>',  # Define as coordenadas screenXY
            f'<rotationXY x="{screen_overlay_data["rotationXY"][0]}" y="{screen_overlay_data["rotationXY"][1]}" xunits="fraction" yunits="fraction"/>',  # Define as coordenadas rotationXY
            f'<size x="{screen_overlay_data["sizeXY"][0]}" y="{screen_overlay_data["sizeXY"][1]}" xunits="pixels" yunits="pixels"/>',  # Define o tamanho do ScreenOverlay
            '</ScreenOverlay>'  # Fecha o elemento ScreenOverlay
        ]
        
        return '\n'.join(screen_overlay_content)  # Junta todas as partes do conteúdo e retorna como uma única string

    def definir_icone_padrao(self, icon_url):
        """
        Define um ícone padrão para todas as imagens no TableView que ainda não possuem um ícone associado.

        Parâmetros:
        icon_url: str - A URL do ícone padrão a ser definido.

        Funções:
        - Verifica se a URL do ícone é válida.
        - Obtém o modelo do TableView.
        - Itera sobre todas as linhas do modelo.
        - Define o ícone padrão para as imagens que ainda não possuem um ícone associado.
        """
        
        if not icon_url:  # Verifica se a URL do ícone é válida
            return

        modelo = self.tableViewFotos.model()  # Obtém o modelo do TableView
        if modelo is None or modelo.rowCount() == 0:  # Verifica se o modelo é válido e possui linhas
            return

        for row in range(modelo.rowCount()):  # Itera sobre todas as linhas do modelo
            item = modelo.item(row)  # Obtém o item da linha
            caminho_imagem = item.data(Qt.UserRole)  # Obtém o caminho da imagem do item
            if caminho_imagem not in FotosManager.icones_imagens:  # Verifica se a imagem não possui um ícone associado
                FotosManager.icones_imagens[caminho_imagem] = icon_url  # Define o ícone padrão para a imagem

    def atualizar_icones(self):
        """
        Atualiza os ícones das imagens no TableView com base na seleção atual ou define um ícone para todas as imagens.

        Funções:
        - Obtém a seleção atual do TableView.
        - Se não houver seleção, define o ícone para todas as imagens.
        - Se houver seleção, define o ícone apenas para a imagem selecionada.
        """
        
        indexes = self.tableViewFotos.selectedIndexes()  # Obtém a seleção atual do TableView
        current_url = self.comboBoxLinks.currentData()  # Obtém a URL do ícone selecionado no comboBoxLinks

        if not indexes:  # Se não houver seleção, define o ícone para todas as imagens
            for caminho_imagem in FotosManager.nomes_imagens.keys():  # Itera sobre todas as imagens
                FotosManager.icones_imagens[caminho_imagem] = current_url  # Define o ícone para a imagem
        else:
            # Define o ícone apenas para a imagem selecionada
            index = indexes[0]  # Obtém o primeiro índice selecionado
            caminho_imagem = index.data(Qt.UserRole)  # Obtém o caminho da imagem do índice selecionado
            FotosManager.icones_imagens[caminho_imagem] = current_url  # Define o ícone para a imagem selecionada

    def atualizar_icone_imagem_selecionada(self):
        """
        Atualiza o ícone da imagem atualmente selecionada no TableView.

        Funções:
        - Obtém a seleção atual do TableView.
        - Se não houver seleção, retorna sem fazer nada.
        - Obtém o caminho da imagem selecionada.
        - Obtém a URL do ícone selecionado no comboBoxLinks.
        - Atualiza o dicionário icones_imagens com o novo ícone para a imagem selecionada.
        - Chama a função exibir_icone para atualizar a exibição do ícone no graphicsViewIcones.
        """
        
        indexes = self.tableViewFotos.selectedIndexes()  # Obtém a seleção atual do TableView
        if not indexes:  # Se não houver seleção, retorna
            return

        index = indexes[0]  # Obtém o primeiro índice selecionado
        caminho_imagem = index.data(Qt.UserRole)  # Obtém o caminho da imagem do índice selecionado
        current_url = self.comboBoxLinks.currentData()  # Obtém a URL do ícone selecionado no comboBoxLinks

        if current_url:  # Se a URL do ícone for válida
            FotosManager.icones_imagens[caminho_imagem] = current_url  # Atualiza o ícone da imagem selecionada no dicionário icones_imagens
            self.exibir_icone()  # Chama a função para atualizar a exibição do ícone no graphicsViewIcones

    def exibir_icone(self):
        """
        Exibe o ícone selecionado no comboBoxLinks no graphicsViewIcones.

        Funções:
        - Obtém a URL do ícone selecionado no comboBoxLinks.
        - Se a URL for válida, faz uma requisição HTTP para obter a imagem do ícone.
        - Carrega a imagem em um QPixmap e configura o graphicsViewIcones para exibir o ícone.
        - Define as dicas de renderização para antialiasing e transformação suave de pixmap.
        - Limpa a cena atual e adiciona o novo ícone à cena.
        - Ajusta a cena para se adaptar ao tamanho do ícone mantendo a proporção.
        - Em caso de erro na requisição HTTP, exibe uma mensagem de erro.
        """
        
        current_url = self.comboBoxLinks.currentData()  # Obtém a URL do ícone selecionado no comboBoxLinks
        if current_url:  # Se a URL for válida
            try:
                response = requests.get(current_url, timeout=10)  # Faz uma requisição HTTP para obter a imagem do ícone
                response.raise_for_status()  # Verifica se a requisição foi bem-sucedida
                pixmap = QPixmap()  # Cria um QPixmap vazio
                pixmap.loadFromData(response.content)  # Carrega a imagem no QPixmap a partir dos dados da resposta

                self.graphicsViewIcones.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)  # Define as dicas de renderização

                self.icon_scene.clear()  # Limpa a cena atual
                self.icon_scene.addPixmap(pixmap)  # Adiciona o novo ícone à cena

                rect = QRectF(pixmap.rect())  # Cria um QRectF com as dimensões do pixmap
                self.graphicsViewIcones.setSceneRect(rect)  # Define o retângulo da cena
                self.graphicsViewIcones.fitInView(rect, Qt.KeepAspectRatio)  # Ajusta a cena para se adaptar ao tamanho do ícone mantendo a proporção
            except requests.RequestException as e:  # Em caso de erro na requisição HTTP
                self.mostrar_mensagem(f"Erro ao carregar ícone: {str(e)}", "Erro")  # Exibe uma mensagem de erro

    def carregar_imagens_no_tableview(self, caminhos_imagens, progressBar):
        """
        Carrega imagens no TableView e atualiza a barra de progresso.

        Parâmetros:
        caminhos_imagens: list - Lista de caminhos completos das imagens a serem carregadas.
        progressBar: QProgressBar - Barra de progresso para atualizar durante o carregamento das imagens.

        Funções:
        - Cria um modelo padrão e define os cabeçalhos das colunas.
        - Itera sobre os caminhos das imagens, carregando cada imagem e adicionando ao modelo.
        - Redimensiona as imagens se forem maiores que 160x160 pixels.
        - Extrai e armazena informações EXIF das imagens.
        - Define o ícone padrão para cada imagem carregada.
        - Configura o TableView para exibir as miniaturas das imagens.
        - Conecta sinais para exibir coordenadas e atualizar ícones.
        """
        
        modelo = QStandardItemModel()  # Cria um modelo padrão
        modelo.setHorizontalHeaderLabels(['Miniaturas'])  # Define os cabeçalhos das colunas

        icon_url = self.comboBoxLinks.currentData()  # Obtém a URL do ícone selecionado no comboBoxLinks

        for i, caminho_completo in enumerate(caminhos_imagens):  # Itera sobre os caminhos das imagens
            pixmap = QPixmap(caminho_completo)  # Carrega a imagem em um QPixmap
            if pixmap.width() > 160 or pixmap.height() > 160:  # Redimensiona a imagem se for maior que 160x160 pixels
                pixmap = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QStandardItem()  # Cria um item padrão
            item.setIcon(QIcon(pixmap))  # Define o ícone do item como a imagem carregada
            item.setData(caminho_completo, Qt.UserRole)  # Define o caminho da imagem como dado do item
            modelo.appendRow(item)  # Adiciona o item ao modelo
            progressBar.setValue(i + 1)  # Atualiza a barra de progresso

            nome_imagem = os.path.splitext(os.path.basename(caminho_completo))[0]  # Obtém o nome da imagem
            FotosManager.nomes_imagens[caminho_completo] = nome_imagem  # Armazena o nome da imagem
            FotosManager.icones_imagens[caminho_completo] = icon_url  # Define o ícone padrão para a imagem

            try:
                with PIL.Image.open(caminho_completo) as imagem:  # Abre a imagem usando PIL
                    exif_data = imagem._getexif()  # Obtém os dados EXIF da imagem
                    if exif_data:
                        exif = {
                            TAGS.get(k, k): v
                            for k, v in exif_data.items()
                            if k in TAGS
                        }

                        gps_info = exif.get("GPSInfo")
                        if gps_info:  # Obtém informações de GPS se disponíveis
                            lat = self._get_gps_coordinate(gps_info, 2, gps_info.get(1))
                            lon = self._get_gps_coordinate(gps_info, 4, gps_info.get(3))
                            alt = self._get_gps_altitude(gps_info)
                        else:
                            lat, lon, alt = "N/A", "N/A", "N/A"

                        data_hora = exif.get("DateTimeOriginal", "N/A N/A").split()
                        data = data_hora[0] if len(data_hora) > 0 else "N/A"
                        hora = data_hora[1] if len(data_hora) > 1 else "N/A"

                        width, height = imagem.size  # Obtém a resolução da imagem
                        resolucao = f"{width}x{height}"

                        FotosManager.info_imagens[caminho_completo] = {
                            "latitude": lat,
                            "longitude": lon,
                            "altitude": alt,
                            "data": data,
                            "hora": hora,
                            "resolucao": resolucao
                        }
            except Exception as e:  # Em caso de erro ao obter informações EXIF
                FotosManager.info_imagens[caminho_completo] = {
                    "latitude": "N/A",
                    "longitude": "N/A",
                    "altitude": "N/A",
                    "data": "N/A",
                    "hora": "N/A",
                    "resolucao": "N/A"
                }

        self.tableViewFotos.setModel(modelo)  # Define o modelo do TableView
        self.tableViewFotos.setItemDelegate(DeleteButtonDelegate(self))  # Define o delegate para o botão de deletar
        self.tableViewFotos.setSelectionBehavior(QAbstractItemView.SelectRows)  # Define o comportamento de seleção para linhas
        self.tableViewFotos.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Define o comportamento de edição
        self.tableViewFotos.setIconSize(QSize(160, 160))  # Define o tamanho dos ícones

        for row in range(modelo.rowCount()):  # Define a altura das linhas para se ajustar aos ícones
            self.tableViewFotos.setRowHeight(row, modelo.item(row).icon().availableSizes()[0].height())

        header = self.tableViewFotos.horizontalHeader()  # Obtém o cabeçalho horizontal
        header.setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)  # Define o alinhamento do cabeçalho
        header.setSectionResizeMode(QHeaderView.Stretch)  # Define o modo de redimensionamento das seções

        modelo.setHeaderData(0, Qt.Horizontal, Qt.AlignCenter, Qt.TextAlignmentRole)  # Define o alinhamento dos dados do cabeçalho

        selection_model = self.tableViewFotos.selectionModel()  # Obtém o modelo de seleção
        selection_model.selectionChanged.connect(self.mostrar_coordenadas)  # Conecta o sinal de alteração de seleção para exibir coordenadas
        selection_model.selectionChanged.connect(self.atualizar_icone_selecionado)  # Conecta o sinal de alteração de seleção para atualizar ícones

        self.atualizar_estado_itens()  # Atualiza o estado dos itens

    def decimal_to_dms(self, decimal, coord_type):
        """
        Converte coordenadas decimais para DMS (Graus, Minutos, Segundos).

        Parâmetros:
        decimal: float - O valor da coordenada em formato decimal.
        coord_type: str - O tipo de coordenada ('lat' para latitude ou 'lon' para longitude).

        Retorna:
        str - A coordenada formatada em DMS com a direção apropriada.

        Funções:
        - Converte o valor decimal da coordenada em graus, minutos e segundos.
        - Determina a direção da coordenada com base no tipo e no sinal do valor decimal.
        - Retorna a coordenada formatada em DMS com a direção.
        """

        is_positive = decimal >= 0  # Verifica se o valor decimal é positivo
        decimal = abs(decimal)  # Obtém o valor absoluto da coordenada
        degrees = int(decimal)  # Obtém a parte inteira dos graus
        minutes = int((decimal - degrees) * 60)  # Calcula os minutos a partir da parte decimal dos graus
        seconds = (decimal - degrees - minutes / 60) * 3600  # Calcula os segundos a partir da parte decimal dos minutos
        direction = ''  # Inicializa a direção como uma string vazia

        if coord_type == 'lat':  # Define a direção para latitude
            direction = 'N' if is_positive else 'S'
        elif coord_type == 'lon':  # Define a direção para longitude
            direction = 'E' if is_positive else 'W'
        
        return f"{degrees}°{minutes}'{seconds:.2f}\"{direction}"  # Retorna a coordenada formatada em DMS com a direção

    def gerar_conteudo_kml(self, screen_overlay_data=None):
        """
        Gera o conteúdo KML para todas as imagens carregadas no TableView e, opcionalmente, para o ScreenOverlay.

        Parâmetros:
        screen_overlay_data: dict (opcional) - O dicionário contendo os dados do ScreenOverlay.

        Retorna:
        tuple - Contendo o conteúdo KML como string e uma lista de imagens para incluir no KMZ.

        Funções:
        - Obtém o nome da última pasta usada.
        - Cria a estrutura inicial do documento KML.
        - Itera sobre as imagens carregadas no TableView.
        - Extrai informações EXIF e converte coordenadas para DMS.
        - Adiciona as informações de estilo e marcadores das imagens ao KML.
        - Inclui o ScreenOverlay no KML se fornecido.
        - Retorna o conteúdo KML e a lista de imagens para incluir no KMZ.
        """
        
        nome_pasta = os.path.basename(FotosManager.ultima_pasta)  # Obtém o nome da última pasta usada
        kml_content = ['<?xml version="1.0" encoding="UTF-8"?>']  # Inicia o conteúdo KML
        kml_content.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">')
        kml_content.append(f'<Document id="feat_1"><name>{nome_pasta}.kmz</name>')  # Define o documento KML
        kml_content.append('<open>1</open>')  # Define o documento como aberto por padrão

        imagens_para_incluir = []  # Lista de imagens para incluir no KMZ
        modelo = self.tableViewFotos.model()  # Obtém o modelo do TableView

        if modelo is None or modelo.rowCount() == 0:  # Verifica se o modelo é válido e possui imagens
            self.mostrar_mensagem("Nenhuma imagem carregada no TableViewFotos", "Erro")  # Exibe uma mensagem de erro
            return None, None  # Retorna None se não houver imagens

        largura_imagem = self.lineEditExibir.text() if self.lineEditExibir.text() else "1400"  # Obtém a largura da imagem
        shp_id = 1  # Inicializa o ID do shapefile

        for row in range(modelo.rowCount()):  # Itera sobre as imagens carregadas no TableView
            item = modelo.item(row)  # Obtém o item da linha
            caminho_imagem = item.data(Qt.UserRole)  # Obtém o caminho da imagem do item
            nome_imagem = FotosManager.nomes_imagens.get(caminho_imagem, os.path.splitext(os.path.basename(caminho_imagem))[0])  # Obtém o nome da imagem

            if caminho_imagem not in FotosManager.info_imagens:  # Verifica se as informações da imagem estão disponíveis
                self.mostrar_mensagem(f"Informações da imagem não encontradas para {caminho_imagem}", "Erro")  # Exibe uma mensagem de erro
                continue  # Pula para a próxima imagem

            info = FotosManager.info_imagens[caminho_imagem]  # Obtém as informações da imagem
            latitude = info["latitude"]
            longitude = info["longitude"]
            altitude = info["altitude"]
            data = info["data"]
            hora = info["hora"]
            resolucao = info["resolucao"]

            if latitude == "N/A" or longitude == "N/A":  # Verifica se as coordenadas são válidas
                self.mostrar_mensagem(f"Coordenadas inválidas para a imagem {caminho_imagem}", "Erro")  # Exibe uma mensagem de erro
                continue  # Pula para a próxima imagem

            # Converter latitude e longitude para DMS
            latitude_dms = self.decimal_to_dms(latitude, 'lat')
            longitude_dms = self.decimal_to_dms(longitude, 'lon')

            autor_texto = FotosManager.autor_texto  # Obtém o texto do autor
            autor_html = (
                f'<td style="text-align:right; font-size:12px; color:blue;"><b>FOTO: {autor_texto}</b></td>'
            ) if autor_texto else ''  # Cria o HTML do autor se disponível

            icon_url = FotosManager.icones_imagens.get(caminho_imagem, self.comboBoxLinks.itemData(0))  # Obtém a URL do ícone

            # Adiciona o estilo do marcador ao KML
            kml_content.append(
                f'<Style id="stylesel_{shp_id}">'
                f'<BalloonStyle>'
                f'<text><![CDATA[<div style="width:100%"><table width="100%"><tr><td><b>Latitude:</b> {latitude_dms} <b>Longitude:</b> {longitude_dms} <b>Altitude:</b> {altitude}{"m" if altitude != "N/A" else ""}</td>{autor_html}</tr></table></div>'
                f'<p><b>Data:</b> {data} <b>Horário:</b> {hora}</p>'
                f'<div style="width:{largura_imagem}px;"><table width="100%" cellpadding="0" cellspacing="0"><tbody><tr><td><img width="100%" height="auto" src="files/{os.path.basename(caminho_imagem)}"></td></tr></tbody></table></div>'
                f']]></text>'
                f'<displayMode>default</displayMode>'
                f'</BalloonStyle>'
                f'<IconStyle>'
                f'<Icon>'
                f'<href>{icon_url}</href>'
                f'</Icon>'
                f'</IconStyle>'
                f'</Style>'
            )

            # Adiciona o marcador da imagem ao KML
            kml_content.append(
                f'<Placemark id="feat_{shp_id}">'
                f'<name>{nome_imagem}</name>'
                f'<styleUrl>#stylesel_{shp_id}</styleUrl>'
                f'<Point id="geom_{shp_id}">'
                f'<coordinates>{longitude},{latitude},{altitude}</coordinates>'
                f'</Point>'
                f'</Placemark>'
            )

            imagens_para_incluir.append(caminho_imagem)  # Adiciona a imagem à lista de imagens para incluir no KMZ
            shp_id += 1  # Incrementa o ID do shapefile

        # Adicionando o ScreenOverlay se fornecido
        if screen_overlay_data:  # Verifica se os dados do ScreenOverlay foram fornecidos
            kml_content.append(self.gerar_conteudo_screenoverlay(screen_overlay_data))  # Adiciona o ScreenOverlay ao KML

        kml_content.append('</Document>')  # Fecha o documento KML
        kml_content.append('</kml>')  # Fecha o elemento KML

        self.mostrar_mensagem("Geração do conteúdo KML concluída.", "Info")  # Exibe uma mensagem informativa

        return '\n'.join(kml_content), imagens_para_incluir  # Retorna o conteúdo KML e a lista de imagens para incluir no KMZ

class DeleteButtonDelegate(QStyledItemDelegate):
    """
    Delegate para adicionar um botão de deletar estilizado em cada item de uma view.
    
    Funções:
    - Inicializa o delegate com um parent opcional.
    - Renderiza um ícone de deletar no canto superior direito do item.
    - Lida com eventos de clique no ícone de deletar para remover a imagem correspondente.
    """
    
    def __init__(self, parent=None):
        """
        Inicializa o DeleteButtonDelegate.
        
        Parâmetros:
        parent: QWidget (opcional) - O widget pai, se houver.
        """
        super(DeleteButtonDelegate, self).__init__(parent)  # Chama o construtor da classe base QStyledItemDelegate
        self.parent = parent  # Armazena o widget pai

    def paint(self, painter, option, index):
        """
        Renderiza o ícone de deletar no canto superior direito do item.
        
        Parâmetros:
        painter: QPainter - O objeto QPainter usado para desenhar o item.
        option: QStyleOptionViewItem - As opções de estilo para o item.
        index: QModelIndex - O índice do item a ser desenhado.
        """
        super(DeleteButtonDelegate, self).paint(painter, option, index)  # Chama o método paint da classe base

        # Renderizar o ícone de deletar no canto superior direito
        if index.isValid():  # Verifica se o índice é válido
            rect = option.rect  # Obtém o retângulo do item
            icon_rect = QRect(rect.right() - 15, rect.top() + 2, 12, 12)  # Ajusta o tamanho e posição do ícone

            # Desenhar ícone estilizado com quadrado de bordas arredondadas
            painter.save()  # Salva o estado atual do painter
            painter.setRenderHint(QPainter.Antialiasing)  # Habilita antialiasing
            painter.setPen(QPen(QColor(0, 0, 255), 2))  # Cor da borda do quadrado
            painter.setBrush(QBrush(QColor(255, 0, 0, 200)))  # Fundo vermelho claro
            radius = 2  # Raio das bordas arredondadas
            painter.drawRoundedRect(icon_rect, radius, radius)  # Desenha o quadrado com bordas arredondadas

            # Desenha o "x" dentro do quadrado
            painter.setPen(QPen(QColor(255, 255, 255), 2))  # Cor e espessura do "x"
            # Desenha o "x" simétrico dentro do quadrado
            painter.drawLine(icon_rect.topLeft() + QPoint(2, 2), icon_rect.bottomRight() - QPoint(2, 2))
            painter.drawLine(icon_rect.topRight() + QPoint(-2, 2), icon_rect.bottomLeft() + QPoint(2, -2))
            painter.restore()  # Restaura o estado do painter

    def editorEvent(self, event, model, option, index):
        """
        Lida com eventos de clique no ícone de deletar para remover a imagem correspondente.
        
        Parâmetros:
        event: QEvent - O evento de entrada.
        model: QAbstractItemModel - O modelo de dados.
        option: QStyleOptionViewItem - As opções de estilo para o item.
        index: QModelIndex - O índice do item a ser manipulado.
        
        Retorna:
        bool - True se o evento foi tratado, caso contrário chama o método da classe base.
        """
        if event.type() == QEvent.MouseButtonRelease:  # Verifica se o evento é de clique do mouse
            rect = option.rect  # Obtém o retângulo do item
            icon_rect = QRect(rect.right() - 15, rect.top() + 2, 12, 12)  # Ajusta o tamanho e posição do ícone
            if icon_rect.contains(event.pos()):  # Verifica se o clique ocorreu dentro do ícone
                # Aciona a remoção da imagem
                caminho_imagem = index.data(Qt.UserRole)  # Obtém o caminho da imagem do índice
                self.parent.remover_imagem(caminho_imagem)  # Chama a função de remover imagem no widget pai
                return True  # Indica que o evento foi tratado
        return super(DeleteButtonDelegate, self).editorEvent(event, model, option, index)  # Chama o método da classe base para outros eventos

class ScreenOverlay(QDialog):
    def __init__(self, parent=None):
        """
         Inicializa a classe ScreenOverlay, configurando a interface do usuário e conectando os sinais e slots.

        Parâmetros:
        - parent: O widget pai opcional para este diálogo.
        
        Funções realizadas:
        - Inicializa o diálogo com a interface do usuário.
        - Define o título da janela.
        - Conecta os sinais dos widgets aos métodos correspondentes.
        - Desativa os controles inicialmente.
        - Define variáveis de instância para armazenamento de estado e configurações.
        - Carrega dados de ScreenOverlay se estiverem disponíveis no widget pai.
        - Ativa ou desativa os controles com base na presença dos dados de ScreenOverlay no widget pai.
        """
        super(ScreenOverlay, self).__init__(parent)  # Chama o construtor da classe base QDialog
        self.setupUi(self)  # Configura a interface do usuário

        self.setWindowTitle("Adicionar ScreenOverlay ao KMZ")  # Define o título da janela

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False) # Inicia inativo e ativa ao detectar imagem no gráfico

        #Captura a configuração definida no QT Designer, para o caso de redifinição posterior
        self.parent().pushButton_Screen.setStyleSheet(self.parent().pushButton_Screen_default_style)

        # Conecta os sinais dos widgets aos métodos correspondentes
        self.pushButtonAdd.clicked.connect(self.adicionar_imagem)  # Conecta o clique do botão ao método adicionar_imagem
        self.lineEditPX.textChanged.connect(self.redimensionar_imagem)  # Conecta a mudança de texto ao método redimensionar_imagem
        self.lineEditPY.textChanged.connect(self.redimensionar_imagem)  # Conecta a mudança de texto ao método redimensionar_imagem
        self.lineEditX.textChanged.connect(self.atualizar_posicao_imagem)  # Conecta a mudança de texto ao método atualizar_posicao_imagem
        self.lineEditY.textChanged.connect(self.atualizar_posicao_imagem)  # Conecta a mudança de texto ao método atualizar_posicao_imagem
        self.pushButtonReseta.clicked.connect(self.resetar_valores)  # Conecta o botão ao método de reset

        self.desativar_controles()  # Desativar controles inicialmente
        self.last_opened_folder = QDir.homePath()  # Define last_opened_folder na instância
        self.original_pixmap = None  # Para armazenar a imagem original
        self.pixmap_item = None  # Para armazenar o item pixmap na cena gráfica
        self.linha_horizontal = None  # Armazenar a linha horizontal
        self.linha_vertical = None  # Armazenar a linha vertical
        self.original_pos = (0, 0)  # Inicializar original_pos para evitar erro de atributo
        self.image_path = None  # Atributo de instância para armazenar o caminho da imagem
        self.transform_state = None  # Atributo para armazenar o estado da transformação

        # Verifica se o widget pai tem dados de screen_overlay e carrega-os se existirem
        if hasattr(self.parent(), 'screen_overlay_data') and self.parent().screen_overlay_data:
            self.carregar_dados_screen_overlay()  # Carrega os dados de screen_overlay
            self.ativar_controles()  # Ativa os controles se os dados existirem
        else:
            self.desativar_controles()  # Desativa os controles se os dados não existirem

    def showEvent(self, event):
        """
        Método showEvent que é chamado automaticamente sempre que o diálogo é exibido.

        O objetivo deste método é restaurar o estado visual do gráfico (imagem e transformações aplicadas)
        para o último estado modificado antes do diálogo ser fechado ou oculto. Ele garante que,
        ao reabrir o diálogo, a imagem seja exibida exatamente como estava na última vez que foi visualizada.

        A função realiza as seguintes operações:
        1. Chama o método showEvent da classe base para garantir que qualquer comportamento padrão do QDialog seja executado.
        2. Verifica se há uma imagem (pixmap_item) no gráfico.
        3. Se uma transformação anterior foi aplicada (transform_state), a função restaura essa transformação ao gráfico.
        4. Ajusta a visualização do gráfico dentro do QGraphicsView para garantir que a imagem caiba perfeitamente na área disponível.
        """

        super(ScreenOverlay, self).showEvent(event)  # Chama o método showEvent da classe base QDialog para manter o comportamento padrão

        if self.pixmap_item:  # Verifica se há uma imagem no gráfico
            if self.transform_state:  # Verifica se há uma transformação salva para o gráfico
                self.graphicsView.setTransform(self.transform_state)  # Aplica a transformação salva ao gráfico

            # Ajusta a visualização do gráfico para caber na área do QGraphicsView mantendo a proporção
            self.graphicsView.fitInView(self.graphicsView.scene().itemsBoundingRect(), Qt.KeepAspectRatio)

    def setupUi(self, Dialog):
        """
        Configura a interface do usuário do diálogo, incluindo layouts, widgets e conexões de sinais.
        
        Parâmetros:
        Dialog: QDialog - O diálogo que está sendo configurado.
        
        Funções:
        - Define o nome do objeto do diálogo.
        - Redimensiona o diálogo e define o tamanho máximo.
        - Configura layouts e widgets, incluindo QGraphicsView, QLineEdits, QLabel, QCheckBox, QPushButton e QDialogButtonBox.
        - Conecta os sinais dos botões a funções específicas.
        - Inverte o eixo Y do QGraphicsView.
        """

        Dialog.setObjectName("Dialog")  # Define o nome do objeto do diálogo como "Dialog"
        Dialog.resize(270, 360)  # Redimensiona o diálogo para 270x360 pixels
        Dialog.setMaximumSize(QtCore.QSize(270, 360))  # Define o tamanho máximo do diálogo para 270x360 pixels
        self.gridLayout_6 = QtWidgets.QGridLayout(Dialog)  # Cria um layout de grade para o diálogo
        self.gridLayout_6.setObjectName("gridLayout_6")  # Define o nome do objeto do layout de grade
        self.frame = QtWidgets.QFrame(Dialog)  # Cria um frame dentro do diálogo
        self.frame.setFrameShape(QtWidgets.QFrame.Box)  # Define a forma do frame como uma caixa
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)  # Define a sombra do frame como elevada
        self.frame.setObjectName("frame")  # Define o nome do objeto do frame
        self.gridLayout_5 = QtWidgets.QGridLayout(self.frame)  # Cria um layout de grade para o frame
        self.gridLayout_5.setObjectName("gridLayout_5")  # Define o nome do objeto do layout de grade
        self.graphicsView = QtWidgets.QGraphicsView(self.frame)  # Cria um QGraphicsView dentro do frame
        self.graphicsView.setObjectName("graphicsView")  # Define o nome do objeto do QGraphicsView
        self.gridLayout_5.addWidget(self.graphicsView, 0, 0, 1, 1)  # Adiciona o QGraphicsView ao layout de grade na posição (0, 0)

        self.frame_2 = QtWidgets.QFrame(self.frame)  # Inicializa frame_2 dentro do frame principal
        self.frame_2.setFrameShape(QtWidgets.QFrame.Box)  # Define a forma do frame como uma caixa
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)  # Define a sombra do frame como elevada
        self.frame_2.setObjectName("frame_2")  # Define o nome do objeto do frame
        self.gridLayout_4 = QtWidgets.QGridLayout(self.frame_2)  # Cria um layout de grade para frame_2
        self.gridLayout_4.setObjectName("gridLayout_4")  # Define o nome do objeto do layout de grade
        self.gridLayout = QtWidgets.QGridLayout()  # Cria um layout de grade
        self.gridLayout.setObjectName("gridLayout")  # Define o nome do objeto do layout de grade

        self.label = QtWidgets.QLabel(self.frame_2)  # Cria um QLabel dentro de frame_2
        self.label.setObjectName("label")  # Define o nome do objeto do QLabel
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)  # Adiciona o QLabel ao layout de grade na posição (0, 0)

        self.lineEditX = QtWidgets.QLineEdit(self.frame_2)  # Cria um QLineEdit dentro de frame_2
        self.lineEditX.setObjectName("lineEditX")  # Define o nome do objeto do QLineEdit
        self.lineEditX.setText("0")  # Define o valor inicial como "0"
        self.lineEditX.setPlaceholderText("0")  # Define o texto do placeholder como "0"
        self.lineEditX.setAlignment(Qt.AlignCenter)  # Centraliza o texto em lineEditX
        self.gridLayout.addWidget(self.lineEditX, 0, 1, 1, 1)  # Adiciona o QLineEdit ao layout de grade na posição (0, 1)

        self.label_5 = QtWidgets.QLabel(self.frame_2)  # Cria um QLabel dentro de frame_2
        self.label_5.setObjectName("label_5")  # Define o nome do objeto do QLabel
        self.gridLayout.addWidget(self.label_5, 0, 2, 1, 1)  # Adiciona o QLabel ao layout de grade na posição (0, 2)

        self.lineEditY = QtWidgets.QLineEdit(self.frame_2)  # Cria um QLineEdit dentro de frame_2
        self.lineEditY.setObjectName("lineEditY")  # Define o nome do objeto do QLineEdit
        self.lineEditY.setText("0")  # Define o valor inicial como "0"
        self.lineEditY.setPlaceholderText("0")  # Define o texto do placeholder como "0"
        self.lineEditY.setAlignment(Qt.AlignCenter)  # Centraliza o texto em lineEditY
        self.gridLayout.addWidget(self.lineEditY, 0, 3, 1, 1)  # Adiciona o QLineEdit ao layout de grade na posição (0, 3)

        self.label_3 = QtWidgets.QLabel(self.frame_2)  # Cria um QLabel dentro de frame_2
        self.label_3.setObjectName("label_3")  # Define o nome do objeto do QLabel
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)  # Adiciona o QLabel ao layout de grade na posição (1, 0)

        self.lineEditPX = QtWidgets.QLineEdit(self.frame_2)  # Cria um QLineEdit dentro de frame_2
        self.lineEditPX.setObjectName("lineEditPX")  # Define o nome do objeto do QLineEdit
        self.lineEditPX.setAlignment(Qt.AlignCenter)  # Centraliza o texto em lineEditPX
        self.gridLayout.addWidget(self.lineEditPX, 1, 1, 1, 1)  # Adiciona o QLineEdit ao layout de grade na posição (1, 1)

        self.label_4 = QtWidgets.QLabel(self.frame_2)  # Cria um QLabel dentro de frame_2
        self.label_4.setObjectName("label_4")  # Define o nome do objeto do QLabel
        self.gridLayout.addWidget(self.label_4, 1, 2, 1, 1)  # Adiciona o QLabel ao layout de grade na posição (1, 2)

        self.lineEditPY = QtWidgets.QLineEdit(self.frame_2)  # Cria um QLineEdit dentro de frame_2
        self.lineEditPY.setObjectName("lineEditPY")  # Define o nome do objeto do QLineEdit
        self.lineEditPY.setAlignment(Qt.AlignCenter)  # Centraliza o texto em lineEditPY
        self.gridLayout.addWidget(self.lineEditPY, 1, 3, 1, 1)  # Adiciona o QLineEdit ao layout de grade na posição (1, 3)

        self.gridLayout_4.addLayout(self.gridLayout, 0, 0, 1, 2)  # Adiciona o layout de grade gridLayout ao layout de grade gridLayout_4 na posição (0, 0) ocupando 1 linha e 2 colunas

        self.checkBoxPropocao = QtWidgets.QCheckBox(self.frame_2)  # Cria um QCheckBox dentro de frame_2
        self.checkBoxPropocao.setObjectName("checkBoxPropocao")  # Define o nome do objeto do QCheckBox
        self.gridLayout_4.addWidget(self.checkBoxPropocao, 1, 0, 1, 1)  # Adiciona o QCheckBox ao layout de grade na posição (1, 0)

        self.pushButtonReseta = QtWidgets.QPushButton(self.frame_2)  # Cria um QPushButton dentro de frame_2
        self.pushButtonReseta.setObjectName("pushButtonReseta")  # Define o nome do objeto do QPushButton
        self.gridLayout_4.addWidget(self.pushButtonReseta, 1, 1, 1, 1)  # Adiciona o QPushButton ao layout de grade na posição (1, 1)

        self.gridLayout_5.addWidget(self.frame_2, 1, 0, 1, 1)  # Adiciona frame_2 ao layout de grade gridLayout_5 na posição (1, 0) ocupando 1 linha e 1 coluna

        self.pushButtonAdd = QtWidgets.QPushButton(self.frame)  # Cria um QPushButton dentro do frame principal
        self.pushButtonAdd.setObjectName("pushButtonAdd")  # Define o nome do objeto do QPushButton
        self.gridLayout_5.addWidget(self.pushButtonAdd, 2, 0, 1, 1)  # Adiciona o QPushButton ao layout de grade na posição (2, 0)

        self.gridLayout_6.addWidget(self.frame, 0, 0, 1, 1)  # Adiciona o frame principal ao layout de grade gridLayout_6 na posição (0, 0) ocupando 1 linha e 1 coluna

        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)  # Cria um QDialogButtonBox dentro do diálogo
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)  # Define os botões padrão como Cancelar e Ok
        self.buttonBox.setCenterButtons(True)  # Centraliza os botões
        self.buttonBox.setObjectName("buttonBox")  # Define o nome do objeto do QDialogButtonBox
        self.gridLayout_6.addWidget(self.buttonBox, 1, 0, 1, 1)  # Adiciona o QDialogButtonBox ao layout de grade na posição (1, 0)

        self.retranslateUi(Dialog)  # Chama a função retranslateUi para definir os textos dos widgets
        QtCore.QMetaObject.connectSlotsByName(Dialog)  # Conecta os slots por nome

        self.graphicsView.setTransform(QtGui.QTransform().scale(1, -1))  # Inverte o eixo Y do QGraphicsView

        self.buttonBox.accepted.connect(self.aceitar)  # Conecta o botão OK do buttonBox à função aceitar
        self.buttonBox.rejected.connect(self.remover_imagem)  # Conecta o botão Cancelar ao método de remoção

    def remover_imagem(self):
        """
        Remove a imagem do QGraphicsView e reseta os dados de screen_overlay.
        
        Funções:
        - Verifica se o item do pixmap existe e o remove da cena do QGraphicsView.
        - Reseta o caminho da imagem e os dados de screen_overlay do pai.
        - Atualiza o texto e o estilo do botão pushButton_Screen do pai.
        - Desativa os controles.
        - Rejeita (fecha) o diálogo.
        """
        
        # Verifica se o item do pixmap existe e o remove da cena do QGraphicsView
        if hasattr(self, 'pixmap_item') and self.pixmap_item:
            scene = self.graphicsView.scene()  # Obtém a cena do QGraphicsView
            if scene:
                scene.removeItem(self.pixmap_item)  # Remove o item do pixmap da cena
                self.pixmap_item = None  # Reseta o item do pixmap

        self.image_path = None  # Reseta o caminho da imagem

        # Verifica se o pai tem dados de screen_overlay e os reseta
        if hasattr(self.parent(), 'screen_overlay_data'):
            self.parent().screen_overlay_data = {}

        # Atualiza o texto e o estilo do botão pushButton_Screen do pai
        self.parent().pushButton_Screen.setText("ScreenOverlay")
        self.parent().pushButton_Screen.setStyleSheet(self.parent().pushButton_Screen_default_style)

        self.desativar_controles()  # Desativa os controles

        self.reject()  # Rejeita (fecha) o diálogo

        # Desativa o botão OK porque a imagem foi removida
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

    def retranslateUi(self, Dialog):
        """
        Define os textos dos widgets do diálogo, traduzindo-os conforme necessário.
        
        Parâmetros:
        Dialog: QDialog - O diálogo que está sendo configurado.
        
        Funções:
        - Define o título da janela do diálogo.
        - Define os textos dos labels, checkboxes e botões.
        """
        
        _translate = QtCore.QCoreApplication.translate  # Atalho para a função de tradução do Qt

        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))  # Define o título da janela do diálogo como "Dialog"

        self.label.setText(_translate("Dialog", "OverlayXY:"))  # Define o texto do QLabel self.label como "OverlayXY:"
        self.label_5.setText(_translate("Dialog", "x"))  # Define o texto do QLabel self.label_5 como "x"
        self.label_3.setText(_translate("Dialog", "Pixels:"))  # Define o texto do QLabel self.label_3 como "Pixels:"
        self.label_4.setText(_translate("Dialog", "x"))  # Define o texto do QLabel self.label_4 como "x"
        self.checkBoxPropocao.setText(_translate("Dialog", "Manter Proporção"))  # Define o texto do QCheckBox self.checkBoxPropocao como "Manter Proporção"
        self.pushButtonReseta.setText(_translate("Dialog", "Reseta"))  # Define o texto do QPushButton self.pushButtonReseta como "Reseta"
        self.pushButtonAdd.setText(_translate("Dialog", "Adicionar"))  # Define o texto do QPushButton self.pushButtonAdd como "Adicionar"

    def ativar_controles(self):
        """
        Ativa os controles do diálogo, permitindo que o usuário interaja com eles.
        
        Funções:
        - Ativa o botão de resetar.
        - Ativa os campos de texto de posição e tamanho da imagem.
        - Ativa a caixa de seleção para manter proporção.
        """
        
        self.pushButtonReseta.setEnabled(True)  # Ativa o botão de resetar
        self.lineEditPX.setEnabled(True)  # Ativa o campo de texto de largura da imagem
        self.lineEditPY.setEnabled(True)  # Ativa o campo de texto de altura da imagem
        self.lineEditX.setEnabled(True)  # Ativa o campo de texto de posição X da imagem
        self.lineEditY.setEnabled(True)  # Ativa o campo de texto de posição Y da imagem
        self.checkBoxPropocao.setEnabled(True)  # Ativa a caixa de seleção para manter proporção

    def desativar_controles(self):
        """
        Desativa os controles do diálogo, impedindo que o usuário interaja com eles.
        
        Funções:
        - Desativa o botão de resetar.
        - Desativa os campos de texto de posição e tamanho da imagem.
        - Desativa a caixa de seleção para manter proporção.
        """
        
        self.pushButtonReseta.setEnabled(False)  # Desativa o botão de resetar
        self.lineEditPX.setEnabled(False)  # Desativa o campo de texto de largura da imagem
        self.lineEditPY.setEnabled(False)  # Desativa o campo de texto de altura da imagem
        self.lineEditX.setEnabled(False)  # Desativa o campo de texto de posição X da imagem
        self.lineEditY.setEnabled(False)  # Desativa o campo de texto de posição Y da imagem
        self.checkBoxPropocao.setEnabled(False)  # Desativa a caixa de seleção para manter proporção

    def redimensionar_imagem(self):
        """
        Redimensiona a imagem no QGraphicsView com base nos valores de largura e altura fornecidos pelo usuário.
        
        Funções:
        - Verifica se a imagem original existe.
        - Obtém os valores de largura e altura dos campos de texto.
        - Ajusta os valores de largura e altura para não excederem os tamanhos originais da imagem.
        - Mantém a proporção da imagem se a opção estiver marcada.
        - Aplica a transformação de escala à imagem.
        """

        if not self.original_pixmap:  # Verifica se a imagem original existe
            return

        try:
            largura = int(self.lineEditPX.text())  # Obtém o valor de largura do campo de texto
            altura = int(self.lineEditPY.text())  # Obtém o valor de altura do campo de texto
        except ValueError:  # Lida com valores inválidos
            return

        original_width = self.original_pixmap.width()  # Obtém a largura original da imagem
        original_height = self.original_pixmap.height()  # Obtém a altura original da imagem

        if largura > original_width:  # Ajusta a largura para não exceder a largura original
            largura = original_width
            self.lineEditPX.setText(str(largura))

        if altura > original_height:  # Ajusta a altura para não exceder a altura original
            altura = original_height
            self.lineEditPY.setText(str(altura))

        if self.checkBoxPropocao.isChecked():  # Mantém a proporção da imagem se a opção estiver marcada
            aspect_ratio = original_width / original_height  # Calcula a proporção da imagem
            if self.sender() == self.lineEditPX:  # Ajusta a altura com base na largura
                altura = int(largura / aspect_ratio)
                self.lineEditPY.blockSignals(True)  # Bloqueia sinais temporariamente
                self.lineEditPY.setText(str(altura))
                self.lineEditPY.blockSignals(False)  # Desbloqueia sinais
            elif self.sender() == self.lineEditPY:  # Ajusta a largura com base na altura
                largura = int(altura * aspect_ratio)
                self.lineEditPX.blockSignals(True)  # Bloqueia sinais temporariamente
                self.lineEditPX.setText(str(largura))
                self.lineEditPX.blockSignals(False)  # Desbloqueia sinais

        # Aplicar a transformação de escala
        scale_x = largura / original_width  # Calcula a escala em X
        scale_y = altura / original_height  # Calcula a escala em Y

        transform = QtGui.QTransform()  # Cria uma transformação
        transform.scale(scale_x, scale_y)  # Aplica a escala à transformação
        self.pixmap_item.setTransform(transform)  # Aplica a transformação ao item do pixmap
        
        self.transform_state = self.graphicsView.transform()  # Salvar o estado da transformação após adicionar a imagem

    def adicionar_linhas_eixos(self):
        """
        Adiciona linhas horizontais e verticais no QGraphicsView para indicar os eixos da imagem.
        
        Funções:
        - Verifica se o item do pixmap existe.
        - Obtém as coordenadas da origem da imagem.
        - Cria e adiciona uma linha horizontal se não existir, ou atualiza a posição da linha existente.
        - Cria e adiciona uma linha vertical se não existir, ou atualiza a posição da linha existente.
        """

        if not self.pixmap_item:  # Verifica se o item do pixmap existe
            return

        # Coordenadas da origem da imagem
        x_origem, y_origem = self.pixmap_item.pos().x(), self.pixmap_item.pos().y()  # Obtém as coordenadas da origem da imagem
        largura = self.original_pixmap.width()  # Obtém a largura da imagem original
        altura = self.original_pixmap.height()  # Obtém a altura da imagem original

        # Cria e adiciona a linha horizontal, se não existir
        if not self.linha_horizontal:
            self.linha_horizontal = self.graphicsView.scene().addLine(
                x_origem, y_origem, x_origem + largura, y_origem, QtGui.QPen(QtCore.Qt.red, 3)
            )  # Cria e adiciona a linha horizontal
        else:
            # Atualiza a posição da linha existente
            self.linha_horizontal.setLine(
                x_origem, y_origem, x_origem + largura, y_origem
            )  # Atualiza a posição da linha horizontal existente

        # Cria e adiciona a linha vertical, se não existir
        if not self.linha_vertical:
            self.linha_vertical = self.graphicsView.scene().addLine(
                x_origem, y_origem, x_origem, y_origem + altura, QtGui.QPen(QtCore.Qt.blue, 3)
            )  # Cria e adiciona a linha vertical
        else:
            # Atualiza a posição da linha existente
            self.linha_vertical.setLine(
                x_origem, y_origem, x_origem, y_origem + altura
            )  # Atualiza a posição da linha vertical existente

    def resetar_valores(self):
        """
        Restaura os valores originais da imagem e dos controles do diálogo.
        
        Funções:
        - Verifica se a imagem original existe.
        - Restaura os valores originais de largura e altura nos campos de texto.
        - Verifica se a posição original está definida e restaura os valores de posição nos campos de texto.
        - Redefine a cena do QGraphicsView e adiciona a imagem original.
        - Adiciona novamente as linhas de eixos.
        - Redimensiona a imagem para os valores originais.
        - Ajusta a visualização da cena para manter a proporção.
        - Adiciona um indicador visual de seleção ao botão pushButton_Screen.
        """

        if not self.original_pixmap:  # Verifica se a imagem original existe
            return

        # Restaurar os valores originais nos lineEdits
        largura = self.original_pixmap.width()  # Obtém a largura original da imagem
        altura = self.original_pixmap.height()  # Obtém a altura original da imagem
        self.lineEditPX.setText(str(largura))  # Define o valor de largura no campo de texto
        self.lineEditPY.setText(str(altura))  # Define o valor de altura no campo de texto

        # Verificar se self.original_pos está definida
        if hasattr(self, 'original_pos'):  # Verifica se a posição original está definida
            self.lineEditX.setText(str(self.original_pos[0]))  # Define o valor de posição X no campo de texto
            self.lineEditY.setText(str(self.original_pos[1]))  # Define o valor de posição Y no campo de texto

        # Redefinir a cena do graphicsView
        scene = QtWidgets.QGraphicsScene()  # Cria uma nova cena do QGraphicsView
        self.graphicsView.setScene(scene)  # Define a cena no QGraphicsView
        self.pixmap_item = scene.addPixmap(
            self.original_pixmap.transformed(QtGui.QTransform().scale(1, -1))
        )  # Adiciona a imagem original transformada na cena
        self.pixmap_item.setPos(self.original_pos[0], self.original_pos[1])  # Define a posição da imagem

        # Adiciona as linhas de eixos novamente
        self.linha_horizontal = None  # Reseta a linha horizontal
        self.linha_vertical = None  # Reseta a linha vertical
        self.adicionar_linhas_eixos()  # Adiciona as linhas de eixos

        # Redimensionar a imagem para os valores originais
        self.redimensionar_imagem()  # Redimensiona a imagem
        self.graphicsView.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)  # Ajusta a visualização da cena

        # Adiciona o "✓" azul ao pushButton_Screen
        self.parent().pushButton_Screen.setText("ScreenOverlay ✓")  # Adiciona o indicador de seleção ao botão
        self.parent().pushButton_Screen.setStyleSheet("color: blue;")  # Define a cor do texto do botão como azul

    def atualizar_posicao_imagem(self):
        """
        Atualiza a posição da imagem no QGraphicsView com base nos valores fornecidos pelo usuário.
        
        Funções:
        - Verifica se o item do pixmap existe.
        - Obtém os valores de posição X e Y dos campos de texto.
        - Ajusta os valores para não serem negativos.
        - Define a nova posição da imagem.
        - Reseta os valores se ambos forem zero.
        - Atualiza o botão pushButton_Screen se a imagem foi removida.
        """

        if not self.pixmap_item:  # Verifica se o item do pixmap existe
            return

        try:
            x = int(self.lineEditX.text())  # Obtém o valor de posição X do campo de texto
            y = int(self.lineEditY.text())  # Obtém o valor de posição Y do campo de texto
        except ValueError:  # Lida com valores inválidos
            x = 0  # Define X como 0
            y = 0  # Define Y como 0
            self.lineEditX.setText(str(x))  # Define o valor de X no campo de texto
            self.lineEditY.setText(str(y))  # Define o valor de Y no campo de texto

        if x < 0:  # Ajusta X para não ser negativo
            x = 0
            self.lineEditX.setText(str(x))

        if y < 0:  # Ajusta Y para não ser negativo
            y = 0
            self.lineEditY.setText(str(y))

        # Ajustar a posição da imagem para o canto inferior esquerdo
        self.pixmap_item.setPos(x, y)  # Define a nova posição da imagem

        # Verificar se ambos os valores são 0 e resetar valores se necessário
        if x == 0 and y == 0:
            self.resetar_valores()  # Reseta os valores

        # Verificar se a imagem foi removida e atualizar o botão
        if x == 0 and y == 0 and self.pixmap_item is None:
            self.parent().pushButton_Screen.setText("ScreenOverlay")  # Atualiza o texto do botão
            self.parent().pushButton_Screen.setStyleSheet("color: black;")  # Define a cor do texto do botão como preto

    def aceitar(self):
        """
        Aceita e salva os dados do screen overlay, fechando o diálogo.
        
        Funções:
        - Verifica se o item do pixmap e o caminho da imagem existem.
        - Cria um dicionário com os dados do screen overlay.
        - Salva os dados no objeto pai.
        - Fecha o diálogo com aceitação.
        """

        if not self.pixmap_item:  # Verifica se o item do pixmap existe
            return

        if not self.image_path:  # Verifica se o caminho da imagem existe
            return

        self.screen_overlay_data = {  # Cria um dicionário com os dados do screen overlay
            "screenXY": (self.lineEditX.text(), self.lineEditY.text()),  # Posição da imagem
            "overlayXY": (1, 1),  # Posição do overlay (fixo como 1, 1)
            "sizeXY": (self.lineEditPX.text(), self.lineEditPY.text()),  # Tamanho da imagem
            "rotationXY": (0, 0),  # Rotação do overlay (fixo como 0, 0)
            "image_path": self.image_path  # Caminho da imagem
        }

        self.parent().screen_overlay_data = self.screen_overlay_data  # Salva os dados no objeto pai
        self.accept()  # Fecha o diálogo com aceitação

    def carregar_dados_screen_overlay(self):
        """
        Carrega os dados do screen overlay a partir do objeto pai e atualiza a interface do usuário.
        
        Funções:
        - Obtém os dados do screen overlay do objeto pai.
        - Verifica se há dados de screen overlay disponíveis.
        - Carrega a imagem se o caminho existir e for válido.
        - Atualiza os campos de texto com os valores de posição e tamanho.
        - Atualiza a posição e o tamanho da imagem.
        """
        
        screen_overlay_data = self.parent().screen_overlay_data  # Obtém os dados do screen overlay do objeto pai
        if screen_overlay_data:  # Verifica se há dados de screen overlay disponíveis
            self.image_path = screen_overlay_data.get("image_path")  # Obtém o caminho da imagem
            if self.image_path and os.path.exists(self.image_path):  # Verifica se o caminho da imagem existe e é válido
                self.adicionar_imagem(self.image_path)  # Carrega a imagem

            self.lineEditX.setText(screen_overlay_data["screenXY"][0])  # Atualiza o campo de texto de posição X
            self.lineEditY.setText(screen_overlay_data["screenXY"][1])  # Atualiza o campo de texto de posição Y
            self.lineEditPX.setText(screen_overlay_data["sizeXY"][0])  # Atualiza o campo de texto de largura
            self.lineEditPY.setText(screen_overlay_data["sizeXY"][1])  # Atualiza o campo de texto de altura

            self.atualizar_posicao_imagem()  # Atualiza a posição da imagem
            self.redimensionar_imagem()  # Redimensiona a imagem

    def adicionar_imagem(self, caminho_imagem=None):
        """
        Adiciona uma imagem ao QGraphicsView a partir de um caminho especificado ou abre um diálogo para selecionar a imagem.
        
        Parâmetros:
        caminho_imagem: str (opcional) - O caminho da imagem a ser adicionada.
        
        Funções:
        - Abre um diálogo de arquivo para selecionar a imagem se o caminho não for fornecido.
        - Carrega a imagem selecionada e a transforma para o QGraphicsView.
        - Atualiza os campos de texto com os valores de largura e altura da imagem.
        - Inicializa a posição da imagem.
        - Adiciona linhas de eixos.
        - Ativa os controles de redimensionamento e posicionamento.
        - Atualiza o botão pushButton_Screen do pai com um indicador visual.
        """
        
        if not caminho_imagem:  # Verifica se o caminho da imagem não foi fornecido
            formatos = "Imagens (*.png *.jpg *.jpeg *.bmp)"  # Define os formatos de imagem permitidos
            caminho_imagem, _ = QFileDialog.getOpenFileName(
                self, "Selecione uma imagem", self.last_opened_folder, formatos
            )  # Abre um diálogo para selecionar a imagem

        if caminho_imagem:  # Verifica se um caminho de imagem válido foi selecionado
            self.last_opened_folder = os.path.dirname(caminho_imagem)  # Atualiza o último diretório aberto
            self.image_path = caminho_imagem  # Armazena o caminho da imagem
            scene = QtWidgets.QGraphicsScene()  # Cria uma nova cena
            pixmap = QPixmap(caminho_imagem)  # Carrega a imagem selecionada
            self.original_pixmap = pixmap  # Armazena a imagem original
            pixmap = pixmap.transformed(QtGui.QTransform().scale(1, -1))  # Inverte a imagem no eixo Y
            self.pixmap_item = scene.addPixmap(pixmap)  # Adiciona a imagem à cena

            self.graphicsView.setScene(scene)  # Define a cena no QGraphicsView
            self.graphicsView.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)  # Ajusta a visualização da cena

            largura = pixmap.width()  # Obtém a largura da imagem
            altura = pixmap.height()  # Obtém a altura da imagem
            self.lineEditPX.setText(str(largura))  # Define o valor de largura no campo de texto
            self.lineEditPY.setText(str(altura))  # Define o valor de altura no campo de texto
            self.lineEditX.setText("0")  # Define o valor de posição X no campo de texto
            self.lineEditY.setText("0")  # Define o valor de posição Y no campo de texto

            self.original_pos = (0, 0)  # Inicializa a posição original da imagem
            self.atualizar_posicao_imagem()  # Atualiza a posição da imagem
            self.adicionar_linhas_eixos()  # Adiciona as linhas de eixos
            self.ativar_controles()  # Ativa os controles de redimensionamento e posicionamento

            self.parent().pushButton_Screen.setText("ScreenOverlay ✓")  # Atualiza o botão pushButton_Screen do pai
            self.parent().pushButton_Screen.setStyleSheet("color: blue;")  # Define a cor do texto do botão como azul

        if self.pixmap_item:  # ou outra condição que confirme a presença da imagem
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)