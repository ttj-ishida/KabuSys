# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行層のスキーマ定義など、戦略運用に必要な主要コンポーネントを提供します。

## 主要な特徴
- J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・リトライ・レート制御）
- DuckDB ベースのデータスキーマと初期化ユーティリティ（冪等的な保存）
- ETL（差分取得・バックフィル・品質チェック）を含む日次パイプライン
- 研究用ファクター計算モジュール（Momentum / Volatility / Value）
- 特徴量の Z スコア正規化・クリップと features テーブルへの保存
- シグナル生成（複数コンポーネントによるスコア統合・Bear フィルタ・エグジット判定）
- RSS からのニュース収集、記事正規化、銘柄抽出および DB への保存
- 監査ログ（signal → order → execution のトレーサビリティ）スキーマ

## 必要条件
- Python 3.10 以上（PEP 604 の型記法 "X | Y" を使用）
- 主な依存パッケージ:
  - duckdb
  - defusedxml
（外部 HTTP 操作は標準ライブラリ urllib を使用）

例:
pip install duckdb defusedxml

プロジェクトをパッケージとしてインストールできる場合:
pip install -e .

## 環境変数（主要）
KabuSys は環境変数 / .env ファイルから設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われ、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化できます。

必須（アプリケーション実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

※ .env の書式は一般的なシェル形式をサポートしています（export KEY=val、クォート、インラインコメント等を考慮）。

## セットアップ手順（ローカル実行の例）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存ライブラリをインストール
   pip install duckdb defusedxml

   （パッケージに requirements.txt / pyproject.toml がある場合はそちらを利用）

4. 環境変数を設定
   プロジェクトルートに .env を作成して必要なキーを設定してください。
   例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   init_schema は必要なディレクトリを作成し、全テーブル／インデックスを冪等に作成します。

## 使い方（主要操作の例）

- 日次 ETL の実行
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

run_daily_etl は市場カレンダー取得 → 株価差分取得 → 財務データ取得 → 品質チェック を順に実行します。エラーは捕捉して結果に記録します。

- 特徴量（features）構築
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 10))
  print(f"{n} 銘柄の features を書き込みました")

build_features は research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ・Zスコア正規化・±3 クリップを行って features テーブルへ日付単位で置換保存します。

- シグナル生成
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024, 1, 10))
  print(f"{count} 件のシグナルを signals テーブルへ保存しました")

generate_signals は features と ai_scores を統合して最終スコアを計算し、BUY/SELL シグナルを生成して signals テーブルへ置換保存します。パラメータで重みや閾値を上書き可能です。

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # デフォルトソースを使い、known_codes を渡して銘柄紐付けを実行
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)

ニュース収集は RSS を取得・正規化して raw_news に冪等保存し、抽出した銘柄コードを news_symbols に保存します。SSRF 対策・gzip 上限・XML 脅威対策が組み込まれています。

- J-Quants データ取得を直接使う（例: 株価取得）
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from datetime import date

  token = get_id_token()  # settings からリフレッシュトークンを使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- ロギング
  アプリ側では標準 logging を設定してください。環境変数 LOG_LEVEL でデフォルトレベルを設定できます。

## 主要モジュールと役割（ディレクトリ構成）
リポジトリの主なソースは src/kabusys 以下にあります。主なモジュールを簡潔にまとめます。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・設定アクセスラッパー（settings）
  - data/
    - __init__.py
    - schema.py — DuckDB スキーマ定義・初期化・接続
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — zscore_normalize の再エクスポート
    - stats.py — 統計ユーティリティ（Z スコア等）
    - news_collector.py — RSS 収集・前処理・DB 保存
    - calendar_management.py — market_calendar の管理ユーティリティ
    - audit.py — 監査ログ（signal / order / execution）スキーマ
    - (他: quality.py が想定されるが、本リポジトリ内で別途実装)
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - execution/
    - __init__.py  （発注・ブローカ連携は別実装想定）
  - monitoring/  （監視・Slack 通知等の実装想定）

※ 上記はソース中の docstring とモジュール名を基にまとめています。

## 注意点 / 設計上のポイント
- ルックアヘッドバイアス防止: 特徴量計算・シグナル生成は target_date 時点のデータのみを使用する設計です。
- 冪等性: DB 保存は ON CONFLICT / トランザクション・置換で実装されており、再実行による二重登録を防止します。
- セキュリティ: news_collector は SSRF、XML Bomb、gzip Bomb、トラッキングパラメータ等に配慮した実装です。
- エラー耐性: ETL は各ステップを独立して実行し、1 ステップの失敗で全体を停止しないよう設計されています。結果の ETLResult に詳細が残ります。

## 開発 / テスト
- 自動 .env ロードはプロジェクトルート検出ロジックを利用します（.git または pyproject.toml を基準）。テスト時に自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モジュールは外部 HTTP 呼び出しや DB 書き込みを行うため、単体テストでは get_id_token や HTTP 呼び出し、_urlopen、DuckDB 接続等をモックしてテストすることを推奨します。

## 追加のヒント
- 実運用では KABUSYS_ENV を paper_trading / live に設定し、実環境とテスト環境の分離を行ってください。
- Slack 通知等の実装は別モジュールで組み合わせる想定です（settings.slack_bot_token / slack_channel_id を利用）。
- DuckDB ファイルはバックアップやスキーママイグレーションに気を配って管理してください。

----

問題や改善要望があれば、利用予定のユースケース（ETL の頻度、運用環境、証券ブローカー）を教えてください。README のサンプルコマンドやコード例を運用環境向けに合わせて調整できます。