<template>
    <div class="three-scene-wrapper">
        <div ref="container" class="three-container"></div>
        <div class="controls-hint">
            <span>🎮 WASD/方向鍵 移動 | 🖱️ 拖曳旋轉鏡頭 | ␣ 上升 / Shift 下降</span>
        </div>
        <div class="speed-control">
            <label>
                速度
                <input
                    v-model.number="moveSpeed"
                    type="range"
                    min="1"
                    max="20"
                    step="0.5"
                />
                <span class="speed-value">{{ moveSpeed.toFixed(1) }}</span>
            </label>
        </div>
        <div
            v-if="hoveredBoxInfo"
            class="box-tooltip"
            :style="{ left: `${tooltipPosition.x}px`, top: `${tooltipPosition.y}px` }"
        >
            <div class="tooltip-label">箱子編號</div>
            <div class="tooltip-id">#{{ hoveredBoxInfo.boxId }}</div>
            <div class="tooltip-label">商品名稱</div>
            <div class="tooltip-name">{{ hoveredBoxInfo.productName }}</div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { useCargoData } from "../composables/useCargoData.js";
import {
    convertBoxesToCargoData,
    saveCargoDataToBackend,
} from "../utils/cargoStorage.js";

const container = ref(null);
let scene,
    camera,
    renderer,
    boxes = [],
    baseModel = null,
    trackPieces = [],
    player = null;
const unloadBays = [
    { cells: ["0-0", "1-0"], protrudeSteps: 1 },
    { cells: ["3-0", "4-0"], protrudeSteps: 1 },
];
const unloadAreaCells = new Set(unloadBays.flatMap((bay) => bay.cells));
let yaw = 0;
let pitch = -0.3;
const cameraOffset = new THREE.Vector3(0, 2, 6);
const moveSpeed = ref(6.5);
const keyState = new Set();
let isDragging = false;
let previousPointer = { x: 0, y: 0 };
const clock = new THREE.Clock();
let animationId = null;
let handleResize = null;
let handleKeyDown = null;
let handleKeyUp = null;
let handlePointerDown = null;
let handlePointerMove = null;
let handlePointerUp = null;
let handleMouseLeave = null;
const hoveredBoxInfo = ref(null);
const tooltipPosition = ref({ x: 0, y: 0 });
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

// 使用 cargo 數據管理
const {
    cargoData,
    loading: cargoLoading,
    error: cargoError,
    startPolling,
    stopPolling,
} = useCargoData({
    apiBaseUrl: "http://localhost:8000",
    pollInterval: 5000,
    autoStart: false, // 手動控制啟動
});

