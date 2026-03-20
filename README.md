# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査用スキーマ等を含むモジュール群を提供します。

注意: 本リポジトリはライブラリ／バッチ処理のコア部分であり、ブローカー送信や運用時のジョブスケジューラ等は別実装を想定しています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API から株価・財務・カレンダーを取得し DuckDB に保存する ETL（差分更新・バックフィル対応）
- RSS ベースのニュース収集と銘柄紐付け
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）とクロスセクション正規化
- 戦略用特徴量の構築（features テーブルへの保存）
- シグナル生成（final_score 計算、BUY/SELL 生成、エグジット判定）
- DuckDB のスキーマ定義および監査テーブル（トレーサビリティ）
- カレンダー管理（営業日判定、next/prev_trading_day など）
- 設定管理（環境変数 / .env 自動読み込み）

設計方針として、「ルックアヘッドバイアス防止」「冪等性（idempotent）」「外部サービスへの過度な依存を排する」ことを重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からのページネーション取得、トークン自動リフレッシュ、保存用ユーティリティ
  - pipeline: 日次 ETL（差分取得・バックフィル・品質チェック）と個別ジョブ
  - schema: DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 収集、前処理、raw_news への冪等保存、銘柄抽出と紐付け
  - calendar_management: JPX カレンダーの更新・営業日判定
  - stats / features: Z スコア正規化などの統計ユーティリティ
  - audit: 監査ログ用テーブル定義（シグナル→発注→約定のトレース）
- research/
  - factor_research: モメンタム・ボラティリティ・バリューのファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー
- strategy/
  - feature_engineering: research 側で算出した raw factor を正規化・フィルタして features テーブルを作成
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルに保存
- config:
  - 環境変数管理（自動 .env ロード、必須項目チェック、環境・ログレベル判定）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing | union 表記等の利用に合わせ適宜）
- DuckDB を使用（Python パッケージ duckdb）
- defusedxml（ニュース収集で使用）

1. リポジトリをクローン / カレント環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   ※プロジェクトに requirements ファイルがある場合はそちらを使用してください。

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定
   必須環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実運用で使用する場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
   オプション:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   .env / .env.local をプロジェクトルートに置くと自動で読み込まれます。
   自動ロードを無効化する場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベーススキーマ初期化
   Python から init_schema を呼ぶことで DuckDB にテーブルを作成します（:memory: も可）。

   例:
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（主要 API と実行例）

以下は簡単な Python スクリプト例です。プロダクションではジョブスケジューラ（cron, systemd, Airflow など）で定期実行してください。

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants から取得 → 保存 → 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

5) RSS ニュース収集と DB 保存

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {'7203', '6758', ...}）
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)  # {source_name: saved_count}
```

6) カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

注意点:
- 各 API は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。init_schema は接続を返しますが、既存 DB に接続する場合は get_connection を使ってください。
- jquants_client の API 呼び出しは rate limit とリトライ・トークンリフレッシュを内蔵していますが、ID トークンの環境変数設定は必須です。
- ETL の差分ロジックやバックフィルは pipeline のデフォルトで実行されます。パラメータで調整可能です。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知連携)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化

config.Settings クラスから各設定へアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - calendar_management.py
  - features.py
  - stats.py
  - audit.py
  - (その他: quality.py 等を想定)
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
- monitoring/ (パッケージとしてエクスポート対象にある想定)

各モジュールの役割は上記「主な機能一覧」を参照してください。

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアスに注意: ファクター計算・シグナル生成は target_date 時点までのデータのみを用いる設計ですが、運用側でもデータタイミングに注意してください。
- DuckDB ファイルは定期的にバックアップしてください（単一ファイルで管理されます）。
- ETL とシグナル生成は idempotent（冪等）を意識しているため、過去日再実行が可能です。ただし DB スキーマや外部ステートに変更がある場合は注意してください。
- news_collector は外部 HTTP を利用します。SSRF 対策など複数の安全策が組み込まれていますが、運用環境のプロキシ・ネットワーク設定との整合性を確認してください。

---

もし README に追加したい内容（例: テスト方法、CI 設定、より詳細な API ドキュメント、サンプルデータの生成スクリプト等）があれば教えてください。必要に応じてサンプル .env.example も作成します。