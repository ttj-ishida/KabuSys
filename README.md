# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データの ETL、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（オーダー／約定トレーサビリティ）など、トレーディングシステムの基盤となる機能群を提供します。

主な設計方針
- ルックアヘッドバイアス（backtesting における未来情報参照）を避ける実装
- DuckDB を用いたローカルデータベース中心の処理
- 外部 API 呼び出し（J-Quants / OpenAI 等）にはリトライ・レート制御等の堅牢性を組み込み
- 冪等性を考慮した DB 保存・ETL 実装

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場銘柄、マーケットカレンダー）
  - 差分取得・バックフィル・保存（冪等）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック
- カレンダー管理
  - market_calendar テーブルの更新、営業日判定、next/prev/trading days
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、SSRF 対策、サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄別ニュースのセンチメントスコアリング（gpt-4o-mini、JSON Mode）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM の合成）
- リサーチ用ファクター計算
  - Momentum / Volatility / Value 等のファクター算出、将来リターン、IC 等
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによるトレーサビリティ
  - DDL / インデックス初期化ユーティリティ
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルートの検出、.env.local の優先度）

---

## 動作要件（推奨）

- Python 3.10 以上（注: 型ヒントに | 演算子を使用）
- 各種ランタイム依存ライブラリ（インストール手順参照）
- ネットワーク接続（J-Quants / OpenAI / RSS）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに setup.py や pyproject.toml がある想定で記載していますが、最低限以下を入れてください）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは additional dependencies（例えば Slack SDK 等）が必要になる場合があります。requirements.txt があればそれを使用してください。

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を作成します。`.env.local` は `.env` を上書きします。

   例（.env.example）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabu ステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作モード / ログ
   KABUSYS_ENV=development      # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   - 自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化）。
   - 必須項目は Settings クラス経由で参照され、未設定時はエラーが発生します（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。

5. データベース初期化（監査ログ用の例）
   監査ログ用の DuckDB を初期化する簡単な例:
   ```python
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings
   from pathlib import Path

   audit_db_path = Path("data/audit.duckdb")
   conn = init_audit_db(audit_db_path)
   # 接続 conn を使って監査テーブルが作成済み
   conn.close()
   ```

   メインのデータ用 DuckDB（prices / financials / raw_news 等）は、ETL 実行時にテーブル作成ユーティリティを呼ぶ設計になっていることが多いです（プロジェクトのスキーマ初期化関数が別途あればそちらを実行してください）。

---

## 使い方（サンプル）

以下に代表的なユースケースのコードスニペットを示します。実行前に .env を用意し、必要なトークンを設定してください。

- ETL（日次パイプライン）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース NLP スコア（特定日分）を取得して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  conn.close()
  ```
  - 引数 api_key を渡さない場合は環境変数 OPENAI_API_KEY を利用します。

- 市場レジーム（ma200 と マクロニュース LLM による合成）を判定する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- 監査ログ（audit schema）を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を用いて監査ログの INSERT 等を行う
  conn.close()
  ```

- 設定取得（コード内での使用例）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_paper)
  ```

---

## 主なモジュール・ディレクトリ構成

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの銘柄別センチメント算出（OpenAI）
    - regime_detector.py
      - ma200 とマクロニュースの LLM を合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 / rate limiter / retry）
    - pipeline.py
      - run_daily_etl、個別 ETL ジョブ、ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存（SSRF 対策等）
    - quality.py
      - データ品質チェック群（欠損・重複・スパイク・日付不整合）
    - calendar_management.py
      - market_calendar の管理と営業日ロジック
    - audit.py
      - 監査ログ向け DDL / インデックス / 初期化ユーティリティ
    - stats.py
      - zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター算出
    - feature_exploration.py
      - 将来リターン計算、IC、rank、summary

各モジュールはドメインごとに責務が分かれており、外部 API 呼び出しを伴う部分（OpenAI / J-Quants / RSS）は堅牢化（リトライ・バックオフ・バリデーション）されています。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 動作モード（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

自動 .env ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## トラブルシューティング（よくある注意点）

- OpenAI レスポンスが不正な JSON を返すことがあり、その場合はログに警告が出てスコアは 0.0（フェイルセーフ）になります。API キーやモデル利用環境を確認してください。
- J-Quants API では 401 が返ると自動でリフレッシュを試みます。refresh token が無効だと失敗します。
- DuckDB のテーブルが存在しないと ETL・保存処理は失敗します（プロジェクトでスキーマ定義ユーティリティがあれば最初に実行してください）。
- ニュース収集で RSS 取得が失敗する場合は SSRF 対策により内部アドレスへのアクセスを拒否している可能性があります。RSS URL とネットワーク環境を確認してください。
- テストを実行する際や特殊な起動順序で .env の自動ロードを妨げたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

この README はコードベースの概要と基本的な操作方法をまとめたものです。各モジュールの詳細は該当ファイル（src/kabusys/**）のドキュメント文字列を参照してください。必要であれば具体的なスキーマ初期化手順や CI / デプロイ手順、例外処理ポリシーなどを別ドキュメントとして追加できます。