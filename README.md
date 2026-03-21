# KabuSys

日本株自動売買システムのコアライブラリ（パイプライン・ファクター計算・シグナル生成・データ収集 等）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータ基盤・特徴量エンジニアリング・戦略シグナル生成・監査・発注レイヤを想定した Python パッケージです。  
主に以下を提供します。

- J-Quants API からの株価・財務・カレンダー取得クライアント（ページネーション、レート制御、トークン自動更新、冪等保存）
- DuckDB を用いたデータスキーマ定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- 研究（research）向けのファクター計算・特徴量正規化ユーティリティ
- 戦略層: 特徴量合成（features 作成）、シグナル生成（buy/sell）
- ニュース収集（RSS）と記事—銘柄紐付け
- カレンダー管理・営業日判定
- 監査ログ（発注から約定までのトレーサビリティ）設計

設計方針として、ルックアヘッドバイアスに配慮し「target_date 時点で観測可能なデータのみ」を使うこと、DuckDB によるローカル永続化、外部依存を最小限にすることが挙げられます。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存ユーティリティ）
  - schema: DuckDB スキーマ定義 & 初期化
  - pipeline: 差分 ETL / 日次 ETL 実行（run_daily_etl）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー更新・営業日判定ユーティリティ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）等の解析ユーティリティ
- strategy/
  - feature_engineering: raw ファクターを正規化・フィルタして `features` テーブルを作成
  - signal_generator: features と ai_scores を統合して final_score を計算し `signals` テーブルを生成
- execution / monitoring: （エントリポイント定義。今後の発注 / 監視機能の配置想定）
- config: 環境変数管理（.env 自動ロード、必須設定の取得）

---

## 必須環境変数 (.env)

パッケージは .env または実行環境の環境変数を参照します。プロジェクトルート（.git あるいは pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants の refresh token。`jquants_client.get_id_token` で ID トークン取得に使います。
- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード（発注等で利用予定）。
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)  
  kabu API ベース URL。
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（監視等で利用）。
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID。
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  DuckDB データベースファイルのパス。
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)  
  監視用 SQLite ファイルパス（別途使用する場合）。
- KABUSYS_ENV (任意, default: development)  
  動作モード: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO)  
  ログ出力レベル

.env の書式は shell の export/KEY=val 形式やコメント行をサポートします。クォートやエスケープも扱えます。

例 (`.env.example` の例):

KQUANTS_REFRESH_TOKEN や機密情報は実運用で安全に管理してください。

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（コード内 typing 構文に依存）
- 必要な外部パッケージ例:
  - duckdb
  - defusedxml
（プロジェクトの pyproject.toml / requirements.txt を参照してインストールしてください）

基本的なセットアップ例:

1. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. パッケージのインストール（開発用に editable）
   - pip install -e .

   もしくは必要パッケージを個別に:
   - pip install duckdb defusedxml

3. .env を作成して上の必須変数を設定
   - cp .env.example .env
   - 編集してトークン等を設定

4. DuckDB スキーマの初期化
   - 下記の「データベース初期化」を参照

---

## データベース初期化

DuckDB スキーマを作成して接続オブジェクトを得る例:

Python スクリプト / REPL:

from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照して Path を返す
conn = schema.init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを自動作成

# または明示的にパスを渡す
conn = schema.init_schema("data/kabusys.duckdb")

init_schema はテーブル作成を行い、DuckDB 接続を返します（":memory:" を指定するとインメモリ DB）。

---

## 使い方（代表的なワークフロー例）

以下は主要な処理を順に実行する最小のスニペット例です。

1) DuckDB 初期化

from kabusys.data import schema
from kabusys.config import settings
conn = schema.init_schema(settings.duckdb_path)

2) 日次 ETL（J-Quants から市場カレンダー / 日足 / 財務 を差分取得して保存）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())       # ETL 実行結果の要約

3) 特徴量作成（feature engineering）

from kabusys.strategy import build_features
from datetime import date
# ETL の対象日（通常 run_daily_etl で使用した営業日）
target = date.today()
n_upsert = build_features(conn, target)
print(f"features upserted: {n_upsert}")

4) シグナル生成

from kabusys.strategy import generate_signals
n_signals = generate_signals(conn, target_date=target)
print(f"signals written: {n_signals}")

5) ニュース収集（RSS）

from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効コード集合（存在しないコードを除外）
# known_codes を渡さなければ銘柄抽出はスキップされる
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)

6) カレンダー夜間更新ジョブ（定期実行）

from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意点:
- jquants_client は ID トークン自動リフレッシュ・レートリミットを備えています。認証トークンは環境変数 JQUANTS_REFRESH_TOKEN で提供してください。
- 全ての DB 書き込みは可能な限り冪等（ON CONFLICT）を採用しています。
- target_date の扱いは「その日までにシステムが知り得るデータのみ」を想定しています。ルックアヘッドバイアスに注意して下さい。

---

## API（主要関数一覧）

- kabusys.config.settings  
  - settings.jquants_refresh_token, .kabu_api_password, .duckdb_path, .env など

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(...)
  - calc_ic(...)
  - factor_summary(...)

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

---

## 注意事項 / 運用上のヒント

- 本リポジトリは「戦略ロジック・発注ロジックの基盤」を提供します。実運用ではリスク管理やブローカー API の堅牢な実装、監査・復旧手順が必要です。
- 環境変数や機密情報は安全に管理してください（Vault / Secrets manager の利用を推奨）。
- J-Quants のレート制限を守るため、長時間バッチや並列取得時は注意して下さい（内部で固定間隔スロットリングを実装済み）。
- テスト時に .env の自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルはバックアップを推奨します。in-memory モード(":memory:") を使うと永続化されません。

---

## ディレクトリ構成

プロジェクトの主要なファイル構成（src 配下）:

src/kabusys/
- __init__.py
- config.py                # 環境変数/設定管理
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント（fetch/save）
  - schema.py              # DuckDB スキーマ定義 & init_schema
  - pipeline.py            # ETL パイプライン（run_daily_etl 等）
  - stats.py               # zscore_normalize 等
  - news_collector.py      # RSS 取得・保存・銘柄抽出
  - calendar_management.py # カレンダー更新・営業日判定
  - features.py            # zscore_normalize の再エクスポート
  - audit.py               # 監査ログ用 DDL（発注～約定のトレーサビリティ）
- research/
  - __init__.py
  - factor_research.py     # calc_momentum / calc_value / calc_volatility
  - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary
- strategy/
  - __init__.py
  - feature_engineering.py # build_features
  - signal_generator.py    # generate_signals
- execution/                # 発注/実行層（エントリプレースホルダ）
- monitoring/               # 監視モジュール（エントリプレースホルダ）

---

## ライセンス・貢献

（ここにライセンス情報を明記してください。OSS として公開する場合は LICENSE ファイルを追加してください。）

貢献: バグ報告・機能改善の PR は歓迎します。大きな設計変更は Issue で事前に相談してください。

---

README は以上です。必要であれば、導入用のサンプルスクリプト（cron ジョブ、systemd ユニット、Dockerfile など）や .env.example を作成しますので、用途に応じてお知らせください。