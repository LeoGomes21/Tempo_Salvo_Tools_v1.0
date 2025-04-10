from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QProgressBar
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsPointXY, QgsFeature, QgsGeometry, QgsPoint, QgsCoordinateReferenceSystem, QgsMeshLayer, QgsMapSettings, QgsFields, QgsField
from qgis.PyQt.QtCore import Qt, QVariant
import xml.etree.ElementTree as ET
from qgis.utils import iface
from qgis.PyQt import uic
import processing
import math
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ConverterMalhas.ui'))

class MalhaConverteManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(MalhaConverteManager, self).__init__(parent)
        # Configura a interface do usuário a partir do Designer.
        self.setupUi(self)

        # Altera o título da janela
        self.setWindowTitle("Converte para Malhas")

        self.iface = iface  # Armazena a referência da interface QGIS

        # Deixa o checkBoxPontos marcado por padrão
        self.checkBoxPontos.setChecked(True)

        # Conecta os sinais aos slots
        self.connect_signals()

    def connect_signals(self):

        # Conecta o botão pushButton_converte para abrir o arquivo DXF e converter
        self.pushButton_converte.clicked.connect(self.converter_dxf_para_malha)

        # Conecta o botão pushButton_converteDAE para abrir o arquivo DAE e converter  
        self.pushButton_converteDAE.clicked.connect(self.on_converte_dae_clicked)

        # Conecta o botão pushButton_converteSTL para abrir o arquivo STL e converter
        self.pushButton_converteSTL.clicked.connect(self.on_converte_stl_clicked)

        # Conecta o botão pushButton_converteOBJ para abrir o arquivo OBJ e converter
        self.pushButton_converteOBJ.clicked.connect(self.on_converte_obj_clicked)

        # Conecta o botão Fechar ao slot de fechar o diálogo
        self.pushButtonFechar.clicked.connect(self.close)

    def showEvent(self, event):
        """
        Sobrescreve o evento de exibição do diálogo para resetar os Widgets.
        """
        super(MalhaConverteManager, self).showEvent(event)

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
        progressMessageBar = self.iface.messageBar().createMessage("Gerando Camadas de Pontos de Apoio...")
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

    def execute_mesh_calculation(self, points_layer):
        """
        Executa o algoritmo de criação da malha TIN a partir de uma camada de pontos.
        
        :param points_layer: Camada de pontos (PointZ) já carregada no projeto.
        """
        temp_layer = None
        progress_msg = None

        try:
            # Se a camada não for válida ou não for de pontos, emite mensagem de erro
            if not points_layer or not points_layer.isValid():
                self.mostrar_mensagem("Camada inválida ou não encontrada.", "Erro")
                return

            if points_layer.geometryType() != QgsWkbTypes.PointGeometry:
                self.mostrar_mensagem("A camada fornecida não é do tipo ponto.", "Erro")
                return

            # Inicia barra de progresso
            progress_bar, progress_msg = self.iniciar_progress_bar(1)

            # No caso em que a camada já é PointZ, usamos -1 para indicar 
            # "pegar o Z diretamente da geometria"
            z_field_index = -1

            # Monta os parâmetros de entrada para o algoritmo
            source_data = [{
                'source': points_layer.id(),
                'type': 2,               # 2 significa "Usar pontos para os vértices do TIN"
                'attributeIndex': z_field_index
            }]

            # Executa o algoritmo de criação TIN
            result = processing.run("native:tinmeshcreation", {
                'SOURCE_DATA': source_data,
                'MESH_FORMAT': 0,  # 0 = .mesh, 1 = .vtk
                'CRS_OUTPUT': QgsCoordinateReferenceSystem(),  # CRS vazio => mantém o CRS da camada
                'OUTPUT_MESH': 'TEMPORARY_OUTPUT'
            })

            # Carrega o arquivo de malha resultante
            mesh_path = result['OUTPUT_MESH']
            mesh_layer = QgsMeshLayer(mesh_path, "Malha_TIN", "mdal")
            if not mesh_layer.isValid():
                raise Exception("Falha ao carregar a malha gerada.")

            # Adiciona ao projeto QGIS
            QgsProject.instance().addMapLayer(mesh_layer)

            # Exibe mensagem de sucesso
            self.mostrar_mensagem(
                "Malha TIN gerada com sucesso a partir da camada de pontos!",
                "Sucesso",
                caminho_pasta=QgsProject.instance().homePath()
            )

        except Exception as e:
            self.mostrar_mensagem(f"Erro: {str(e)}", "Erro")
        finally:
            # Fecha a barra de progresso, se aberta
            if progress_msg is not None:
                self.iface.messageBar().popWidget(progress_msg)

    def converter_dxf_para_malha(self):
        try:
            # Abre o diálogo para selecionar o arquivo DXF
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self,
                "Abrir Arquivo DXF",
                "",
                "Arquivos DXF (*.dxf)"
            )
            if not file_path:
                self.mostrar_mensagem("Nenhum arquivo selecionado.", "Aviso")
                return

            # Carrega o arquivo DXF como uma camada vetorial
            dxf_layer = QgsVectorLayer(file_path, "DXF Layer", "ogr")
            if not dxf_layer.isValid():
                raise ValueError("Falha ao carregar o arquivo DXF.")

            # Se o checkBoxGRADE estiver marcado, adiciona o DXF como camada ao projeto
            if self.checkBoxGRADE.isChecked():
                QgsProject.instance().addMapLayer(dxf_layer)

            # Filtra apenas as feições do tipo PolygonZ
            face_features = [
                f for f in dxf_layer.getFeatures() 
                if f.geometry().wkbType() == QgsWkbTypes.PolygonZ
            ]
            if not face_features:
                raise ValueError("O arquivo DXF não contém polígonos 3D (PolygonZ).")

            # Lista para armazenar (ID, QgsPoint) já com coordenadas Z
            points_with_z = []
            invalid_z_count = 0
            feature_id = 1  # Contador para o campo 'ID'

            # Extrai vértices de cada feição PolygonZ
            for feature in face_features:
                geom = feature.geometry()
                # .vertices() retorna todos os vértices do polígono,
                # preservando Z se a geometria for 3D
                for pt in geom.vertices():
                    # Se Z for inválido ou NaN, forçamos Z = 0
                    if pt.z() is None or math.isnan(pt.z()):
                        invalid_z_count += 1
                        pt.setZ(0)
                    points_with_z.append((feature_id, pt))
                    feature_id += 1

            if invalid_z_count > 0:
                self._log_message(
                    f"{invalid_z_count} pontos possuíam Z inválido ou nulo. Ajustados para Z = 0."
                )

            # Cria camada de memória com suporte a Z
            crs = dxf_layer.crs()
            points_layer = QgsVectorLayer(
                f"PointZ?crs={crs.authid()}",
                "Pontos_3D",
                "memory"
            )

            # Adiciona campos: ID, X, Y, Z
            fields = QgsFields()
            fields.append(QgsField("ID", QVariant.Int))
            fields.append(QgsField("X", QVariant.Double))
            fields.append(QgsField("Y", QVariant.Double))
            fields.append(QgsField("Z", QVariant.Double))

            provider = points_layer.dataProvider()
            provider.addAttributes(fields)
            points_layer.updateFields()

            # Adiciona as feições de pontos na camada
            features = []
            for (pid, pt) in points_with_z:
                feat = QgsFeature()
                # Define a geometria diretamente como 3D
                feat.setGeometry(QgsGeometry(QgsPoint(pt.x(), pt.y(), pt.z())))
                feat.setAttributes([
                    pid,
                    pt.x(),
                    pt.y(),
                    pt.z()
                ])
                features.append(feat)

            provider.addFeatures(features)
            points_layer.updateExtents()

            # 1) Adiciona a camada de pontos ao projeto para garantir ID válido
            QgsProject.instance().addMapLayer(points_layer)
            
            # 2) Executa a criação da malha
            self.execute_mesh_calculation(points_layer)
            
            # 3) Se o usuário não marcou a checkBoxPontos, removemos do projeto
            if not self.checkBoxPontos.isChecked():
                QgsProject.instance().removeMapLayer(points_layer.id())

            self.mostrar_mensagem(
                "Malha TIN gerada a partir do DXF com sucesso!",
                "Sucesso")

        except Exception as e:
            self.mostrar_mensagem(f"Erro: {str(e)}", "Erro")

    def parse_collada_generic(dae_file):
        """
        Exemplo de parser Collada que percorre todas as <geometry> dentro de <library_geometries>,
        tentando ler <mesh> com <source> e <triangles> ou <polylist>.
        
        Retorna uma lista de (vertices, faces), onde:
          vertices = [(x, y, z), (x, y, z), ...]
          faces = [(i1, i2, i3), (i1, i2, i3), ...]
        representando cada <geometry> encontrada.
        Não aplica transformações de <visual_scene>.
        """
        import xml.etree.ElementTree as ET

        tree = ET.parse(dae_file)
        root = tree.getroot()
        ns = {"c": "http://www.collada.org/2005/11/COLLADASchema"}

        # Pode haver várias <geometry> em <library_geometries>
        geometries = root.findall(".//c:library_geometries/c:geometry", ns)
        all_geoms = []  # lista de (vertices, faces)

        for geometry in geometries:
            mesh = geometry.find("c:mesh", ns)
            if mesh is None:
                continue

            # Descobrir <source> que contenha as posições (semantic="POSITION")
            # 1) tentar via <vertices> -> <input semantic="POSITION" source="#...">
            vertices_source_id = None
            vertices_input = mesh.find("c:vertices/c:input[@semantic='POSITION']", ns)
            if vertices_input is not None:
                vertices_source_id = vertices_input.get("source", "").replace("#", "")

            # 2) Se não achou, tentar via <triangles> ou <polylist> -> <input semantic="VERTEX" source="#...">
            if not vertices_source_id:
                tri_or_poly = mesh.find("c:triangles|c:polylist", ns)
                if tri_or_poly is not None:
                    vertex_input = tri_or_poly.find("c:input[@semantic='VERTEX']", ns)
                    if vertex_input is not None:
                        vertices_source_id = vertex_input.get("source", "").replace("#", "")

            if not vertices_source_id:
                # Não achou a fonte de posições
                continue

            # Achar <source id="vertices_source_id"> e pegar float_array
            pos_source = mesh.find(f"c:source[@id='{vertices_source_id}']", ns)
            if pos_source is None:
                continue

            float_array = pos_source.find("c:float_array", ns)
            if float_array is None:
                continue

            pos_values = list(map(float, float_array.text.split()))
            vertices = []
            for i in range(0, len(pos_values), 3):
                x = pos_values[i]
                y = pos_values[i + 1]
                z = pos_values[i + 2]
                vertices.append((x, y, z))

            # Juntar faces
            faces = []

            # Tentar <triangles>
            for tri_block in mesh.findall("c:triangles", ns):
                p_elem = tri_block.find("c:p", ns)
                if p_elem is not None:
                    idx_list = list(map(int, p_elem.text.split()))
                    # (Exemplo simples, assumindo offset=0 e só VERTEX)
                    for i in range(0, len(idx_list), 3):
                        i1 = idx_list[i]
                        i2 = idx_list[i+1]
                        i3 = idx_list[i+2]
                        faces.append((i1, i2, i3))

            # Tentar <polylist>
            for poly_block in mesh.findall("c:polylist", ns):
                p_elem = poly_block.find("c:p", ns)
                if p_elem is not None:
                    idx_list = list(map(int, p_elem.text.split()))
                    # Se <polylist> tiver vcount ou polígonos com + de 3 lados, é preciso triangulá-los.
                    # Aqui, faremos um parse simples assumindo triângulos diretos (vcount=3).
                    for i in range(0, len(idx_list), 3):
                        i1 = idx_list[i]
                        i2 = idx_list[i+1]
                        i3 = idx_list[i+2]
                        faces.append((i1, i2, i3))

            # Adiciona esse (vertices, faces) à lista
            all_geoms.append((vertices, faces))

        return all_geoms

    def parse_collada_export_to_dae_format(self, dae_file):
        """
        Lê um .dae no formato exato gerado pela sua função 'export_to_dae',
        retornando UMA lista de vértices e UMA lista de triângulos.
        """
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(dae_file)
        root = tree.getroot()
        ns = {"c": "http://www.collada.org/2005/11/COLLADASchema"}

        # 1) Achar o array de posições <source id="mesh-positions"> -> <float_array>
        float_positions = root.find(".//c:source[@id='mesh-positions']/c:float_array", ns)
        if float_positions is None:
            raise ValueError("Não foi encontrado <float_array> de posições com id='mesh-positions-array' no DAE.")
        pos_values = list(map(float, float_positions.text.split()))

        vertices = []
        for i in range(0, len(pos_values), 3):
            x = pos_values[i]
            y = pos_values[i+1]
            z = pos_values[i+2]
            vertices.append((x, y, z))

        # 2) Achar <triangles> -> <p> ...
        p_element = root.find(".//c:mesh/c:triangles/c:p", ns)
        if p_element is None:
            raise ValueError("Não foi encontrado o elemento <p> dentro de <triangles> no DAE exportado.")
        all_indices_text = p_element.text.strip().split()
        if len(all_indices_text) % 3 != 0:
            raise ValueError("A quantidade de índices em <p> não é múltipla de 3.")

        indices = list(map(int, all_indices_text))
        faces = []
        for i in range(0, len(indices), 3):
            i1 = indices[i]
            i2 = indices[i+1]
            i3 = indices[i+2]
            faces.append((i1, i2, i3))

        return [(vertices, faces)]  # Retorna uma lista de 1 tupla

    def on_converte_dae_clicked(self):
        file_dialog = QFileDialog()
        dae_path, _ = file_dialog.getOpenFileName(
            self,
            "Selecione o arquivo DAE",
            "",
            "Arquivos Collada (*.dae)"
        )
        if not dae_path:
            self.mostrar_mensagem("Nenhum arquivo DAE selecionado.", "Aviso")
            return

        # Gera o mesmo nome, porém com extensão .2dm
        dae_dir = os.path.dirname(dae_path)
        dae_base = os.path.splitext(os.path.basename(dae_path))[0]  # ex: "modelo" se o arquivo for "modelo.dae"
        output_2dm = os.path.join(dae_dir, f"{dae_base}.2dm")

        # Chama a função que faz a leitura do .dae, gera .2dm e gerencia camadas
        self.converter_dae_para_2dm_auto(dae_path, output_2dm)

    def _adicionar_vertices_como_pontos(self, list_of_vertices, mesh_crs):
        """
        Cria e adiciona ao projeto uma camada de pontos (PointZ)
        a partir de uma lista de vértices (x, y, z), usando o
        mesmo CRS definido pela malha (mesh_crs).
        """
        # Verifica se o CRS é válido; se não for, use um fallback (ex: EPSG:4326)
        if mesh_crs.isValid():
            crs_string = f"PointZ?crs={mesh_crs.authid()}"
        else:
            crs_string = "PointZ?crs=EPSG:4326"

        layer = QgsVectorLayer(crs_string, "Pontos_3D", "memory")
        if not layer.isValid():
            self.mostrar_mensagem("Falha ao criar camada de pontos em memória", "Erro")
            return

        # Define campos
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        fields.append(QgsField("X", QVariant.Double))
        fields.append(QgsField("Y", QVariant.Double))
        fields.append(QgsField("Z", QVariant.Double))

        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()

        # Cria as feições e atribui a geometria 3D
        feats = []
        for i, (x, y, z) in enumerate(list_of_vertices, start=1):
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry(QgsPoint(x, y, z)))
            feat.setAttributes([i, x, y, z])
            feats.append(feat)

        provider.addFeatures(feats)
        layer.updateExtents()

        # Adiciona a camada ao projeto
        QgsProject.instance().addMapLayer(layer)

    def converter_dae_para_2dm_auto(self, dae_path, output_2dm):
        """
        Tenta converter automaticamente um arquivo .dae (Collada) para .2dm:
          1) Tenta parse específico (padrão 'export_to_dae').
          2) Se falhar, faz parse genérico.
          3) Gera o arquivo .2dm com ND e E3T.
          4) Carrega a malha .2dm no QGIS.
          5) Se checkBoxPontos estiver marcada, cria camada de pontos 3D.
          6) Se checkBoxGRADE estiver marcada, cria camada de linhas com o mesmo CRS da malha.
        """
        try:
            if not os.path.exists(dae_path):
                raise FileNotFoundError(f"Arquivo DAE não encontrado: {dae_path}")

            # 1) Tenta parse específico
            try:
                all_geoms = self.parse_collada_export_to_dae_format(dae_path)
                self.mostrar_mensagem("Arquivo DAE no formato 'export_to_dae' detectado!", "Aviso")
            except Exception as e_esp:
                # 2) Se falhar, tenta parse genérico
                self.mostrar_mensagem(
                    "Não é do formato específico. Tentando parser genérico...",
                    "Aviso"
                )
                try:
                    all_geoms = self.parse_collada_generic(dae_path)
                    self.mostrar_mensagem("Arquivo DAE parseado em modo genérico!", "Aviso")
                except Exception as e_gen:
                    raise ValueError(
                        f"Não foi possível parsear o DAE de forma específica nem genérica.\n"
                        f"Erro específico: {str(e_esp)}\n"
                        f"Erro genérico: {str(e_gen)}"
                    )

            if not all_geoms:
                raise ValueError("Não foram encontradas geometrias válidas no arquivo DAE.")

            # Consolida as geometrias em um único conjunto de vértices (global_vertices) e faces (global_faces)
            global_vertices = []
            global_faces = []
            for (verts, faces) in all_geoms:
                start_idx = len(global_vertices)
                global_vertices.extend(verts)
                for (i1, i2, i3) in faces:
                    global_faces.append((start_idx + i1, start_idx + i2, start_idx + i3))

            if not global_vertices or not global_faces:
                raise ValueError("Nenhum vértice ou face encontrado após o parse.")

            # 3) Gera o arquivo .2dm (ND e E3T)
            with open(output_2dm, "w", encoding="utf-8") as f:
                f.write("MESH2D\n")
                # ND (nós) - 1-indexado
                for idx, (x, y, z) in enumerate(global_vertices, start=1):
                    f.write(f"ND {idx} {x} {y} {z}\n")
                # E3T (faces triangulares) - 1-indexado
                for t_idx, (i1, i2, i3) in enumerate(global_faces, start=1):
                    f.write(f"E3T {t_idx} {i1+1} {i2+1} {i3+1}\n")

            # 4) Carrega a malha .2dm no QGIS
            mesh_layer = QgsMeshLayer(output_2dm, "DAE_2DM_Mesh", "mdal")
            if not mesh_layer.isValid():
                raise ValueError("Falha ao carregar a malha .2dm gerada no QGIS.")
            QgsProject.instance().addMapLayer(mesh_layer)

            # Vamos obter o CRS da malha:
            # (Observação: algumas malhas podem não ter CRS definido, nesse caso mesh_crs.isValid() será False)
            mesh_crs = mesh_layer.crs()

            # 5) Se checkBoxPontos estiver marcada, cria camada de pontos 3D (pode definir outro CRS, se desejar)
            if self.checkBoxPontos.isChecked():
                self._adicionar_vertices_como_pontos(global_vertices, mesh_crs)

            # 6) Se checkBoxGRADE estiver marcada, cria camada de linhas com o mesmo CRS da malha
            if self.checkBoxGRADE.isChecked():
                self._adicionar_linhas_grade(global_vertices, global_faces, mesh_crs)

            # Mensagem final de sucesso
            self.mostrar_mensagem(
                f"Conversão de '{os.path.basename(dae_path)}' para '{os.path.basename(output_2dm)}' concluída com sucesso!",
                "Sucesso"
            )

        except Exception as e:
            self.mostrar_mensagem(f"Erro na conversão DAE→2DM: {str(e)}", "Erro")

    def _adicionar_linhas_grade(self, vertices, faces, mesh_crs):
        """
        Cria uma camada de linhas (LineString) representando as arestas
        de cada triângulo, usando o CRS da malha (caso válido).
        Cada aresta vira uma feição.

        :param vertices: lista de (x, y, z) zero-based
        :param faces: lista de (i1, i2, i3)
        :param mesh_crs: QgsCoordinateReferenceSystem obtido do mesh_layer.crs()
        """
        # Determina qual string de CRS usar
        crs_string = "LineString"
        if mesh_crs.isValid():
            # Ex: "EPSG:31982", "EPSG:4326", etc.
            crs_string += f"?crs={mesh_crs.authid()}"
        else:
            # fallback
            crs_string += "?crs=EPSG:4326"

        # 1) Descobrir todas as arestas sem duplicar
        edges = set()
        for (i1, i2, i3) in faces:
            e1 = tuple(sorted((i1, i2)))
            e2 = tuple(sorted((i2, i3)))
            e3 = tuple(sorted((i3, i1)))
            edges.add(e1)
            edges.add(e2)
            edges.add(e3)

        # 2) Criar camada de linhas em memória usando crs_string
        lines_layer = QgsVectorLayer(crs_string, "Grade_Linhas_2D", "memory")
        if not lines_layer.isValid():
            self.mostrar_mensagem("Falha ao criar camada de linhas em memória", "Erro")
            return

        # Adiciona campos
        provider = lines_layer.dataProvider()
        fields = QgsFields()
        fields.append(QgsField("EDGE_ID", QVariant.Int))
        fields.append(QgsField("V1", QVariant.Int))
        fields.append(QgsField("V2", QVariant.Int))
        provider.addAttributes(fields)
        lines_layer.updateFields()

        # 3) Preparar feições
        feats = []
        edge_id = 1
        for (vA, vB) in edges:
            xA, yA, zA = vertices[vA]
            xB, yB, zB = vertices[vB]

            feat = QgsFeature()
            # Cria linha 2D
            line_geom = QgsGeometry.fromPolyline([
                QgsPoint(xA, yA),
                QgsPoint(xB, yB)
            ])
            feat.setGeometry(line_geom)
            feat.setAttributes([edge_id, vA+1, vB+1])
            feats.append(feat)
            edge_id += 1

        # 4) Adiciona feições em modo de edição
        lines_layer.startEditing()
        provider.addFeatures(feats)
        lines_layer.commitChanges()

        lines_layer.updateExtents()
        QgsProject.instance().addMapLayer(lines_layer)

        self.mostrar_mensagem(f"{len(feats)} arestas adicionadas à camada de linhas (CRS: {mesh_crs.authid()}).", "Aviso")

    def parse_stl_ascii(stl_path):
        """
        Lê um arquivo STL ASCII e retorna:
          - Uma lista de vértices (x, y, z) em 'global_vertices'
          - Uma lista de faces (i1, i2, i3) em 'global_faces'
        Cada face corresponde a 3 vértices. Duplicados são unificados.

        Retorna (global_vertices, global_faces).

        * Não lida com STL binário.
        """
        import re

        # Regex para extrair linhas do tipo "vertex x y z"
        vertex_pattern = re.compile(r'^\s*vertex\s+([+-]?\d+(\.\d+)?([eE][+-]?\d+)?)\s+([+-]?\d+(\.\d+)?([eE][+-]?\d+)?)\s+([+-]?\d+(\.\d+)?([eE][+-]?\d+)?)')

        vertices_map = {}  # dict para evitar vértices duplicados => {(x, y, z): index}
        global_vertices = []
        global_faces = []
        
        with open(stl_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        current_facet_vertices = []  # vai acumular índices de 3 vértices

        for line in lines:
            line = line.strip()
            # Tenta casar com "vertex x y z"
            m = vertex_pattern.match(line)
            if m:
                # Extraímos x, y, z
                x_str, y_str, z_str = m.group(1), m.group(4), m.group(7)
                x, y, z = float(x_str), float(y_str), float(z_str)

                # Se ainda não existe no map, cria
                if (x, y, z) not in vertices_map:
                    idx = len(global_vertices)
                    vertices_map[(x, y, z)] = idx
                    global_vertices.append((x, y, z))
                
                # Index do vértice
                v_idx = vertices_map[(x, y, z)]
                current_facet_vertices.append(v_idx)

                # Se já pegamos 3 vértices => 1 triângulo
                if len(current_facet_vertices) == 3:
                    # (i1, i2, i3)
                    i1, i2, i3 = current_facet_vertices
                    global_faces.append((i1, i2, i3))
                    current_facet_vertices = []  # zera para o próximo triângulo

        return (global_vertices, global_faces)

    def converter_stl_para_2dm_auto(self, stl_path, output_2dm):
        """
        Converte um arquivo STL ASCII para .2dm (Mesh 2D).
        - Lê o STL usando parse_stl_ascii (não binário).
        - Gera e adiciona a malha .2dm ao QGIS.
        - Se checkBoxPontos estiver marcado, cria camada de pontos.
        - Se checkBoxGRADE estiver marcado, cria camada de linhas.
        """
        import os
        
        try:
            if not os.path.exists(stl_path):
                raise FileNotFoundError(f"Arquivo STL não encontrado: {stl_path}")

            # 1) Lê STL ASCII, obtém vértices e faces
            global_vertices, global_faces = self.parse_stl_ascii(stl_path)
            if not global_vertices or not global_faces:
                raise ValueError("Não foi possível extrair triângulos do STL (pode não ser ASCII ou estar vazio).")

            # 2) Gera arquivo .2dm
            with open(output_2dm, 'w', encoding='utf-8') as f:
                f.write("MESH2D\n")
                # ND
                for idx, (x, y, z) in enumerate(global_vertices, start=1):
                    f.write(f"ND {idx} {x} {y} {z}\n")

                # E3T
                for t_idx, (i1, i2, i3) in enumerate(global_faces, start=1):
                    f.write(f"E3T {t_idx} {i1+1} {i2+1} {i3+1}\n")

            # 3) Carrega .2dm no QGIS
            mesh_layer = QgsMeshLayer(output_2dm, "STL_2DM_Mesh", "mdal")
            if not mesh_layer.isValid():
                raise ValueError("Falha ao carregar a malha .2dm gerada no QGIS.")
            QgsProject.instance().addMapLayer(mesh_layer)

            # 4) Obter CRS da malha (talvez seja indefinido, mas tentamos):
            mesh_crs = mesh_layer.crs()

            # 5) Se checkBoxPontos estiver marcado, cria camada de pontos
            if self.checkBoxPontos.isChecked():
                self._adicionar_vertices_como_pontos(global_vertices, mesh_crs)

            # 6) Se checkBoxGRADE estiver marcado, cria camada de linhas
            if self.checkBoxGRADE.isChecked():
                self._adicionar_linhas_grade(global_vertices, global_faces, mesh_crs)

            self.mostrar_mensagem(
                f"Conversão de '{os.path.basename(stl_path)}' para '{os.path.basename(output_2dm)}' concluída com sucesso!",
                "Sucesso"
            )

        except Exception as e:
            self.mostrar_mensagem(f"Erro na conversão STL→2DM: {str(e)}", "Erro")

    def parse_stl_ascii(self, stl_path):
        """
        Lê um arquivo STL ASCII e retorna (global_vertices, global_faces).
        Cada triângulo = 3 linhas "vertex x y z".
        """
        import re

        vertex_pattern = re.compile(r'^\s*vertex\s+([+-]?\d+(\.\d+)?([eE][+-]?\d+)?)\s+([+-]?\d+(\.\d+)?([eE][+-]?\d+)?)\s+([+-]?\d+(\.\d+)?([eE][+-]?\d+)?)')

        vertices_map = {}
        global_vertices = []
        global_faces = []
        current_facet_vertices = []

        with open(stl_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        for line in lines:
            match = vertex_pattern.match(line)
            if match:
                x_str, y_str, z_str = match.group(1), match.group(4), match.group(7)
                x, y, z = float(x_str), float(y_str), float(z_str)

                if (x, y, z) not in vertices_map:
                    idx = len(global_vertices)
                    vertices_map[(x, y, z)] = idx
                    global_vertices.append((x, y, z))

                v_idx = vertices_map[(x, y, z)]
                current_facet_vertices.append(v_idx)
                
                if len(current_facet_vertices) == 3:
                    # fechou 1 triângulo
                    i1, i2, i3 = current_facet_vertices
                    global_faces.append((i1, i2, i3))
                    current_facet_vertices = []

        return (global_vertices, global_faces)

    def on_converte_stl_clicked(self):
        # Abre diálogo para selecionar STL
        file_dialog = QFileDialog()
        stl_path, _ = file_dialog.getOpenFileName(
            self,
            "Selecione o arquivo STL (ASCII)",
            "",
            "Arquivos STL (*.stl)"
        )
        if not stl_path:
            self.mostrar_mensagem("Nenhum arquivo STL selecionado.", "Aviso")
            return

        # Monta nome .2dm no mesmo diretório
        stl_dir = os.path.dirname(stl_path)
        stl_base = os.path.splitext(os.path.basename(stl_path))[0]
        output_2dm = os.path.join(stl_dir, f"{stl_base}.2dm")

        # Converte e adiciona ao projeto
        self.converter_stl_para_2dm_auto(stl_path, output_2dm)

    def converter_obj_para_2dm_auto(self, obj_path, output_2dm):
        """
        Converte um arquivo OBJ (simplificado) para .2dm e adiciona ao QGIS:
          - Lê o OBJ (v, f) com parse_obj
          - Gera ND/E3T
          - Carrega Mesh .2dm
          - Se checkBoxPontos estiver marcado => cria camada de pontos
          - Se checkBoxGRADE estiver marcado => cria camada de linhas
        """

        try:
            if not os.path.exists(obj_path):
                raise FileNotFoundError(f"Arquivo OBJ não encontrado: {obj_path}")

            # 1) Parse do OBJ
            global_vertices, global_faces = self.parse_obj(obj_path)
            if not global_vertices or not global_faces:
                raise ValueError("Não foi possível extrair vértices/faces do OBJ. Verifique o formato.")

            # 2) Gera .2dm
            with open(output_2dm, 'w', encoding='utf-8') as f:
                f.write("MESH2D\n")
                # ND
                for idx, (x, y, z) in enumerate(global_vertices, start=1):
                    f.write(f"ND {idx} {x} {y} {z}\n")
                # E3T
                for t_idx, (i1, i2, i3) in enumerate(global_faces, start=1):
                    f.write(f"E3T {t_idx} {i1+1} {i2+1} {i3+1}\n")

            # 3) Carrega .2dm no QGIS
            mesh_layer = QgsMeshLayer(output_2dm, "OBJ_2DM_Mesh", "mdal")
            if not mesh_layer.isValid():
                raise ValueError("Falha ao carregar a malha .2dm gerada no QGIS.")
            QgsProject.instance().addMapLayer(mesh_layer)

            # 4) Tentamos obter CRS (normalmente OBJ não define CRS)
            mesh_crs = mesh_layer.crs()

            # 5) Se checkBoxPontos estiver marcado => criar camada de pontos
            if self.checkBoxPontos.isChecked():
                self._adicionar_vertices_como_pontos(global_vertices, mesh_crs)

            # 6) Se checkBoxGRADE estiver marcado => criar camada de linhas
            if self.checkBoxGRADE.isChecked():
                self._adicionar_linhas_grade(global_vertices, global_faces, mesh_crs)

            # Mensagem final
            self.mostrar_mensagem(
                f"Conversão de '{os.path.basename(obj_path)}' para '{os.path.basename(output_2dm)}' concluída com sucesso!",
                "Sucesso"
            )

        except Exception as e:
            self.mostrar_mensagem(f"Erro na conversão OBJ→2DM: {str(e)}", "Erro")

    def parse_obj(self, obj_path):
        """
        Lê um arquivo Wavefront OBJ (simplificado) e retorna (global_vertices, global_faces).

        - Considera apenas linhas que começam com 'v ' para vértices e 'f ' para faces.
        - Faz triangulação em fan se a face tiver mais de 3 vértices.
        - Ignora 'vn', 'vt', etc.
        - Indíces em faces são 1-based no OBJ, convertidos para 0-based para a lista de vértices.

        Exemplo de face triangular:
            f 1 2 3
        Exemplo de face poligonal (5 vértices):
            f 1 2 3 4 5
          -> Triangulado em: (1,2,3), (1,3,4), (1,4,5) [ajustando para 0-based depois]
        """
        global_vertices = []
        global_faces = []

        with open(obj_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('v '):
                    # Ex: v x y z
                    # Quebra em tokens. tokens[0] = 'v', tokens[1] = x, etc.
                    tokens = line.split()
                    if len(tokens) < 4:
                        continue
                    x = float(tokens[1])
                    y = float(tokens[2])
                    z = float(tokens[3])
                    global_vertices.append((x, y, z))
                
                elif line.startswith('f '):
                    # Ex: f 1 2 3   ou f 1 2 3 4 ...
                    tokens = line.split()
                    # tokens[0] = 'f', tokens[1..] = índices
                    face_indices = []
                    for t in tokens[1:]:
                        # Se vier no formato "v/vt" ou "v/vt/vn", pegamos apenas a parte antes do '/'
                        # Por ex, se t='10/11', split('/') -> ['10','11']; pegamos '10'
                        v_str = t.split('/')[0]
                        v_idx = int(v_str) - 1  # OBJ é 1-based => convertemos p/ 0-based
                        face_indices.append(v_idx)
                    
                    # Se a face tiver 3 vértices, é um triângulo
                    # Se tiver mais, triangulamos em FAN (ex: face 4 ou 5)
                    # Ex: se face_indices = [0,1,2,3], geramos tri (0,1,2) e (0,2,3).
                    if len(face_indices) < 3:
                        continue

                    v0 = face_indices[0]
                    for i in range(1, len(face_indices) - 1):
                        v1 = face_indices[i]
                        v2 = face_indices[i + 1]
                        global_faces.append((v0, v1, v2))

        return (global_vertices, global_faces)

    def on_converte_obj_clicked(self):
        # Diálogo para escolher .obj
        file_dialog = QFileDialog()
        obj_path, _ = file_dialog.getOpenFileName(
            self,
            "Selecione o arquivo OBJ",
            "",
            "Arquivos OBJ (*.obj)"
        )
        if not obj_path:
            self.mostrar_mensagem("Nenhum arquivo OBJ selecionado.", "Aviso")
            return

        # Monta caminho .2dm com mesmo nome
        obj_dir = os.path.dirname(obj_path)
        obj_base = os.path.splitext(os.path.basename(obj_path))[0]
        output_2dm = os.path.join(obj_dir, f"{obj_base}.2dm")

        # Chama a conversão
        self.converter_obj_para_2dm_auto(obj_path, output_2dm)