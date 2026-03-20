# KabuSys

日本株向けの自動売買 / データパイプライン基盤。J-Quants から市場データを取得して DuckDB に保存し、リサーチ -> 特徴量生成 -> シグナル生成 -> 発注監査に繋ぐためのモジュール群を提供します。

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成される日本株自動売買基盤です：

- Data（取得・保存）: J-Quants API から株価・財務・カレンダー・ニュースを取得し、DuckDB に冪等保存
- Research（因子計算）: prices_daily / raw_financials を元にモメンタム・ボラティリティ・バリュー等のファクターを計算
- Strategy（特徴量・シグナル）: ファクターを正規化・合成して BUY/SELL シグナルを生成
- Execution / Monitoring: 発注・約定・ポジション・監査ログ（スキーマ、ユーティリティを含む）

設計上の要点：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- DuckDB を中心としたローカル DB 構成（インメモリ or ファイル）
- 冪等性（API 保存は ON CONFLICT で上書き or スキップ）
- ネットワーク安全性（RSS の SSRF 防止、J-Quants のレート制御・リトライ）

---

## 主な機能一覧

- J-Quants API クライアント（取得・リトライ・トークン自動リフレッシュ・レート制御）
  - 日次株価（OHLCV）取得 / 財務データ取得 / 市場カレンダー取得
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェックのフロー）
- モメンタム / ボラティリティ / バリュー等のファクター計算（research モジュール）
- Zスコア正規化ユーティリティ
- 特徴量作成（features テーブルへのアップサート、ユニバースフィルタ）
- シグナル生成（final_score 計算、BUY/SELL の判定、signals テーブルへ保存）
- ニュース収集（RSS フィード取得、前処理、raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions 等のテーブル定義）

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装されている部分も多いですが、実行時に上記パッケージが必要になります。

例（pip）:
pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトがパッケージ化されていれば pip install -e . などを利用）

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（少なくとも実行上必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（execution を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / ...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

   簡易の .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - 以下のように Python REPL やスクリプトで実行します（デフォルトのファイルパスは settings.duckdb_path）:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化
   ```

---

## 使い方（主要なワークフロー例）

以下は典型的な運用フローの簡易サンプルです。各関数は DuckDB の接続オブジェクト（duckdb.connect が返す接続）を受け取ります。

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 の差分取得）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に処理
print(result.to_dict())
```

- 特徴量（features）作成
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date(2024, 1, 10))
print("upserted features:", n)
```

- シグナル生成
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date(2024, 1, 10))
print("signals generated:", count)
```

- ニュース収集（RSS）と保存
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection(settings.duckdb_path)
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})  # sources None => デフォルト
print(results)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意：
- J-Quants API にはレート制限（120 req/min）があり、クライアントで固定間隔のスロットリングを行います。
- ETL やデータ取得はネットワークや API の制約により失敗することがあります。例外やログに注意して運用してください。

---

## 主要モジュール（簡易説明）

- kabusys.config
  - .env / 環境変数読み込み、Settings クラス（settings）で各種設定を取得
- kabusys.data
  - jquants_client: J-Quants API 用クライアント（取得＋保存用ユーティリティ）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: ETL ジョブ（run_daily_etl 等）
  - news_collector: RSS 取得と raw_news / news_symbols への保存
  - calendar_management: market_calendar の管理・営業日判定ユーティリティ
  - stats / features: 統計・正規化ユーティリティ
- kabusys.research
  - factor_research: mom/vol/val 等のファクター計算
  - feature_exploration: IC / 将来リターン計算 / サマリー
- kabusys.strategy
  - feature_engineering.build_features
  - signal_generator.generate_signals
- kabusys.execution
  - （今後発注関連ロジックを配置）
- kabusys.monitoring
  - （監視・メトリクス関連。現状はパッケージ構成に含めています）

---

## ディレクトリ構成（src 配下の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - features.py
    - stats.py
    - pipeline.py
    - (その他 data モジュール)
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
    - (監視用モジュール)

（上記は主要ファイルを抜粋した構成です。実際のファイル群はリポジトリをご確認ください）

---

## 運用上の注意 / トラブルシューティング

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。CI 等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスは settings.duckdb_path で指定可能。":memory:" を渡すとインメモリ DB を使えます（テスト用途）。
- J-Quants へのリクエストで 401 が発生した場合、自動でリフレッシュトークンを用いたトークン更新を試行します（1 回のみリトライ）。
- RSS の取得は SSRF 対策・サイズ制限・gzip 解凍制御等を実装していますが、外部フィードによってはパースできない場合があります。ログを参照してください。
- シグナル生成は features / ai_scores / positions 等の DB テーブルに依存します。スクリプト順序（ETL → build_features → generate_signals）を守ってください。

---

必要であれば、README に以下を追加できます：
- 具体的な SQL スキーマの説明（テーブルごとのカラム定義）
- CI / デプロイ手順（systemd / cron / Airflow の例）
- サンプルデータを用いたハンズオン手順
- ロギング / モニタリング設定例

追加してほしい項目があれば教えてください。