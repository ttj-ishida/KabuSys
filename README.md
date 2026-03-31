# KabuSys

日本株の自動売買／データプラットフォーム用ライブラリ（モジュール群）。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（LLM）によるセンチメント評価、ファクター算出、監査ログ（取引トレーサビリティ）などを提供します。

本リポジトリはバックテスト・リサーチ・本番実行で使える共通ユーティリティ群を備え、以下の設計方針を重視しています:
- ルックアヘッドバイアスの排除（内部で date.today()/datetime.today() に依存しない）
- ETL・保存処理の冪等性（ON CONFLICT / 個別 DELETE → INSERT 等）
- 外部 API 呼び出しに対する堅牢なリトライとレート制御
- DuckDB を中心としたローカル DB 管理
- OpenAI（LLM）や J-Quants API を利用したスコアリング機能

---

## 主な機能（機能一覧）

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（jquants_client, pipeline）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理（quality）
  - 欠損、重複、スパイク（急騰・急落）、日付不整合の検出
- カレンダー管理（calendar_management）
  - 営業日判定・前後営業日の取得・期間内営業日列挙等
  - 夜間バッチでのカレンダー更新（calendar_update_job）
- ニュース収集（news_collector）
  - RSS 取得、前処理、記事ID生成、SSRF 対策、保存向けユーティリティ
- LLM を用いたニュース NLP（ai.news_nlp）
  - 銘柄別記事を集約して gpt-4o-mini でセンチメントを算出（score_news）
- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離と LLM マクロセンチメントを合成して日次レジーム判定（score_regime）
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査用テーブル定義と初期化（init_audit_schema / init_audit_db）
- 汎用統計（data.stats）
  - Zスコア正規化など

---

## 前提条件

- Python 3.9+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI API など）

実際のインストール要件はプロジェクトの packaging（pyproject.toml / requirements.txt）に合わせてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements があれば
   # pip install -r requirements.txt
   # 開発中はローカルインストール:
   # pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY
   - オプション:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development|paper_trading|live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=pa$$w0rd
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（例）

以下は Python REPL / スクリプトから呼び出す代表的な例です。

- DuckDB 接続を作成して ETL を実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 監査ログ DB を初期化（監査テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # :memory: も可
  ```

- ニュース NLP（OpenAI を利用して銘柄別スコア計算）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（MA200 + マクロセンチメント）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- RSS フィード取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode（response_format={"type":"json_object"}）を利用する設計です。テスト時は内部の _call_openai_api をモック可能です。
- run_daily_etl 等は内部で日付調整やカレンダーを参照します。バックテスト用途では Look-ahead を防ぐため利用方法に注意してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for LLM features) — OpenAI API キー
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN、SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID ファイルパス
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment: development / paper_trading / live
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

---

## 運用時の注意

- J-Quants API のレート制限（120 req/min）は jquants_client 内の RateLimiter により制御されますが、外部で多数の並列プロセスを動かすと制限を超える可能性があるため注意してください。
- OpenAI 呼び出しにはリトライ・バックオフが組み込まれていますが、API の課金やレート制限に留意してください。
- ETL は各ステップで例外を捕捉して継続する設計です。結果の ETLResult.has_errors / has_quality_errors を確認してアラートや手動対応を行ってください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                            — 記事センチメント算出 (score_news)
    - regime_detector.py                     — 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py                      — J-Quants API クライアント & 保存ロジック
    - pipeline.py                            — ETL パイプライン（run_daily_etl 等）
    - etl.py                                 — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py                       — RSS 収集・前処理ユーティリティ
    - calendar_management.py                 — 市場カレンダー管理（is_trading_day 等）
    - quality.py                             — データ品質チェック
    - stats.py                               — 統計ユーティリティ（zscore_normalize）
    - audit.py                               — 監査ログ（監査テーブル定義 / init）
  - research/
    - __init__.py
    - factor_research.py                     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py                 — 将来リターン / IC / 統計サマリ
  - research/（その他）...

（上記は主要なファイルと概要で、実際のツリーはリポジトリ内の完全な構成を参照してください）

---

## テスト・モックポイント

- LLM 呼び出しは ai.news_nlp._call_openai_api / ai.regime_detector._call_openai_api を unittest.mock.patch で差し替え可能です（テスト時に実 API 呼び出しを避けるため）。
- news_collector 内の _urlopen はネットワーク I/O をモックするのに使いやすく設計されています。

---

## ライセンス / コントリビューション

- 本 README はコードベースの説明を目的としたもので、実際のライセンス情報や貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、具体的なコマンド一覧（systemd サービスや cron ジョブ、監視設定、Slack 通知フローなど）や、より詳細な API 使用例（SQL スキーマ、テーブル定義一覧、ETL のデバッグ手順等）も作成します。どの情報がさらに必要か教えてください。