# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ収集（J-Quants）、ETL パイプライン、ファクター計算、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ・監査など、戦略・実行層の基盤機能を提供します。

バージョン: src/kabusys/__init__.py の __version__ = 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存
- ETL（差分更新・バックフィル）と品質チェック
- ファクター計算（モメンタム／バリュー／ボラティリティ等）
- クロスセクション Z スコア正規化による特徴量生成（features テーブル）
- 特徴量と AI スコアを統合した売買シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理、監査ログ、発注/約定管理のスキーマ定義

設計上のポイント:
- ルックアヘッドバイアスの回避（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全化）
- 外部依存（DuckDB / defusedxml 等）を限定してテストしやすく実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（prices / financials / calendar）と差分取得ロジック
  - schema: DuckDB スキーマ初期化（raw / processed / feature / execution 層）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定／カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: mom/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）等の解析ユーティリティ
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL を生成
- config:
  - 環境変数管理（.env 自動ロード、必須チェック、環境モード判定）
- monitoring / execution / audit:
  - 監査ログ・発注/約定・ポジション等のスキーマと補助機能（初期化/保存ロジックは各モジュールに含まれます）

---

## 必要条件

- Python 3.8+
- 主要依存パッケージ（例）:
  - duckdb
  - defusedxml

実運用ではネットワークアクセス（J-Quants API、RSS）と DuckDB 書き込み権限が必要です。

example:
pip install duckdb defusedxml

プロジェクトをパッケージとして使う場合は setup / pyproject に従ってインストールしてください（ここでは src/ 配下を想定）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリ>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （ローカルで開発する場合）pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参照してください）
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - 任意 / 既定値:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH : DuckDB 保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite（デフォルト: data/monitoring.db）
   - 自動 .env ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行:
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作成

---

## 環境変数（まとめ）

必須（実行する処理によって変わる可能性があります）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション／既定値あり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化

config.py の Settings で追加設定が必要な場合があります。

---

## 使い方（よく使うワークフロー例）

以下は最小限の利用例です。実運用ではログや例外ハンドリング、スケジューラ（cron / Airflow 等）と組み合わせてください。

1) DB の初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants から差分取得して保存）
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の構築（features テーブルの作成）
```
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"upserted features: {n}")
```

4) シグナル生成
```
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today())
print(f"signals written: {total}")
```

5) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は既知銘柄コードのセット（抽出品質向上のため推奨）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

6) カレンダー更新ジョブ
```
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

---

## 実装上の注意点 / 運用メモ

- リトライやレート制御:
  - jquants_client は 120 req/min のレート制御、指数バックオフ、401 時のトークン自動更新を実装しています。
- 冪等性:
  - raw テーブル保存は ON CONFLICT DO UPDATE / DO NOTHING を使って重複保存を回避します。
- ルックアヘッド対策:
  - 特徴量生成/シグナル生成は target_date 時点までの情報のみを参照することでルックアヘッドバイアスを避けています。
- テスト:
  - config の自動 .env 読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト環境構築が容易です。
- DuckDB のファイルパスは Settings.duckdb_path で管理されます。運用上は永続ボリューム・バックアップを検討してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - schema.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - features.py
  - audit.py
  - (その他: quality, etc. が想定される)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py
- monitoring/
  - (監視/モニタリング用モジュール群)

上記以外にも補助モジュール（logging 設定、Slack 通知等）をプロジェクトに組み込むことが想定されます。

---

## 開発 / 貢献

- コーディング規約: 型ヒントを活用し、明確な例外処理とログ出力を行ってください。
- テスト: データ取得やネットワーク依存部分はモック化し単体テストを実施してください（例: _urlopen をモック、jquants_client の HTTP 呼び出しを差し替え）。
- ドキュメント: StrategyModel.md / DataPlatform.md 等の仕様書と実装の整合性を確認の上、変更時に更新してください。

---

この README はコードベース（src/kabusys 配下）の現状実装に基づいて作成しています。具体的な API キーや .env.example、CI/CD の設定、運用 runbook（ジョブスケジューリングやアラート設定）は別途プロジェクト固有の運用ドキュメントを用意してください。