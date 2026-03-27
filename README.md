# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを一貫して提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() に直接依存しない）
- DuckDB を中心としたローカルデータベース構成
- J-Quants / OpenAI 等外部 API 呼び出しに対する堅牢なリトライ / フェイルセーフ
- 冪等性（INSERT ... ON CONFLICT 等）を重視した保存ロジック

---

## 機能一覧

- 環境設定読み込み（`.env` / 環境変数）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可）
- Data（jquants_client, ETL, カレンダー管理, ニュース収集, 品質チェック, 監査ログ 初期化）
  - J-Quants API クライアント（株価、財務、上場情報、マーケットカレンダー）
  - ETL パイプライン（日次 ETL 実行、差分取得、バックフィル、品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去）
  - 監査ログ DB 初期化（signal_events / order_requests / executions）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- AI（ニュース NLP、レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントのバッチ分析
  - ETF(1321)の MA とマクロセンチメントを合成した市場レジーム判定
  - API 呼び出しのリトライ / フェイルセーフ設計
- Research（ファクター計算、特徴量探索、統計ユーティリティ）
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 共通ユーティリティ
  - 統計ユーティリティ（Z スコア正規化など）
  - 設定管理（settings オブジェクト経由で環境変数へアクセス）

---

## セットアップ手順

前提：
- Python 3.10 以上（コード内で | 型注釈を使用しているため）
- ネットワークアクセス可能（J-Quants / OpenAI など）

1. リポジトリをクローン/配置
   - 例: git clone ... またはプロジェクトフォルダを作成して `src/` 配下にパッケージがある状態にする

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - 必須 (一例):
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（注文連携を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャネル ID
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合（関数引数で渡すことも可）
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマの初期化（監査ログ DB など）
   - 監査用 DB を作る例:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - その他のスキーマ初期化はプロジェクト固有のスクリプト（data.schema 等）に従ってください。

---

## 使い方（短いコード例）

- 設定の参照:
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- 日次 ETL 実行（例）:
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,25))
  print(result.to_dict())
  ```

- ニュース NLP スコア付け（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）:
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026,3,25))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定:
  ```
  from kabusys.ai.regime_detector import score_regime
  # conn は duckdb 接続, target_date は判定日
  score_regime(conn, target_date=date(2026,3,25))
  ```

- 監査 DB 初期化（専用ファイルを作る）:
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以後、order_requests / executions 等をこの conn で操作できます
  ```

---

## 主要ディレクトリ構成（src/kabusys）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS / raw_news をまとめて OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルに書き込む
    - regime_detector.py
      - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime を出す
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数含む）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、calendar_update_job）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存（SSRF / Gzip / XML の対策あり）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - 汎用統計ユーティル（zscore_normalize）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ、ランク関数
  - monitoring/ (概念的に存在：監視用ロジックや DB 操作用コードが入る想定)
  - execution/, strategy/, monitoring/（パッケージ公開のため __all__ でまとめられているが、実装はプロジェクトによる）

（上記はコードベースに含まれる主要モジュールの概要です）

---

## 注意事項・トラブルシューティング

- 環境変数
  - settings で必須とされる変数が未設定だと ValueError が投げられます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
  - 自動で .env をロードしますが、プロジェクトルートが特定できない場合（.git や pyproject.toml が無い）や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定した場合はロードされません。

- OpenAI / J-Quants API
  - API 呼び出しはレート制限とリトライロジックが含まれますが、適切な API キー・トークンの設定が必要です。
  - OpenAI のレスポンスが想定外の場合、ニューススコアやレジーム判定はフォールバック（スコア0など）して継続する設計です。

- DuckDB
  - ファイルパスのディレクトリは自動で作成されない関数もあるため、必要に応じてディレクトリを作成してください（audit.init_audit_db は親ディレクトリを自動作成します）。
  - DuckDB のバージョン依存の挙動（executemany に空リストを渡すとエラー等）があるため、コード内は互換性に配慮していますが、DuckDB のバージョンはプロジェクトごとに合わせてください。

- ニュース収集 / RSS
  - fetch_rss は SSRF 対策、gzip 解凍上限・XML Defused 対策を実装しています。外部フィードのフォーマットによってはパース失敗で空リストが返ります。

- ロギング
  - settings.log_level でログレベルを制御してください。デフォルトは INFO。

---

## 開発メモ

- ユニットテストは外部 API 呼び出しをモックする設計になっています（内部で _call_openai_api 等を差し替え可能）。
- DuckDB 接続はテストで :memory: を使うことで副作用を抑えられます。
- ルックアヘッドバイアスへの配慮により、多くの関数が target_date 引数を受け取ります。バックテスト用途ではこれを利用して時刻を固定してください。

---

必要であれば、この README に次の項目を追加できます：
- 詳細なテーブルスキーマ（raw_prices, raw_financials, ai_scores, market_regime 等）
- 実行可能な CLI や systemd / cron の設定例
- CI / CD（テスト・Lint）セットアップ手順

ほかに追記したい情報（例: .env.example 内容、具体的な SQL スキーマ抜粋、運用手順など）があれば教えてください。