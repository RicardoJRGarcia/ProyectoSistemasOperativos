import time
import random
import heapq
import threading
from collections import deque
from queue import Queue


# -------------------------
# Clases Básicas y Utilidades
# -------------------------
class Proceso:
    def __init__(self, pid, prioridad):
        self.pid = pid
        self.prioridad = prioridad  # Un número mayor indica mayor prioridad
        self.recursos_asignados = []
        self.remaining_time = random.randint(3, 6)  # Tiempo de ejecución en quanta

    def __lt__(self, otro):
        return self.prioridad > otro.prioridad


class Recursos:
    def __init__(self, num_procesadores, ram_total):
        self.num_procesadores = num_procesadores
        self.ram_total = ram_total
        self.procesos_activos = []
        self.ram_disponible = ram_total

    def asignar_recursos(self, proceso, memoria_requerida):
        if len(self.procesos_activos) < self.num_procesadores and memoria_requerida <= self.ram_disponible:
            proceso.recursos_asignados.append(f"Memoria {memoria_requerida} MB")
            self.procesos_activos.append(proceso)
            self.ram_disponible -= memoria_requerida
            print(
                f"Proceso {proceso.pid} asignado con {memoria_requerida} MB. Memoria restante: {self.ram_disponible} MB.")
            return True
        else:
            print(
                f"Proceso {proceso.pid} no pudo asignarse (requiere {memoria_requerida} MB, disponible {self.ram_disponible} MB).")
        return False

    def liberar_recursos(self, proceso, memoria_requerida):
        if proceso in self.procesos_activos:
            self.procesos_activos.remove(proceso)
            self.ram_disponible += memoria_requerida
            proceso.recursos_asignados = []
            print(f"Proceso {proceso.pid} finalizó/suspendido. Memoria disponible actual: {self.ram_disponible} MB.")


# -------------------------
# Memoria Compartida con Timeout
# -------------------------
class MemoriaCompartida:
    def __init__(self, tamaño):
        self.buffer = Queue(maxsize=tamaño)
        self.sem_productor = threading.Semaphore(tamaño)
        self.sem_consumidor = threading.Semaphore(0)

    def producir(self, item, pid):
        # Intentamos adquirir el semáforo por máximo 1 segundo
        if not self.sem_productor.acquire(timeout=1):
            print(f"Advertencia [Memoria] Proceso {pid} no pudo producir: buffer lleno.")
            return
        self.buffer.put(item)
        print(f"🟢 [Memoria] Proceso {pid} PRODUCIO: {item}")
        self.sem_consumidor.release()

    def consumir(self, pid):
        # Intentamos adquirir el semáforo por máximo 1 segundo
        if not self.sem_consumidor.acquire(timeout=1):
            print(f"Advertencia [Memoria] Proceso {pid} no pudo consumir: buffer vacío.")
            return None
        item = self.buffer.get()
        print(f"[Memoria] Proceso {pid} CONSUMIÓ: {item}")
        self.sem_productor.release()
        return item


# -------------------------
# Planificador FCFS (No apropiativo)
# -------------------------
class PlanificadorFCFS:
    def __init__(self, gestor_recursos, memoria):
        self.cola_listos = deque()
        self.gestor_recursos = gestor_recursos
        self.memoria = memoria

    def agregar_proceso(self, proceso, memoria_requerida):
        self.cola_listos.append((proceso, memoria_requerida))
        print(f"Proceso {proceso.pid} agregado a la cola FCFS.")

    def ejecutar_procesos(self):
        while self.cola_listos:
            proceso, mem_req = self.cola_listos.popleft()
            asignado = False
            while not asignado:
                asignado = self.gestor_recursos.asignar_recursos(proceso, mem_req)
                if not asignado:
                    time.sleep(0.5)
            self.ejecutar_tarea_no_preemptible(proceso)
            self.gestor_recursos.liberar_recursos(proceso, mem_req)
        print("Todos los procesos han sido atendidos con FCFS.")

    def ejecutar_tarea_no_preemptible(self, proceso):
        role = random.choice(["producer", "consumer", "normal"])
        print(f"Proceso {proceso.pid} se ejecuta (no apropiativo) como '{role}'.")
        if role == "producer":
            for _ in range(3):
                item = random.randint(1, 100)
                self.memoria.producir(item, proceso.pid)
                time.sleep(0.3)
        elif role == "consumer":
            for _ in range(3):
                self.memoria.consumir(proceso.pid)
                time.sleep(0.3)
        else:
            print(f"Proceso {proceso.pid} realizando operaciones críticas.")
            time.sleep(1)
        print(f"Proceso {proceso.pid} terminó su tarea.")


