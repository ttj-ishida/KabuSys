# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、日本株向けのデータ基盤・特徴量エンジニアリング・シグナル生成・ETL・監査機能を備えた内部ライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API / RSS ニュース / kabu ステーション等と連携する設計になっています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の層を含む、トレーディングシステムのコア機能を提供します。

- データ収集（J-Quants API 経由の株価・財務・カレンダー取得／RSS ニュース収集）
- ETL（差分取得、冪等保存、品質チェック）
- 研究（ファクター計算 / 将来リターン / IC 計測）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合による買い／売りシグナル）
- スキーマ定義・監査ログ（DuckDB 上のテーブル群）
- カレンダー管理・ニュースの銘柄紐付け・発注監査など

設計上、発注実行（ブローカーへの実際の送信）は execution 層で分離されており、特徴量・シグナル生成モジュールは発注 API に直接依存しないように作られています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - RSS ニュース収集（SSRF 対策・トラッキング除去・記事ID生成・銘柄抽出）
  - マーケットカレンダー管理（営業日判定など）
  - 統計ユーティリティ（Z スコア正規化など）
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- strategy
  - 特徴量生成（build_features: raw ファクターを正規化して `features` テーブルに保存）
  - シグナル生成（generate_signals: features と ai_scores を統合して BUY/SELL を生成）
- audit / execution（スキーマ・監査テーブル）：発注→約定のトレーサビリティを想定

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型表記（|）や typing の仕様に依存）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装していますが、実運用では追加の依存（Slack SDK、HTTP クライアント等）を組み合わせることが想定されます。

requirements.txt を用意している場合はそれを使ってください。最低限のインストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 他に必要なライブラリがあれば追加で pip install してください
```

---

## 環境変数 / 設定

KabuSys は .env ファイル（プロジェクトルート）や環境変数から設定を自動読込します（CWD に依存せず、パッケージの配置位置からプロジェクトルートを探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に利用する環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.example の .env ファイル（README 用サンプル）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェル風の書式（export 染みやコメント・クォート処理）に対応しています。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
```

2. 依存パッケージをインストール

（プロジェクトに requirements.txt がある場合はそれを使用）

```bash
pip install duckdb defusedxml
# 追加の依存（Slack, requests など）が必要な場合は適宜インストール
```

3. 環境変数を設定（.env をプロジェクトルートに作成）

例: `.env` を作成して上記の必須キーを記入してください。

4. DuckDB スキーマを初期化

Python REPL やスクリプトで以下を実行します:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # デフォルトパスでも可
# conn を使って ETL や他の処理を呼べます
```

初期化は冪等で、既存テーブルがあればスキップされます。

---

## 使い方（主要な API & サンプル）

以下はライブラリの代表的な使い方の例です。実運用ではこれらをラッパーしたバッチジョブや CI/CD、スケジューラ（cron / Airflow 等）で呼び出します。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- カレンダー更新ジョブ

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- ニュース収集（RSS → raw_news + news_symbols）

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出で許可する銘柄コード集合（任意）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 特徴量構築（features テーブルへ保存）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 5))
print(f"built features: {count}")
```

- シグナル生成（features / ai_scores / positions を参照して signals テーブルへ挿入）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2024, 1, 5), threshold=0.6)
print("signals written:", total_signals)
```

- J-Quants の生データ取得（クライアントを直接利用）

```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を経由して自動取得されます
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
```

注意:
- ほとんどの操作は DuckDB 接続を引数に取り、テーブル名ベースで入出力を行います。
- API 呼び出しはレート制御・リトライ・トークン自動更新などのロジックを含みます。

---

## ディレクトリ構成（主要ファイル）

（src 配下の kabusys パッケージを示します）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み・必須変数チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存のユーティリティ含む）
    - news_collector.py — RSS フィード収集、前処理、raw_news 保存、銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - features.py — data.stats の再エクスポート
    - calendar_management.py — マーケットカレンダーの更新 / 営業日ユーティリティ
    - audit.py — 監査ログ（signal_events / order_requests / executions 等）
    - (その他: quality モジュール等が想定される)
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・フィルタ・UPSERT）
    - signal_generator.py — generate_signals（final_score 計算・BUY/SELL 生成）
  - execution/ —（発注実行関連モジュール；空の __init__ が存在）
  - monitoring/ —（監視用コードやメトリクス関連を想定）

---

## 運用上の注意 / 実装ノート

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストなどで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API 呼び出しは 120 req/min の制限を守るため内部でスロットリングしています。重いバックフィル等は時間をかけて実行してください。
- RSS フェッチは SSRF 対策・gzip サイズ検査などを実装しており、外部入力に対して厳密な検証を行います。
- シグナル生成ロジックは features / ai_scores / positions を参照します。AI スコア等は別プロセスで生成して ai_scores テーブルに書き込む前提です。
- DuckDB スキーマは冪等に作られるため、既存 DB を上書きせずに安全に初期化できます。
- 本リポジトリは発注（実際のブローカー送信）や本番口座の運用について慎重な設計（paper_trading/live 切替、ログレベル、SLACK 通知等）を想定しています。実際に送金等に関わる部分を接続する場合はリスク管理を徹底してください。

---

## 開発・テスト

- 各モジュールは DuckDB のインメモリ DB（":memory:"）で簡単にテストできます。
- config.Settings の自動環境読み込みはテスト時に副作用を与える可能性があるため、テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境を注入することを推奨します。
- news_collector._urlopen や jquants_client._request 等は外部依存（ネットワーク）を持つため、単体テストではモックやスタブで差し替えてください。

---

この README はコードベースの主要機能・使い方の概要を示しています。より詳細な設計仕様（StrategyModel.md、DataPlatform.md、DataSchema.md 等）が別途ある想定です。必要であればそれらに対応した具体的な運用手順やサンプルスクリプトを追加します。