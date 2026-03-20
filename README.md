# KabuSys

日本株向けの自動売買システム用ライブラリ群です。データ収集・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、DuckDBスキーマ・監査ログなどを提供します。研究（research）と本番（execution）を分離した設計で、ルックアヘッドバイアス対策・冪等性・堅牢なネットワーク処理を重視しています。

---

## 概要

KabuSys は以下のレイヤーで構成されるモジュール群です。

- data: J-Quants からのデータ取得クライアント、ETL パイプライン、DuckDBスキーマ、ニュース収集、カレンダー管理、統計ユーティリティ等
- research: ファクター計算（モメンタム・ボラティリティ・バリュー）や特徴量探索（将来リターン・IC・統計サマリ）
- strategy: 特徴量の正規化・合成（features テーブルへの UPSERT）とシグナル生成（final_score 計算、BUY/SELL 判定）
- execution: 発注／実行層（パッケージは存在しますが、実装は用途に合わせて拡張）
- config: 環境変数の自動ロード・設定管理

設計上の特徴：
- DuckDB をローカル DB として使用（idempotent な保存）
- J-Quants API 用のレートリミッタ・リトライ・トークン刷新ロジック
- RSS ニュース収集での SSRF 対策・サイズチェック・XML 攻撃対策（defusedxml）
- 研究環境での再現性を重視（target_date 時点のデータのみ使用）

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch/save: 株価・財務・カレンダー）
  - news RSS 収集・記事保存・銘柄抽出
  - DuckDB スキーマ定義と初期化（init_schema）
- ETL
  - run_daily_etl: 市場カレンダー、株価、財務の差分取得＋品質チェック
  - 差分更新・バックフィル対応
- ファクター / 研究
  - モメンタム・ボラティリティ・バリューの定量ファクター計算
  - 将来リターン計算（複数ホライズン）、IC（Spearman）の計算、統計サマリー
- 特徴量・シグナル
  - features テーブル向けの Zスコア正規化・ユニバースフィルタ・日付単位UPSERT
  - final_score 計算（momentum/value/volatility/liquidity/news の重み付け）
  - BUY/SELL シグナル生成（Bear レジーム判定・ストップロス等）
- ユーティリティ
  - 環境変数自動ロード（.env/.env.local）と settings オブジェクト
  - 汎用統計関数（zscore_normalize）
  - マーケットカレンダー補完ロジック（営業日判定・next/prev_trading_day 等）
- 監査ログ（audit）: signal → order → execution までトレース可能な監査テーブル群

---

## 必要条件（想定）

- Python 3.10 以上（型ヒントに | 記法を使用）
- 依存パッケージ（例）
  - duckdb
  - defusedxml

（実行環境によって追加依存が必要になる場合があります。setup.cfg / pyproject.toml があればそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   - 例:
     - git clone ...
     - cd <repo>
     - python -m pip install -e ".[all]"  （extras や依存はプロジェクト設定に依存）

2. 必要な環境変数を用意
   - 必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション等の API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動ロードを無効化

   - .env をプロジェクトルートに置くと自動で読み込まれます（.env.local は上書き）。テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. DuckDB スキーマを初期化
   - Python から:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")  # または ":memory:"

4. （任意）ロギング設定
   - 環境変数 LOG_LEVEL を設定、あるいはアプリ側で logging.basicConfig を設定してください。

---

## 使い方（簡易例）

以下は主要 API のサンプル利用例（Python スクリプト内で使用）。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（J-Quants からの差分取得・保存・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を渡すことも可能
  - print(result.to_dict())

- 特徴量の構築（features テーブルへの書き込み）
  - from datetime import date
    from kabusys.strategy import build_features
  - cnt = build_features(conn, target_date=date(2024, 1, 31))
  - print(f"features upserted: {cnt}")

- シグナル生成（features と ai_scores を参照して signals に挿入）
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, target_date=date(2024, 1, 31))
  - print(f"signals written: {total}")

- ニュース収集ジョブ（RSS から raw_news 保存・銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, known_codes={"7203","6758"})
  - print(results)

- J-Quants データ取得を個別で使う（テストやバッチ）
  - from kabusys.data import jquants_client as jq
  - rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - jq.save_daily_quotes(conn, rows)

注意点:
- すべての日付処理は target_date 時点の「知られているデータのみ」を使う設計で、ルックアヘッドバイアスを避けるために future データを参照しません。
- ETL / save 関数は idempotent（ON CONFLICT / DO UPDATE）なので、再実行に耐えます。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (INFO) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to 1 to disable automatic .env loading

.env ファイルをプロジェクトルートに置くと自動的に読み込まれます（.git または pyproject.toml をプロジェクトルート判定に利用）。

---

## ディレクトリ構成

以下はパッケージ内の主なファイル・モジュールと概要（src/kabusys 以下）:

- __init__.py
  - パッケージのエクスポート定義とバージョン (0.1.0)
- config.py
  - 環境変数自動ロード、Settings オブジェクト（各種設定取得）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出・SSRF 対策
  - schema.py — DuckDB テーブル定義と init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - features.py — features 用ユーティリティ（再エクスポート）
  - calendar_management.py — market_calendar の管理・営業日判定
  - audit.py — 監査ログ用 DDL と初期化（signal_events / order_requests / executions 等）
  - (その他: quality 等の補助モジュールが想定される)
- research/
  - __init__.py — 研究用ユーティリティの再エクスポート
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- strategy/
  - __init__.py — public API: build_features, generate_signals
  - feature_engineering.py — raw ファクターのマージ、ユニバースフィルタ、Z スコア正規化、features への UPSERT
  - signal_generator.py — final_score 計算、BUY/SELL 生成、signals テーブル 書込
- execution/
  - __init__.py — 発注 / 実行層のエントリ（拡張用）
- monitoring/ (パッケージとして宣言されているがこのコード一覧には実装が見当たりません)
  - （監視系実装を配置）

---

## 開発・運用上の注意

- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みをオフにできます。
- J-Quants API はレート制限 (120 req/min) があるため、大量リクエスト時は注意してください。jquants_client は内部で固定間隔スロットリングと指数バックオフを実装しています。
- RSS 収集では外部 URL の検証と応答サイズ制限を行っていますが、運用では追加の監視を推奨します。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップや保護を運用ポリシーに従って行ってください。
- Strategy の重みや閾値は generate_signals の引数で上書きできます。重みは自動正規化されます。

---

## よくある操作の例（まとめ）

- DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn)

- 特徴量構築 → シグナル生成:
  - from datetime import date
    from kabusys.strategy import build_features, generate_signals
  - build_features(conn, date(2024,1,31))
  - generate_signals(conn, date(2024,1,31))

- ニュース収集:
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, known_codes={"7203","6758"})

---

README の内容は現行のコードベース（src/kabusys）に基づいています。追加の実運用機能（ブローカー接続、オーダー管理 UI、モニタリングエージェントなど）は execution / monitoring 層で拡張してください。必要であれば各モジュールの詳細 API ドキュメントや .env.example のテンプレートも作成します。必要なら指示してください。