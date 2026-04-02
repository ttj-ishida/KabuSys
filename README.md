# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査ログ（注文・約定トレーサビリティ）など、取引システムと研究環境に必要な処理をモジュール単位で提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境変数ベースの設定管理（.env 自動読み込み機能付き）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得
  - レート制御・リトライ・トークンリフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア生成）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを統合）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化 等）
- 監査ログスキーマの初期化・監査用 DB 操作（signal / order_request / execution）
- DuckDB をデータ格納に利用（軽量かつ SQL ベース）

---

## 動作環境・依存関係（推奨）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- （実行環境に応じて）SQLite（監視用 DB）や kabuステーション 等の外部サービス設定

プロジェクトを使う際は、requirements.txt または poetry/poetry.lock 等で依存を管理してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存ライブラリをインストール（例）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. .env を用意する

   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最小の例（.env.example）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知等)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # OpenAI (ニュースNLP / レジーム判定)
   OPENAI_API_KEY=sk-...

   # DB / ファイルパス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development / paper_trading / live
   LOG_LEVEL=INFO
   ```

4. DuckDB 用のディレクトリ作成（必要に応じて）

   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトやインタラクティブでの利用例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（market calendar / prices / financials / 品質チェック）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとのスコアを ai_scores テーブルへ書き込む）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は env または api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（1321 MA200 とマクロニュースを統合）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る場合）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注: AI 関連機能（news_nlp, regime_detector）は OpenAI の API キー（OPENAI_API_KEY）を必要とします。関数呼び出し時に引数でキーを渡すことも可能です（テストや鍵の分離に便利）。

---

## 主要な API / エントリポイント

- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.jquants_client.fetch_* / save_*（低レイヤー）
- 品質チェック
  - kabusys.data.quality.run_all_checks(...)
- ニュース収集
  - kabusys.data.news_collector.fetch_rss(...)
- ニュース NLP / レジーム判定
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
- 研究用ユーティリティ
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.feature_exploration.calc_forward_returns, calc_ic, factor_summary
  - kabusys.data.stats.zscore_normalize(...)
- 監査ログ
  - kabusys.data.audit.init_audit_db(...)
  - kabusys.data.audit.init_audit_schema(...)

---

## 設定（環境変数）

主要な環境変数一覧（settings クラスにより参照されます）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector などで使用）

自動で .env / .env.local をプロジェクトルートから読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発時のヒント

- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。テスト時に環境を固定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってください。
- OpenAI 呼び出しや外部 API 呼び出しは各モジュールでリトライ処理・フェイルセーフを実装していますが、テスト時はネットワークをモックすることを推奨します。各モジュールは内部の _call_openai_api 等を patch して差し替え可能です。
- DuckDB の executemany は空リストを受け付けないバージョンもあるため、モジュール側でチェック済みです。ETL 呼び出し前に接続とスキーマを準備してください。

---

## ディレクトリ構成

説明は src/kabusys 以下を基準にしています。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定を提供（Settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py  — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL の公開インターフェース（ETLResult エクスポート）
    - calendar_management.py — JPX カレンダー管理 / 営業日判定
    - news_collector.py   — RSS ニュース収集・前処理
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize 等）
    - audit.py            — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー等
  - monitoring, strategy, execution, etc.（パッケージ公開名は __all__ に含まれますが、本コードベースに含まれる主要モジュールは上記）

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス防止: AI モジュールや ETL は内部で datetime.today()/date.today() を不用意に参照せず、呼び出し側が target_date を明示する設計です。
- 冪等性: J-Quants のデータ保存、監査ログ初期化などは冪等操作を意識して実装しています（ON CONFLICT / INSERT ... DO UPDATE 等）。
- フェイルセーフ: 外部 API の失敗時はサービス全体を停止させずにフォールバック（例: マクロスコアが得られない場合は 0.0）する実装が多く含まれます。
- セキュリティ: news_collector では SSRF 防止、XML インジェクション対策（defusedxml）などの安全対策を実装しています。

---

必要であれば README にサンプル .env.example を追加したり、CI 用のテスト実行手順（ユニットテストのモック方法など）を追記します。どの項目を詳しくしたいか教えてください。