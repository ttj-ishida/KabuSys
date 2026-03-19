# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ取得・ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを備えたモジュール群を提供します。

主な目的は「J-Quants 等の外部データを取り込み、DuckDB に整備した上で戦略用特徴量を作り、シグナルを生成する」ことです。発注層（broker API）や実行ロジックは Execution 層で扱います（このリポジトリの一部として実装されています）。

---

## 主要機能一覧

- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - レート制限、リトライ、トークン自動リフレッシュの実装
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 日次 ETL（run_daily_etl）でカレンダー・株価・財務を差分取得
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- 特徴量計算（research / strategy）
  - Momentum / Volatility / Value 等のファクター計算（ルックアヘッド対策あり）
  - クロスセクション Z スコア正規化
- シグナル生成
  - 正規化済み特徴量 + AI スコアを統合して final_score を算出
  - Bear レジーム抑制、エグジット（ストップロス等）判定
  - signals テーブルへ書き込み（日付単位の置換で冪等）
- ニュース収集
  - RSS 取得・前処理（URL 正規化、トラッキング除去）・SSRF 対策
  - raw_news に冪等保存、銘柄コード抽出と news_symbols 紐付け
- マーケットカレンダー管理（営業日判定など）
- 監査ログ（signal → order → execution のトレースを保存）
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## 必要条件 / 依存ライブラリ

このコードベースは Python3.10+ を想定しています（型アノテーションに union 型 `X | Y` を使用）。

主な依存（最小）:
- duckdb
- defusedxml

その他、J-Quants API 呼び出しや HTTP/URL 処理は標準ライブラリを利用します。

pip でのインストール例（プロジェクトに合わせて pyproject/setup に従ってください）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# プロジェクトを editable install する場合（setup/pyproject があれば）
# pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env / .env.local または OS 環境変数から設定を自動読込します（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト向け）。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意の環境変数（デフォルトあり）:
- KABUSYS_ENV — environment: "development" | "paper_trading" | "live"（default: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（1）

例 `.env`（README 用、実運用では秘密情報は安全に管理してください）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` を使ってアクセスできます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # 必要ならテスト用パッケージ等を追加
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数を設定します。
   - 必須変数（上記参照）を設定してください。

4. DuckDB スキーマ初期化
   Python REPL などで以下を実行して DB とテーブルを作成します:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（代表的な API と例）

以下は最小限の利用例です。実運用スクリプトやジョブスケジューラ（cron / Airflow 等）から呼び出して使用します。

- 日次 ETL を走らせる
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量を構築（戦略層）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"features built: {count}")
```

- シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {n_signals}")
```

- ニュース収集ジョブ（RSS）
```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- マーケットカレンダーに関するユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- 上記関数は DuckDB の適切なテーブルが存在することを前提とします（init_schema を事前に実行してください）。
- run_daily_etl は品質チェックや各 ETL ステップで例外を捕捉しつつ処理を継続する設計です。結果の ETLResult で詳細を確認してください。

---

## 開発用ヒント

- 自動 .env 読み込みを無効化したいテスト等では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `kabusys.config.Settings` はプロパティベースで値を提供します。未設定の必須変数へのアクセスは ValueError を投げます。
- J-Quants の API コールにはレート制限が組み込まれており、最大リトライ・トークン自動リフレッシュ等が実装されています。
- ニュース取得は SSRF 対策（リダイレクト検査・プライベートアドレス除外）や XML の安全パーサ（defusedxml）を利用しています。
- DuckDB への保存は可能な限り冪等性（ON CONFLICT）を意識しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得 + 保存）
  - news_collector.py        — RSS ニュース収集・保存
  - schema.py                — DuckDB スキーマ定義・初期化
  - stats.py                 — 統計ユーティリティ（zscore_normalize）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py   — カレンダー管理（is_trading_day 等）
  - audit.py                 — 監査ログ関連スキーマ
  - features.py              — data の特徴量公開インターフェース
- research/
  - __init__.py
  - factor_research.py       — Momentum/Volatility/Value 計算
  - feature_exploration.py   — IC / forward returns / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py   — features テーブル構築（build_features）
  - signal_generator.py      — signals 生成（generate_signals）
- execution/
  - __init__.py
- monitoring/ (パッケージとして公開されているが詳細はコード参照)

その他:
- pyproject.toml / setup.cfg 等（プロジェクトルート、存在する場合）

---

## 注意事項 / 制限

- 実際の発注（ブローカー連携）には別途認証情報や取引ルールの実装、リスク管理が必要です。本リポジトリは戦略・データ基盤を中心に設計されています。
- 金融データは正確性が重要です。ETL・品質チェックの結果は運用判断に必ず組み込んでください。
- 環境変数に含まれる機密情報は安全に管理してください（Vault 等の使用を推奨）。

---

この README はコードベースに含まれるモジュール群の概要・使い方をまとめたものです。詳細な API 仕様や設計文書（StrategyModel.md / DataPlatform.md 等）がプロジェクトに含まれている想定なので、運用時はそれらも参照してください。質問や追加で欲しいサンプル（デプロイ手順や Airflow 連携例など）があれば教えてください。