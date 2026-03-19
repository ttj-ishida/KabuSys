# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
市場データの取得・ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むモジュール群を提供します。

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータレイクスキーマ（raw → processed → feature → execution）
- 量的ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- 特徴量の正規化（Z スコア）と features テーブルへの永続化
- ファクター + AI スコア統合による売買シグナルの生成（signals テーブル）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- 市場カレンダー管理と営業日計算
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計上、発注（execution）層やブローカー API への依存を限定し、研究（research）環境や本番環境で同じロジックを共有できるようになっています。

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（fetch / save）：日次株価、財務、マーケットカレンダー
  - rate-limit とリトライ、401 時のトークン自動リフレッシュ対応
- ETL
  - 差分更新（最終取得日からの差分取得）
  - backfill（最終取得日の数日前から再取得して後出し修正を吸収）
  - 品質チェック（欠損・スパイク等の検出）
- データモデル（DuckDB スキーマ）
  - raw_prices / raw_financials / raw_news / prices_daily / features / ai_scores / signals / orders / executions / positions など
- 研究・特徴量
  - モメンタム / ボラティリティ / バリューファクター計算
  - クロスセクション Z スコア正規化ユーティリティ
  - IC（Spearman）や将来リターン計算等の解析ツール
- 戦略
  - 特徴量合成（build_features）
  - シグナル生成（generate_signals）：重み付け、Bear レジーム抑制、エグジット判定（ストップロス等）
- ニュース収集
  - RSS 取得、記事正規化、重複防止（URL 正規化 → SHA-256 ハッシュ）
  - 銘柄コード抽出（4桁コード）と news_symbols への紐付け
  - SSRF / XML bombing / レスポンスサイズ制限等の安全対策
- カレンダー管理
  - market_calendar の差分更新、next/prev 営業日計算、SQ 判定 など
- 監査ログ
  - signal_events / order_requests / executions 等によりトレーサビリティを確保

## セットアップ手順

前提
- Python 3.10+（typing の一部で | 型注釈を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS XML パース用）
- その他標準ライブラリのみで動作するユーティリティ

例: 仮想環境とインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（プロジェクトに requirements ファイルがない場合の例）
   - pip install duckdb defusedxml

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（execution 層用）
- SLACK_BOT_TOKEN: Slack 通知（オプションで監視/通知に使用）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルト
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

.env 自動読み込み
- パッケージはプロジェクトルートにある .env / .env.local を自動で読み込みます（CWD ではなくパッケージファイル位置から .git または pyproject.toml を探索）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 .env（必須キーのみ）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

## 使い方（主要な操作例）

以下は Python スクリプトや REPL での利用例です。target_date は datetime.date 型を使用します。

1) DuckDB スキーマの初期化
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可

2) 日次 ETL 実行（J-Quants から差分取得して保存）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) 特徴量の構築（features テーブルに書き込む）
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

4) シグナル生成（features と ai_scores を参照して signals へ書き込む）
from kabusys.strategy import generate_signals
num = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {num}")

5) RSS ニュース収集ジョブ
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使用する有効コードの集合（任意）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count}

6) カレンダー更新ジョブ（夜間バッチ用）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

7) DuckDB 既存接続取得（スクリプト再実行時など）
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")

注意点・運用ヒント
- ETL の差分ロジックは最終取得日を基準に backfill_days を使って再取得します（API の後出し修正に対応）。
- J-Quants API はレート制限（120 req/min）に従うため、大量取得時は遅延が入ります。
- シグナル生成では Bear レジーム検知により BUY を抑制するロジックがあります。
- トランザクション（BEGIN/COMMIT/ROLLBACK）で日付単位の置換を行い、冪等性を担保しています。

## ディレクトリ構成

（パッケージルートが src/ 配置の場合の主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント（fetch/save）
      - news_collector.py            # RSS ニュース収集・保存
      - schema.py                    # DuckDB スキーマ定義・初期化
      - stats.py                     # Z スコア等統計ユーティリティ
      - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      - features.py                  # data 層の feature ユーティリティ（再エクスポート）
      - calendar_management.py       # market_calendar 管理・営業日ロジック
      - audit.py                     # 監査ログ DDL
      - audit.py                     # （監査関連 DDL、トレーサビリティ）
    - research/
      - __init__.py
      - factor_research.py           # ファクター計算（mom/vol/value）
      - feature_exploration.py       # IC / forward returns / summary
    - strategy/
      - __init__.py
      - feature_engineering.py       # build_features（正規化・ユニバースフィルタ）
      - signal_generator.py          # generate_signals（最終スコア → signals）
    - execution/                      # 発注 / execution 層（プレースホルダ／拡張用）
      - __init__.py
    - monitoring/                     # 監視・Slack 通知など（拡張用）
- pyproject.toml / setup.cfg / README.md（このファイル）

（上記は主要モジュールの抜粋です。実運用時は packaging・CI・デプロイ用ファイルを追加してください。）

## ロギング・環境切替

- KABUSYS_ENV により env を切り替えます（development, paper_trading, live）。
  - settings.is_live / is_paper / is_dev で判定可能。
- LOG_LEVEL 環境変数でログレベルを指定してください（デフォルト INFO）。

## セキュリティ / 安全対策について（要点）

- J-Quants クライアントはレート制限とリトライ、401 時の自動トークン再取得を実装。
- ニュース収集は XML パーサに defusedxml を使用し、SSRF 対策のためリダイレクト先やホストのプライベートアドレスチェック、最大レスポンスサイズ制限、gzip 解凍制限等を実装。
- DB への保存は Idempotent（ON CONFLICT / DO UPDATE / DO NOTHING）を採用。
- トランザクションで日付単位の置換を行い原子性を確保。

## 参考 / 追加情報

- コード内に StrategyModel.md / DataPlatform.md / DataSchema.md などの設計メモへの参照があります。運用や拡張時はこれらの設計ドキュメントに従ってください。
- 発注（execution）やブローカー統合、Slack 通知等は本パッケージの外側での実装・拡張が想定されています。

---

ご要望があれば、README に具体的なコマンド例（systemd / cron ジョブ、Dockerfile、GitHub Actions ワークフロー等）や .env.example のテンプレート、よくあるトラブルシュートを追加します。