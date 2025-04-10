from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import QAction, QLabel

class ToolbarManager:
    def __init__(self, iface, dialog):
        """
        Inicializa o gerenciador de toolbar.

        :param iface: A interface do QGIS.
        :param dialog: O diálogo que contém os checkboxes.
        """
        self.iface = iface
        self.dialog = dialog
        self.settings = QSettings()

        # Define o texto com links
        self.dialog.label_refe.setTextFormat(Qt.RichText)
        self.dialog.label_refe.setText(
            'Criado por: <a href="https://www.facebook.com/leogomes21/">Leonardo Gomes</a> '
            '(<a href="mailto:leogomes21@gmail.com">leogomes21@gmail.com</a>)  * Nenhum <a href="https://www.youtube.com/@OLeoGomes">Direito Reservado</a>'
        )
        self.dialog.label_refe.setOpenExternalLinks(True)

        # Define os tooltips diretamente para o QLabel
        self.dialog.label_refe.setToolTip("Me mande Mensagens ou E-mails: Erros e ou Sugestões")

        # Nome das configurações e checkboxes associadas
        self.checkbox_mapping = {
            'checkBox_setasraster': 'add_to_toolbar_setasraster',
            'checkBox_curvas': 'add_to_toolbar_curvas',
            'checkBox_fotos_kmz': 'add_to_toolbar_fotos_kmz',
            'checkBox_linha_poligono': 'add_to_toolbar_linha_poligono',
            'checkBox_grade_utm_geo': 'add_to_toolbar_grade_utm_geo',
            'checkBox_cotasraster': 'add_to_toolbar_cotasraster',
            'checkBox_poligono_linha': 'add_to_toolbar_poligono_linha',
            'checkBox_op_linhas': 'add_to_toolbar_operacoeslinhas',
            'checkBox_linhas_dentro_poligonos': 'add_to_toolbar_dentrolinhas',
            'checkBox_cria_malhas': 'add_to_toolbar_malha',
            'checkBox_rasterizar_malhas': 'add_to_toolbar_rasterizar_malha',
            'checkBox_converter_para_malhas': 'add_to_toolbar_converte_malha',
            'checkBox_criar_plato': 'add_to_toolbar_plato_mdt',
            'checkBox_calculos_volume': 'add_to_toolbar_volume_mdt',
            'checkBox_grafico_talude': 'add_to_toolbar_grafico_PyQt',
            'checkBox_grafico_perfis': 'add_to_toolbar_grafico_perfil',
            'checkBox_grafico_estruturas': 'add_to_toolbar_grafico_estruturas',
        }
        # Carrega as configurações iniciais
        self.load_settings()

        # # Conecta os checkboxes às funções de salvamento e atualização da toolbar
        self.dialog.checkBox_setasraster.stateChanged.connect(lambda state: self.save_setting('checkBox_setasraster', state))
        self.dialog.checkBox_curvas.stateChanged.connect(lambda state: self.save_setting('checkBox_curvas', state))
        self.dialog.checkBox_fotos_kmz.stateChanged.connect(lambda state: self.save_setting('checkBox_fotos_kmz', state))
        self.dialog.checkBox_linha_poligono.stateChanged.connect( lambda state: self.save_setting('checkBox_linha_poligono', state))
        self.dialog.checkBox_grade_utm_geo.stateChanged.connect(lambda state: self.save_setting('checkBox_grade_utm_geo', state))
        self.dialog.checkBox_cotasraster.stateChanged.connect(lambda state: self.save_setting('checkBox_cotasraster', state))
        self.dialog.checkBox_poligono_linha.stateChanged.connect( lambda state: self.save_setting('checkBox_poligono_linha', state))
        self.dialog.checkBox_op_linhas.stateChanged.connect(lambda state: self.save_setting('checkBox_op_linhas', state))
        self.dialog.checkBox_linhas_dentro_poligonos.stateChanged.connect(lambda state: self.save_setting('checkBox_linhas_dentro_poligonos', state))
        self.dialog.checkBox_cria_malhas.stateChanged.connect(lambda state: self.save_setting('checkBox_cria_malhas', state))
        self.dialog.checkBox_rasterizar_malhas.stateChanged.connect(lambda state: self.save_setting('checkBox_rasterizar_malhas', state))
        self.dialog.checkBox_converter_para_malhas.stateChanged.connect(lambda state: self.save_setting('checkBox_converter_para_malhas', state))
        self.dialog.checkBox_criar_plato.stateChanged.connect(lambda state: self.save_setting('checkBox_criar_plato', state))
        self.dialog.checkBox_calculos_volume.stateChanged.connect(lambda state: self.save_setting('checkBox_calculos_volume', state))
        self.dialog.checkBox_grafico_talude.stateChanged.connect(lambda state: self.save_setting('checkBox_grafico_talude', state))
        self.dialog.checkBox_grafico_perfis.stateChanged.connect(lambda state: self.save_setting('checkBox_grafico_perfis', state))
        self.dialog.checkBox_grafico_estruturas.stateChanged.connect(lambda state: self.save_setting('checkBox_grafico_estruturas', state))

    def load_settings(self):
        """
        Carrega as configurações armazenadas para os checkboxes.
        """
        for checkbox, setting_key in self.checkbox_mapping.items():
            state = self.settings.value(setting_key, False, type=bool)
            getattr(self.dialog, checkbox).setChecked(state)

    def save_setting(self, checkbox, state):
        """
        Salva o estado do checkbox nas configurações e atualiza a barra de ferramentas.

        :param checkbox: O nome do checkbox.
        :param state: O estado do checkbox (0 para não marcado, 2 para marcado).
        """
        setting_key = self.checkbox_mapping[checkbox]
        should_add = state == 2
        self.settings.setValue(setting_key, should_add)

        # Atualiza a barra de ferramentas imediatamente
        action = self.get_action_for_checkbox(checkbox)
        if action:
            if should_add:
                self.iface.addToolBarIcon(action)
            else:
                self.iface.removeToolBarIcon(action)

    def should_add_to_toolbar(self, setting_key):
        """
        Verifica se a ação deve ser adicionada à barra de ferramentas.

        :param setting_key: A chave de configuração associada à ação.
        :return: True se a ação deve ser adicionada à barra de ferramentas, False caso contrário.
        """
        return self.settings.value(setting_key, False, type=bool)

    def get_action_for_checkbox(self, checkbox):
        """
        Retorna a ação associada ao checkbox para que ela possa ser adicionada/removida da toolbar.

        :param checkbox: O nome do checkbox.
        :return: A QAction correspondente.
        """
        # Retorne a ação correspondente ao checkbox
        if checkbox == 'checkBox_setasraster':
            return self.iface.mainWindow().findChild(QAction, 'setasraster_action')
        elif checkbox == 'checkBox_curvas':
            return self.iface.mainWindow().findChild(QAction, 'curvas_action')  # Retorna a ação para curvas
        elif checkbox == 'checkBox_fotos_kmz':
            return self.iface.mainWindow().findChild(QAction, 'fotos_action')  # Retorna a ação para fotos_kmz
        elif checkbox == 'checkBox_linha_poligono':
            return self.iface.mainWindow().findChild(QAction, 'linha_poligono_action')  # Retorna a ação para linha_poligono
        elif checkbox == 'checkBox_grade_utm_geo':
            return self.iface.mainWindow().findChild(QAction, 'grade_utm_geo_action')  # Retorna a ação para grade_utm_geo
        elif checkbox == 'checkBox_cotasraster':
            return self.iface.mainWindow().findChild(QAction, 'cotasraster_action')  # Retorna a ação para cotasraster
        elif checkbox == 'checkBox_poligono_linha':
            return self.iface.mainWindow().findChild(QAction, 'poligono_linha_action')  # Retorna a ação para poligono_linha
        elif checkbox == 'checkBox_op_linhas':
            return self.iface.mainWindow().findChild(QAction, 'operacoeslinhas_action')
        elif checkbox == 'checkBox_linhas_dentro_poligonos':
            return self.iface.mainWindow().findChild(QAction, 'dentrolinhas_action')
        elif checkbox == 'checkBox_cria_malhas':
            return self.iface.mainWindow().findChild(QAction, 'malha_action')
        elif checkbox == 'checkBox_rasterizar_malhas':
            return self.iface.mainWindow().findChild(QAction, 'rasterizarmalha_action')
        elif checkbox == 'checkBox_converter_para_malhas':
            return self.iface.mainWindow().findChild(QAction, 'malhaconverte_action')
        elif checkbox == 'checkBox_criar_plato':
            return self.iface.mainWindow().findChild(QAction, 'plato_mdt_action')
        elif checkbox == 'checkBox_calculos_volume':
            return self.iface.mainWindow().findChild(QAction, 'volume_mdt_action')
        elif checkbox == 'checkBox_grafico_talude':
            return self.iface.mainWindow().findChild(QAction, 'grafico_PyQt_action')
        elif checkbox == 'checkBox_grafico_perfis':
            return self.iface.mainWindow().findChild(QAction, 'grafico_perfil_action')
        elif checkbox == 'checkBox_grafico_estruturas':
            return self.iface.mainWindow().findChild(QAction, 'grafico_estruturas_action')

        return None
