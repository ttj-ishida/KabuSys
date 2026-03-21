# KabuSys

日本株向けの自動売買システム用ライブラリ／ツール群です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査記録などを含むモジュール設計になっています。本リポジトリはコア処理ロジックを提供し、実運用やジョブスケジューリング、ブローカー接続は別レイヤで組み合わせて利用します。

## 主な特徴（機能一覧）

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）
  - 必須変数未設定時は明示的エラーを発生

- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT）

- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル、品質チェックフック
  - 市場カレンダー先読み、価格/財務データの差分取得

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - テーブル・インデックスの自動作成（init_schema）

- ニュース収集
  - RSS フィードの取得・前処理・保存（raw_news）
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去、銘柄コード抽出

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC（Spearman）・ファクター統計サマリ

- 特徴量エンジニアリング
  - 生ファクターの正規化（Zスコア）・ユニバースフィルタ（最低株価・売買代金）・features テーブルへの UPSERT

- シグナル生成
  - features および ai_scores を組み合わせて final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナルの日次置換保存（signals）

- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティ用DDL（監査テーブル群）

## セットアップ手順

前提
- Python 3.9+（型注釈や一部の記法を踏まえた想定）
- DuckDB（Pythonパッケージ）
- ネットワークアクセス（J-Quants API 等）

1. リポジトリをクローン／ワークディレクトリへ移動。

2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール:
   - pip install duckdb defusedxml
   - （任意で lint/test 等のパッケージを追加）

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数（.env）を準備:
   - プロジェクトルートに .env（あるいは .env.local）を置くと自動読み込みされます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（代表）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - （任意）KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データベース初期化:
   - Python REPL やスクリプトから DuckDB スキーマを作成します（親ディレクトリは自動作成されます）。

   例:
   ```
   >>> from kabusys.data import schema
   >>> conn = schema.init_schema("data/kabusys.duckdb")
   ```

## 使い方（代表的なワークフロー）

以下はライブラリを直接使う最小例です。実際はジョブスケジューラ（cron / Airflow / GitHub Actions 等）や運用レイヤーと組み合わせます。

- 日次 ETL（市場カレンダー・株価・財務の差分取得・品質チェック）
  ```
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへ）
  ```
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 10))
  print(f"features updated for {n} symbols")
  ```

- シグナル生成（signals テーブルへ）
  ```
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 10))
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → news_symbols 紐付け）
  ```
  from kabusys.data import schema, news_collector
  conn = schema.init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants からのデータ取得（個別利用）
  ```
  from kabusys.data import jquants_client as jq
  # get id token (内部で settings.jquants_refresh_token を使う)
  token = jq.get_id_token()
  quotes = jq.fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,1,10))
  ```

注意:
- 各 API 呼び出しにはレート制限とリトライロジックが組み込まれていますが、バッチ運用時は十分なスロット間隔を確保してください。
- 実運用での発注処理（execution 層）やブローカー API の統合は本コードに部分的なテーブル定義・ログ設計はありますが、ブローカー固有の実装は含みません。

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なモジュール一覧（抜粋）です。実ファイルはさらに細分化されています。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得/保存）
    - news_collector.py       # RSS ニュース収集
    - schema.py               # DuckDB スキーマ定義・初期化
    - stats.py                # 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # 市場カレンダー管理・判定ユーティリティ
    - features.py             # features の公開ラッパ（再エクスポート）
    - audit.py                # 監査ログ用 DDL（signal_events / order_requests / executions 等）
    - audit テーブル関連 DDL は多数含む
  - research/
    - __init__.py
    - factor_research.py      # Momentum / Volatility / Value の計算
    - feature_exploration.py  # forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py  # 生ファクターから features 作成
    - signal_generator.py     # features + ai_scores → signals 生成
  - execution/
    - __init__.py             # 発注/実行関連はここに拡張
  - monitoring/
    - （監視・アラート関連の実装領域）

各ファイル内には関数・クラスの docstring が充実しており、処理フローや設計方針、引数・戻り値、例外挙動が記載されています。内部ユーティリティ（DB トランザクションやバルク INSERT、SSRF 対策など）も考慮されています。

## 注意点 / 運用メモ

- 環境（KABUSYS_ENV）:
  - development / paper_trading / live の 3 種類があり、live 時は実売買に繋ぐ際の安全チェックやログポリシーに注意が必要です。

- 自動環境ロード:
  - config.py はリポジトリルート（.git または pyproject.toml で検出）を基準に .env/.env.local を自動ロードします。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- DuckDB:
  - init_schema() により必要なテーブル・インデックスを作成します（冪等）。実運用では DB ファイルのバックアップとアクセス制御を推奨します。

- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、XML パーサの安全版（defusedxml）を利用していますが、RSS ソースの追加時には十分な検証を行ってください。
  - J-Quants のトークンや kabu API のパスワード等は外部に漏れないように .env ファイルの管理に注意してください。

## 開発・テスト

- 各モジュールは外部依存を最小化する設計（duckdb/defusedxml 等のみ）ですが、単体テスト時は API 呼び出し部分（jquants_client._request, news_collector._urlopen など）をモックすることを推奨します。
- pipeline 等の ETL は idempotent（冪等）設計になっており、再実行しても重複保存を回避します。

---

詳細は各モジュールの docstring を参照してください。README にない運用上のルール（運用スクリプト、cron 例、Slack 通知フロー等）は別途運用ドキュメントとして整備することを推奨します。必要であれば運用手順書（ジョブ設計、監視/アラート、バックテスト手順など）も作成できます。