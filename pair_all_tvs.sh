#!/bin/bash
echo "🚀 Starting concurrent pairing for all 15 Samsung TVs..."
echo "This will attempt to pair with all TVs simultaneously using threads!"
echo ""

curl -X POST http://127.0.0.1:8002/api/v1/tv/pair \
  -H "Content-Type: application/json" \
  -d '{
    "tv_ids": [
      "b4_tv", "m2_tv", "b3_tv", "m4_tv", "t1_tv",
      "t4_tv", "m3_tv", "t3_tv", "m1_tv", "t2_tv",
      "b1_tv", "t5_tv", "b2_tv", "m5_tv", "b5_tv"
    ]
  }' --silent | python -m json.tool

echo ""
echo "✅ Concurrent pairing command completed!"
echo "📺 Check your TV screens for pairing prompts (they may appear simultaneously)"