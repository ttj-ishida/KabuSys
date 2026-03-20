# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants API や RSS を取り込み、特徴量生成→シグナル生成→発注監査までの主要コンポーネントを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群を含みます。

- J-Quants API クライアント（データ取得・保存、レートリミット・リトライ・トークン自動更新）
- DuckDB ベースのスキーマ定義と初期化
- ETL パイプライン（株価・財務・市場カレンダーの差分更新、品質チェック）
- ニュース収集（RSS → raw_news、記事から銘柄抽出）
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ等）
- 特徴量正規化、戦略のシグナル生成（BUY / SELL 判定）
- 発注・監査（スキーマ設計によるトレーサビリティ）

設計方針として「ルックアヘッドバイアスを防ぐ」「冪等性」「テスト容易性」「外部依存の限定」を掲げています。

---

## 主な機能一覧

- データ取得
  - J-Quants からの日次株価・四半期財務・市場カレンダーのフェッチ（ページネーション対応）
  - レート制限（120 req/min）遵守、リトライ、401 時のトークンリフレッシュ
- データ保存
  - DuckDB への冪等保存（ON CONFLICT / UPSERT 相当）
  - スキーマ初期化（raw / processed / feature / execution レイヤ）
- ETL
  - 差分更新、バックフィル、品質チェックを組み合わせた日次 ETL
- ニュース収集
  - RSS 取得、XML の安全パース、URL 正規化、記事ID生成（SHA-256）
  - 銘柄コード抽出（4 桁コード）
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - Z スコア正規化ユーティリティ
- 戦略
  - 特徴量合成（build_features）
  - final_score 算出と BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム判定、売買シグナルのエグジット判定（ストップロス等）
- 監査・実行
  - signals / orders / executions / audit テーブル定義でトレーサビリティを確保

---

## 必要条件 / 依存関係

- Python 3.10+
  - 型記法（|）や一部の typing 機能を利用しています。
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）

インストール例（最低限）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必須であれば他のユーティリティを追加
```

プロジェクト配布用に requirements.txt / pyproject.toml がある想定では、そちらを利用してください。

---

## 環境変数（設定）

kabusys は .env ファイルまたは OS 環境変数から設定を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（Settings から参照されるもの）:

- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注連携時）
- SLACK_BOT_TOKEN        — Slack 通知（ボットトークン）
- SLACK_CHANNEL_ID       — Slack チャンネル ID

任意（デフォルト有り）:

- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）

注意: .env のパースはシェル風の quoting コメント処理をサポートしています。

---

## セットアップ手順

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境を作成・有効化

```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存ライブラリをインストール

```bash
pip install duckdb defusedxml
# 必要に応じて追加パッケージをインストール
```

4. 環境変数を準備

プロジェクトルートに `.env` を作成（例: .env.example をコピーして編集する想定）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xxxx
SLACK_CHANNEL_ID=xxxx
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

5. DuckDB スキーマ初期化

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

---

## 使い方（基本的なワークフロー例）

以下は典型的な日次処理の流れです。

1) DB 初期化（上記）

2) 日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量（features）構築

```python
from datetime import date
from kabusys.strategy import build_features

build_count = build_features(conn, date.today())
print(f"features built: {build_count}")
```

4) シグナル生成

```python
from kabusys.strategy import generate_signals
from datetime import date

signal_count = generate_signals(conn, date.today())
print(f"signals generated: {signal_count}")
```

5) ニュース収集（RSS）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(saved_map)
```

6) カレンダー更新バッチ

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

その他、jquants_client の fetch/save や research モジュールの IC 計算等は、そのまま呼び出して利用できます。

- J-Quants の直接利用例:

```python
from kabusys.data import jquants_client as jq
rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 開発 / テストに関するメモ

- 自動で .env を読み込みますが、テスト中に自動ロードを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリ DB を使いたい場合は `init_schema(":memory:")` を用いると一時的にメモリ DB が作れます。
- 外部 API 呼び出しをテストで差し替えるために、jquants_client の HTTP 呼び出しや news_collector の _urlopen などをモックする設計になっています。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（src/kabusys 配下）と簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（自動 .env 読込、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証 / レートリミット）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - 差分 ETL（run_daily_etl, run_prices_etl, ...）
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
    - features.py
      - zscore_normalize の再エクスポート
    - audit.py
      - 発注・約定の監査トレーサビリティ用 DDL
    - execution/ (空 __init__ あり、発注連携は別モジュールに分離想定)
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算・IC（Spearman）・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - raw factor を正規化・合成して features テーブルへ保存
    - signal_generator.py
      - features と ai_scores を統合して final_score を計算、signals へ保存

（上記はコードベースの抜粋に基づく主要ファイルです。実際のリポジトリでは他の補助ファイルや CLI、テストが存在することがあります。）

---

## よくある質問 / 注意点

- Q: DuckDB のテーブル定義は変更できますか？  
  A: スキーマは init_schema で作成されます。既存テーブルは IF NOT EXISTS でスキップするので、DDL を変更する場合はマイグレーション手順（既存データのバックアップと ALTER/移行）を行ってください。

- Q: J-Quants のトークンはどのように扱われますか？  
  A: リフレッシュトークン（JQUANTS_REFRESH_TOKEN）を設定し、内部で ID トークンを取得・キャッシュし、401 時は自動でリフレッシュして再試行します。

- Q: 本番運用（live）はどのように切替えますか？  
  A: 環境変数 `KABUSYS_ENV=live` を設定します。strategy や execution 層では env を基に挙動を変える想定です。

---

## 貢献 / 拡張ポイント

- execution 層の実際のブローカー連携（kabuステーション API 実装）
- AI スコア算出の外部モデル接続
- 品質チェックの追加ルール（quality モジュール拡張）
- CLI / スケジューラ統合（cron / Airflow / Prefect）

---

ご不明点や README に追加したい使用例（たとえば CLI の例や Unit Test の実行方法）があれば教えてください。必要に応じてサンプルスクリプトや .env.example のテンプレートも作成できます。