# -------------------------
# Planificador por Prioridades (Preemptivo)
# -------------------------
class PlanificadorPrioridades:
    def __init__(self, gestor_recursos, memoria):
        self.cola_prioridad = []
        self.gestor_recursos = gestor_recursos
        self.memoria = memoria
        self.QUANTUM = 0.5

    def agregar_proceso(self, proceso, memoria_requerida):
        heapq.heappush(self.cola_prioridad, (-proceso.prioridad, proceso, memoria_requerida))
        print(f"Proceso {proceso.pid} (Prioridad: {proceso.prioridad}) agregado a la cola de prioridades.")

    def ejecutar_procesos(self):
        while self.cola_prioridad:
            neg_prio, proceso, mem_req = heapq.heappop(self.cola_prioridad)
            asignado = False
            while not asignado:
                asignado = self.gestor_recursos.asignar_recursos(proceso, mem_req)
                if not asignado:
                    time.sleep(0.5)
            role = random.choice(["producer", "consumer", "normal"])
            print(
                f"Proceso {proceso.pid} se ejecuta como '{role}'. Tiempo restante: {proceso.remaining_time} quantum.")
            while proceso.remaining_time > 0:
                if role == "producer":
                    item = random.randint(1, 100)
                    self.memoria.producir(item, proceso.pid)
                elif role == "consumer":
                    self.memoria.consumir(proceso.pid)
                else:
                    print(f"Proceso {proceso.pid} realizando operaciones críticas.")
                time.sleep(self.QUANTUM)
                proceso.remaining_time -= 1
                print(f"⏱ Proceso {proceso.pid} ejecutó un quantum. Tiempo restante: {proceso.remaining_time}.")
                if self.cola_prioridad:
                    proximo_prio = -self.cola_prioridad[0][0]
                    if proximo_prio > proceso.prioridad:
                        print(f"⏸ Proceso {proceso.pid} suspendido por la llegada de proceso de mayor prioridad.")
                        break
            self.gestor_recursos.liberar_recursos(proceso, mem_req)
            if proceso.remaining_time > 0:
                heapq.heappush(self.cola_prioridad, (-proceso.prioridad, proceso, mem_req))
                print(
                    f"Proceso {proceso.pid} reanudado en la cola con tiempo restante {proceso.remaining_time} quantum.")
            else:
                print(f"Proceso {proceso.pid} completó su ejecución.")
        print("🎉 Todos los procesos han sido atendidos con planificación por prioridades.")


# -------------------------
# Función Principal
# -------------------------
def main():
    print("Bienvenido al simulador integrado.")
    print("Seleccione el método de planificación:")
    print("1. FCFS (No apropiativo)")
    print("2. Planificación por prioridades (Apropiativo)")

    opcion = input("Ingrese el número de opción: ").strip()
    gestor = Recursos(num_procesadores=2, ram_total=4096)
    memoria = MemoriaCompartida(tamaño=5)

    if opcion == "1":
        planificador = PlanificadorFCFS(gestor, memoria)
    elif opcion == "2":
        planificador = PlanificadorPrioridades(gestor, memoria)
    else:
        print("Opción no válida. Saliendo...")
        return

    for _ in range(10):
        proc = Proceso(pid=random.randint(1, 1000), prioridad=random.randint(1, 10))
        mem_req = random.randint(256, 1024)
        planificador.agregar_proceso(proc, mem_req)

    planificador.ejecutar_procesos()
    print("Simulación completa.")


if __name__ == "__main__":
    main()