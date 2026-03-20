KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータ層に用い、J-Quants などの外部データソースからデータを取得・整形し、特徴量生成・シグナル生成・ニュース収集・監査ログまで含む一連の処理を提供します。

要点
- ETL（J-Quants → DuckDB）を差分・バックフィル対応で実行
- ファクター（モメンタム / バリュー / ボラティリティ / 流動性）計算
- Zスコア正規化・特徴量の生成（features テーブルへのUPSERT）
- 戦略シグナル生成（final_score の計算、BUY/SELL 判定）
- RSS ベースのニュース収集と銘柄抽出（SSRF対策・トラッキング除去）
- DuckDB スキーマ定義・監査ログテーブルを備えたデータモデル

主な機能
- データ取得・保存
  - J-Quants API クライアント（fetch/save：日足・財務・カレンダー）
  - 差分 ETL（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - DuckDB スキーマの初期化（init_schema）
- データ品質・カレンダー
  - market_calendar 管理・営業日判定（is_trading_day / next_trading_day / get_trading_days）
  - 品質チェックフレーム（quality モジュールと連携）
- 研究 / 戦略
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_engineering: build_features（Zスコア正規化・ユニバースフィルタ）
  - signal_generator: generate_signals（最終スコア計算、BUY/SELL判定、signals へ保存）
  - research/feature_exploration: 将来リターン計算、IC、統計サマリー
- ニュース
  - RSS 取得・前処理（SSRF/サイズ上限/トラッキング除去）
  - raw_news / news_symbols への冪等保存
- 監査・実行レイヤ
  - audit モジュール: signal_events / order_requests / executions 等の監査テーブル
  - Execution 層のスキーマ（signal_queue / orders / trades / positions など）

必要条件
- Python 3.9+
- 必須ライブラリ（代表例）
  - duckdb
  - defusedxml
（実行環境によっては追加のパッケージや OS 依存ライブラリが必要になる場合があります）

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（省略時: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env → .env.local を自動読み込みします。
- テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の書式は export KEY=val や KEY="value" など一般的な形式に対応します。

セットアップ手順（開発用）
1. リポジトリをクローン
   - git clone <repo>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール（例）
   - pip install duckdb defusedxml
   - （ローカル開発向け）pip install -e .
4. .env を作成して必要な環境変数を設定
   - .env.example を参照して設定してください（プロジェクトに同梱されている想定）
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで init_schema を呼ぶ（下記参照）

基本的な使い方（コード例）
- DuckDB を初期化して接続を取得する
  - from kabusys.data.schema import init_schema, get_connection
  - conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成しスキーマを作る
  - もしくは既存 DB へ接続: conn = get_connection("data/kabusys.duckdb")

- 日次ETL を実行する（J-Quants から差分取得）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - result.to_dict() をログや監査に利用できます

- 市場カレンダー更新（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- ニュース収集実行（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", ...}  # 既知のコードセット（抽出に使用）
  - res = run_news_collection(conn, known_codes=known_codes)
  - res は {source_name: saved_count} の辞書

- 特徴量ビルド
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2025, 1, 31))  # 指定日分を計算して features テーブルに UPSERT

- シグナル生成
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
  - signals テーブルに BUY/SELL が書き込まれます（日付単位の置換: 冪等）

- 研究用ユーティリティ
  - from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  - forward = calc_forward_returns(conn, date(2025, 1, 31))
  - ic = calc_ic(factor_records, forward, factor_col="mom_1m", return_col="fwd_1d")

注意・設計上のポイント
- ルックアヘッドバイアス対策: 各モジュールは target_date 時点までのデータのみ参照する設計です。ETL やシグナル生成は常に過去データに基づいて計算します。
- 冪等性: save_* 系関数やテーブル操作は ON CONFLICT を用いるなど冪等性を考慮しています。
- エラー耐性: ETL は個別ステップで例外を捕捉して処理を継続する方針です（ログに残して呼び出し元で判定）。
- セキュリティ: RSS フェッチでは SSRF 対策、レスポンスサイズ制限、XML パースの安全化（defusedxml）を実施しています。J-Quants API はレート制限・リトライ・トークン自動更新対応です。

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数/設定読み込みロジック
  - data/
    - __init__.py
    - schema.py                      — DuckDB スキーマ定義・init_schema/get_connection
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - news_collector.py              — RSS 取得・前処理・保存ロジック
    - calendar_management.py         — market_calendar 管理（営業日判定/更新）
    - features.py                    — zscore_normalize の公開インターフェース
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ用テーブル DDL（signal_events 等）
    - (その他: quality.py 等想定)
  - research/
    - __init__.py
    - factor_research.py             — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py          — calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py            — generate_signals（final_score, BUY/SELL, signals へ保存）
  - execution/                        — （発注周りの実装層、空の __init__ 等）
  - monitoring/                       — 監視・メトリクス関連（想定）
  - その他モジュール（docs/やtests/はプロジェクトによる）

開発・テストのヒント
- 自動環境変数読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを抑制し、テスト内で明示的に環境変数を注入してください。
- インメモリ DuckDB を利用して単体テストを高速化: init_schema(":memory:")
- ネットワーク呼び出しをモック: jquants_client._request や news_collector._urlopen をモックして外部依存を切り離すと良いです。

ライセンス / 貢献
- 本 README にはライセンス条項を含めていません。利用・配布方針やコントリビューション方法はプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在する想定）。

以上が KabuSys の概要と基本的な使い方です。特定の機能やコードの利用例（例: ETL の詳細パラメータ、シグナル重みのチューニング、news_collector の RSS ソース追加）について詳細が必要であれば教えてください。必要に応じて README にコマンド例やスニペットを追加します。