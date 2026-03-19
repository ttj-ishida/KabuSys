kabusys

日本株向け自動売買 / データプラットフォーム用 Python パッケージの README（日本語）
この README は、与えられたコードベース（src/kabusys/...）の使い方、セットアップ、主要機能をまとめたドキュメントです。

1. プロジェクト概要
- KabuSys は日本株を対象としたデータ取得・ETL・特徴量作成・シグナル生成・監査用スキーマを備えたモジュール群です。
- 主に以下レイヤーを提供します：
  - Data (J-Quants からのデータ取得・保存、RSS ニュース収集、DuckDB スキーマ、ETL パイプライン)
  - Research (ファクター計算・特徴量解析ユーティリティ)
  - Strategy (特徴量合成 → シグナル生成)
  - Execution / Monitoring（発注・モニタリング周りのインターフェースを想定）
- 設計方針：ルックアヘッドバイアス回避・冪等性（DB 保持）・ネットワークエラー/レート制御・トレーサビリティ重視。

2. 主な機能一覧
- 環境変数管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動で読み込み（必要に応じて無効化可能）。
  - 必須環境変数をプロパティ経由で取得（settings.jquants_refresh_token など）。
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義。init_schema() により冪等的に初期化。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - rate limiting、リトライ、トークン自動更新に対応。
  - 日足・財務・カレンダー取得、DuckDB への保存ユーティリティ（save_*）。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分）・バックフィル・品質チェック統合（run_daily_etl 等）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事保存、銘柄コード抽出。SSRF 対策・サイズ制限あり。
- 研究系ユーティリティ（kabusys.research）
  - ファクター計算（momentum / volatility / value）、将来リターン計算、IC 計算、Zスコア正規化等。
- 戦略（kabusys.strategy）
  - 特徴量合成（build_features: 生ファクターを統合・正規化・features テーブルへ保存）
  - シグナル生成（generate_signals: features + ai_scores を統合して BUY/SELL を作成）
- 監査ログ / オーディット（kabusys.data.audit）
  - signal_events / order_requests / executions 等、監査目的のテーブル群を定義。

3. セットアップ手順（開発用）
前提：Python 3.9+（型アノテーションで | を使うため切り替え環境に依存する場合があります）、DuckDB と defusedxml 等が必要。

例：venv を使う
1) 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

2) 依存パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトの extras / requirements ファイルがある場合はそれに従ってください）

3) パッケージのインストール（開発モード）
   pip install -e .

4) 環境変数の用意
   プロジェクトルートに .env/.env.local を作成するか、OS 環境変数で設定してください。
   主要な環境変数（必須）：
     - JQUANTS_REFRESH_TOKEN   （J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD       （kabu API が必要な場合のパスワード）
     - SLACK_BOT_TOKEN         （Slack 通知を使う場合）
     - SLACK_CHANNEL_ID        （Slack 通知先チャンネル）
   オプション：
     - KABUSYS_ENV             : development / paper_trading / live （デフォルト development）
     - LOG_LEVEL               : DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト INFO）
     - DUCKDB_PATH             : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH             : 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込みを無効化

5) DB スキーマ初期化（例）
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

4. 使い方（主要 API の例）
以下は典型的なワークフローのサンプルです。実際はログ設定や例外ハンドリングを追加してください。

- DuckDB 接続とスキーマ初期化
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # ファイルとスキーマを作成して接続を返す
  # 既存 DB に接続するだけなら:
  # conn = get_connection("data/kabusys.duckdb")

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- カレンダー更新バッチ（夜間ジョブ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（任意）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- 特徴量構築（戦略層）
  from datetime import date
  from kabusys.strategy import build_features
  cnt = build_features(conn, target_date=date(2024, 1, 4))
  print("features upserted:", cnt)

- シグナル生成
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2024, 1, 4))
  print("signals written:", total)

- J-Quants からデータを直接取得して保存（テストや再取得時）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,4))
  saved = jq.save_daily_quotes(conn, records)

- ニュース RSS の個別取得（デバッグ）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

5. 環境変数 / 設定の詳細
- 自動 .env 読み込み
  - kabusys.config はプロジェクトルート（.git または pyproject.toml の存在する場所）を探索し、.env を読み込みます。
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Settings（kabusys.config.settings）でプロパティ経由で必須/既定値取得をします。未設定の必須値は ValueError になります。

6. 推奨実運用ポイント
- DuckDB のバックアップとファイルローテーションを検討してください（データ増大に伴う I/O）。
- J-Quants API はレート制限があるため、バッチ設計・レート制御（モジュール内実装）に留意してください。
- ニュース取得は外部 RSS に依存するため、SSRF/ファイルスキーム排除・タイムアウト・サイズチェックが実装されています。プロダクションでは known_codes の管理を行って銘柄抽出精度を上げてください。
- ログは LOG_LEVEL で制御できるため、運用時は適切に設定してください。
- シグナル → 発注フローは監査テーブル（audit）でトレース可能。order_request_id を冪等キーとして扱うことで二重発注を防止する設計です。

7. ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py        # J-Quants API クライアント（取得・保存）
  - news_collector.py       # RSS ニュース収集・解析・保存
  - schema.py               # DuckDB スキーマ定義と初期化
  - pipeline.py             # ETL パイプライン（run_daily_etl 等）
  - stats.py                # zscore_normalize 等の統計ユーティリティ
  - features.py             # data 層の feature ユーティリティ再エクスポート
  - calendar_management.py  # market_calendar の管理・ユーティリティ
  - audit.py                # 監査ログスキーマ
  - ...（その他）
- research/
  - __init__.py
  - factor_research.py      # momentum/volatility/value の計算
  - feature_exploration.py  # 将来リターン、IC、統計サマリー等
- strategy/
  - __init__.py
  - feature_engineering.py  # raw factor を正規化して features テーブルに保存
  - signal_generator.py     # final_score 計算と signals テーブルへの挿入
- execution/
  - __init__.py
- monitoring/ (パッケージエクスポートにあるがコード抜粋は省略)

8. 既知の注意点 / 実装上の留意点（コードベースからのメモ）
- DuckDB の一部制約（ON DELETE CASCADE 等）はバージョン依存で省略している箇所があります（コメント参照）。
- research と data は外部ライブラリ（pandas 等）に依存せず純 Python + DuckDB の SQL で実装されています。大規模データ処理時はパフォーマンス確認を行ってください。
- generate_signals / build_features は target_date 時点のデータのみを使用してルックアヘッドバイアスを避けるよう設計されています。
- ニュース収集は XML パースに defusedxml を利用して安全対策を行っています。インストールを忘れないでください。

9. 追加情報 / 次のステップ
- CI / テスト：ユニットテストや統合テストを用意して、ETL / シグナルロジックの回帰防止を行ってください（モックで外部 API を差し替え可能）。
- ドキュメント：StrategyModel.md / DataPlatform.md 等の仕様書がプロジェクト内にある前提で実装されているため、仕様書とコードの整合性を常に保持してください。
- 運用：paper_trading / live モード切替や Slack 通知の導入等、運用パイプラインと監視体制の整備を推奨します。

---
この README はコードベースの注釈・ドキュメント文字列を元に作成しています。追加で README に含めたい項目（例: example .env の内容、Docker / systemd サービス構成、テストコマンドなど）があれば教えてください。必要に応じて README を拡張して具体的なコマンド例やテンプレートを追記します。