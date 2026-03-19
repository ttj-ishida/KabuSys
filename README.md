# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB を用いたデータレイク、J-Quants API からのデータ収集、特徴量生成・シグナル作成、ニュース収集、監査ログなどをワンパッケージで提供します。

主な設計方針
- ルックアヘッドバイアス防止（対象日までのデータのみを利用）
- 冪等性（DB 保存は ON CONFLICT で上書き・重複排除）
- テスト容易性（トークン注入、auto env load の無効化オプション等）
- 外部依存は最小限（標準ライブラリ中心、必要なパッケージは明記）

---

## 機能一覧

- 環境・設定管理
  - .env 自動読み込み（プロジェクトルートを検出）と必須環境変数取得（kabusys.config.Settings）
- データ取得／保存（J-Quants）
  - 株価日足、財務データ、JPX マーケットカレンダーの取得（jquants_client）
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
  - レート制限・リトライ・トークン自動更新対応
- ETL パイプライン
  - 差分取得・バックフィル、品質チェック、日次 ETL 実行（data.pipeline.run_daily_etl）
- スキーマ管理
  - DuckDB スキーマ定義および初期化（data.schema.init_schema）
- 特徴量エンジニアリング / 研究
  - モメンタム／ボラティリティ／バリュー等のファクター計算（research.factor_research）
  - 将来リターン、IC、統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats）
- シグナル生成
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成（strategy.signal_generator）
  - 保有ポジションのエグジット判定（ストップロス等）
- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出（data.news_collector）
  - SSRF/サイズ制限/XML 安全処理等の堅牢化
- カレンダー管理
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ（data.calendar_management）
- 監査（Audit）
  - signal → order → execution のトレーサビリティ（data.audit）
- 実行層プレースホルダ
  - execution パッケージ（発注等は個別実装向け）

---

## 必要条件

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリのみで動作する部分も多いですが、実運用・ETL では上記をインストールしてください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

※ パッケージ化される場合は requirements.txt / extras を用意してください。

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトルートへ移動

2. 仮想環境作成・有効化（上記参照）

3. 依存インストール
   - pip install duckdb defusedxml
   - （任意）ローカル開発用に linters やテストフレームワークを追加

4. 環境変数設定
   - プロジェクトルートに `.env` を配置するか、OS 環境変数で設定
   - 自動ロードはデフォルトで有効。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

5. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # または init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要 API とサンプル）

以下はライブラリをインポートして使う際の代表例です。

- 日次 ETL（市場カレンダー・株価・財務データの差分 ETL と品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定すれば任意日を処理
print(result.to_dict())
```

- 特徴量生成（features テーブル作成）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 6))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブル作成）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 6), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar entries saved: {saved}")
```

注意点:
- J-Quants API を使う関数はトークンが必要です（settings.jquants_refresh_token）。
- ETL / API 呼び出しはネットワーク・レート制限に依存します（内部で制御あり）。
- 実運用での発注（kabu API 等）は execution 層の実装が必要です（サンプルコードは含まれていません）。

---

## 環境変数一覧（重要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注実装時）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知実装時）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境 (development | paper_trading | live)、デフォルト `development`
- LOG_LEVEL — ログレベル (DEBUG/INFO/...), デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス、デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — 監視用 SQLite パス、デフォルト `data/monitoring.db`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする場合は `1` を設定

---

## ディレクトリ構成

主要モジュール・ファイルの概要（リポジトリ内 `src/kabusys/` を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数自動ロード、Settings クラス（必須 env の取得）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 / レート制御 / リトライ）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン、差分取得ロジック、run_daily_etl 等
    - features.py
      - data.stats の再エクスポート（互換性用）
    - calendar_management.py
      - market_calendar 管理・営業日判定・更新ジョブ
    - audit.py
      - 監査テーブル定義 / 初期化（signal_events, order_requests, executions 等）
    - (その他: quality モジュール等が別ファイルに想定される)
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - raw ファクターから features テーブルを作成（Zスコア正規化・フィルタ）
    - signal_generator.py
      - features + ai_scores を使い final_score を算出、signinls テーブルへ書き込み
  - execution/
    - __init__.py
    - （発注／ブローカー連携の実装は各運用環境で追加）
  - monitoring/
    - （監視・アラート用コードを配置する想定）

---

## 開発・運用上の注意

- データ整合性
  - DuckDB のスキーマには CHECK 制約や PRIMARY KEY が多く定義されています。ETL 実行前にスキーマを初期化してください。
- テスト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env 自動ロードを無効にでき、テストで環境を分離しやすくなります。
- ロギング
  - settings.log_level を参照してアプリ側で logging.basicConfig(level=...) を設定してください。
- セキュリティ
  - news_collector は SSRF 対策や XML 安全対策を組み込んでいますが、運用環境ではプロキシやネットワーク制御も併用してください。
- 実運用での発注
  - 本コードベースは戦略生成・シグナル作成までを提供します。実際の発注・ブローカー連携は execution 層の実装・検証が必須です（リスク管理・冪等性に注意）。

---

## 付録：よく使うサンプルコマンド

- Python REPL でスキーマ作成 & ETL 実行
```bash
python - <<'PY'
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
res = run_daily_etl(conn)
print(res.to_dict())
PY
```

---

README に書かれている API や挙動はソースコードコメント（各モジュールの docstring）に詳細に記載されています。必要に応じて各モジュールの docstring を参照して実装やパラメータの意味を確認してください。質問や追加したい使用例があれば教えてください。