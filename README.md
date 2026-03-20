KabuSys
======

日本株向けの自動売買プラットフォームのライブラリ群です。データの取得・保存（DuckDB）、特徴量計算、シグナル生成、ニュース収集、ETLパイプライン、監査ログなどを含む設計になっています。ライブラリは発注（ブローカ）への直接送信層とは分離されており、戦略層 → 実行層 → 発注インターフェースの形で利用できます。

主な目的
- J-Quants API 等からの市場データ・財務データ・カレンダーの自動取得
- DuckDB を用いたデータ保存スキーマとETL実装（冪等性を重視）
- 研究（research）で計算したファクターを使った特徴量作成と正規化
- 正規化済み特徴量＋AIスコアを統合したシグナル生成（BUY / SELL）
- RSS からのニュース収集・銘柄抽出
- 監査ログ（signal → order → execution）を追跡可能にするテーブル設計

機能一覧
- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートの検出）と必須変数チェック
- データ層（kabusys.data）
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ）
  - DuckDB スキーマ定義と初期化（init_schema）
  - データ保存ユーティリティ（raw_prices / raw_financials / market_calendar / raw_news 等）
  - ETL パイプライン（差分取得、バックフィル、品質チェックの呼び出し）
  - ニュース収集（RSS fetch / 正規化 / raw_news 保存 / 銘柄抽出）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day）
  - 統計ユーティリティ（Zスコア正規化 等）
- リサーチ層（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- 戦略層（kabusys.strategy）
  - 特徴量作成（build_features: raw factor から features テーブルへ）
  - シグナル生成（generate_signals: features + ai_scores → signals テーブル）
- ニュース収集の安全対策
  - SSRF対策、最大受信サイズ制限、XMLパースの安全化（defusedxml）
- 監査（audit）テーブル設計
  - signal_events, order_requests, executions などの監査用テーブル

セットアップ手順（開発環境）
1. リポジトリをクローンまたはソースを配置
2. 依存パッケージのインストール
   - 最低限必要: Python 3.9+
   - pip install duckdb defusedxml
   - その他のユーティリティは標準ライブラリで実装されていますが、実行環境に応じて追加が必要になる場合があります。
3. パッケージをインストール（開発時）
   - pip install -e .
4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（CWD ではなくソースファイル位置からプロジェクトルートを探索）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（kabusys.config.Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注実装時）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（通知を行う場合）
     - SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID
   - オプション:
     - KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト "development"）
     - LOG_LEVEL : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト "INFO"）
   - サンプル .env 内容:
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

使い方（主要エントリポイント例）
- DuckDB スキーマ初期化
  - Python REPL またはスクリプトで:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
  - ":memory:" を指定するとインメモリ DB になります。

- 日次ETL の実行（市場データ / 財務 / カレンダー）
  - from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)
    print(result.to_dict())
  - run_daily_etl は品質チェックや backfill を行い ETLResult を返します。

- 特徴量作成（features テーブルへの書き込み）
  - from kabusys.strategy import build_features
    from kabusys.data.schema import get_connection
    from datetime import date
    conn = get_connection("data/kabusys.duckdb")
    count = build_features(conn, date(2024, 1, 31))
    print(f"features upserted: {count}")

- シグナル生成（signals テーブルへの書き込み）
  - from kabusys.strategy import generate_signals
    conn = get_connection("data/kabusys.duckdb")
    total = generate_signals(conn, date(2024, 1, 31))
    print(f"signals written: {total}")
  - generate_signals は weights と threshold をオーバーライド可能（辞書 / float）。

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    conn = get_connection("data/kabusys.duckdb")
    known_codes = {"7203","6758", ...}  # あらかじめ有効銘柄リストを用意
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(results)

- カレンダー更新バッチ
  - from kabusys.data.calendar_management import calendar_update_job
    conn = get_connection("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"calendar saved: {saved}")

開発・デバッグのポイント
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テストで環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- J-Quants API 周りはネットワーク・レート制限やトークン処理（自動リフレッシュ）を組み込んでいます。テスト時は get_id_token にテスト用トークンを渡す、あるいは _request をモックしてください。
- RSS 取得は defusedxml を使い XML 攻撃対策を実施しています。外部への HTTP リクエストは _urlopen をモックすることでユニットテスト可能です。
- DuckDB への挿入は冪等性（ON CONFLICT）を念頭に実装されているため、何度実行してもデータの上書きや重複を回避できます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（fetch/save）
    - news_collector.py            : RSS 収集・保存・銘柄抽出
    - schema.py                    : DuckDB スキーマ定義と初期化
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等）
    - features.py                  : zscore_normalize の再エクスポート
    - calendar_management.py       : カレンダー関連ユーティリティ & バッチ
    - audit.py                     : 監査ログ用 DDL（signal/order/execution）
    - stats.py                     : 統計ユーティリティ（zscore_normalize）
    - quality.py?                  : （品質チェックモジュールが参照されます）
  - research/
    - __init__.py
    - factor_research.py           : momentum/volatility/value 等のファクター計算
    - feature_exploration.py       : 将来リターン、IC、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py       : features テーブル作成（build_features）
    - signal_generator.py          : generate_signals（BUY/SELL 判定）
  - execution/                      : 発注・ブローカー接続層（空のパッケージが含まれます）
  - monitoring/                     : 監視系（将来的な実装想定）

注意事項 / 制約
- 本リポジトリのコードは設計仕様（コメント）を広く含みますが、実行時の環境（J-Quants API キー、ネットワーク、DuckDB バージョン）に依存します。実運用前にローカルで十分なテストを行ってください。
- 発注（order）を実際に送るコード（証券会社APIとの橋渡し）は実装方針上分離されています。実運用時は execution 層で適切なブローカー実装を追加してください。
- データの整合性・監査証跡は重視していますが、DuckDB の機能差（バージョン）により外部キーの振る舞いが異なる点があるため README の記述やコード内注記に従って運用してください。

ライセンス / 貢献
- 本プロジェクトに関するライセンス情報や貢献方法はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本 README には含まれていません）。

以上が KabuSys の概要・セットアップ・簡易利用方法です。必要であれば、より具体的なセットアップ手順（Docker、CI、実行スクリプト例）や各モジュールの API 使用例を追加で用意します。どの部分を詳しく知りたいか教えてください。