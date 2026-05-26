# Kiro example-repo

> Este es un mini-repo de ejemplo que podés cargar como contexto en Kiro para correr el demo del talk. Simula una organización con misconfigurations típicas y specs ya armados.

## Estructura

```
example-repo/
├── README.md                  # Este archivo
├── spec.md                    # Spec del Nivel 1 target
├── baseline-mock.json         # Baseline simulado (con gaps a propósito)
└── constraints.md             # Constraints de la "org" ejemplo
```

## Cómo usarlo

1. Abrí Kiro.
2. Cargá esta carpeta como contexto.
3. Decile a Kiro:

```
Acá tenés los archivos del proyecto.

Tarea:
1. Leé spec.md (lo que querés alcanzar).
2. Leé baseline-mock.json (el estado actual).
3. Generá plan.md con los gaps y cómo resolverlos.

NO uses comandos AWS reales (esto es un simulacro). Generá los comandos como si fueras a ejecutarlos.
```

Kiro va a generar plan.md.

4. Pediéle que te explique uno de los items en detalle.
5. Pediéle que genere los archivos de Terraform para esos fixes.
6. Mostrá el output al público.

## Por qué usar mock data

En vivo en una conferencia, no podés:

- Tener tu account real de prod abierta (datos sensibles en pantalla).
- Esperar a que AWS APIs respondan en tiempo real (latencia variable, falla red).
- Hacer demos destructivos.

Con mock data:

- Output predecible.
- Sin latencia.
- Si Kiro propone algo destructivo, no rompe nada.
- El público entiende el patrón sin distraerse con detalles de tu cuenta real.

## Tip de tiempo

Para la demo de 4 minutos:

- Min 0: cargar contexto, mostrar archivos.
- Min 1: pedir el plan.
- Min 2: Kiro genera plan.
- Min 3: pedir explicación de 1 item.
- Min 4: cierre.

Si tenés más tiempo (8 min):

- Pedirle a Kiro que genere los Terraform files.
- Mostrar el diff que generó.
- Comentar 1 caso edge que Kiro manejó bien.
