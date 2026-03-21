# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理などを含む。DuckDB を中心に設計され、研究（research）と本番（execution）を分離したアーキテクチャを採用しています。

---

## 概要

KabuSys は以下の機能を提供する Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（最終スコア計算、BUY/SELL 判定、エグジット判定）
- ニュース収集（RSS -> raw_news、銘柄抽出・紐付け）
- マーケットカレンダー管理（営業日/半日/SQ 判定・更新ジョブ）
- 監査ログ（signal → order → execution のトレース用テーブル群）

設計方針として、ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）、発注層への直接依存を避ける（戦略は signals テーブルへ書き込む）などを重視しています。

---

## 主な機能一覧

- data/jquants_client:
  - API 呼び出し（ページネーション対応）、リトライ、レート制御、トークン自動更新
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/schema:
  - DuckDB スキーマ定義・初期化（raw_prices / prices_daily / features / signals / ...）
- data/pipeline:
  - 日次 ETL（calendar / prices / financials）の差分更新・バックフィル・品質チェック統合
- research:
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価・探索ツール
- strategy:
  - build_features：ファクター正規化・features テーブルへの UPSERT
  - generate_signals：features + ai_scores から final_score を算出し signals を作成
- data/news_collector:
  - RSS フィード収集、安全対策（SSRF / XML Bomb / サイズ制限）、記事ID生成、raw_news 保存、銘柄抽出・紐付け
- data/calendar_management:
  - market_calendar の更新、営業日判定・前後営業日取得・期間の営業日列挙
- audit（監査ログ）:
  - signal_events / order_requests / executions など監査用テーブル（トレーサビリティ）

---

## セットアップ手順

必要環境
- Python 3.10 以上（型注釈の `X | Y` 構文を使用）
- DuckDB（Python パッケージ）
- defusedxml（ニュース XML パースの安全化）
- 標準ライブラリ以外で利用される主な依存例:
  - duckdb
  - defusedxml

例（仮の requirements.txt に基づくインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 他に必要なパッケージがあれば併せてインストール
```

環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層使用時）
  - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID — Slack チャンネル ID
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト: development
  - LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で自動読み込みを行います。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。

初期 DB の準備
- DuckDB スキーマを初期化します（例: data/kabusys.duckdb に作成）。
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

---

## 使い方（代表的なコード例）

1) DuckDB の初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants からデータ取得・保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 例：保有/注目銘柄セット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) J-Quants の低レベル API 使用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
saved = save_daily_quotes(conn, records)
```

注意点
- 各関数は target_date 時点のデータのみを参照する設計（ルックアヘッド防止）。
- ストラテジー/研究用関数は直接発注を行わず、signals テーブルへ書き込むことにより発注層と分離しています。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py
      - 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - news_collector.py
      - RSS 取得・記事正規化・保存・銘柄抽出
    - calendar_management.py
      - market_calendar 更新・営業日計算（is_trading_day, next_trading_day, ...）
    - audit.py
      - 監査ログ用 DDL（signal_events, order_requests, executions）
    - (その他: quality.py 等は参照されますがここには含まれていません)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - build_features: ファクター統合・正規化・features テーブル更新
    - signal_generator.py
      - generate_signals: final_score 計算・BUY/SELL 生成・signals テーブル更新
  - execution/
    - __init__.py
      - （発注層：未実装 or 外部接続用のフレーム）
  - monitoring/
    - （監視・外部通知等のモジュールが入る想定）

---

## 環境変数の主な説明（config.Settings）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン。get_id_token で使用。
- KABU_API_PASSWORD (必須): kabuステーション API パスワード（execution 層で使用）。
- KABU_API_BASE_URL (任意): kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須): Slack 通知用。
- DUCKDB_PATH / SQLITE_PATH (任意): DB パス。デフォルト値あり。
- KABUSYS_ENV: development / paper_trading / live（validation あり）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

config.py はプロジェクトルートの .env / .env.local を自動読み込みします。テストなどで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 開発・テストに関する補足

- Python の型アノテーション（|）を利用しているため、Python 3.10 以上を推奨します。
- DuckDB を使うため、データベースはローカルファイルで簡単に運用できます。":memory:" を渡せばインメモリ DB でのユニットテストが可能です。
- ETL / ニュース収集 / カレンダー更新などは外部 API に依存するため、ユニットテストでは jquants_client._request や news_collector._urlopen 等をモックすることを想定しています。
- ニュース収集は外部 RSS をパースするため、defusedxml 等の安全ライブラリを導入済みです。

---

## ライセンス / 貢献

この README はコードベースに基づくドキュメント例です。実際のライセンスや貢献ルールはプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、README にサンプル .env.example、実行可能なスクリプト例（cron 化、Dockerfile、systemd ユニット等）、詳細なテーブル定義（DataSchema.md を元にした要約）を追加で作成します。どの情報を追記しますか？