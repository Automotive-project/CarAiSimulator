﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Threading;

[RequireComponent(typeof(Terrain))]
[ExecuteInEditMode]
public class TerrainGenerator : MonoBehaviour
{

	public bool generateOnStart = false;
	public DetailLayer[] detailLayers;
	public Transform water;
	public ReflectionProbe reflection;

	Terrain terrain;
	Thread thread;
	float[,] tempHeights;
	float waterHeight;

	private void Awake()
	{
		terrain = GetComponent<Terrain>();
	}

	void Start()
	{
		if (generateOnStart)
			Generate();
	}

	[ContextMenu("Generate")]
	public void Generate()
	{
		tempHeights = null;
		int size = terrain.terrainData.heightmapResolution;
		float[,] heights = terrain.terrainData.GetHeights(0, 0, size, size);
		float mapHeight = terrain.terrainData.heightmapScale.y;
		float mapWidth = terrain.terrainData.heightmapWidth;
		for (int h = 0; h < detailLayers.Length; h++)
		{
			detailLayers[h].x = Random.Range(-1000f, 1000f);
			detailLayers[h].y = Random.Range(-1000f, 1000f);
		}
		thread = new Thread(() => {
			float sumHeight = 0f;
			for (int i = 0; i < size; i++)
			{
				for (int j = 0; j < size; j++)
				{
					float px = (float)i / size * 2f - 1f;
					float py = (float)j / size * 2f - 1f;
					float height = Mathf.Sqrt(px * px + py * py)-0.3f;
					px = px * (float)mapWidth / 1000;
					py = py * (float)mapWidth / 1000;
					height = height*height * 0.6f + 0.4f;
					for (int h = 0; h < detailLayers.Length; h++)
					{
						float detail = Mathf.PerlinNoise(
							detailLayers[h].x + px * detailLayers[h].scale,
							detailLayers[h].y + py * detailLayers[h].scale
							) * 2 - 1;
						if(detailLayers[h].detail)
							height += Mathf.Clamp(detail * detail * detail, -0.75f, 0.75f) * detailLayers[h].height;
						else
							height += detail * detailLayers[h].height;
					}
					heights[i, j] = height;
					sumHeight += height;
				}
			}
			waterHeight = sumHeight / (1.8f * size * size) * mapHeight;
			tempHeights = heights;
		});
		thread.Start();
		StartCoroutine(WaitForResult());
	}

	IEnumerator WaitForResult()
	{
		while (tempHeights == null)
			yield return null;
		terrain.terrainData.SetHeights(0, 0, tempHeights);
		terrain.Flush();
		water.position = new Vector3(water.position.x, waterHeight, water.position.z);
		tempHeights = null;
		thread = null;
		yield return null;
		reflection.RenderProbe();
	}

	private void OnDestroy()
	{
		if (thread != null)
			thread.Abort();
	}

	[System.Serializable]
	public struct DetailLayer
	{
		[Range(0f, 40f)]
		public float scale;
		[Range(0f, 0.5f)]
		public float height;
		public bool detail;
		[System.NonSerialized]
		public float x;
		[System.NonSerialized]
		public float y;
	}
}