# KabuSys

日本株向けの自動売買システム向けライブラリ（ライブラリ的モノリポジトリ）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、監査ログ／実行層のスキーマ定義などを含みます。

---

## 概要

KabuSys は日本株の自動売買パイプラインを構成するためのモジュール群です。主な目的は以下：

- J-Quants API から日次データ・財務データ・マーケットカレンダーを取得して DuckDB に保存する（差分ETL・再取得（backfill）対応）
- 研究環境で計算した生ファクターを正規化・合成して特徴量テーブルを作成
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- RSS を使ったニュース収集と記事→銘柄紐付け
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day など）
- DuckDB 上のスキーマ（Raw / Processed / Feature / Execution / Audit）の初期化

設計上のポイント：
- ルックアヘッドバイアスを防ぐため、常に target_date 時点のデータのみを参照
- DuckDB を主データストアとして使用（軽量かつ SQL によるバッチ処理に適合）
- 冪等性を考慮した保存（ON CONFLICT/UPSERT、トランザクション）
- J-Quants クライアントはレート制御・リトライ・トークン自動リフレッシュを実装

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（fetch/save の一連）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（prices/financials/calendar）
  - schema: DuckDB スキーマ定義と init_schema()
  - news_collector: RSS 取得・正規化・保存・銘柄抽出
  - calendar_management: 営業日判定／更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー
- strategy
  - feature_engineering.build_features: 生ファクターから features テーブルを作成
  - signal_generator.generate_signals: features/ai_scores/positions から signals を生成
- audit / execution / monitoring
  - スキーマ／監査ログに関連する DDL が含まれる（orders, executions, positions, signal_events など）

---

## 必要要件

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- （その他）標準ライブラリのみで実装されている箇所も多いですが、実行環境に応じて追加パッケージが必要になる場合があります。

インストール例（最小）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ化されていれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境の作成・有効化
3. 依存パッケージをインストール（duckdb と defusedxml など）
4. 環境変数を設定（.env をルートに置くと自動読み込みされます。自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

必須環境変数（config.py にて必須とされるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（execution 層を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル

任意 / 既定値あり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL — one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）

.env 例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードについて:
- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動的に読み込みます。
- テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## DB の初期化

DuckDB スキーマを作成するには次を実行します：

Python REPL / スクリプト例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

db_path = settings.duckdb_path  # 環境変数に従う
conn = init_schema(db_path)     # テーブルが存在しなければ作成して接続を返す
```

メモリ DB を使う場合:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

既存 DB に接続するだけの場合は get_connection() を使ってください（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("/path/to/kabusys.duckdb")
```

---

## 使い方（クイックスタート）

以下は主要なワークフローの最小例です。

1) 日次 ETL（J-Quants からデータ取得→保存→品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を None（今日）にすると今日基準で実行
print(result.to_dict())
```

2) 特徴量作成（research の生ファクターを正規化して features テーブルに保存）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 20))
print(f"features upserted: {n}")
```

3) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 3, 20))
print(f"signals generated: {count}")
```

4) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（抽出で使用）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # 各ソースごとの新規保存件数
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 開発・実装上の注意点

- jquants_client:
  - レート制限（120 req/min）をモジュール内で制御。連続で大量リクエストを投げない設計になっています。
  - HTTP 408/429/5xx に対して指数バックオフで自動リトライを行います。401 が来た場合はリフレッシュトークンで ID トークンを自動更新して再試行します。
- ETL pipeline:
  - 差分取得と backfill（後出し修正吸収） をサポート。
  - 品質チェックは失敗しても他処理を止めない（呼び出し元で結果を確認して対応）。
- ニュース収集:
  - RSS の XML を defusedxml で安全にパースし、SSRF 対策や受信サイズ制限を実装。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性を担保。
- 環境（KABUSYS_ENV）:
  - 有効値は development / paper_trading / live。live 時は実際の発注等に注意。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings
- data/
  - __init__.py
  - schema.py                      — DuckDB スキーマ定義・init_schema
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - news_collector.py              — RSS 収集・保存・銘柄抽出
  - calendar_management.py         — マーケットカレンダー管理 / ジョブ
  - features.py                    — zscore_normalize のエクスポート
  - stats.py                       — 統計ユーティリティ
  - audit.py                       — 監査テーブルの DDL
- research/
  - __init__.py
  - factor_research.py             — momentum/volatility/value の計算
  - feature_exploration.py         — forward returns, IC, summary
- strategy/
  - __init__.py
  - feature_engineering.py         — features テーブルの構築
  - signal_generator.py            — final_score 計算と signals 生成
- execution/                        — 発注/実行に関するモジュール（空の __init__ 等）
- monitoring/                       — 監視・メトリクス等（存在する場合）

（実際のプロジェクト本文書に依存します。上記はコード内の主なモジュールを抜粋した構成です。）

---

## よくある運用フロー（例）

1. 環境変数をセットして DuckDB を初期化（init_schema）
2. 夜間バッチで run_daily_etl を実行（カレンダー・株価・財務を差分取得）
3. feature_engineering.build_features を実行して features を更新
4. generate_signals でシグナルを作成
5. execution 層（別モジュール）で signals を受け取り注文を出し、orders/executions を記録
6. audit テーブルでトレース

---

## 貢献・拡張

- ファクターやシグナルロジックは research/ と strategy/ に分離されています。新しいファクターや別のシグナリング手法はこれらのモジュールを拡張してください。
- DuckDB のスキーマは schema.py に集約されています。テーブル追加やカラム変更はここに反映してマイグレーション手順を別途用意してください。
- J-Quants API のエンドポイント追加は jquants_client.py に実装し、対応する save_* を実装して schema にテーブルを追加してください。

---

必要であれば README にコマンドラインツール例や systemd / cron ジョブの例（run_daily_etl を定期実行するための起動スクリプト）も追加できます。どの程度の運用例（cron/airflow/kubernetes/worker構成）を含めるか指定してください。