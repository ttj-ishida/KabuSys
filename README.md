# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ取得（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、DuckDB スキーマ・監査など、戦略研究および運用に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全）
- 外部依存を必要最小限に（標準ライブラリ + 一部必須パッケージ）
- 運用環境・研究環境を想定した設定管理と分離

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数から読み込み（自動ロード可 / 無効化フラグあり）
  - 必須環境変数のチェック（J-Quants / kabu / Slack 等）
- データ層（DuckDB）
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - raw_prices / raw_financials / raw_news / prices_daily / features / ai_scores / signals / orders / trades / positions 等のテーブル
- J-Quants API クライアント
  - 株価（日足）・財務データ・市場カレンダーの取得（ページネーション / レート制御 / リトライ / トークン自動リフレッシュ）
  - DuckDB への冪等保存（save_* 関数）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを含む日次 ETL（run_daily_etl 等）
- 特徴量エンジニアリング
  - research 層で計算した raw factor を正規化・合成し `features` テーブルへ保存（build_features）
- シグナル生成
  - features と ai_scores を統合し最終スコアを計算、BUY / SELL シグナルを `signals` テーブルへ保存（generate_signals）
  - Bear レジーム判定、ストップロス判定、SELL 優先ポリシー など
- ニュース収集
  - RSS フィードから記事取得、正規化、raw_news へ冪等登録、銘柄コード抽出（SSRF・XML bomb 対策あり）
- 研究ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Z スコア正規化など
- 監査・トレーサビリティ（audit）
  - signal_events / order_requests / executions 等で戦略から約定までを UUID で追跡

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントの | を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （実運用では）J-Quants API アクセス情報、kabu API、Slack トークンなどが必要

requirements.txt は含まれていませんが、開発環境では少なくとも次をインストールしてください：

```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# 開発時に editable install する場合
pip install -e .
```

---

## 環境変数（主なもの）

自動読み込み順序: OS 環境 > .env.local > .env  
（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）

必須（アプリ起動・一部機能で必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルト:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

.env の書式は Unix 風の KEY=VAL を想定し、export プレフィックスやクォート、インラインコメント等に対応しています。

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（duckdb, defusedxml など）
4. .env を作成（必須トークン等を設定）
5. DuckDB スキーマを初期化

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# （パッケージをプロジェクトとしてインストールする場合）
pip install -e .
```

.env の例（最低限）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

DuckDB スキーマ初期化（Python REPL またはスクリプト）:

```python
from kabusys.data.schema import init_schema, get_connection, settings
conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
# またはメモリ DB でテスト:
conn = init_schema(":memory:")
```

---

## 使い方（主要 API の例）

- 日次 ETL を実行してデータを取得・保存する:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量をビルドして `features` テーブルに保存する:

```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（features / ai_scores / positions を参照）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n_signals}")
```

- ニュース収集ジョブ（RSS）:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes に取引対象の銘柄リスト（set）を渡すとニュースと銘柄紐付けを行う
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- J-Quants の取得と保存（低レベル）:

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, recs)
print(f"saved {saved}")
```

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数を読み込む Settings オブジェクト（settings）
- kabusys.data.schema
  - init_schema / get_connection：DuckDB スキーマ初期化・接続取得
- kabusys.data.jquants_client
  - API によるデータ取得と DuckDB への保存ユーティリティ
- kabusys.data.pipeline
  - run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl
- kabusys.data.news_collector
  - RSS 取得・記事保存・銘柄抽出
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals

---

## ディレクトリ構成（主要ファイル）

リポジトリのルートは pyproject.toml/.git を基準に自動検出されます。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - schema.py
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他 data 関連モジュール)
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
      # （execution 層の実装ファイル）
    - monitoring/
      # （監視 / アラート 関連の実装、__all__ に含まれる）
- .env.example (想定)
- pyproject.toml / setup.cfg 等（プロジェクトメタ情報）

各サブパッケージは責務ごとに分離されており、研究（research）用ユーティリティは本番の発注層や外部 API への直接アクセスを行わない設計になっています。

---

## 運用上の注意

- 環境変数や API トークンは厳重に管理してください（特に本番環境では KABUSYS_ENV=live を使用）。
- DuckDB ファイルはバックアップを適宜取得してください。
- J-Quants の API レート制限（120 req/min）に従う設計になっていますが、運用時は API 利用状況に注意してください。
- news_collector には SSRF / XML Flood 対策を実装していますが、外部 RSS ソースの取り扱いは慎重に行ってください。
- schema の DDL は外部キー制約の一部を DB 側でサポートされないため（DuckDB バージョン差異）、アプリ側での整合性管理が必要な箇所があります（README 内コメント参照）。

---

## テスト / 開発

- 単体テストや CI を導入する場合、`.env` の自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して環境を固定することが推奨されます。
- DuckDB のインメモリモード（":memory:"）を使うとテストが簡単になります。

---

この README はコードベースの主要部分を要約しています。詳細な仕様（StrategyModel.md / DataPlatform.md など）が別途ある想定です。実装詳細やパラメータ設計はソースの docstring を参照してください。