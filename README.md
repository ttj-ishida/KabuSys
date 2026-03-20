# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。市場データの取得・ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ用スキーマなどを提供し、DuckDB によるローカルデータレイヤを中心に研究（research）→ 戦略（strategy）→ 実行（execution）までのワークフローをサポートします。

主な設計方針:
- ルックアヘッドバイアスを防ぐため「対象日（target_date）時点で利用可能なデータのみ」を原則とする
- DuckDB を用いたローカル DB（冪等保存 / ON CONFLICT での更新）
- 外部 API 呼び出し（J-Quants 等）はレート制御・リトライ・トークンリフレッシュ等を考慮
- 発注（execution）層へ直接アクセスしない分離設計（strategy は signals テーブル出力まで）

---

## 機能一覧

- ETL / Data pipeline
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - 差分更新・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
  - DuckDB 用のスキーマ定義・初期化（init_schema）

- データ層ユーティリティ
  - raw/process/feature/execution 層のテーブル DDL（schema.py）
  - 統計ユーティリティ（zscore 正規化等）

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）・ファクター統計サマリー

- 戦略（strategy）
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントを統合して最終スコアを計算、BUY/SELL を signals テーブルへ保存

- ニュース収集（news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出・news_symbols 紐付け
  - SSRF・XML Bomb・レスポンス上限等のセーフガードを実装

- マーケットカレンダー管理
  - 営業日判定、次/前営業日算出、カレンダー差分更新ジョブ

- 監査（audit）
  - signal → order_request → execution のトレーサビリティ用テーブル群（監査ログ）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに | 演算子を使用しているため）
- Git 等

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要な Python パッケージをインストール
   （このコードベースに明示的な requirements.txt は含まれていません。以下は最低限の依存例）
   ```bash
   pip install duckdb defusedxml
   # その他必要に応じて: requests 等
   ```

4. 環境変数の設定
   プロジェクトルートの `.env` / `.env.local` または OS 環境変数で以下を設定してください（少なくとも API トークン類は必須）。

   必須:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API 用パスワード（execution 層等で使用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : Monitoring 用 SQLite（デフォルト: data/monitoring.db）

   自動で .env を読み込む仕組みがあります。自動ロードを無効化したい場合は:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで初期化します:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   conn.close()
   ```

---

## 使い方（簡単な例）

以下は典型的なワークフロー例です。

- 日次 ETL を実行してデータを取得・保存する

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

conn.close()
```

- 特徴量作成（build_features）

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features updated for {count} codes")
conn.close()
```

- シグナル生成（generate_signals）

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
conn.close()
```

- ニュース収集ジョブを実行（run_news_collection）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと銘柄紐付けを行う
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
conn.close()
```

- カレンダー更新バッチ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar records: {saved}")
conn.close()
```

注:
- 上記はいずれもローカルの DuckDB 接続を直接操作するサンプルです。
- 実運用での発注（kabu API）や Slack 通知等は別モジュール（execution / monitoring）を介して実装する想定です（このリポジトリに含まれる機能を組み合わせて利用してください）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須)     : kabu ステーション API のパスワード
- KABU_API_BASE_URL            : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)       : Slack bot token
- SLACK_CHANNEL_ID (必須)      : Slack チャンネル ID
- DUCKDB_PATH                  : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH                  : SQLite path for monitoring（デフォルト data/monitoring.db）
- KABUSYS_ENV                  : development / paper_trading / live（default: development）
- LOG_LEVEL                    : ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                : .env 自動ロード / Settings（環境変数管理）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント、保存ユーティリティ
    - news_collector.py      : RSS 収集・前処理・保存・銘柄抽出
    - schema.py              : DuckDB スキーマ定義と init_schema / get_connection
    - stats.py               : zscore_normalize 等の統計ユーティリティ
    - pipeline.py            : 日次 ETL 実行ロジック（run_daily_etl 等）
    - calendar_management.py : 市場カレンダー関連ユーティリティ
    - audit.py               : 監査ログ（signal_events / order_requests / executions）
    - features.py            : data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     : momentum / volatility / value の計算
    - feature_exploration.py : forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py : build_features
    - signal_generator.py    : generate_signals
  - execution/               : 実行層（発注関連。空の __init__ が存在）
  - monitoring/              : 監視用コード（例: Slack 通知等を想定）

各モジュールは docstring に詳細な設計意図・処理フロー・注意点を記載しています。実装や拡張の際は docstring を参照してください。

---

## 開発・貢献

- テスト: 各モジュールは外部依存を注入可能な実装（id_token の注入など）になっており、ユニットテストが書きやすく設計されています。
- 自動ロードされる .env は .git または pyproject.toml を基準に探索されます。CI / テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコードベースの主要部分に基づいて作成しています。より詳細な仕様（StrategyModel.md / DataPlatform.md / Research ドキュメントなど）がある場合はそちらも参照してください。