KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
=================================

概要
----
KabuSys は日本株向けのデータパイプライン・特徴量生成・シグナル生成・ニュース収集・監査ログを含む自動売買基盤のライブラリ群です。本リポジトリは次の目的を持ちます。

- J-Quants API から株価/財務/カレンダーを取得して DuckDB に保存する ETL
- 研究環境（research）で計算した生ファクターを正規化して features テーブルを構築する特徴量パイプライン
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成する戦略ロジック
- RSS を用いたニュース収集と銘柄紐付け
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）の初期化・管理
- 各種ユーティリティ（統計、マーケットカレンダー補助、監査ログなど）

現バージョン: 0.1.0

主な機能
--------
- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）、財務（四半期）、市場カレンダーのページネーション対応取得
  - レートリミットと再試行（リトライ、トークン自動リフレッシュ）を内包
- ETL パイプライン
  - 差分取得（最終取得日を基準に差分取得）、バックフィル対応、品質チェック呼び出し
- DuckDB スキーマ管理
  - raw_prices / prices_daily / features / signals / orders / executions / positions / audit 系などの DDL を定義し初期化
- 特徴量計算（research/factor_research）
  - Momentum, Volatility, Value（PER / ROE）等を計算
  - z-score 正規化ユーティリティ（data.stats）
- 特徴量エンジニアリング（strategy/feature_engineering）
  - ユニバースフィルタ（最低株価・最低売買代金）を適用し、Z スコアをクリップして features テーブルへ UPSERT
- シグナル生成（strategy/signal_generator）
  - momentum/value/volatility/liquidity/news の重み付き合算による final_score 計算
  - Bear レジーム判定、BUY/SELL シグナルの生成と signals テーブルへの日次置換（冪等）
- ニュース収集（data/news_collector）
  - RSS 取得・XML パース（defusedxml 使用）、SSRF/サイズ制限/トラッキングパラメータ除去、記事IDは正規化 URL の SHA-256 先頭 32 文字で冪等保証
  - raw_news / news_symbols への保存（チャンク / トランザクション）
- マーケットカレンダー管理（data/calendar_management）
  - DB に基づく営業日判定（フォールバックは曜日ベース）、calendar 更新ジョブ
- 監査ログ（data/audit）
  - signal → order → execution のトレーサビリティ用テーブル群

セットアップ手順
--------------
前提
- Python 3.10 以上（ソース内での型ヒントに | None 等の構文を使用）
- DuckDB（Python パッケージ）および defusedxml

推奨パッケージインストール例:
- pip を用いる場合:
  - pip install "duckdb" "defusedxml"
  - （開発用にローカルインストールする場合）pip install -e .

環境変数
- 本ライブラリは環境変数から設定を読み込みます（kabusys.config.Settings）。
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API パスワード（必要に応じて）
  - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（必要に応じて）
  - SLACK_CHANNEL_ID — Slack 投稿先チャンネル ID
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（モニタリング）ファイルパス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — 環境識別 (development | paper_trading | live)（デフォルト: development）
  - LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

例: .env（プロジェクトルート）
    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

使い方（主要な API・ワークフロー）
--------------------------------

1) DuckDB スキーマ初期化
- 初回はスキーマを作成します（ファイル DB を使う場合はパスの親ディレクトリが自動作成されます）。

Python 例:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants からの差分取得）
- ETL 実行は run_daily_etl を使います。内部で calendar・prices・financials の差分取得と品質チェックを行います。

Python 例:
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    # conn は init_schema で得た DuckDB 接続
    result = run_daily_etl(conn, target_date=date.today())
    if result.has_errors:
        print("ETL 中にエラーが発生しました:", result.errors)
    if result.has_quality_errors:
        print("品質チェックにエラーがあります")

3) 特徴量構築（features テーブルへの書き込み）
- research 側で計算された生ファクターを集約・正規化して features テーブルを生成します。

Python 例:
    from datetime import date
    from kabusys.strategy import build_features
    count = build_features(conn, target_date=date.today())
    print(f"features に書き込んだ銘柄数: {count}")

