KabuSys — 日本株自動売買基盤（README 日本語版）
概要
KabuSys は日本株を対象とした自動売買／データ基盤のプロジェクトです。J-Quants API から市場データ・財務データ・市場カレンダーを取得して DuckDB に保存する ETL、RSS ベースのニュース収集、特徴量（ファクター）計算、監査ログ／発注周りのスキーマ等を含むデータプラットフォームとリサーチツール群を提供します。発注処理や戦略モジュールは拡張して実運用に接続できるよう設計されています。

主な特徴（機能一覧）
- データ取得
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
- ETL / データ基盤
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - 差分更新（最終取得日からの差分取得、バックフィル対応）
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集
  - RSS フィード取得、前処理、記事保存、銘柄コード抽出（SSRF対策・gzip上限等の堅牢設計）
- 研究（Research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査・トレーサビリティ
  - シグナル → 発注要求 → 約定 を追跡する監査テーブル群（UUID ベース）
- スケーラビリティと堅牢性
  - DuckDB を中心に冪等保存（ON CONFLICT）やトランザクションでデータ整合性を保つ設計
- 拡張ポイント
  - strategy, execution, monitoring パッケージにより、実際の戦略やブローカー接続を差し替え可能

前提（Prerequisites）
- Python 3.10 以上（型注釈に | を使用）
- システム依存パッケージ（主に pip パッケージ）
  - duckdb
  - defusedxml
  - （必要に応じて他パッケージを追加）

セットアップ手順
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - requirements.txt が無い場合は最低限次を入れてください:
     pip install duckdb defusedxml
   - 開発インストール（パッケージとして利用したい場合）:
     pip install -e .

4. 環境変数設定
   - プロジェクトルートの .env またはシステム環境変数で設定します。
   - 自動ロード: パッケージ import 時にプロジェクトルート（.git か pyproject.toml）から .env/.env.local を自動で読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注連携を使う場合）
     - SLACK_BOT_TOKEN       : Slack 通知を使う場合
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 .env（簡易）
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

使い方（簡単な利用例）
- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得＋品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 手動で株価を取得して保存（J-Quants から直接フェッチ）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

- ニュース収集ジョブを実行
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203","6758", ...}  # 監視対象銘柄セット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: saved_count}

- ファクター計算 / リサーチ
  from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  from datetime import date
  momentum = calc_momentum(conn, date(2024,3,1))
  vol = calc_volatility(conn, date(2024,3,1))
  value = calc_value(conn, date(2024,3,1))
  fwd = calc_forward_returns(conn, date(2024,3,1))
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

- 監査スキーマ初期化（発注監査用）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意点 / 実装上の設計方針（概要）
- J-Quants API クライアントはレート制限（120 req/min）を守るために内部でスロットリングし、ネットワーク/HTTP エラーに対するリトライや 401 時のトークンリフレッシュを行います。
- ETL は差分更新（最終取得日ベース）とバックフィルを組み合わせ、API の後出し修正を吸収する方針です。
- ニュース収集では SSRF 対策、XML 脆弱性対策（defusedxml）、レスポンスサイズ上限等の安全対策を施しています。
- DuckDB スキーマは raw / processed / feature / execution / audit と層別に定義され、冪等性・トランザクション設計に配慮しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                : パッケージ定義（version 等）
  - config.py                  : 環境変数・設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py        : RSS ニュース収集・保存・銘柄抽出
    - schema.py                : DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                 : 統計ユーティリティ（zscore_normalize）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - features.py              : features の公開インタフェース（再エクスポート）
    - calendar_management.py   : market_calendar 管理・営業日判定
    - audit.py                 : 監査ログテーブル定義 / init_audit_db
    - quality.py               : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - etl.py                   : ETLResult の再エクスポート
  - research/
    - __init__.py              : 研究用 API 再エクスポート（calc_momentum 等）
    - feature_exploration.py   : 将来リターン計算 / IC / summary / rank
    - factor_research.py       : momentum/value/volatility の計算
  - strategy/                   : 戦略ロジック（拡張ポイント）
    - __init__.py
  - execution/                  : 発注・証券会社連携（拡張ポイント）
    - __init__.py
  - monitoring/                 : 監視・アラート関連（拡張ポイント）
    - __init__.py

その他
- ログ設定、Slack 通知、kabuステーションとの接続・発注処理などはプロジェクトの拡張点です。実運用で「live」モードを使う場合は安全対策（リスク管理・二重確認・テスト口座での検証）を必ず行ってください。
- テストや CI のセットアップ、依存関係 pin（requirements.txt / pyproject.toml）はプロジェクトに合わせて追加してください。

問題報告 / コントリビュート
- 不具合や改善提案は Issue を立ててください。設計方針に沿った実装・テストの PR を歓迎します。

以上で README の簡易版です。必要であれば、セクションを追記（API ドキュメント、サンプル .env.example、CLI ユーティリティの説明、運用ガイドなど）して拡張できます。どの情報を追加しますか？