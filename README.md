# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログなどの主要機能を提供します。

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易例）
- 環境変数（設定項目）
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要
KabuSys は、日本株向けのデータプラットフォームと研究／自動売買運用で必要となる機能群をモジュール化した Python パッケージです。  
主に以下を提供します。
- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB を使ったローカルデータ永続化とクエリ処理
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）および OpenAI を用いたセンチメント／AI スコアリング
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z-score 正規化 等）

設計思想として「ルックアヘッドバイアス回避」「冪等性（idempotency）」「外部 API に対する堅牢なリトライ／レート制御」「DuckDB による効率的な集計」を重視しています。

---

## 主な機能一覧
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 抽出・前処理・保存）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログ初期化・DB 管理（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize など）
- ai
  - ニュース NLP（score_news：銘柄ごとのニュースセンチメントを ai_scores に書き込み）
  - 市場レジーム判定（score_regime：ETF 200 日 MA とマクロニュースを合成）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量解析（forward returns / IC / summary / rank）
- config
  - 環境変数および .env 自動読み込み（プロジェクトルート検出、.env/.env.local 読込）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法 `X | None` を使用しているため）
- Git（推奨）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 最低依存（例）:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. プロジェクトのパスを PYTHONPATH に含めるか、パッケージを editable インストール
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに .env を作成して以下の必須設定を行う（下記「環境変数」参照）。
   - 自動読み込み:
     - パッケージは起動時に .git または pyproject.toml を基準としてプロジェクトルートを探索し、`.env` → `.env.local` の順で読み込みます。
     - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡易サンプル）

以下は Python REPL やスクリプトからの使い方例です。実行前に必要な環境変数（J-Quants / OpenAI など）を設定してください。

- DuckDB 接続を作って日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付け（OpenAI API キーが設定されていること）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- LLM を利用する機能（news_nlp, regime_detector）は OpenAI の API キーが必要です。引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants へアクセスする ETL は `JQUANTS_REFRESH_TOKEN` を必要とします（config.Settings から参照）。

---

## 環境変数（主な設定項目）

以下はコードで参照される主要な環境変数です。`.env.example` 相当のファイルを作成して管理してください。

必須（実行する機能に応じて必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先のチャンネル ID
- KABU_API_PASSWORD: kabuステーション API パスワード（実行系がある場合）

OpenAI 関連
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）

DB パス（任意：デフォルトが設定される）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

システム設定
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO

自動 .env 読込制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化します。

.config モジュールの動作:
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し `.env`（上書き不可）→ `.env.local`（上書き）を読み込みます。OS 環境変数は `.env` で上書きされません（保護）。

---

## ディレクトリ構成（主要ファイル説明）

概要: src/kabusys 以下にモジュールが分割されています。

- src/kabusys/__init__.py
  - パッケージのエントリ。バージョンと公開サブモジュールを定義。

- src/kabusys/config.py
  - 環境変数管理、.env の自動読み込み、Settings クラス（アプリ設定）を提供。

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（fetch / save / 認証 / rate limiter）
  - pipeline.py: ETL パイプラインの実装（run_daily_etl 等）、ETLResult 定義
  - etl.py: ETL 関連の再エクスポート
  - news_collector.py: RSS 取得と前処理、raw_news 保存ロジック
  - calendar_management.py: 市場カレンダー管理（is_trading_day / next_trading_day 等）
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit.py: 監査ログ（signal / order_requests / executions）の DDL と初期化
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）

- src/kabusys/ai/
  - news_nlp.py: ニュースを LLM に送って銘柄毎にスコア化し ai_scores に書き込む
  - regime_detector.py: ETF MA とマクロニュース LLM 評価を組み合わせて市場レジーム判定
  - __init__.py: 公開関数のエクスポート（score_news など）

- src/kabusys/research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー、ランク変換等
  - __init__.py: 公開 API のエクスポート

備考:
- 各モジュールは「ルックアヘッドバイアス防止」「冪等性」「DuckDB を想定した SQL」などの設計方針に従って実装されています。
- OpenAI 呼び出し部分は retry（指数バックオフ）や JSON バリデーション、レスポンスのフォールバックを行う実装になっています。
- jquants_client は rate limiting（120 req/min）・トークン自動リフレッシュ・ページネーション対応を備えています。

---

## 開発上の注意・運用上のヒント
- DuckDB ファイルは定期バックアップを推奨します（ETL データは重要）。
- OpenAI や J-Quants の API 呼び出しにはコストとレート制限があるため、本番稼働前に十分なテストを行ってください。
- news_nlp / regime_detector を使う際は API レスポンスの変化やモデル差（フォーマット違い）を想定してログ監視を行ってください。
- audit（監査）スキーマは冪等に初期化可能です。運用開始時に必ず初期化してください。

---

必要であれば、README にサンプル .env.example 内容、より詳細な API 使用例、テーブルスキーマ（DDL）の抜粋、運用フロー（夜間 ETL cron 例）などを追記できます。どの情報を優先して追加しますか？