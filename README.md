# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ取得・品質管理・研究用ツール群と、AI（LLM）を用いたニュースセンチメント評価、さらに自動売買に必要な監査・発注周りの補助機能を一体で提供する Python パッケージです。主な用途は次のとおりです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- DuckDB への冪等保存と品質チェック
- RSS ニュース収集と前処理
- OpenAI を用いたニュースセンチメント（銘柄ごと・マクロ）評価
- ETF とマクロセンチメントを統合した市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析支援
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ

設計上、バックテスト時のルックアヘッドバイアスを避けるために「日付の取り扱い」や「ETL の差分/バックフィル」等に配慮しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - pipeline: 日次 ETL 実行（prices / financials / calendar）、ETL 結果クラス
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS → raw_news 収集（SSRF 対策・正規化）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: zscore 正規化など汎用統計ユーティリティ
- ai/
  - news_nlp: 銘柄ごとのニュースセンチメント（gpt-4o-mini / JSON mode）
  - regime_detector: ETF（1321）の MA とマクロニュース LLM を合成した市場レジーム判定
- research/
  - factor_research: Momentum / Volatility / Value のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）、統計サマリー等
- config: 環境変数読み込み・設定管理（.env 自動ロード機能あり）
- audit・監視・実行補助モジュール群

---

## 必要条件（依存関係）

主に以下を使用しています（必須バージョンはプロジェクト側で管理してください）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ

インストール方法の例は次節を参照してください。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. パッケージをインストール
   - 開発中であればプロジェクトルートで editable install:
     ```bash
     pip install -e .
     ```
   - あるいは必要パッケージを直接インストール:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動でロードされます（config モジュールが .git または pyproject.toml を基にルートを探します）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

   代表的な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の引数で指定可能）
   - KABU_API_PASSWORD — kabu ステーション API のパスワード
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視関連
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
   - KABUSYS_ENV — environment: development / paper_trading / live
   - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の例（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なサンプル）

以下は Python REPL またはスクリプトからの利用例です。事前に DuckDB のスキーマ（必要なテーブル）を準備しておくことを想定します。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄単位）を生成して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定済みなら省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 + マクロニュース LLM）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これにより signal_events / order_requests / executions テーブルが作成されます
  ```

- J-Quants の id_token を直接取得する（ユーティリティ）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照
  print(token)
  ```

注意:
- OpenAI 呼び出しはコストとレート制限があるため、テスト時はモック（unittest.mock）して差し替えることを推奨します。モジュール内で _call_openai_api をパッチ可能に実装しています（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB の一部 executemany は空リストを受け付けない制約に対するガードがコード内にあります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - pipeline.py
    - jquants_client.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - ai/__init__.py
  - etc.

説明（抜粋）:
- data/jquants_client.py: J-Quants API 呼び出し・保存ロジック（レート制御、リトライ、トークン管理）
- data/pipeline.py: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- data/news_collector.py: RSS 取得・前処理・raw_news への冪等保存
- ai/news_nlp.py: 銘柄単位のニュースセンチメント取得（OpenAI）
- ai/regime_detector.py: ETF マクロ合成による市場レジーム判定
- research/*: ファクター計算・IC など研究支援

---

## 実運用上の注意点

- 環境変数管理: .env に API キーやパスワードを保存する場合は権限管理に注意してください。`.env.local` は優先度が高くローカル上書きに使えます。
- OpenAI の利用: レスポンスの整形・JSON パースに失敗するケースをコード側でフォールバック（0.0）していますが、コスト管理と正確性を考慮してください。
- J-Quants API: レート制限（120 req/min）を遵守する設計になっています。大量取得時は pipeline のページネーションや間引きを考慮してください。
- DuckDB スキーマ: ETL や audit 初期化前に適切なスキーマが必要です（audit.init_audit_db が監査スキーマを作成します）。その他テーブル（raw_prices, raw_news, ai_scores 等）は ETL / collector 側で期待されるスキーマに合わせて用意してください。
- テスト: LLM 呼び出し・ネットワーク呼び出しは外部依存なので unittest.mock による差し替えでテスト可能です。コード内に差し替えポイント（プライベート関数）を用意しています。

---

## 開発・貢献

- コーディング規約・テスト・ドキュメントはプロジェクトルートの規約に従ってください。
- 安全性上の懸念（SSRF / XML インジェクション / 大量データ取扱）を考慮して実装していますが、外部入力（RSS 等）の扱いは運用で更に監査してください。

---

必要であれば、README にサンプル .env.example、DuckDB スキーマ（DDL）、またはよく使う CLI スクリプト例（cron 用 ETL 実行や監視サービス起動コマンド）を追加で作成します。どの内容を追加しますか？