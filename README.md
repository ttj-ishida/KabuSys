# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ KabuSys のリポジトリ内 README（日本語）。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方（主要なエントリポイントの利用例）、およびディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチ用データプラットフォームを想定した Python ライブラリ群です。  
主に次を提供します：

- J-Quants API を用いた株価・財務・カレンダーの ETL（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と銘柄ごとのニュース・センチメント解析（OpenAI）
- マーケットレジーム判定（ETF の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算、特徴量探索、統計ユーティリティ
- 監査ログ（signal → order → execution のトレースを保持する監査テーブル初期化）
- データ品質チェック、マーケットカレンダー管理 等

設計上のポイント：
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を不用意に参照しない（多くの関数は target_date を明示的に受け取る）
- DuckDB をデータストアとして利用（ETL / 解析は DuckDB 接続を受け取る）
- OpenAI／J-Quants 等はリトライやバックオフなど安全側の実装あり
- 自動的な .env 読み込み（プロジェクトルートを検出して `.env` → `.env.local` を適用。無効化可能）

---

## 機能一覧（抜粋）

- data
  - jquants_client: J-Quants API からのデータ取得（株価・財務・カレンダー等）と DuckDB への保存（冪等）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl, run_prices_etl 等）と ETL 結果クラス（ETLResult）
  - news_collector: RSS フィードからのニュース取得・前処理・raw_news へ保存
  - quality: データ品質チェック（欠損／重複／スパイク／日付整合性）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - audit: 監査ログテーブルの初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 記事を集約して OpenAI で銘柄別センチメントを算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime に書き込む
- research
  - factor_research: calc_momentum, calc_value, calc_volatility などファクター計算
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理
  - config.Settings: 環境変数からの設定取得（自動 .env ロード機能）

---

## 前提・必須事項

- Python 3.9+
- 必要なパッケージ（例）:
  - duckdb
  - openai (OpenAI の Python SDK)
  - defusedxml
- 外部サービスの認証情報（環境変数または .env）
  - JQUANTS_REFRESH_TOKEN（必須：J-Quants リフレッシュトークン）
  - OPENAI_API_KEY（OpenAI を用いる場合）
  - KABU_API_PASSWORD（kabu ステーション等の発注 API を使う場合）
  - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID（通知／監視用）
- DuckDB ファイル保存先のパス（デフォルト: `data/kabusys.duckdb`）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)
   ```

3. 依存ライブラリをインストール（プロジェクトに requirements.txt があればそれを使用）
   ```
   pip install duckdb openai defusedxml
   # または開発用に:
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルート（`.git` か `pyproject.toml` のある階層）に `.env` を置くと自動読み込みされます（デフォルトで `.env` → `.env.local`）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベースファイルの格納ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要なサンプル）

ここではライブラリを直接インポートして主要な処理を実行する例を示します。多くの関数は DuckDB の接続オブジェクト（duckdb.connect）を引数に取ります。

- 基本的な接続と設定読み込み
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（株価 / 財務 / カレンダーの差分取得と品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI でセンチメントを算出し ai_scores に書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import os

  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム（bull/neutral/bear）のスコアリング
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import os

  score_regime(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
  ```

- 監査ログ用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # 監査専用 DB を初期化（ファイル db）
  audit_conn = init_audit_db(settings.duckdb_path)
  ```

- 研究用ファクター計算の例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

注意点：
- OpenAI・J-Quants など外部 API を呼び出す処理ではリトライ／フェイルセーフの実装がありますが、API キーやネットワークが正しく設定されている必要があります。
- 多くの処理は target_date を明示的に渡す設計で、バックテスト等でもルックアヘッドバイアスを避けられるようになっています。

---

## 主要な設定（環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールの一覧（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (README に含まれているがコードベースでの詳細は省略)
  - execution/ (発注に関わるモジュール群: README はここで設定を期待)

各モジュールの役割は上に記載した「機能一覧」やコード内の docstring に詳述しています。

---

## 運用上の注意・ベストプラクティス

- ETL やニュース収集は非同期またはバッチでの定期実行（cron / Airflow / ジョブスケジューラ）を想定しています。
- OpenAI 呼び出しはコストとレイテンシの観点からバッチ化されるよう設計されています（news_nlp は銘柄をチャンクで処理）。
- J-Quants のレート制限を尊重するために固定間隔スロットリングと指数バックオフを実装しています。ID トークンの自動リフレッシュも組み込まれています。
- 監査ログは削除せず永続化する前提です。order_request_id を冪等キーとして利用してください。
- テスト時には自動 .env ロードを無効化するか、必要な環境変数だけを注入してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 貢献 / 拡張

- 新しいニュースソースの追加：`data/news_collector.py` の DEFAULT_RSS_SOURCES を拡張し、必要に応じてパーサを追加
- 追加の品質チェック：`data/quality.py` に関数を追加して `run_all_checks` に組み込む
- 発注エンジン／ブローカー統合：`execution` / `monitoring` 層に実装して監査ログ（audit）と連携

---

この README はコードベースの概要をまとめたものです。詳細な API の動作やスキーマ、外部サービスとの連携仕様は各モジュールの docstring とコードコメントを参照してください。必要であれば、各モジュールの呼び出し例や運用手順（cron 定義、Airflow DAG 例、Slack 通知設定等）を追加で作成します。必要な項目があれば教えてください。