# KabuSys — 日本株自動売買システム

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買戦略の骨組みを提供する Python パッケージです。J-Quants API から市場データ・財務データ・マーケットカレンダーを収集し、DuckDB に格納してファクター計算、特徴量正規化、シグナル生成を行います。ニュース収集や監査ログ、実行レイヤ（発注・約定・ポジション管理）を含む設計を想定しています。

主な特徴
--------
- J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制限・リトライ対応）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（日次差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value など）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントスコアの統合、Buy / Sell 判定）
- ニュース収集（RSS、URL 正規化、SSRF対策、記事→銘柄マッピング）
- 監査ログ設計（signal → order_request → execution のトレース設計）
- テストしやすい設計（依存注入、冪等性、ログ）

必要条件
--------
- Python 3.10 以上（型ヒントに | 記法を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで済む機能も多い）

インストール（開発環境）
---------------------
1. リポジトリをクローンして仮想環境を作成・有効化します。
2. 必要パッケージをインストールします（例）:

   - pip を利用する場合（例）:
     pip install duckdb defusedxml

3. パッケージを editable インストール（任意）:
   pip install -e .

環境変数 / 設定
----------------
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` ファイルから読み込まれます（自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（代表例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API パスワード
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID      : Slack 通知対象チャネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト INFO）

簡単な設定例（.env）
--------------------
例としてプロジェクトルートに `.env` を作成します：
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（サンプル）
-----------------

1) DuckDB スキーマ初期化
- Python スクリプトや REPL で DuckDB ファイルを作成・初期化します。

例:
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・テーブル作成

2) 日次 ETL 実行（市場データ・財務データ・カレンダーを取得）
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) 特徴量作成（feature テーブルへ保存）
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

4) シグナル生成（signals テーブルへ保存）
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date.today())
print(f"signals generated: {n}")

5) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)

6) カレンダー夜間更新ジョブ
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意事項
--------
- J-Quants API に対するリクエストはレート制限（120 req/min）やトークン刷新処理を実装していますが、API 利用ポリシーに従ってください。
- 本ライブラリは発注（execution）に関して抽象層を提供しますが、実際の実運用（live）ではリスク管理・検証が必須です。
- DuckDB のバージョンや SQL 構文互換性に注意してください（README 内の制約はコード内コメントに従います）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数・.env ロード・Settings
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得/保存ユーティリティ）
  - news_collector.py       — RSS ニュース取得・正規化・保存
  - schema.py               — DuckDB スキーマ定義 & init_schema/get_connection
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py  — マーケットカレンダー管理 / 営業日判定
  - features.py             — zscore_normalize の再エクスポート
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログ用スキーマ（signal/order/execution のトレース）
  - (その他: quality, execution raw テーブル などを想定)
- research/
  - __init__.py
  - factor_research.py      — Momentum/Volatility/Value のファクター計算
  - feature_exploration.py  — 将来リターン/IC/統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  — features テーブル作成ロジック
  - signal_generator.py     — final_score 計算・BUY/SELL 生成
- execution/
  - __init__.py
  - (発注・約定を扱う実装層を格納予定)
- monitoring/
  - (監視・メトリクス関連の実装を格納予定)

主要設計ポイント（短く）
-----------------------
- 冪等性: DB への保存は ON CONFLICT / INSERT … DO UPDATE / DO NOTHING を多用し再実行可能に。
- ルックアヘッドバイアス対策: すべての計算は target_date 時点のデータのみを使用する設計。
- 安全対策: ニュース収集で SSRF/XML Bomb 対策（ホワイトリスト化・defusedxml）を実装。
- テスト容易性: id_token の注入、KABUSYS_DISABLE_AUTO_ENV_LOAD などの仕掛け。

貢献とライセンス
----------------
- バグレポートや改善提案は Pull Request / Issue を通してください。
- ライセンスはリポジトリに含まれる LICENSE を参照してください（本 README には未記載）。

問い合わせ
----------
- 実運用や設定に関する質問があれば、リポジトリの Issue を作成してください。README のコマンド例を元に環境情報（Python バージョン、DuckDB バージョン、使用している .env の非機密な設定）を添えると早く対応できます。

以上。必要であれば「導入手順のスクリーンショット」「.env.example の自動生成サンプル」「よくあるエラーと対処法」などを追加で作成します。どれを優先しますか？