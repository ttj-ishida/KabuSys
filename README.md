# KabuSys

日本株向けの自動売買システム用ライブラリコア（データ収集・ETL・研究・戦略・実行／監査レイヤ）です。  
本リポジトリは次の目的を持つモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー等の取得（rate-limit / retry / token refresh 対応）
- DuckDB ベースのスキーマ定義と冪等保存
- ETL パイプライン（差分更新・品質チェック）
- ニュース収集（RSS → 正規化 → DB 保存・銘柄抽出）
- 研究／ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量生成（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（最終スコア算出・BUY / SELL 判定）
- カレンダー管理・監査ログ等の補助機能

バージョン: 0.1.0

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レート制御・再試行・トークン自動更新）
  - fetch / save の Idempotent 実装（ON CONFLICT を使用）
- data/schema
  - DuckDB 用の完全なスキーマ定義（Raw / Processed / Feature / Execution / Audit レイヤ）
  - init_schema(db_path) による一括初期化
- data/pipeline
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル対応
- data/news_collector
  - RSS フィード収集、XML 防御、SSRF 対策、トラッキングパラメータ除去、銘柄コード抽出
  - raw_news / news_symbols への冪等保存
- data/calendar_management
  - market_calendar の管理、営業日判定・前後営業日の取得等
- research
  - calc_momentum / calc_volatility / calc_value
  - forward returns / IC 計算 / factor summary
  - zscore_normalize の提供
- strategy
  - build_features(conn, target_date): 特徴量の構築と features テーブルへの保存
  - generate_signals(conn, target_date, ...): final_score 計算と signals テーブルへの保存
- config
  - .env（.env.local）自動読み込み（プロジェクトルート検出）と Settings API（環境変数アクセス）

---

## 動作環境・前提

- Python 3.10 以上（コード中に `X | Y` 型アノテーションを使用）
- 主要依存パッケージ（少なくとも）:
  - duckdb
  - defusedxml

実行環境に合わせて追加の依存が必要になる場合があります（例: ネットワーク経由で Slack 通知等）。

---

## セットアップ手順

1. リポジトリをクローン／取得してください。

2. Python 仮想環境を作成・有効化（例: venv）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール:
   - 開発環境にパッケージ化された要件ファイルがない場合、最低限以下を入れてください：
   ```bash
   pip install duckdb defusedxml
   ```
   - プロジェクトを編集可能モードでインストールできる場合:
   ```bash
   pip install -e .
   ```

4. 環境変数（必須）を設定してください。主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot のトークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development / paper_trading / live)（デフォルト development）
   - LOG_LEVEL: ログレベル (DEBUG/INFO/...)（デフォルト INFO）

   .env をプロジェクトルートに置くと自動で読み込まれます（.env.local は上書き）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマを初期化:
   Python スクリプトまたは REPL で以下を実行します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: でも可
   conn.close()
   ```

---

## 使い方（主なユースケース）

以下は代表的な操作の簡単な例です。各関数は duckdb の接続オブジェクト（kabusys.data.schema.init_schema / get_connection が返す接続）を受け取ります。

- DuckDB 接続の取得・初期化:
  ```python
  from kabusys.data.schema import init_schema, get_connection

  # DB 初期化（ファイルが存在しない場合は親ディレクトリも作成）
  conn = init_schema("data/kabusys.duckdb")

  # 既存 DB へ接続する場合
  conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants のトークンは settings 経由で自動取得）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行:
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")

  # known_codes を渡すと記事と銘柄の紐付けが行われる
  known_codes = {"7203", "6758", "9984"}
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)
  ```

- 研究用ファクター計算 / 特徴量生成 / シグナル生成:
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 10)

  # 研究モジュールは DuckDB の prices_daily / raw_financials を参照
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 特徴量を作成して features テーブルへ保存
  n = build_features(conn, target)
  print(f"features upserted: {n}")

  # シグナル生成（threshold や weights は上書き可能）
  total = generate_signals(conn, target)
  print(f"signals written: {total}")
  ```

- カレンダー操作例:
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  d = date(2024, 1, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## 設定・環境変数の詳細

- 自動 .env 読み込み
  - プロジェクトルートはパッケージファイル位置を起点に上位ディレクトリを探索し、`.git` または `pyproject.toml` を発見したディレクトリがルートとなります。
  - 読み込み順: OS 環境 > .env.local > .env
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- Settings API
  - 使用例: `from kabusys.config import settings; token = settings.jquants_refresh_token`
  - バリデーション:
    - KABUSYS_ENV は `development` / `paper_trading` / `live`
    - LOG_LEVEL は `DEBUG/INFO/WARNING/ERROR/CRITICAL`

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント（fetch/save）
  - news_collector.py         # RSS → raw_news / news_symbols
  - schema.py                 # DuckDB スキーマ定義・init_schema
  - pipeline.py               # ETL パイプライン（run_daily_etl 等）
  - stats.py                  # zscore_normalize 等の統計ユーティリティ
  - features.py               # data 層の features 再エクスポート
  - calendar_management.py    # market_calendar 管理・営業日ユーティリティ
  - audit.py                  # 監査ログ用 DDL
- research/
  - __init__.py
  - factor_research.py        # calc_momentum / calc_volatility / calc_value
  - feature_exploration.py    # forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py    # build_features
  - signal_generator.py       # generate_signals
- execution/                   # 発注・execution 層（空の __init__ と実装予定）
- monitoring/                  # 監視用コード（別モジュールに分割予定）

---

## 実運用上の注意点

- DuckDB のバージョンや SQL 構文互換性に依存します。初期化・マイグレーション時はテスト環境で十分検証してください。
- J-Quants API のレートや認証情報は各自の契約に従ってください。クレデンシャルは安全に管理してください（.env は .gitignore 推奨）。
- シグナルの自動発注を行う場合はまず paper_trading 環境で十分なバックテスト・フォワードテストを行ってください。
- news_collector は外部 RSS を取得するため、SSRF・XML解析攻撃に対する保護（defusedxml・SSRF checks）を行っていますが、実運用ではネットワーク ACL やプロキシ設定も検討してください。

---

## 貢献 / 開発

- 新しい ETL チェックや品質ルール、戦略ロジックの追加を歓迎します。  
- 開発時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定しテスト用環境を構築することで、ローカルの .env 読み込みを抑制できます。

---

もし README に追加してほしいサンプル（例: systemd タスク、Airflow ジョブ定義、CI 設定）や、各モジュールのより詳細な API ドキュメント（関数一覧・引数説明）をご希望であれば教えてください。