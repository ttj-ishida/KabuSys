# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
Data（ETL / ニュース収集 / カレンダー管理 / DuckDB スキーマ）、Research（ファクター計算・解析）、Strategy（特徴量作成・シグナル生成）、Execution（発注周りのスキーマ等）などのモジュールを含みます。

主な設計方針：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- DuckDB を用いたローカルデータレイク（冪等な保存）
- 外部 API 呼び出しは専用クライアントで管理（リトライ・レート制御・トークンリフレッシュ）
- 冪等性・トランザクションを重視した DB 操作

---

## 機能一覧

- データ取得・保存（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーのフェッチと DuckDB への冪等保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 日次差分 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義と初期化
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 上限、XML パース保護）
  - raw_news 保存、記事ID 正規化（URL 正規化 + SHA256）
  - 銘柄コード抽出（既知コードに基づく）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計サマリ
  - クロスセクション Z スコア正規化
- 戦略レイヤー
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）：最終スコア計算・BUY/SELL の判定・signals テーブルへの保存
- カレンダー管理（営業日判定、次/前営業日、カレンダー更新ジョブ）
- 監査（audit）用スキーマ（signal/events/order/exec のトレーサビリティ）

---

## 必要な依存（主なもの）

（プロジェクトの pyproject.toml / requirements.txt を参照してください。ここでは主要ライブラリのみ示します）

- Python 3.9+
- duckdb
- defusedxml

インストール例（仮）:
pip install duckdb defusedxml

※ 実際にはプロジェクト配布方法に合わせて pyproject.toml から pip install -e . などでインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ移動
2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate
3. パッケージと依存をインストール
   pip install -e .      # プロジェクトルートに pyproject.toml がある前提
   pip install duckdb defusedxml
4. 環境変数の設定
   - .env / .env.local をプロジェクトルートに作成するか、環境変数を直接設定してください。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必須）
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   .env の自動読み込みはデフォルトで有効です。テスト等で自動ロードを無効化するには:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化（例）
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（簡単な例）

以下は主な操作の例です。実行前に必ず JQUANTS_REFRESH_TOKEN 等の必要な環境変数を設定してください。

- DuckDB 接続とスキーマ初期化
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema('data/kabusys.duckdb')  # ファイル作成・テーブル作成
  # 既存 DB に接続する場合:
  # conn = get_connection('data/kabusys.duckdb')

- 日次 ETL を実行する（市場カレンダー→株価→財務→品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量のビルド（feature layer）
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date(2024, 1, 4))
  print(f"features upserted: {count}")

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  n = generate_signals(conn, target_date=date(2024, 1, 4), threshold=0.6)
  print(f"signals generated: {n}")

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203', '6758'})
  print(results)

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- 研究用ユーティリティ
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  mom = calc_momentum(conn, date(2024,1,4))
  fwd = calc_forward_returns(conn, date(2024,1,4), horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col='mom_1m', return_col='fwd_1d')
  print(ic)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 任意（1 にすると .env 自動読み込みを無効化）

.env.example をプロジェクトルートに置いて編集する運用を推奨します（本リポジトリに例が無い場合は README の環境変数リストを参考に作成してください）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                          : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 : J-Quants API クライアント（レート制御・リトライ・保存）
    - news_collector.py                 : RSS ニュース収集・保存・銘柄抽出
    - schema.py                         : DuckDB スキーマ定義・初期化
    - stats.py                          : 統計ユーティリティ（zscore_normalize）
    - pipeline.py                       : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py            : カレンダー管理・update ジョブ
    - audit.py                          : 監査ログ用スキーマ
    - features.py                        : features インターフェース
  - research/
    - __init__.py
    - factor_research.py                : momentum / volatility / value の計算
    - feature_exploration.py            : 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py            : build_features
    - signal_generator.py               : generate_signals
  - execution/
    - __init__.py
  - (monitoring モジュールが __init__ の __all__ に含まれますが、実体はこのスナップショットに含まれない場合があります)

---

## 開発・テスト時のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を制御できます。
- J-Quants API 呼び出し部分は id_token 注入が可能なので、ユニットテストではモック化しやすく設計されています（関数に id_token を渡せます）。
- DuckDB の init_schema は冪等なので CI で毎回実行しても安全です。テストでは ":memory:" を使ってインメモリ DB に接続できます。
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")

---

## 注意事項

- 実際の発注（Execution / ブローカー連携）部分は本コードベースのスキーマやインターフェースを含みますが、証券会社への送信処理や口座管理などは外部実装が必要です。実運用前に十分な検証を行ってください。
- API トークン・秘密情報は .env に保管する際も取り扱いに注意し、ソース管理に含めないでください。
- 本 README に記載されていない付帯設定や運用フロー（監視、再試行ポリシー、資金管理ルール等）はプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。

---

貢献・バグ報告はリポジトリの Issue / PR へお願いします。