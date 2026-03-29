# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株のデータ基盤・リサーチ・AI（ニュースNLP）・監査ログ・ETL・研究用ユーティリティを含むライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からの市場データ ETL（株価・財務・市場カレンダー）
- RSS ベースのニュース収集と記事の前処理
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄単位、マクロ判定）
- ファクター計算・特徴量探索・IC 計算（リサーチ向け）
- 監査ログ（シグナル → 発注 → 約定トレース）用スキーマ初期化
- データ品質チェック、カレンダー管理、各種ユーティリティ

特徴
---
主な機能一覧（抜粋）:

- data
  - jquants_client: J-Quants REST API 用クライアント（認証・レート制御・ページネーション・保存関数）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・ID 生成（SSRF 防止・サイズ制限・トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日判定・更新ジョブ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ用テーブル定義・初期化（冪等、UTC タイムスタンプ）
  - stats: 汎用統計ユーティリティ（Z-score 正規化 等）
- ai
  - news_nlp.score_news: ニュース記事を銘柄別にまとめて LLM（JSON Mode）でスコア化し ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロ記事の LLM センチメントを合成して市場レジーム判定を書く
- research
  - factor_research: momentum/volatility/value ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク変換

要求・依存
---
- Python 3.10+
- 主要依存（参考、requirements.txt をプロジェクトに用意してください）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他: typing 標準ライブラリ、urllib、json 等

セットアップ手順
---
1. リポジトリをクローン（またはパッケージを取得）:
   git clone ...

2. 仮想環境作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（プロジェクトに requirements.txt を用意している想定）:
   pip install -r requirements.txt

   目安の requirements（参考）
   - duckdb
   - openai
   - defusedxml

4. 環境変数設定 (.env)
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主な環境変数（必須 / 任意）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル
- DUCKDB_PATH (任意) — データベースファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/...（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime に渡すことも可）

例 .env（抜粋）
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

使い方（簡易クイックスタート）
---

以下は Python スクリプト内での呼び出し例です。DuckDB 接続は duckdb.connect(...) を使用します。

1) ETL（日次パイプライン）を実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース記事のスコア化（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数で設定されている場合は api_key を省略できます
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {n_written} ai_scores")
```

3) 市場レジーム判定（AI + MA200）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) RSS 取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

5) 監査ログ（audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

運用上の注意
---
- OpenAI 呼び出しはリトライやフォールバック（失敗時は 0.0）などの安全策が組まれていますが、API 利用はコストとレート制限に注意してください。
- J-Quants API はレート制限を守るため内部に RateLimiter を実装していますが、ID トークンの管理・更新・キャッシュ動作に注意してください。
- ETL / AI モジュールは「ルックアヘッドバイアス」を避ける設計になっており、target_date 引数を明示的に渡すことを想定しています。backtest では target_date を適切に操作してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
---
主要ファイル/フォルダ（src/kabusys 配下）:

- __init__.py
- config.py                             — 環境変数/設定読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py                          — ニュース NLP（score_news 等）
  - regime_detector.py                   — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                    — J-Quants API クライアント（fetch/save）
  - pipeline.py                          — ETL パイプライン（run_daily_etl 等）
  - etl.py                               — ETLResult の再エクスポート
  - news_collector.py                    — RSS 収集・前処理
  - calendar_management.py               — 市場カレンダー管理・更新ジョブ
  - quality.py                           — データ品質チェック
  - stats.py                             — 統計ユーティリティ（zscore_normalize）
  - audit.py                             — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                   — Momentum / Volatility / Value 計算
  - feature_exploration.py               — 将来リターン / IC / 統計サマリー

追加情報
---
- .env のパースロジックは config._parse_env_line に実装され、export KEY=val やクォート内エスケープ、インラインコメントなどに対応します。
- OpenAI 呼び出し部分は OpenAI Python SDK に依存します。テストのために _call_openai_api をモックする設計になっています。
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE / DO NOTHING）を想定しており、ETL は部分失敗しても既存データを過度に消さない実装です。

ライセンスや貢献方法などはリポジトリのトップに合わせて追記してください。

以上が本プロジェクトの README（日本語）です。追加で CI、デプロイ、サンプルワークフロー（cron / Airflow）、requirements.txt の雛形などが必要であれば作成します。