# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（データ収集・ETL、特徴量生成、シグナル生成、発注監査など）を想定した Python パッケージです。本リポジトリには DuckDB を用いたデータスキーマ、J-Quants API クライアント、RSS ニュース収集、研究用のファクター計算・探索、戦略の特徴量作成・シグナル生成ロジックなどが含まれます。

バージョン: 0.1.0

---

## 概要

主な目的は次の通りです。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存（差分更新・冪等保存）
- RSS ニュースの収集と記事 — 銘柄紐付け
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と特徴量正規化
- 戦略用スコア計算・BUY/SELL シグナル生成（冪等）
- 発注・約定・ポジション管理のためのスキーマと監査ログ設計
- カレンダー管理（営業日判定）・ETL パイプライン・品質チェックの基盤

設計上の特徴:
- DuckDB をデータ層に利用（高速なローカル分析）
- 冪等（ON CONFLICT/UPSERT）を重視した保存設計
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 外部ライブラリへの依存を限定（ただし duckdb / defusedxml 等は必要）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
  - pipeline: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定、calendar_update_job
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- research/
  - factor_research: モメンタム / ボラティリティ / バリューのファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリ
- strategy/
  - feature_engineering: research の raw factor を正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- config: 環境変数管理（.env/.env.local 自動読み込み、必須チェック）
- audit / execution / monitoring: 発注・監査・監視に関するスキーマ・骨組み（スキーマ定義内に含む）

---

## 前提・必須要件

- Python 3.9+
- duckdb
- defusedxml
- （ネットワーク経由で J-Quants API を使うため）インターネット接続
- J-Quants のリフレッシュトークン等の環境変数

推奨インストール例（仮の requirements）:
```
pip install duckdb defusedxml
```
（プロジェクト配布時は requirements.txt / pyproject.toml を用意してください）

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml を検索）を探し、`.env` → `.env.local` の順に環境変数をロードします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

オプション:
- KABUSYS_ENV: environment (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

注: Settings クラスで未設定の必須変数を参照すると ValueError を送出します。

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo>
```

2. 必要パッケージをインストール（例）
```
python -m pip install -r requirements.txt
# もしくは最小限
python -m pip install duckdb defusedxml
```

3. 環境変数を準備
- プロジェクトルートに `.env`（および任意で `.env.local`）を作成してください。
- 必須キー（例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
```

4. DuckDB スキーマの初期化（Python から）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
`:memory:` を渡すとインメモリ DB が使えます。

---

## 使い方（主要な操作の例）

以下は Python REPL / スクリプトでの利用例です。

- DuckDB 接続作成（初回はスキーマ初期化推奨）
```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")  # スキーマ作成 + 接続
# または既存 DB に接続するだけ:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- RSS ニュース収集（既知銘柄コードセットを与えて銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # など
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- 研究用ファクター計算（単独）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

- 特徴量生成（strategy レイヤ）→ features テーブルへ保存
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print("built features:", count)
```

- シグナル生成（features + ai_scores → signals テーブルへ）
```python
from datetime import date
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("generated signals:", n)
```

- schema / audit の利用
  - スキーマは init_schema で作成済みのため、orders / executions / signal_events 等は DB 上に存在します。
  - 発注フローや監査のためのユーティリティは audit・execution 配下に適宜実装していきます。

---

## ディレクトリ構成（抜粋）

以下は本コードベースの主要ファイル・モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集・DB 保存・銘柄抽出
    - calendar_management.py — 営業日判定・calendar_update_job
    - stats.py               — zscore_normalize 等
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログ用スキーマ DDL
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（フィルタ・正規化）
    - signal_generator.py    — final_score 計算とシグナル生成
  - execution/                — 発注層（空の __init__ 等）
  - monitoring/               — 監視関連（スキーマ、SQLite など）

注: 上記は実装済みの主要モジュールを抜粋しています。スキーマ定義は data/schema.py 内に詳細があります。

---

## 注意点 / 補足

- 設計は「データの冪等保存」「ターゲット日での計算（ルックアヘッド防止）」「トランザクションでの日付単位置換」を重視しています。実運用ではさらにエラーハンドリングやリソース管理（並列性・ロギング・モニタリング）を検討してください。
- J-Quants API の利用にはトークン管理（get_id_token が実装済み）があります。rate limit（120 req/min）を守るため内部で固定間隔のレート制御と指数バックオフを行います。
- news_collector は RSS の XML パースに defusedxml を利用し、SSRF や XML Bomb 対策が盛り込まれています。
- 本リポジトリは戦略ロジックや発注ロジックの「骨格」を提供します。実際の売買システムとして運用する場合は、安全性・監査・リスク管理の強化が必須です。

---

もし README に追加したい内容（例: サンプル .env.example、CI の設定方法、デプロイ手順、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記・調整します。