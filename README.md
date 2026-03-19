# KabuSys

日本株の自動売買基盤向けライブラリ集。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ/初期化、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のクオンツ戦略運用に必要な以下の機能をコンポーネント化した Python パッケージです。

- J-Quants API からの市場データ・財務データ取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB を用いたデータベーススキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェックフック）
- 特徴量（features）計算・正規化と戦略シグナル生成（BUY / SELL 判定）
- RSS ベースのニュース収集・記事前処理・銘柄紐付け
- マーケットカレンダー管理（営業日判定・次営業日/前営業日取得）
- 監査ログ（signal → order → execution をトレースする仕組み）
- 開発・リサーチ用ユーティリティ（IC 計算、将来リターン計算、Z スコア正規化 等）

設計方針としては「ルックアヘッドバイアスに配慮したデータ使用」「DB 操作の冪等性」「外部 API との堅牢な接続制御」「テストしやすい注入可能な認証」などを重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークンリフレッシュ）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: 日次 ETL（run_daily_etl、個別 run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集、記事前処理、raw_news / news_symbols への保存
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - stats / features: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value ファクター計算（prices_daily / raw_financials に依存）
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリー
- strategy/
  - feature_engineering.build_features: ファクターの統合・ユニバースフィルタ・正規化・features テーブル保存
  - signal_generator.generate_signals: features / ai_scores / positions を参照して BUY/SELL シグナルを作成し signals テーブルへ保存
- execution/ (発注周りの実装を配置するためのパッケージ（コードベース内に初期化ファイルあり）)
- monitoring/ (監視・Slack 通知等の実装を配置するための場所)
- config.py: 環境変数管理（.env 自動ロード機能、必須変数チェック）

---

## 依存関係

必須（コード中で明示的に使用されている主なライブラリ）：

- Python 3.9+
- duckdb
- defusedxml

インストール例（最低限）:

```bash
pip install duckdb defusedxml
```

パッケージ化された環境であれば setup / pyproject.toml からインストールしてください。

---

## 環境変数

config.Settings が参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development | paper_trading | live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

自動で .env（プロジェクトルート判定: .git または pyproject.toml があるディレクトリ）を読み込みます。
自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 仮想環境作成（推奨）

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

3. 必要パッケージをインストール

```bash
pip install duckdb defusedxml
# あるいはパッケージ化されていれば:
# pip install -e .
```

4. 環境変数設定

プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定してください。
例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化

Python REPL かスクリプトから init_schema を呼ぶことで DB とテーブルを作成します。

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

---

## 使い方（主要な例）

以下は基本的な操作フローと簡単なコード例です。

- 日次 ETL を実行する（市場カレンダー、株価、財務データの差分取得と品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量を構築して features テーブルへ保存する

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

- シグナル生成（features と ai_scores を統合して signals テーブルに保存）

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", num_signals)
```

- RSS ニュースの収集と保存

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けを試みる
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

- カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar records saved:", saved)
```

注意: これらはライブラリ関数を直接呼ぶ例です。運用ではジョブスケジューラ（cron / Airflow 等）や、監視・通知（Slack）と組み合わせて下さい。

---

## ディレクトリ構成

主要ファイル・モジュールの概観:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py — ETL（run_daily_etl, run_prices_etl, ...）
    - news_collector.py — RSS 収集・記事正規化・DB 保存
    - calendar_management.py — マーケットカレンダー管理、営業日判定、calendar_update_job
    - features.py — zscore_normalize のエクスポート
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ用スキーマ定義（signal / order / execution トレース）
    - quality.py? — （品質チェックモジュールを参照するコードあり、実装箇所がある場合）
  - research/
    - __init__.py (エクスポート)
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features
    - signal_generator.py — generate_signals
  - execution/
    - __init__.py — 発注層（拡張ポイント）
  - monitoring/
    - (監視・通知関連モジュールを配置する場所)

（上記はコードベースに含まれる主要モジュールを抜粋しています。）

---

## 開発上の注意・設計ポイント

- データの取得・加工はルックアヘッドバイアスを防ぐ設計（target_date 時点までのデータのみ使用）。
- DuckDB への挿入は冪等性を重視（ON CONFLICT / RETURNING を活用）。
- J-Quants クライアントはレート制御（120 req/min）、リトライ、401 の自動リフレッシュを実装。
- NewsCollector は SSRF/XML-Bomb/Gzip-Bomb 等の脅威を考慮した堅牢な実装を意図（defusedxml・サイズチェック・プライベートホスト拒否等）。
- 環境変数が未設定の場合は明示的に ValueError を投げるため、CI/運用環境での設定ミスを早期に検出できます。
- strategy と execution は分離。strategy は signals テーブルまで出力し、実際の発注（execution 層）は別モジュールで扱うことを想定。

---

## 貢献・拡張

- execution 層に証券会社 API（kabuステーション等）の具体的な送信・再送ロジック・約定処理を実装できます。
- monitoring に Slack 通知やメトリクス送信を組み込むと運用が容易になります。
- quality モジュールを拡充して ETL 品質チェックを強化してください。

---

README は以上です。必要であれば「運用ガイド（デプロイ/cron 設定/監視）」や「開発者向けテスト手順」などの追補資料を作成できます。どの情報を優先して追加しますか？