4) シグナル生成
- features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ保存します。

Python 例:
    from datetime import date
    from kabusys.strategy import generate_signals
    total = generate_signals(conn, target_date=date.today(), threshold=0.6)
    print(f"生成したシグナル数: {total}")

- 重みをカスタマイズする場合は weights パラメータに辞書を渡します（未指定キーはデフォルトにフォールバックし、合計が 1 に再スケールされます）。

5) ニュース収集ジョブ
- RSS ソースからニュースを収集し raw_news / news_symbols を更新します。

Python 例:
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    # known_codes は銘柄コード抽出に利用する既知のコード集合（例: {'7203','6758',...}）
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(results)

6) カレンダー更新ジョブ（夜間バッチ）
- calendar_update_job を呼んで market_calendar を更新できます。

Python 例:
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print(f"保存件数: {saved}")

ユーティリティ
- data.stats.zscore_normalize: クロスセクションで指定列を Z スコア正規化します。
- research.calc_forward_returns / calc_ic / factor_summary 等: 研究用途の統計解析ツール群。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py           — パッケージのバージョン等
- config.py             — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得 + 保存）
  - news_collector.py   — RSS ニュース収集・保存
  - schema.py           — DuckDB スキーマ定義・初期化
  - stats.py            — 統計ユーティリティ（z-score 等）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - features.py         — features 公開インターフェース
  - calendar_management.py — カレンダー管理・更新ジョブ
  - audit.py            — 監査ログ（signal / order / execution）
- research/
  - __init__.py
  - factor_research.py  — Momentum/Volatility/Value 等ファクター計算
  - feature_exploration.py — forward returns, IC, 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築（正規化・ユニバースフィルタ）
  - signal_generator.py    — final_score 計算とシグナル生成
- execution/             — （発注/約定周りの実装場所、現状空）
- monitoring/            — （モニタリング用モジュール置き場、現状未実装）

設計上の注意点（要点）
--------------------
- ルックアヘッドバイアス回避:
  - ファクター/シグナル生成は target_date 時点のデータのみを参照するよう設計されています。
  - データ取得時は取得日時（fetched_at）を保存し、いつデータを利用可能だったかを追跡できます。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING で冪等化されています。
  - ETL / シグナル生成は「日付単位で削除→挿入」のパターンで日次置換（トランザクションで原子性確保）。
- セキュリティ・堅牢性:
  - RSS 取得は SSRF 対策、受信バイト数上限、defusedxml による XML パース保護を実施。
  - API クライアントはレート制限・リトライ・トークンリフレッシュを実装。

よくある操作例（簡易スクリプト）
--------------------------------
1. DB 初期化 + 当日の ETL + 特徴量・シグナル生成:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.strategy import build_features, generate_signals

    conn = init_schema("data/kabusys.duckdb")
    etl_res = run_daily_etl(conn, target_date=date.today())
    trading_day = etl_res.target_date
    build_features(conn, trading_day)
    generate_signals(conn, trading_day)

トラブルシュート
-----------------
- 環境変数エラー:
  - settings の必須環境変数が未設定の場合、kabusys.config._require が ValueError を投げます。.env.example を参照して .env を作成してください。
- DuckDB 接続/DDL エラー:
  - init_schema でテーブル作成時に失敗した場合はトレースバックとともに ROLLBACK が試みられます。パーミッションやファイルパスを確認してください。
- RSS 取得のタイムアウト/接続エラー:
  - ネットワークや対象サイトの挙動によっては fetch_rss が urllib.error.URLError を投げます。例外は上位で適切にハンドリングしてください（run_news_collection はソース単位でエラーハンドリングします）。

ライセンス・貢献
----------------
（本リポジトリに付属するライセンス情報をここに記載してください。例: MIT / Apache-2.0 等）

最後に
------
この README はコードベースの主要構成・使用方法を簡潔にまとめたものです。詳細な設計仕様（StrategyModel.md、DataPlatform.md など）や運用手順は別途ドキュメントを参照してください。追加で README に載せたい実行例・CI 設定・開発手順などあれば指定してください。