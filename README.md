# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
市場データの取得（J-Quants）、DuckDB ベースのデータ管理、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とするソフトウェアコンポーネントの集合です。

- J-Quants API からの株価 / 財務 / カレンダー取得（レート制限・リトライ・自動トークン更新対応）
- DuckDB を用いたスキーマ定義と冪等的データ保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用のファクター計算（momentum / volatility / value 等）と IC 分析ユーティリティ
- 特徴量正規化・合成（feature engineering）
- 戦略シグナル生成（final_score の計算、BUY/SELL 判定、エグジット判定）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・サイズ制限）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 発注・監査用スキーマ（execution / audit テーブル群の定義。発注ロジックは execution 層で実装）

設計方針の要点:
- ルックアヘッドバイアス対策として、各種計算/判定は target_date 時点で利用可能なデータのみを使用
- DuckDB への INSERT は冪等（ON CONFLICT）で安全
- ネットワーク処理はレート制御・リトライを行い堅牢化
- 研究（research）層と実運用（execution）層を分離

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数の自動読み込み（`.env` / `.env.local`）と必須項目チェック
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン更新）
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: 日次 ETL 実行 run_daily_etl()、個別 ETL（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策、gzip/サイズ制限）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - features: zscore_normalize の再エクスポート
  - audit: 監査ログ用スキーマ定義
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.data.pipeline
  - 日次 ETL に品質チェックを統合
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存

> 注: execution パッケージは発注ロジックの実装用に準備されていますが、外部ブローカー接続の具体実装はここには含まれていません（execution/__init__.py は空）。

---

## セットアップ手順

### 前提（例）
- Python 3.8+（コードで typing の union 型等を使用。環境に合わせ適宜）
- DuckDB ライブラリ（pip でインストール）
- defusedxml（RSS パースの安全化）
- その他、標準ライブラリのみを多用

例: 仮想環境を作成し依存をインストールする
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

必要であればプロジェクトの pyproject.toml / requirements.txt を用意して依存管理してください。

### 環境変数
`kabusys.config.Settings` で参照される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（実運用時）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV           : "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL             : "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 `.env` 読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` があると自動で読み込みます。
- `.env.local` は `.env` を上書きします（OS 環境変数は保護される）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

### DB 初期化
DuckDB スキーマを初期化します（デフォルト DB パスは settings.duckdb_path）。
Python REPL 例:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルを生成しテーブルを作成します
conn.close()
```

---

## 使い方（主要ワークフロー例）

以下はライブラリを用いた基本的なワークフロー例です。すべて DuckDB の接続（duckdb.DuckDBPyConnection）を渡して実行します。

1) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の作成（research の生ファクターを用いて features テーブルに保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"upserted features: {n}")
```

3) シグナル生成（features と ai_scores を統合して signals に保存）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は文字列4桁コードのセット（銘柄紐付け用）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"market calendar saved: {saved}")
```

注意:
- 各関数は冪等設計（target_date 単位で DELETE→INSERT の置換を行う箇所あり）で、何度実行しても整合な状態になるよう配慮されています。
- jquants_client は API レート制限（120 req/min）やリトライ、401 時のトークン自動更新を実装しています。

---

## 開発 / テストに関するメモ

- 環境変数自動ロードはテスト時に邪魔な場合があるので、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- news_collector はネットワーク I/O を行う個所が多いため、ユニットテストでは `_urlopen` や HTTP 呼び出しをモックすることを推奨します。
- DuckDB のインメモリ DB（":memory:"）を利用するとテストが容易です。init_schema(":memory:") で使用できます。

---

## ディレクトリ構成（抜粋）

以下はコードベース内の主要ファイル／モジュール構成（src/kabusys 下）です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
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
  - monitoring/  (パッケージは README に合わせて存在する想定)

各ファイルはモジュール単位で責務が分かれており、例えば:
- data/schema.py: DuckDB スキーマ定義と init_schema()
- data/jquants_client.py: API 通信と save_* 関数
- research/factor_research.py: ファクター計算（prices_daily / raw_financials を前提）
- strategy/feature_engineering.py: features テーブル作成（zscore 正規化等）
- strategy/signal_generator.py: features と ai_scores を統合して BUY/SELL を判定

---

## ライセンス・貢献

本 README ではライセンス情報は含まれていません。実際のリポジトリでは適切な LICENSE ファイルを配置してください。貢献・バグ報告はリポジトリの Issue / PR フローに従ってください。

---

以上がプロジェクトの概要・セットアップ・使い方・構成の簡易 README です。必要であれば導入スクリプト例 (.env.example、docker-compose、systemd タスク等) や CI 用のテスト手順も追加できます。どの情報を優先して詳述しましょうか？