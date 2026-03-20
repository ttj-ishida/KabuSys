# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ管理などを備え、研究（research）〜運用（execution）までのパイプラインをサポートします。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なサンプル）
- 環境変数（.env）例
- ディレクトリ構成（主要ファイルの説明）
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に必要な共通機能群を提供する Python ライブラリです。主な役割は以下です。

- J-Quants API を使った市場データ（株価日足、財務、カレンダー）の取得・保存（DuckDB）
- ETL（差分取得・バックフィル・品質チェック）によるデータパイプライン
- 研究用ファクター計算（momentum / volatility / value）と Z スコア正規化
- 戦略レイヤーでの特徴量合成（features テーブル）・シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB のスキーマ定義・初期化（冪等性を担保）
- 実行・監視（execution / audit）用のテーブルを含むスキーマ

設計方針として「ルックアヘッドバイアス回避」「冪等性」「外部API への安全なアクセス（レート制御・リトライ）」「DuckDB を中心とした軽量なデータ基盤」を重視しています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン自動リフレッシュ、固定間隔レートリミット、指数バックオフリトライ、ページネーション対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と init_schema(db_path)
- data/pipeline.py
  - ETL ヘルパーと日次 ETL 実行 run_daily_etl（差分取得、バックフィル、品質チェック）
- data/news_collector.py
  - RSS 取得〜前処理〜raw_news への冪等保存、記事から銘柄コード抽出、news_symbols への紐付け
- data/calendar_management.py
  - market_calendar の更新・営業日判定（next/prev/is_trading_day など）
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）
- research/*.py
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）の計算、要約統計
- strategy/feature_engineering.py
  - raw ファクターを結合して features テーブルへ保存（ユニバースフィルタ、正規化、クリップ、日付単位の置換）
- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを作成して signals テーブルへ保存
- execution / monitoring / audit（テーブル定義や骨組み）
  - 監査ログ・発注トレースを保持するスキーマなど

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `X | None` などを使用しているため）
- Git

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （追加で logging 等は標準ライブラリで提供）

4. データベース初期化（例）
   - Python コンソール／スクリプトで以下を実行して DuckDB スキーマを初期化してください（デフォルト DB パスは `data/kabusys.duckdb`）。
     ```
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")
     ```
   - :memory: を指定するとインメモリ DB で初期化できます。

5. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動で読み込まれます（ただしテスト時などに自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数については後の節「環境変数（.env）例」を参照。

---

## 使い方（簡単なサンプル）

以下は主要ワークフローの最小例です。実行前に DB を初期化し、必要な環境変数を設定してください。

1) DuckDB 接続と初期化
```
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# 以降は conn を各モジュールに渡して使用
```

2) 日次 ETL（市場カレンダー・株価・財務の差分取得）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行
print(result.to_dict())
```

3) 特徴量計算（features テーブルの更新）
```
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date(2024, 3, 1))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルの更新）
```
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, target_date=date(2024, 3, 1))
print(f"signals written: {n}")
```

5) ニュース収集
```
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

各関数は「日付単位で既存レコードを削除してから挿入（置換）」するため、冪等に実行できます。

---

## 環境変数（.env）例

必須:
- JQUANTS_REFRESH_TOKEN  → J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      → kabu ステーション API（発注）用パスワード
- SLACK_BOT_TOKEN        → Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       → Slack 投稿先チャンネルID

任意・デフォルトあり:
- KABUSYS_ENV            → development / paper_trading / live（デフォルト development）
- LOG_LEVEL              → DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH            → DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            → 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD → 1 を設定すると自動 .env 読み込みを無効化

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

読み込みの優先順:
- OS 環境変数 > .env.local > .env

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主要モジュール（抜粋）と役割です。

- kabusys/__init__.py
  - パッケージ初期化と __version__
- kabusys/config.py
  - 環境変数読み込み（.env/.env.local 自動ロード）、Settings クラス（設定項目のラッピング）
- kabusys/data/
  - jquants_client.py — J-Quants API クライアント（取得/保存関数）
  - news_collector.py — RSS 収集と raw_news 保存、銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema
  - pipeline.py — ETL（run_daily_etl など）
  - calendar_management.py — market_calendar 管理（is_trading_day 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — zscore_normalize の再エクスポート
  - audit.py — 監査ログ用スキーマ（signal_events / order_requests / executions など）
- kabusys/research/
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — 将来リターン / IC / 要約統計
- kabusys/strategy/
  - feature_engineering.py — raw ファクターの合成 → features テーブル
  - signal_generator.py — final_score 計算 → signals テーブル
- kabusys/execution/
  - （発注実装のプレースホルダ。execution レイヤーはスキーマ/構造を提供）

---

## 注意事項 / 設計上のポイント

- Python バージョンは 3.10 以上を推奨（`X | None` 型表記などを使用）。
- DuckDB をデータ格納に利用しており、スキーマ初期化は init_schema() を通すことを推奨します。
- J-Quants API 呼び出しは内部でレート制御（120 req/min）とリトライ（最大 3 回）を行います。401 についてはリフレッシュトークンから ID トークンを自動で再取得して 1 回リトライします。
- ETL / シグナル生成 / 特徴量作成は「日付単位で置換（削除→挿入）」するため冪等です。
- news_collector は RSS の SSRF 対策、gzip サイズ上限、XML の安全パーサ（defusedxml）を採用しています。
- 環境変数は .env/.env.local から自動読み込みされますが、テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑制できます。
- Strategy / Execution 間は疎結合に設計されています。戦略モジュールは発注 API に依存せず、signals テーブルへ書き込むのみです。実際の発注は execution 層で signals を読み取って行います。

---

もし README に含めたい追加情報（CI 実行方法、ユニットテスト実行手順、例の SQL スキーマダンプ、より詳しい API 使用例等）があれば教えてください。README を用途に合わせて拡張します。