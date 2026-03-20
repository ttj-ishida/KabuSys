# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータ取得・特徴量生成・シグナル生成・ETL といった自動売買プラットフォームのコアロジックを収めた Python パッケージです。J-Quants API からデータを取得して DuckDB に保存し、研究フェーズで得られた生ファクターを正規化・統合して戦略シグナルを生成します。発注層（ブローカー連携）は別途実装する想定で、各モジュールは発注APIへ直接依存しないよう設計されています。

主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 特徴量エンジニアリング（research の生ファクターを正規化し features テーブルへ保存）
- シグナル生成（特徴量 + AI スコア統合 → BUY/SELL シグナル作成、売りのエグジット判定）
- ニュース収集（RSS 取得、SSRF 対策、記事正規化、銘柄紐付け）
- 研究ユーティリティ（フォワードリターン、IC 計算、ファクターサマリー）
- 監査ログ（signal → order → execution のトレーサビリティ設計）

必要な環境
- Python 3.10+
- 主な依存（例）:
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装している部分が多いですが、外部 HTTP や DB 用のライブラリは必要です）
- J-Quants API のリフレッシュトークン等の環境変数

セットアップ（開発マシン）
1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell 以外)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     pip install -r requirements.txt
   - ない場合の最小例:
     pip install duckdb defusedxml

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（CWD ではなくパッケージ位置からプロジェクトルートを探索します）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

基本的な使い方（Python スニペット）
- DuckDB スキーマ初期化
  ```
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・テーブル定義
  ```

- 日次 ETL を実行（市場カレンダー、価格、財務）
  ```
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)  # デフォルトは今日の日付
  print(res.to_dict())
  ```

- 特徴量の生成（research の生ファクターを正規化して features テーブルへ保存）
  ```
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, date(2026, 3, 1))
  print(f"features upserted: {n}")
  ```

- シグナル生成（features / ai_scores / positions を参照して signals テーブルへ書き込む）
  ```
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, date(2026, 3, 1))
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", ...}  # 銘柄コードの集合（任意）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

設定（環境変数の説明）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション用の API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

主要モジュール説明（概要）
- kabusys.config
  - 環境変数読み込み・設定管理（.env 自動ロード、必須キー取得）

- kabusys.data
  - jquants_client.py: J-Quants API クライアント（レート制御・リトライ・保存ユーティリティ）
  - schema.py: DuckDB の全テーブル定義と init_schema / get_connection
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - news_collector.py: RSS 収集・前処理・DB 保存・銘柄抽出（SSRF 対策あり）
  - calendar_management.py: market_calendar 管理・営業日判定ユーティリティ
  - audit.py: 監査ログ用 DDL（signal / order / execution の追跡）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - features.py: stats.zscore_normalize の再エクスポート

- kabusys.research
  - factor_research.py: momentum / volatility / value 等の生ファクター計算
  - feature_exploration.py: 将来リターン計算、IC、ファクターサマリー

- kabusys.strategy
  - feature_engineering.py: 生ファクターの結合・ユニバースフィルタ・正規化 → features テーブルへ
  - signal_generator.py: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成

- kabusys.execution / kabusys.monitoring
  - 発注（execution）や監視（monitoring）関連のエントリプレースホルダー（実装は別途）

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - stats.py
      - features.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/         (empty or implementation-specific)
    - monitoring/        (empty or implementation-specific)

運用上の注意
- 本パッケージの戦略ロジックは実環境（実資金）での使用前に十分なバックテストとペーパートレードでの検証が必須です。
- J-Quants API のレート制限（120 req/min）やトークン管理を遵守してください。jquants_client モジュールはレートとリトライを実装していますが、運用側でも過剰な並列化は避けてください。
- DuckDB スキーマは冪等的に作成されます。初回は init_schema() を呼び出してください。
- news_collector は外部 URL を扱うため SSRF や巨大応答への対策（実装済み）を行っていますが、運用環境での追加対策（プロキシやネットワークポリシー）も推奨します。
- 環境変数や機密情報は適切に管理してください（例: CI/CD の Secrets、Vault 等）。

拡張 / 開発のヒント
- 発注・ブローカー連携（execution）やモニタリングダッシュボードは本リポジトリ外で実装して連携できます。signals / signal_queue / orders / executions テーブルは監査・追跡を容易にする設計です。
- AI スコアやニュース解析は ai_scores テーブルへ格納することで signal_generator が利用できます。
- テストのために自動環境読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

ライセンス
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（無ければプロジェクト管理者に確認してください）。

---

追加で README に載せたい例（CI 実行方法、より詳しい運用手順、CI 用コマンド、実行スクリプト例など）があれば教えてください。必要に応じて README を拡張します。