onMounted(() => {
    if (!container.value) return;

    // 創建場景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1224);
    scene.fog = new THREE.Fog(0x0b1224, 35, 160);

    // 創建相機
    camera = new THREE.PerspectiveCamera(
        75,
        container.value.clientWidth / container.value.clientHeight,
        0.1,
        1000,
    );
    camera.position.set(0, 2, 8);

    // 創建渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.value.clientWidth, container.value.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 確保 canvas 可以正確接收滑鼠事件
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.touchAction = "none";

    container.value.appendChild(renderer.domElement);

    // 添加環境光
    const ambientLight = new THREE.AmbientLight(0xf2f5ff, 0.55);
    scene.add(ambientLight);

    // 添加柔和天空光
    const hemiLight = new THREE.HemisphereLight(0x67e8f9, 0x0f172a, 0.6);
    hemiLight.position.set(0, 25, 0);
    scene.add(hemiLight);

    // 添加定向光
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.9);
    directionalLight.position.set(12, 18, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.set(2048, 2048);
    directionalLight.shadow.camera.near = 2;
    directionalLight.shadow.camera.far = 80;
    directionalLight.shadow.camera.left = -50;
    directionalLight.shadow.camera.right = 50;
    directionalLight.shadow.camera.top = 50;
    directionalLight.shadow.camera.bottom = -50;
    scene.add(directionalLight);

    // 重置對象所有變換的輔助函數
    function resetTransform(object) {
        object.position.set(0, 0, 0);
        object.rotation.set(0, 0, 0);
        object.quaternion.set(0, 0, 0, 1);
        object.scale.set(1, 1, 1);
        object.matrix.identity();
        object.matrixWorld.identity();
        object.matrixWorldNeedsUpdate = false;
    }

    // 加載 blue_box.glb 模型並創建方塊陣列
    const loader = new GLTFLoader();
    loader.load(
        "/blue_box.glb",
        (gltf) => {
            const originalScene = gltf.scene;

            // 先計算原始模型的邊界框（考慮所有變換）
            originalScene.updateMatrixWorld(true);
            const originalBox = new THREE.Box3().setFromObject(originalScene);
            const originalSize = originalBox.getSize(new THREE.Vector3());
            const originalMin = originalBox.min;
            const originalMax = originalBox.max;
            const originalCenter = new THREE.Vector3(
                (originalMin.x + originalMax.x) / 2,
                (originalMin.y + originalMax.y) / 2,
                (originalMin.z + originalMax.z) / 2,
            );

            // 創建一個新的 Group 來作為標準化的基礎模型
            baseModel = new THREE.Group();

            // 深度遍歷原始場景，提取所有 Mesh 的幾何體和材質
            // 然後創建新的 Mesh，不保留任何變換
            const meshes = [];
            originalScene.traverse((child) => {
                if (child.isMesh) {
                    // 獲取世界矩陣
                    child.updateMatrixWorld(true);
                    const worldMatrix = child.matrixWorld.clone();

                    // 提取幾何體和材質
                    let geometry = child.geometry.clone();
                    const material = child.material.clone();

                    // 應用世界變換到幾何體的頂點
                    geometry.applyMatrix4(worldMatrix);

                    // 創建新的 Mesh，沒有任何變換
                    const newMesh = new THREE.Mesh(geometry, material);
                    newMesh.castShadow = true;
                    newMesh.receiveShadow = true;
                    resetTransform(newMesh);

                    meshes.push(newMesh);
                }
            });

            // 將所有 Mesh 添加到一個 Group 中
            const normalizedGroup = new THREE.Group();
            meshes.forEach((mesh) => {
                normalizedGroup.add(mesh);
            });

            // 計算標準化後的邊界框
            resetTransform(normalizedGroup);
            normalizedGroup.updateMatrixWorld(true);
            const normalizedBox = new THREE.Box3().setFromObject(
                normalizedGroup,
            );
            const normalizedSize = normalizedBox.getSize(new THREE.Vector3());
            const normalizedMin = normalizedBox.min;
            const normalizedMax = normalizedBox.max;
            const normalizedCenter = new THREE.Vector3(
                (normalizedMin.x + normalizedMax.x) / 2,
                (normalizedMin.y + normalizedMax.y) / 2,
                (normalizedMin.z + normalizedMax.z) / 2,
            );

            // 平移 Group 使模型中心在原點
            normalizedGroup.position.set(
                -normalizedCenter.x,
                -normalizedCenter.y,
                -normalizedCenter.z,
            );

            // 將標準化的 Group 添加到基礎模型
            baseModel.add(normalizedGroup);
            resetTransform(baseModel);
            baseModel.updateMatrixWorld(true);

            // 重新計算最終的邊界框
            const finalBox = new THREE.Box3().setFromObject(baseModel);
            const modelSize = finalBox.getSize(new THREE.Vector3());
            const finalMin = finalBox.min;
            const finalMax = finalBox.max;
            const modelCenter = new THREE.Vector3(
                (finalMin.x + finalMax.x) / 2,
                (finalMin.y + finalMax.y) / 2,
                (finalMin.z + finalMax.z) / 2,
            );

            console.log("模型加載成功!");
            console.log("原始模型尺寸:", originalSize);
            console.log("標準化後模型尺寸:", modelSize);
            console.log("標準化後模型中心:", modelCenter);
            console.log("最終邊界框:", finalMin, "到", finalMax);

            // 創建方塊陣列 (5x10x5 = 250個)
            const gridMetrics = createBoxGridFromModel(
                5,
                10,
                5,
                modelSize,
                modelCenter,
            );

            // 調整相機位置
            adjustCamera(5, 10, 5, modelSize);

            // 使用 blue_box.glb 打造高於貨物的環形軌道
            createTrackLoop(gridMetrics);

            // 建立卸貨區並鋪設軌道
            createUnloadAreas(gridMetrics);

            // 鋪設地板與氛圍燈光
            createWarehouseGround(gridMetrics);
            createWarehouseLights(gridMetrics);

            // 建立可控制的玩家模型
            createPlayer(modelSize);
        },
        (progress) => {
            console.log(
                "加載進度:",
                (progress.loaded / progress.total) * 100 + "%",
            );
        },
        (error) => {
            console.error("加載模型時出錯:", error);
        },
    );

    // 從模型創建方塊網格的函數
    function createBoxGridFromModel(width, depth, height, modelSize, modelCenter) {
        // 使用模型的實際尺寸（確保為正數）
        const boxWidth = Math.max(Math.abs(modelSize.x), 0.01);
        const boxDepth = Math.max(Math.abs(modelSize.z), 0.01);
        const boxHeight = Math.max(Math.abs(modelSize.y), 0.01);

        // 方塊之間的間距（模型大小的10%）
        const spacingX = boxWidth * 0.2;
        const spacingZ = boxDepth * 0.2;
        const spacingY = boxHeight * 0;

        // 貨架厚度（細細的）
        const shelfThickness = Math.min(spacingX, spacingZ, spacingY) * 0.15;

        // 計算總尺寸
        const totalWidth = width * boxWidth + (width - 1) * spacingX;
        const totalDepth = depth * boxDepth + (depth - 1) * spacingZ;
        const totalHeight = height * boxHeight + (height - 1) * spacingY;

        // 計算起始位置
        const startX = -totalWidth / 2 + boxWidth / 2;
        const startZ = -totalDepth / 2 + boxDepth / 2;
        const startY = -totalHeight / 2 + boxHeight / 2;

        const topLayerCenterY = startY + (height - 1) * (boxHeight + spacingY);
        const topY = topLayerCenterY - modelCenter.y + boxHeight / 2;
        const pillarTopY = topY + boxHeight;
        const bottomY = startY - modelCenter.y - boxHeight / 2;

        // 創建白色材質（用於支柱）
        const shelfMaterial = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            metalness: 0.3,
            roughness: 0.7,
        });

        // 支柱的半徑
        const pillarRadius = Math.min(boxWidth, boxDepth) * 0.02;

        // 創建方塊
        for (let x = 0; x < width; x++) {
            for (let z = 0; z < depth; z++) {
                const isUnloadCell = unloadAreaCells.has(`${x}-${z}`);

                for (let y = 0; y < height; y++) {
                    if (isUnloadCell) {
                        continue;
                    }

                    const targetCenterX = startX + x * (boxWidth + spacingX);
                    const targetCenterZ = startZ + z * (boxDepth + spacingZ);
                    const targetCenterY = startY + y * (boxHeight + spacingY);

                    const clonedModel = baseModel.clone(true);
                    clonedModel.traverse((child) => {
                        if (child.isMesh || child.isGroup || child.isObject3D) {
                            resetTransform(child);
                        }
                    });

                    resetTransform(clonedModel);
                    clonedModel.position.set(
                        targetCenterX - modelCenter.x,
                        targetCenterY - modelCenter.y,
                        targetCenterZ - modelCenter.z,
                    );
                    const boxId = boxes.length + 1;
                    clonedModel.userData = {
                        boxId,
                        productName: `商品 ${boxId}`,
                    };
                    clonedModel.updateMatrixWorld(true);
                    scene.add(clonedModel);
                    boxes.push(clonedModel);
                }
            }
        }

        // 在每個 XZ 位置創建支柱（從地面到最高層頂部再往上一格）
        for (let x = 0; x < width; x++) {
            for (let z = 0; z < depth; z++) {
                const targetCenterX = startX + x * (boxWidth + spacingX);
                const targetCenterZ = startZ + z * (boxDepth + spacingZ);

                // 支柱高度
                const pillarHeight = pillarTopY - bottomY;

                const halfWidth = boxWidth / 2;
                const halfDepth = boxDepth / 2;

                // 四個角的相對位置
                const corners = [
                    { x: -halfWidth, z: -halfDepth }, // 左前
                    { x: halfWidth, z: -halfDepth }, // 右前
                    { x: -halfWidth, z: halfDepth }, // 左後
                    { x: halfWidth, z: halfDepth }, // 右後
                ];

                corners.forEach((corner) => {
                    const pillarGeometry = new THREE.CylinderGeometry(
                        pillarRadius,
                        pillarRadius,
                        pillarHeight,
                        8,
                    );
                    const pillar = new THREE.Mesh(
                        pillarGeometry,
                        shelfMaterial,
                    );

                    // 設置支柱位置
                    pillar.position.set(
                        targetCenterX - modelCenter.x + corner.x,
                        bottomY + pillarHeight / 2,
                        targetCenterZ - modelCenter.z + corner.z,
                    );

                    scene.add(pillar);
                });
            }
        }

        const firstBoxCenterX = startX - modelCenter.x;
        const firstBoxCenterY = startY - modelCenter.y;
        const firstBoxCenterZ = startZ - modelCenter.z;

        console.log(
            `成功創建 ${boxes.length} 個方塊 (${width}x${depth}x${height} = ${width * depth * height})`,
        );
        console.log(
            `模型尺寸: 寬=${boxWidth.toFixed(2)}, 高=${boxHeight.toFixed(2)}, 深=${boxDepth.toFixed(2)}`,
        );
        console.log(
            `陣列總尺寸: 寬=${totalWidth.toFixed(2)}, 高=${totalHeight.toFixed(2)}, 深=${totalDepth.toFixed(2)}`,
        );
        console.log(
            `第一個方塊中心位置: (${firstBoxCenterX.toFixed(2)}, ${firstBoxCenterY.toFixed(2)}, ${firstBoxCenterZ.toFixed(2)})`,
        );

        // 將方塊數據轉換為貨物數據格式並儲存到後端
        console.log("準備儲存貨物數據...", {
            boxesCount: boxes.length,
            modelSize,
        });

        const cargoDataToSave = convertBoxesToCargoData(boxes, {
            x: boxWidth,
            y: boxHeight,
            z: boxDepth,
        });

        console.log(
            "已轉換貨物數據，準備發送到後端...",
            cargoDataToSave.length,
        );

        saveCargoDataToBackend(cargoDataToSave, {
            apiBaseUrl: "http://localhost:8000",
            onSuccess: (result) => {
                console.log("✓ 貨物數據已成功同步到後端", result);
            },
            onError: (error) => {
                console.error("✗ 同步貨物數據到後端時出錯", error);
            },
        }).catch((err) => {
            console.error("✗ 儲存貨物數據異常:", err);
        });

        return {
            width,
            depth,
            height,
            boxWidth,
            boxDepth,
            boxHeight,
            spacingX,
            spacingZ,
            spacingY,
            totalWidth,
            totalDepth,
            totalHeight,
            startX,
            startY,
            startZ,
            topY,
            pillarTopY,
            bottomY,
            modelCenter,
        };
    }

    // 調整相機位置的函數
    function adjustCamera(width, depth, height, modelSize) {
        const boxWidth = modelSize.x;
        const boxDepth = modelSize.z;
        const boxHeight = modelSize.y;

        const spacingX = boxWidth * 0.1;
        const spacingZ = boxDepth * 0.1;
        const spacingY = boxHeight * 0.1;

        const totalWidth = width * boxWidth + (width - 1) * spacingX;
        const totalDepth = depth * boxDepth + (depth - 1) * spacingZ;
        const totalHeight = height * boxHeight + (height - 1) * spacingY;

        // 調整相機初始距離以適應所有方塊
        const maxDim = Math.max(totalWidth, totalDepth, totalHeight);
        const fov = camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
        cameraZ *= 1.6; // 添加一些邊距

        cameraOffset.set(0, Math.max(1.8, cameraZ * 0.2), cameraZ * 0.6);
    }

    function createWarehouseGround(gridMetrics) {
        const pad = Math.max(gridMetrics.boxWidth, gridMetrics.boxDepth) * 6;
        const groundSize = Math.max(gridMetrics.totalWidth, gridMetrics.totalDepth) + pad;
        const groundGeometry = new THREE.PlaneGeometry(groundSize, groundSize);
        const groundMaterial = new THREE.MeshStandardMaterial({
            color: 0x0f172a,
            roughness: 0.92,
            metalness: 0.08,
            envMapIntensity: 0.35,
        });
        const ground = new THREE.Mesh(groundGeometry, groundMaterial);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = gridMetrics.bottomY - gridMetrics.boxHeight * 0.55;
        ground.receiveShadow = true;
        scene.add(ground);

        const grid = new THREE.GridHelper(
            groundSize,
            Math.max(20, Math.floor(groundSize / (gridMetrics.boxWidth * 0.8))),
            0x334155,
            0x1e293b,
        );
        grid.material.opacity = 0.35;
        grid.material.transparent = true;
        grid.position.y = ground.position.y + 0.01;
        scene.add(grid);

        const accentWidth = gridMetrics.totalWidth * 0.4;
        const accentDepth = gridMetrics.boxDepth * 2.5;
        const accentGeometry = new THREE.PlaneGeometry(accentWidth, accentDepth);
        const accentMaterial = new THREE.MeshStandardMaterial({
            color: 0x0ea5e9,
            emissive: 0x0ea5e9,
            emissiveIntensity: 0.12,
            transparent: true,
            opacity: 0.35,
        });
        const accent = new THREE.Mesh(accentGeometry, accentMaterial);
        accent.rotation.x = -Math.PI / 2;
        accent.position.set(
            0,
            ground.position.y + 0.02,
            gridMetrics.startZ - gridMetrics.modelCenter.z - accentDepth * 0.3,
        );
        accent.receiveShadow = true;
        scene.add(accent);
    }

    function createWarehouseLights(gridMetrics) {
        const baseHeight = gridMetrics.pillarTopY + gridMetrics.boxHeight * 1.2;
        const radiusX = gridMetrics.totalWidth * 0.65;
        const radiusZ = gridMetrics.totalDepth * 0.65;

        const ringColor = 0x38bdf8;
        const warmColor = 0xfbbf24;

        const ringPositions = [
            new THREE.Vector3(-radiusX, baseHeight, -radiusZ),
            new THREE.Vector3(radiusX, baseHeight, -radiusZ),
            new THREE.Vector3(-radiusX, baseHeight, radiusZ),
            new THREE.Vector3(radiusX, baseHeight, radiusZ),
        ];

        ringPositions.forEach((pos) => {
            const spot = new THREE.SpotLight(ringColor, 0.6, 120, Math.PI / 4, 0.4, 1);
            spot.position.copy(pos);
            spot.target.position.set(0, gridMetrics.bottomY + gridMetrics.boxHeight, 0);
            spot.castShadow = true;
            spot.penumbra = 0.45;
            scene.add(spot);
            scene.add(spot.target);
        });

        unloadBays.forEach((bay) => {
            bay.cells.forEach((cellKey) => {
                const [x, z] = cellKey.split("-").map(Number);
                const stepX = gridMetrics.boxWidth + gridMetrics.spacingX;
                const stepZ = gridMetrics.boxDepth + gridMetrics.spacingZ;
                const xPos =
                    gridMetrics.startX + (x + 0.5) * stepX - gridMetrics.modelCenter.x;
                const zPos =
                    gridMetrics.startZ + (z + 0.5) * stepZ - gridMetrics.modelCenter.z;
                const light = new THREE.PointLight(warmColor, 0.6, 40, 1.8);
                light.position.set(xPos, baseHeight * 0.7, zPos - stepZ * (bay.protrudeSteps || 0));
                light.castShadow = true;
                scene.add(light);
            });
        });
    }

    function createTrackSegment({
        sizeX,
        sizeZ,
        position,
        gridMetrics,
        trackThickness,
        parent,
    }) {
        const segment = baseModel.clone(true);
        segment.traverse((child) => {
            if (child.isMesh || child.isGroup || child.isObject3D) {
                resetTransform(child);
            }
            if (child.isMesh) {
                child.material = new THREE.MeshStandardMaterial({
                    color: 0xffffff,
                    metalness: 0.08,
                    roughness: 0.3,
                    emissive: 0x2a2a2a,
                    emissiveIntensity: 0.2,
                });
                child.castShadow = true;
                child.receiveShadow = true;
            }
        });

        resetTransform(segment);
        segment.scale.set(
            sizeX / gridMetrics.boxWidth,
            trackThickness / gridMetrics.boxHeight,
            sizeZ / gridMetrics.boxDepth,
        );
        segment.position.copy(position);
        segment.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
            }
        });
        trackPieces.push(segment);
        (parent || scene).add(segment);
    }

    function createTrackLoop(gridMetrics) {
        if (!baseModel) return;

        const trackGroup = new THREE.Group();
        const laneWidth = Math.max(
            Math.min(gridMetrics.spacingX, gridMetrics.spacingZ) * 0.8,
            gridMetrics.boxWidth * 0.1,
        );
        const trackThickness = gridMetrics.boxHeight * 0.08;
        const trackY = gridMetrics.pillarTopY + trackThickness * 0.5;

        const stepX = gridMetrics.boxWidth + gridMetrics.spacingX;
        const stepZ = gridMetrics.boxDepth + gridMetrics.spacingZ;

        const horizontalLength = gridMetrics.totalWidth + laneWidth;
        const verticalLength = gridMetrics.totalDepth + laneWidth;

        for (let z = 0; z < gridMetrics.depth - 1; z++) {
            const zPos =
                gridMetrics.startZ + (z + 0.5) * stepZ - gridMetrics.modelCenter.z;
            createTrackSegment({
                sizeX: horizontalLength,
                sizeZ: laneWidth,
                position: new THREE.Vector3(0, trackY, zPos),
                gridMetrics,
                trackThickness,
                parent: trackGroup,
            });
        }

        for (let x = 0; x < gridMetrics.width - 1; x++) {
            const xPos =
                gridMetrics.startX + (x + 0.5) * stepX - gridMetrics.modelCenter.x;
            createTrackSegment({
                sizeX: laneWidth,
                sizeZ: verticalLength,
                position: new THREE.Vector3(xPos, trackY, 0),
                gridMetrics,
                trackThickness,
                parent: trackGroup,
            });
        }

        const leftRingX =
            gridMetrics.startX - stepX / 2 - gridMetrics.modelCenter.x;
        const rightRingX =
            gridMetrics.startX + (gridMetrics.width - 1) * stepX + stepX / 2 -
            gridMetrics.modelCenter.x;
        const topRingZ = gridMetrics.startZ - stepZ / 2 - gridMetrics.modelCenter.z;
        const bottomRingZ =
            gridMetrics.startZ + (gridMetrics.depth - 1) * stepZ + stepZ / 2 -
            gridMetrics.modelCenter.z;

        const horizontalRingSpan = rightRingX - leftRingX;
        const verticalRingSpan = bottomRingZ - topRingZ;
        const ringCenterX = (leftRingX + rightRingX) / 2;
        const ringCenterZ = (topRingZ + bottomRingZ) / 2;
        const horizontalRingLength = Math.max(
            horizontalRingSpan - laneWidth,
            laneWidth,
        );
        const verticalRingLength = Math.max(verticalRingSpan - laneWidth, laneWidth);

        createTrackSegment({
            sizeX: horizontalRingLength,
            sizeZ: laneWidth,
            position: new THREE.Vector3(ringCenterX, trackY, topRingZ),
            gridMetrics,
            trackThickness,
            parent: trackGroup,
        });

        createTrackSegment({
            sizeX: horizontalRingLength,
            sizeZ: laneWidth,
            position: new THREE.Vector3(ringCenterX, trackY, bottomRingZ),
            gridMetrics,
            trackThickness,
            parent: trackGroup,
        });

        createTrackSegment({
            sizeX: laneWidth,
            sizeZ: verticalRingLength,
            position: new THREE.Vector3(leftRingX, trackY, ringCenterZ),
            gridMetrics,
            trackThickness,
            parent: trackGroup,
        });

        createTrackSegment({
            sizeX: laneWidth,
            sizeZ: verticalRingLength,
            position: new THREE.Vector3(rightRingX, trackY, ringCenterZ),
            gridMetrics,
            trackThickness,
            parent: trackGroup,
        });

        scene.add(trackGroup);
    }

    function createUnloadAreas(gridMetrics) {
        if (!baseModel || unloadBays.length === 0) return;

        const trackThickness = gridMetrics.boxHeight * 0.08;
        const trackY = gridMetrics.bottomY + trackThickness * 0.5;
        const stepX = gridMetrics.boxWidth + gridMetrics.spacingX;
        const stepZ = gridMetrics.boxDepth + gridMetrics.spacingZ;

        unloadBays.forEach((bay) => {
            const unloadCells = bay.cells.map((cellKey) => {
                const [x, z] = cellKey.split("-").map(Number);
                return { x, z };
            });

            const minX = Math.min(...unloadCells.map((cell) => cell.x));
            const maxX = Math.max(...unloadCells.map((cell) => cell.x));
            const minZ = Math.min(...unloadCells.map((cell) => cell.z));
            const maxZ = Math.max(...unloadCells.map((cell) => cell.z));

            const basePadWidth =
                (maxX - minX + 1) * gridMetrics.boxWidth +
                (maxX - minX) * gridMetrics.spacingX;
            const basePadDepth =
                (maxZ - minZ + 1) * gridMetrics.boxDepth +
                (maxZ - minZ) * gridMetrics.spacingZ;

            const protrudeDepth = Math.max(0, bay.protrudeSteps || 0) * stepZ;
            const padWidth = basePadWidth;
            const padDepth = basePadDepth + protrudeDepth;

            const centerX =
                gridMetrics.startX + ((minX + maxX) / 2) * stepX -
                gridMetrics.modelCenter.x;
            const baseCenterZ =
                gridMetrics.startZ + ((minZ + maxZ) / 2) * stepZ -
                gridMetrics.modelCenter.z;
            const centerZ = baseCenterZ - protrudeDepth / 2;

            createTrackSegment({
                sizeX: padWidth,
                sizeZ: padDepth,
                position: new THREE.Vector3(centerX, trackY, centerZ),
                gridMetrics,
                trackThickness,
            });
        });
    }

    function createPlayer(modelSize) {
        const playerGeometry = new THREE.CapsuleGeometry(
            modelSize.x * 0.15,
            modelSize.y * 0.2,
            8,
            16,
        );
        const playerMaterial = new THREE.MeshStandardMaterial({
            color: 0x54a6ff,
            roughness: 0.4,
            metalness: 0.2,
            emissive: 0x123456,
            emissiveIntensity: 0.25,
        });

        player = new THREE.Mesh(playerGeometry, playerMaterial);
        player.castShadow = true;
        player.receiveShadow = true;
        player.position.set(0, modelSize.y * 0.5, Math.max(modelSize.z * 2, 3));
        scene.add(player);
    }

    function updatePlayer(delta) {
        if (!player) return;

        const forward = new THREE.Vector3();
        camera.getWorldDirection(forward);
        forward.y = 0;
        forward.normalize();
        const right = new THREE.Vector3()
            .crossVectors(forward, new THREE.Vector3(0, 1, 0))
            .normalize();

        const direction = new THREE.Vector3();
        const vertical = new THREE.Vector3(0, 1, 0);
        if (keyState.has("KeyW") || keyState.has("ArrowUp")) {
            direction.add(forward);
        }
        if (keyState.has("KeyS") || keyState.has("ArrowDown")) {
            direction.sub(forward);
        }
        if (keyState.has("KeyA") || keyState.has("ArrowLeft")) {
            direction.sub(right);
        }
        if (keyState.has("KeyD") || keyState.has("ArrowRight")) {
            direction.add(right);
        }
        if (keyState.has("Space")) {
            direction.add(vertical);
        }
        if (keyState.has("ShiftLeft") || keyState.has("ShiftRight")) {
            direction.sub(vertical);
        }

        if (direction.lengthSq() > 0) {
            const moveDirection = direction.clone().normalize();
            player.position.addScaledVector(moveDirection, moveSpeed.value * delta);

            const horizontalDirection = moveDirection.clone();
            horizontalDirection.y = 0;

            if (horizontalDirection.lengthSq() > 0.0001) {
                const targetQuaternion = new THREE.Quaternion().setFromRotationMatrix(
                    new THREE.Matrix4().lookAt(
                        new THREE.Vector3(0, 0, 0),
                        horizontalDirection,
                        new THREE.Vector3(0, 1, 0),
                    ),
                );
                player.quaternion.slerp(targetQuaternion, 0.2);
            }
        }
    }

    function updateCamera() {
        if (!player) return;

        const rotation = new THREE.Quaternion().setFromEuler(
            new THREE.Euler(pitch, yaw, 0, "YXZ"),
        );
        const rotatedOffset = cameraOffset.clone().applyQuaternion(rotation);

        camera.position.copy(player.position).add(rotatedOffset);
        camera.lookAt(player.position.clone().add(new THREE.Vector3(0, 1, 0)));
    }

    function findParentBox(object) {
        let current = object;

        while (current) {
            if (boxes.includes(current)) {
                return current;
            }
            current = current.parent;
        }

        return null;
    }

    function updateHoverInfo(event) {
        if (!renderer || !camera || !container.value) return;

        const rect = renderer.domElement.getBoundingClientRect();
        if (
            event.clientX < rect.left ||
            event.clientX > rect.right ||
            event.clientY < rect.top ||
            event.clientY > rect.bottom
        ) {
            hoveredBoxInfo.value = null;
            return;
        }

        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(boxes, true);

        if (intersects.length > 0) {
            const box = findParentBox(intersects[0].object);

            if (box && box.userData?.boxId) {
                const containerRect = container.value.getBoundingClientRect();
                hoveredBoxInfo.value = {
                    boxId: box.userData.boxId,
                    productName: box.userData.productName,
                };
                tooltipPosition.value = {
                    x: event.clientX - containerRect.left,
                    y: event.clientY - containerRect.top,
                };
                return;
            }
        }

        hoveredBoxInfo.value = null;
    }

    function registerInputs() {
        handleKeyDown = (event) => {
            const handledKeys = [
                "KeyW",
                "KeyA",
                "KeyS",
                "KeyD",
                "ArrowUp",
                "ArrowDown",
                "ArrowLeft",
                "ArrowRight",
                "Space",
                "ShiftLeft",
                "ShiftRight",
            ];

            if (handledKeys.includes(event.code)) {
                event.preventDefault();
                keyState.add(event.code);
            }
        };

        handleKeyUp = (event) => {
            keyState.delete(event.code);
        };

        handlePointerDown = (event) => {
            isDragging = true;
            previousPointer = { x: event.clientX, y: event.clientY };
        };

        handlePointerMove = (event) => {
            updateHoverInfo(event);
            if (!isDragging) return;
            const deltaX = event.clientX - previousPointer.x;
            const deltaY = event.clientY - previousPointer.y;
            previousPointer = { x: event.clientX, y: event.clientY };

            const sensitivity = 0.005;
            yaw -= deltaX * sensitivity;
            pitch -= deltaY * sensitivity;
            const pitchLimit = Math.PI / 2 - 0.1;
            pitch = Math.max(-pitchLimit, Math.min(pitchLimit, pitch));
        };

        handlePointerUp = () => {
            isDragging = false;
        };

        handleMouseLeave = () => {
            hoveredBoxInfo.value = null;
        };

        window.addEventListener("keydown", handleKeyDown);
        window.addEventListener("keyup", handleKeyUp);
        renderer.domElement.addEventListener("mousedown", handlePointerDown);
        window.addEventListener("mousemove", handlePointerMove);
        window.addEventListener("mouseup", handlePointerUp);
        renderer.domElement.addEventListener("mouseleave", handleMouseLeave);
    }

    registerInputs();

    // 動畫循環
    const animate = () => {
        animationId = requestAnimationFrame(animate);

        const delta = clock.getDelta();
        updatePlayer(delta);
        updateCamera();

        renderer.render(scene, camera);
    };
    animate();

    // 處理窗口大小變化
    handleResize = () => {
        if (!container.value) return;
        camera.aspect =
            container.value.clientWidth / container.value.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(
            container.value.clientWidth,
            container.value.clientHeight,
        );
    };
    window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
    // 取消動畫循環
    if (animationId) {
        cancelAnimationFrame(animationId);
    }

    // 移除事件監聽器
    if (handleResize) {
        window.removeEventListener("resize", handleResize);
    }

    // 清理 Three.js 資源
    if (container.value && renderer && renderer.domElement) {
        container.value.removeChild(renderer.domElement);
    }

    // 清理事件監聽器
    if (handleKeyDown) window.removeEventListener("keydown", handleKeyDown);
    if (handleKeyUp) window.removeEventListener("keyup", handleKeyUp);
    if (handlePointerDown)
        renderer?.domElement?.removeEventListener("mousedown", handlePointerDown);
    if (handlePointerMove) window.removeEventListener("mousemove", handlePointerMove);
    if (handlePointerUp) window.removeEventListener("mouseup", handlePointerUp);
    if (handleMouseLeave)
        renderer?.domElement?.removeEventListener("mouseleave", handleMouseLeave);

    // 清理方塊資源（GLTF 模型）
    boxes.forEach((box) => {
        // 清理 GLTF 模型的所有子對象
        box.traverse((child) => {
            if (child.isMesh) {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach((material) =>
                            material.dispose(),
                        );
                    } else {
                        child.material.dispose();
                    }
                }
            }
        });
        scene.remove(box);
    });
    boxes = [];

    trackPieces.forEach((track) => {
        track.traverse((child) => {
            if (child.isMesh) {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach((material) => material.dispose());
                    } else {
                        child.material.dispose();
                    }
                }
            }
        });
        scene.remove(track);
    });
    trackPieces = [];

    // 清理基礎模型
    if (baseModel) {
        baseModel.traverse((child) => {
            if (child.isMesh) {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach((material) =>
                            material.dispose(),
                        );
                    } else {
                        child.material.dispose();
                    }
                }
            }
        });
    }

    if (renderer) renderer.dispose();
});
</script>

