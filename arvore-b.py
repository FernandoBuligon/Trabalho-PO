import os

class BTreeNode:
    def __init__(self, is_leaf=False):
        self.is_leaf = is_leaf # flag indicando se é folha
        self.keys = [] # lista de chaves
        self.children = [] # lista de IDs de páginas dos filhos

    def __repr__(self):
        return f"[Keys: {self.keys} | Children: {self.children}]" # depuração

class DiskManager:
    def __init__(self):
        self.memory = {} # mapa page_id -> objeto armazenado
        self.next_page_id = 0 # próximo ID de página disponível
        self.reads = 0 # contador
        self.writes = 0 # contador

    def allocate_page(self, node): # aloca uma nova página
        page_id = self.next_page_id
        self.next_page_id += 1 # atualiza próximo ID
        self.write_page(page_id, node) 
        return page_id

    def read_page(self, page_id):
        self.reads += 1 # incrmenta o contador de leituras
        return self.memory.get(page_id) # retonrna o nó ou None

    def write_page(self, page_id, node):
        self.writes += 1 # incrementa o contador de escritas
        self.memory[page_id] = node # grava o nó 

class BTree:
    def __init__(self, order_m, disk_manager):
        self.m = order_m # ordem da árvore
        self.disk = disk_manager 
        self.root_id = None 

        # criar raiz vazia como folha e alocar no disco simulado
        root_node = BTreeNode(is_leaf=True)
        self.root_id = self.disk.allocate_page(root_node)

    def search(self, k, node_id=None):

        self.disk.reads = 0
        self.disk.writes = 0

        return self.search_recursive(k, node_id)

    def search_recursive(self, k, node_id): # função de busca

        if node_id is None: # começa pela raiz se não fornecido
            node_id = self.root_id 

        node = self.disk.read_page(node_id) # le o nó no disco
        i = 0
        while i < len(node.keys) and k > node.keys[i]: # avança
            i += 1

        if i < len(node.keys) and k == node.keys[i]:
            return True, node_id, i # caso encontrado, retorna sucesso
        
        if node.is_leaf: # folha 
            return False, node_id, i

        # chamada recursiva para o filho apropriado
        return self.search(k, node.children[i])

    def insert(self, k):

        # reinicia contadores
        self.disk.reads = 0
        self.disk.writes = 0

        # operação recursiva de inserção
        result = self._insert_recursive(self.root_id, k)

        # cria nova raiz em caso de cisão
        if result:
            median_key, new_right_child_id = result # mediana e novo nó a direita
            old_root_id = self.root_id # id da raiz antiga
            new_root = BTreeNode(is_leaf=False) # nova raiz
            new_root.keys = [median_key] # chave promovida
            new_root.children = [old_root_id, new_right_child_id] # filhos
            self.root_id = self.disk.allocate_page(new_root) # aloca nova raiz

    def _insert_recursive(self, node_id, k):
        node = self.disk.read_page(node_id) # le o nó

        # caso folha: inserir e possivelmente dividir
        if node.is_leaf: # verifica se é folha
            self._insert_key_into_node(node, k) # insere a chave
            self.disk.write_page(node_id, node) # grava o nó atualizado

            if len(node.keys) > self.m - 1: # verifica se passa da ordem
                return self._split_node(node) # realiza a cisão
            return None # sem cisão
        else:
            i = 0
            while i < len(node.keys) and k > node.keys[i]: # localiza filho apropriado
                i += 1

            child_id = node.children[i] # id do filho
            split_result = self._insert_recursive(child_id, k) # chamada recursiva da inserção

            if split_result: # verifica se houve cisão
                median, new_right_node_id = split_result # salva a mediana e o novo nó
                self._insert_key_into_node(node, median) # insere a chave
                node.children.insert(i + 1, new_right_node_id) # insere o ponteiro do novo nó
                self.disk.write_page(node_id, node) # grava o nó atualizado

                if len(node.keys) > self.m - 1: # caso esse novo nó exceda a ordem
                    return self._split_node(node)

            return None # sem cisão

    def _insert_key_into_node(self, node, k):
        i = 0
        while i < len(node.keys) and k > node.keys[i]: # encontra a posição
            i += 1
        node.keys.insert(i, k) # insere a chave

    def _split_node(self, node):
        mid_index = len(node.keys) // 2 # encontra o índice da mediana
        median_key = node.keys[mid_index] # chave mediana

        new_node = BTreeNode(is_leaf=node.is_leaf) # cria novo nó

        new_node.keys = node.keys[mid_index+1:] # chaves a direita
        node.keys = node.keys[:mid_index] # chaves a esquerda

        if not node.is_leaf: # verifica se não é folha
            new_node.children = node.children[mid_index+1:] # filhos a direita
            node.children = node.children[:mid_index+1] # filhos a esquerda

        # aloca e grava o novo nó
        new_node_id = self.disk.allocate_page(new_node)

        return median_key, new_node_id

    def print_tree(self, node_id=None, level=0):
        if node_id is None: # começa pela raiz se não fornecido
            node_id = self.root_id
            print("\n#----- Árvore -----#")

        node = self.disk.read_page(node_id) # le o nó
        print(f"Nível {level} [ID={node_id}]: {node.keys}") # imprime o nó

        if not node.is_leaf: # se não for folha
            for child_id in node.children: # percorre pelos filhos
                self.print_tree(child_id, level + 1) # chamada recursiva

def process_file(filename, btree):
    if not os.path.exists(filename): # verifica se o arquivo existe
        print(f"Arquivo {filename} não encontrado.")
        return # cancela a operação

    print(f"\nProcessando arquivo: {filename}") # informa que o arquivo foi encontrado e está sendo processado
    with open(filename, 'r') as f: # abre o arquivo
        for line in f: # le linha por linha
            parts = line.strip().split() # quebra as linhas
            if not parts: # linha vazia
                continue # pula

            command = parts[0].upper() # salva o comando em maiúsculo
            value = int(parts[1]) # converte o valor para int

            if command == "INSERT": # comando de inserção
                btree.insert(value) # insere o valor
                print(f"INSERT {value} -> Leituras: {btree.disk.reads}, Escritas: {btree.disk.writes}") # informa o resultado
            elif command == "SEARCH": # comando de busca
                found, page, idx = btree.search(value) # realiza a busca
                result = f"Encontrado na pág {page} índice {idx}" if found else "Não encontrado" # define o resultado
                print(f"SEARCH {value} -> {result} | Leituras: {btree.disk.reads}, Escritas: {btree.disk.writes}") # informa o resultado

    btree.print_tree() # imprime a arvore

if __name__ == "__main__":
    ORDEM = 5 # ordem da árvore
    ARQUIVO_ENTRADA = "comandos.txt" # arquivo de comandos

    disk = DiskManager() # cria o gerenciador de disco
    btree = BTree(order_m=ORDEM, disk_manager=disk) # cria a árvore B

    # criação de um arquivo de teste
    with open(ARQUIVO_ENTRADA, "w") as f:
        f.write("INSERT 85\n")
        f.write("INSERT 60\n")
        f.write("INSERT 52\n")
        f.write("INSERT 70\n")
        f.write("INSERT 58\n")
        f.write("SEARCH 60\n")
        f.write("SEARCH 99\n")

    process_file(ARQUIVO_ENTRADA, btree) # chama a função de processamento do arquivo