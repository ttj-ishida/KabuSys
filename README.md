# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（約定トレーサビリティ）、研究用ファクター計算などを提供します。

主な用途：
- 日次 ETL（株価・財務・市場カレンダー）の自動取得・保存・品質チェック
- ニュース記事のセンチメント評価と銘柄別 AI スコア生成
- 市場レジーム（bull/neutral/bear）判定（MA200 とマクロニュースの組合せ）
- 監査ログ用スキーマの初期化・利用（発注 → 約定のトレーサビリティ）
- 研究用ファクター／統計ユーティリティ（モメンタム・ボラティリティ・バリュー等）

---

## 機能一覧

- 設定管理
  - 環境変数 / .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須/オプション設定のラッパー（kabusys.config.settings）

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価日足、財務、上場情報、マーケットカレンダーを差分取得
  - DuckDB へ冪等保存（ON CONFLICT による上書き）
  - レートリミット制御・リトライ・トークン自動リフレッシュ対応

- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のセンチメント得点化（batch, JSON mode, リトライ）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）で日次判定
  - DuckDB へ冪等書き込み

- 研究ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - forward returns, IC, 統計サマリー、zscore 正規化

- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出、QualityIssue の返却

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DuckDB 初期化関数を提供

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表記などを使用）
- ネットワークアクセス（J-Quants, OpenAI 等）

1. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※実プロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数例（.env）:
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - CPU_THRESHOLD_PCT=90.0
   - MEMORY_THRESHOLD_PCT=85.0
   - DISK_THRESHOLD_PCT=90.0
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

4. プロジェクトのインストール（任意）
   - pip install -e .  （パッケージ化している場合）

---

## 使い方（簡易サンプル）

以下は Python REPL やスクリプトから直接呼ぶ例です。

- 設定の参照
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続作成（設定に従う）
  ```py
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（run_daily_etl）
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（score_news）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジームのスコアリング（score_regime）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```py
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意事項
- OpenAI / J-Quants などの外部 API キーが必要です。API 呼び出しはネットワークや料金が発生する点に注意してください。
- ETL・ニュース処理は Look-ahead バイアス対策のため、内部で date 引数や window を明示的に扱います。実行時に target_date を明示する運用が推奨されます。

---

## 環境変数・自動 .env ロード

- 自動ロード順序: OS 環境変数 > .env.local > .env
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須環境変数は Settings のプロパティ参照時に ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                              — 環境設定ロード/Settings
- ai/
  - __init__.py
  - news_nlp.py                           — ニュース NLU（score_news）
  - regime_detector.py                    — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py                — 市場カレンダー管理
  - etl.py / pipeline.py                  — ETL パイプライン / run_daily_etl 等
  - jquants_client.py                     — J-Quants API クライアント（fetch/save）
  - news_collector.py                     — RSS 収集 / 前処理
  - quality.py                            — データ品質チェック
  - stats.py                              — 統計ユーティリティ（zscore_normalize）
  - audit.py                              — 監査ログスキーマ初期化
  - etl.py (export)                       — ETLResult の公開
- research/
  - __init__.py
  - factor_research.py                    — Momentum / Value / Volatility
  - feature_exploration.py                — forward returns / IC / summary

その他
- 各モジュールは duckdb.DuckDBPyConnection を入力とする関数を公開し、DB への書き込みは冪等性（DELETE/INSERT または ON CONFLICT）を重視しています。

---

## 運用上の注意点

- DuckDB ファイルパスは Settings.duckdb_path（デフォルト data/kabusys.duckdb）で管理。複数プロセスからの同時書き込みには注意。
- J-Quants API はレート制限を守る必要があります（内部で制御あり）。
- OpenAI 呼び出しは課金が発生します。モデルは gpt-4o-mini を想定。
- テスト時は各種内部 API 呼び出しをモックして実行する設計になっています（_call_openai_api, _urlopen などを差し替え可能）。

---

必要に応じて README を拡張して、運用手順（cron / systemd の例）、監視設定、CI/CD、テストの実行方法、依存パッケージ一覧を追加できます。必要であれば追記します。