<style scoped>
.three-scene-wrapper {
    width: 100%;
    position: relative;
}

.three-container {
    width: 100%;
    height: 500px;
    border-radius: 8px;
    overflow: hidden;
    cursor: grab;
    touch-action: none; /* 禁用默認觸摸行為 */
    background: radial-gradient(circle at 20% 20%, #1e293b, #0b1224 55%);
    box-shadow: 0 20px 45px rgba(0, 0, 0, 0.35);
}

.three-container:active {
    cursor: grabbing;
}

.controls-hint {
    position: absolute;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    pointer-events: none;
    z-index: 10;
    backdrop-filter: blur(4px);
}

.controls-hint span {
    display: flex;
    align-items: center;
    gap: 4px;
}

.speed-control {
    position: absolute;
    bottom: 10px;
    left: 10px;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    z-index: 10;
    backdrop-filter: blur(4px);
}

.speed-control input[type="range"] {
    width: 120px;
}

.speed-value {
    min-width: 40px;
    display: inline-block;
    text-align: right;
}

.box-tooltip {
    position: absolute;
    padding: 10px 12px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    border-radius: 8px;
    font-size: 12px;
    pointer-events: none;
    transform: translate(12px, -12px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    z-index: 12;
    backdrop-filter: blur(6px);
    min-width: 160px;
}

.tooltip-label {
    font-size: 11px;
    color: #cbd5e1;
    letter-spacing: 0.5px;
}

.tooltip-id {
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 6px;
    color: #a5b4fc;
}

.tooltip-name {
    font-weight: 600;
    color: #f9fafb;
}
</style>
