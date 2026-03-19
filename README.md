# KabuSys

日本株向けの自動売買システム用ライブラリ群（データプラットフォーム・特徴量作成・戦略シグナル生成・ETL・監査など）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。  
主な役割は以下のとおりです。

- J-Quants API からの市場データ取得（株価日足・財務情報・カレンダー）
- DuckDB を用いたデータスキーマ / 永続化
- ETL パイプライン（日次差分取得・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量作成（正規化・フィルタリング）と features テーブルへの保存
- 戦略シグナルの生成（final_score 計算・BUY/SELL 生成）
- ニュース収集（RSS → raw_news）と記事 → 銘柄紐付け
- マーケットカレンダー管理、監査ログ（発注〜約定トレース） のためのスキーマ

設計上のポイント：
- ルックアヘッドバイアスに配慮し、target_date 時点のデータのみを使用
- 冪等性（ON CONFLICT / トランザクション）を重視
- 外部依存を最小化（可能な限り標準ライブラリと DuckDB で実装）

---

## 主な機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 日次 ETL（run_daily_etl）, 個別 ETL ジョブ（prices, financials, calendar）
  - news_collector: RSS 取得・前処理・DB 保存、銘柄抽出
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリ
- strategy/
  - feature_engineering.build_features: ファクター合成・Z スコア正規化・ユニバースフィルタ・features テーブルへの upsert
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を計算し signals テーブルに書込
- audit / execution / monitoring: 発注〜約定・ポジション管理・監査ログのためのスキーマ（監査テーブル定義あり）
- config: 環境変数の読み込み (.env 自動ロード、必須チェックなど)

---

## 前提 / 要件

- Python 3.10 以上（構文上の union 型 annotations を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - defusedxml
- 追加で J-Quants の利用・Slack 通知・kabuステーション連携を行う場合はそれぞれのアクセサリ／ライブラリが必要になる場合があります。

インストール（例）:
- 仮想環境を作成してから:
  - pip install duckdb defusedxml
  - pip install -e .  （パッケージとして開発インストールする場合）

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・アクティベートする
2. 依存パッケージをインストールする
   - 例: pip install duckdb defusedxml
3. 環境変数を準備する（下記参照）。プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
4. DuckDB の初期スキーマを作成する（例は下記）

---

## 環境変数（主なもの）

config.Settings により取得される主要な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API の refresh token
  - KABU_API_PASSWORD: kabuステーション API のパスワード
  - SLACK_BOT_TOKEN: Slack Bot トークン（通知などで使用）
  - SLACK_CHANNEL_ID: Slack チャネル ID
- オプション / デフォルトあり
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

注意:
- .env(.local) の自動ロードは、プロジェクトルート（.git または pyproject.toml を基準）から行われます。
- テストなどで自動ロードを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## データベース初期化（例）

Python REPL またはスクリプトから DuckDB スキーマを初期化します。

例:
```
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Settings.duckdb_path を参照する Path オブジェクト
conn = init_schema(settings.duckdb_path)
```

- ":memory:" を渡すとインメモリ DB を使用します。
- init_schema はテーブル作成を冪等で行います。

---

## ETL の実行（日次パイプライン）

日次 ETL（カレンダー取得 → 株価差分 → 財務差分 → 品質チェック）を実行する例:

```
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETL 実行結果のサマリ
```

個別ジョブも利用可能:
- run_prices_etl(conn, target_date, ...)
- run_financials_etl(conn, target_date, ...)
- run_calendar_etl(conn, target_date, ...)

ETLResult には品質チェックやエラー情報が含まれます。

---

## 特徴量（features）構築

研究モジュールで計算した raw factor を正規化・合成して features テーブルに保存します。

例:
```
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,15))
print(f"upserted features: {n}")
```

- build_features はユニバースフィルタ（最低株価・最低売買代金）を適用し、Z スコア正規化（±3 クリップ）を行います。
- 処理は日付単位の置換（DELETE + bulk INSERT）で冪等です。

---

## シグナル生成

features テーブルおよび ai_scores 等を使って最終スコアを計算し、BUY / SELL シグナルを signals テーブルへ書き込みます。

例:
```
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,15))
print(f"signals written: {count}")
```

- 重み（weights）や閾値（threshold）はオプション引数で上書き可能
- Bear レジーム判定があり Bear 時は BUY を抑制
- SELL 判定ではストップロスやスコア低下をチェック
- signals も日付単位で置換（冪等）されます

---

## ニュース収集（RSS）

RSS フィードを取得して raw_news テーブルへ保存し、記事と銘柄コードの紐付けを行います。

例:
```
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- RSS の XML パースは defusedxml を使用して安全に処理
- URL 正規化、トラッキングパラメータ除去、SSRF 対策、受信サイズ制限 など安全策を実装
- raw_news と news_symbols に冪等挿入（ON CONFLICT DO NOTHING / RETURNING）を行います

---

## 市場カレンダー管理 / ユーティリティ

- is_trading_day(conn, d), next_trading_day, prev_trading_day, get_trading_days, is_sq_day などを提供
- カレンダーデータが未取得の場合は曜日ベースのフォールバック（平日=営業日）で判定

calendar_update_job で夜間バッチ更新を行えます。

---

## 監査ログ / 発注トレース

- audit モジュール（ddl）には signal_events, order_requests, executions 等の監査テーブル定義が含まれています。
- 監査用テーブルは init_schema で作成されます。発注〜約定のトレースに利用してください。

---

## 開発／テスト時の注意

- 環境変数の自動ロード: config モジュールはプロジェクトルートの `.env` / `.env.local` を自動読込します。テストでこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Python バージョンは 3.10 以上を推奨します（型注釈や union 構文を使用）。
- DB を壊したくない場合はテスト時に ":memory:" を使うか、別パスの DuckDB を使用してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得/保存ユーティリティ）
    - schema.py                       — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - news_collector.py               — RSS 取得・前処理・DB 保存
    - calendar_management.py          — 市場カレンダー ヘルパー / 更新ジョブ
    - features.py                     — zscore_normalize 再エクスポート
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログ用 DDL 定義
  - research/
    - __init__.py
    - factor_research.py              — momentum / volatility / value の計算
    - feature_exploration.py          — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py          — build_features
    - signal_generator.py             — generate_signals
  - execution/                         — 発注関連（空パッケージ / 実装は別途）
  - monitoring/                        — 監視 / メトリクス（空パッケージ / 実装は別途）

---

## 参考（よく使う API）

- DB 初期化: from kabusys.data.schema import init_schema
- 日次 ETL: from kabusys.data.pipeline import run_daily_etl
- 特徴量構築: from kabusys.strategy import build_features
- シグナル生成: from kabusys.strategy import generate_signals
- ニュース収集: from kabusys.data.news_collector import run_news_collection

---

必要であれば README を拡張して、CI 用の実行例、docker-compose 例、cron / Airflow 連携例、より詳しい環境変数ドキュメント（.env.example）などを追加します。どの情報を優先して追加しますか？