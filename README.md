# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants API や RSS を利用したデータ収集、DuckDB を用いたスキーマ管理、特徴量作成、シグナル生成、実行履歴（監査）管理などを提供します。

> 本 README はコードベース（src/kabusys/...）を元にした概要・セットアップ・使い方ドキュメントです。

---

## プロジェクト概要

KabuSys は以下の層を備えた日本株の自動売買プラットフォーム向けコンポーネント群です。

- Data 層（J-Quants から株価・財務・カレンダーを取得、RSS ニュース収集）
- DuckDB によるスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- Research 層（ファクター計算・特徴量探索）
- Strategy 層（特徴量正規化、最終スコア計算、BUY/SELL シグナル生成）
- Execution / Audit 層（シグナル→注文→約定 の追跡と監査）

設計上の特徴:
- 冪等（idempotent）な DB 保存（ON CONFLICT 等）
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- 外部 I/O に対する安全対策（RSS の SSRF 防止、XML 脆弱性対策など）
- 最低限の外部依存で標準ライブラリ＋ DuckDB／defusedxml を想定

---

## 機能一覧

主な機能（モジュール単位）:

- kabusys.config
  - .env または環境変数から設定を自動読み込み（プロジェクトルート基準）
  - 必須設定チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、再試行、レート制限、トークン自動更新）
  - news_collector: RSS 取得・正規化・DB 保存、銘柄抽出（SSRF/サイズ制限/トラッキング除去）
  - schema: DuckDB のスキーマ定義と初期化（init_schema）
  - pipeline: 日次 ETL の実装（差分取得 / 保存 / 品質チェック）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Zスコア正規化等の統計ユーティリティ
- kabusys.research
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）等
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を合成して BUY/SELL を生成
- 実行・監査用のスキーマ（orders/executions/positions/signal_events/order_requests 等）

---

## 必要な環境 / 依存

- Python 3.10+（typing の一部表記を利用）
- 必須パッケージ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime 等）を使用

実際のプロジェクトでは `pyproject.toml` / `requirements.txt` を用意して依存を固定してください。

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

3. パッケージとして開発インストール（リポジトリルートに pyproject.toml がある想定）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config の自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（コード上で _require を用いているもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/... （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
例（.env の一部）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## データベース初期化

DuckDB のスキーマを作成するには `kabusys.data.schema.init_schema` を使用します。

Python 例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
# conn を使って以降の処理を実行
```

- ":memory:" を渡すことでインメモリ DB を利用できます（テスト等）。
- parent ディレクトリが無ければ自動で作成されます。

---

## 使い方（主要ワークフローの例）

以下は基本的な ETL → 特徴量作成 → シグナル生成 の流れ例です。

1) ETL（日次データ取得）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量作成（features テーブルに保存）

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

3) シグナル生成（signals テーブルに保存）

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generated signals: {count}")
```

4) ニュース収集（RSS -> raw_news, news_symbols）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄抽出に使う有効コードの集合（例: 全上場銘柄のコードセット）
res = run_news_collection(conn, sources=None, known_codes={'7203', '6758'})
print(res)
```

5) J-Quants の ID トークン取得（必要な時）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用してトークンを取得
```

注意点:
- 各処理は target_date 時点のデータのみを参照しており、ルックアヘッドを防ぐ設計です。
- ETL / 保存関数は冪等に実装されています（複数回実行しても上書き・重複排除されることを意図）。

---

## ローカル開発でのヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト時に自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb`。バックアップやバージョン管理は運用ポリシーに従ってください。
- RSS の取得は外部ネットワークに依存するため、テストでは `kabusys.data.news_collector._urlopen` をモックすることが想定されています。
- J-Quants API 呼び出しはレート制限・リトライロジックを備えていますが、本番運用ではトークンの安全な管理（シークレット管理）を行ってください。
- ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得/保存）
    - news_collector.py             — RSS 収集・正規化・DB保存
    - schema.py                     — DuckDB スキーマ定義 & init_schema
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   — 日次 ETL パイプライン
    - calendar_management.py        — 市場カレンダー管理
    - audit.py                      — 監査ログ用スキーマ初期化
    - features.py                   — features の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py        — ファクター正規化・features への書込み
    - signal_generator.py           — final_score 計算と signals 書込み
  - execution/                       — 発注周り（ディレクトリは存在する想定）
  - monitoring/                      — 監視・アラート用（ディレクトリは存在する想定）

（実ファイルは src/kabusys 以下を参照してください）

---

## 開発 / 貢献

- バグ修正や機能追加はプルリクエストで受け付けます。テストカバレッジを維持するためユニットテストを追加してください。
- 外部 API キーや機密情報はリポジトリにコミットしないでください。`.env.example` を用意して実運用側で設定してください。

---

この README はコードベースのドキュメント生成を目的としており、詳細設計（StrategyModel.md, DataPlatform.md 等）はコード内コメント・別ドキュメントを参照してください。質問や追加ドキュメントの要望があれば教えてください。