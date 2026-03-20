# KabuSys

日本株向けの自動売買システム基盤ライブラリ（KabuSys）のリポジトリ用 README。

このリポジトリはデータ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含む一連の処理を提供します。ライブラリとして戦略実行や発注層（execution）と連携するための基盤機能を備えています。

## 主要な特徴（概要）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック連携）
- 特徴量エンジニアリング（研究モジュールからの生ファクターを正規化して features テーブルへ保存）
- シグナル生成（features + AIスコアから final_score を計算し signals テーブルへ保存、BUY/SELLロジック）
- ニュース収集（RSS → raw_news、記事正規化・SSRF 対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 監査ログ用スキーマ（signal → order → execution をトレースする DDL）
- 汎用統計ユーティリティ（Z スコア正規化など）
- 環境変数 / .env の自動読み込み（プロジェクトルート判定）

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 必須環境変数のラップ（settings オブジェクトでアクセス）
- kabusys.data
  - jquants_client: J-Quants API クライアント、fetch/save の実装（株価・財務・カレンダー）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl など）
  - news_collector: RSS 収集、記事前処理、DB 保存、銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ用 DDL 定義
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、要約統計など
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターを正規化し features テーブルへ保存
  - signal_generator.generate_signals: features＋ai_scores から BUY/SELL シグナルを作成
- kabusys.execution / kabusys.monitoring
  - （execution と monitoring はパッケージ階層を用意、発注層やモニタリング機能を実装する場所）

---

## 必要条件
- Python >= 3.10（型ヒントの | 合成等を使用）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- （その他のランタイム依存は環境により異なります。requirements.txt がある場合はそちらを参照してください。）

---

## 環境変数（主なもの）
このライブラリは環境変数で設定を読み込みます。必須のものは実行時に settings が参照して ValueError を投げます。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — 通知先チャンネルID

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

.env ファイルがプロジェクトルート（.git または pyproject.toml を起点に探索）にあれば、自動的に読み込まれます。
自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。

---

## セットアップ手順（ローカル開発向けの基本）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. .env を用意
   - プロジェクトルートに .env を作成し、必要な環境変数を設定します（上記必須項目）。
   - 例:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマを初期化
   - Python から直接:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - これにより data/kabusys.duckdb が作成され、DDL が実行されます。

5. （任意）開発用パッケージインストール
   - pip install -e .

---

## 使い方（主要なサンプル）
以下はライブラリを直接インポートして使う際の簡単な例です。実運用では別スクリプトや airflow / Cron などでジョブ化してください。

- DuckDB 初期化（1回）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL（市場カレンダー、株価、財務の差分取得）を走らせる
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日が使われます
print(result.to_dict())
```

- 特徴量の作成（build_features）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2024, 3, 1))
print(f"features upserted: {n}")
```

- シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 3, 1))
print(f"signals generated: {count}")
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー先読みジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 重要な設計ノート / 注意点
- ルックアヘッドバイアス防止:
  - 戦略・特徴量計算は target_date 時点のデータのみを使用する設計です（未来データ混入防止）。
  - J-Quants から取得したデータは fetched_at を付与して「いつデータを知り得たか」を追跡します。
- 冪等性:
  - J-Quants 保存系関数は ON CONFLICT DO UPDATE/DO NOTHING を利用して冪等性を確保しています。
  - ETL や features / signals 挿入は日付単位の DELETE→INSERT をトランザクションで行い、日次置換を実現します。
- セキュリティ:
  - news_collector は SSRF 対策、XML パーサは defusedxml を利用、レスポンスサイズ上限のチェック等を行います。
  - J-Quants クライアントはレート制御、リトライ、401 のトークンリフレッシュを実装しています。
- 環境変数の自動ロード:
  - config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます。テスト時などでこれを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）
リポジトリは src/kabusys 以下にパッケージを配置しています。主要ファイルを列挙します。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / settings
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - stats.py
    - features.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/         — 発注・ブローカー連携を実装するためのパッケージ（空／未実装の初期化）
  - monitoring/        — モニタリング関連（スキーマや実装を配置する想定）

（詳しいモジュール説明は本 README の「機能一覧」を参照してください。）

---

## 開発・運用時のヒント
- 初回ロードは大量のデータを取得する可能性があります（backfill 等）。時間・API レート制限に注意してください。
- DuckDB ファイルやログ、Slack トークンなどの秘密情報は適切に管理してください（.env を Git に含めない等）。
- strategy と research の関数は DuckDB 接続を受け取る純粋関数的インターフェースになっているため、テストしやすくなっています。ユニットテスト時には :memory: の DuckDB を使うと便利です。
- 実運用（本番 live）での注文実行は十分な安全対策（注文量制限、ドローダウン制限、監査ログ）を追加してください。

---

もし README に加えたい具体的な使用シナリオ（例: Airflow でのジョブ定義、cron スクリプト例、Docker イメージのビルド手順など）があれば教えてください。必要に応じて追記・具体化します。