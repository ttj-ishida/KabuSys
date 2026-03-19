# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量（features）生成、シグナル生成、ニュース収集、DuckDB スキーマ定義、監査ログなど、研究・運用の両フェーズで使える機能を備えています。

本 README ではプロジェクト概要、主な機能、セットアップ方法、基本的な使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

- 目的: 日本株の市場データを J-Quants から取得して DuckDB に保存し、研究で計算したファクターを元に特徴量を整備してシグナル生成まで行えるようにする。
- 設計思想:
  - ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
  - DuckDB を中心としたローカルデータ基盤（冪等な保存・ON CONFLICT を多用）
  - 外部 API 呼び出しにはレート制御／リトライ／トークンリフレッシュなどの堅牢性を実装
  - Research 層と Execution 層は明確に分離（発注ロジックへ直接依存しない）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の取得ラッパー（Settings クラス）
- データ取得 / 保存（J-Quants クライアント）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - 市場カレンダー（fetch_market_calendar / save_market_calendar）
  - レート制限・リトライ・トークン自動リフレッシュの実装
- ETL パイプライン
  - 差分取得・バックフィルを考慮した run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
- データスキーマ（DuckDB）
  - raw / processed / feature / execution 層のテーブル定義と初期化（init_schema）
- 研究用ファクター計算（research）
  - momentum / volatility / value の計算（prices_daily / raw_financials を参照）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- 特徴量生成（strategy.feature_engineering）
  - 生ファクターを統合し Zスコア正規化・ユニバースフィルタ適用 → features テーブルへ UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを signals テーブルへ出力
  - Bear レジーム判定、売却（stop loss / score drop）ルールを実装
- ニュース収集（data.news_collector）
  - RSS からのニュース取得、前処理、raw_news への冪等保存、銘柄コード抽出・紐付け
  - SSRF 対策、受信サイズ上限、XML の安全パーサ利用（defusedxml）
- 監査ログ（data.audit）
  - シグナル→発注→約定 のトレーサビリティを保証する監査テーブル群

---

## 必須環境 (推奨)

- Python 3.10+
  - ソース内での型ヒント（`|` 演算子等）により Python 3.10 以上を想定しています
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API 利用時）
- J-Quants のリフレッシュトークン等、各種 API トークン

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらに従ってください）

---

## 環境変数（主なもの）

Settings クラスで使用される主要な環境変数は以下です。`.env.example` を参考に `.env` を作成してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の発注APIパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用の Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（省略時: INFO）

自動 .env 読み込み:
- プロジェクトルート（.git / pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- `.env.local` は `.env` を上書きします（OS 環境変数は保護される）。
- テスト等で自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （パッケージ化されていれば）pip install -e .

   ※プロジェクトに pyproject.toml がある場合は pip install -e . が推奨です。

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env` を置き、上記の必須キーを設定します。
   - 例:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化（Python REPL またはスクリプトで）
   - 以下はサンプルコード（後述）を参照

---

## 使い方（代表的な API とサンプル）

以下に主要な使い方例を示します。実運用ではログや例外処理、環境設定などを適切に行ってください。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

# デフォルト: settings.duckdb_path からパスを読み取ることも可能だが、明示的に指定して初期化
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から市場カレンダ・株価・財務を取得）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ書き込む）

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 10))
print(f"upserted features: {n}")
```

4) シグナル生成（signals テーブルへ書き込む）

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 10))
print(f"generated signals: {count}")
```

5) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) 市場カレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar entries: {saved}")
```

---

## 推奨ワークフロー（簡易）

1. init_schema() で DuckDB を初期化
2. run_daily_etl() をスケジュール（例: cron / Airflow）で日次実行
3. ETL 完了後に build_features() → generate_signals() を実行
4. signals を監視して発注ロジック（execution 層）へ渡す
5. news_collector や calendar_update_job は独立して定期実行

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル・モジュール群（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - news_collector.py      — RSS ニュース収集・DB 保存
    - features.py            — data 側の特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — 市場カレンダー管理・ジョブ
    - audit.py               — 監査ログ用スキーマ/DDL（signal_events 等）
    - execution/              — 発注関連（空の __init__ が存在）
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value 計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター正規化・features 作成
    - signal_generator.py    — final_score 計算・signals 生成
  - monitoring/              — monitoring 用（package エントリは __all__ に含むが実装はプロジェクトに依存）

（上記は現在の実装に基づく抜粋です）

---

## 注意点 / 運用上のメモ

- 環境変数は必ず安全に管理してください（トークンは .env のままコミットしない）。
- DuckDB ファイルはローカルに置く前提です。バックアップや共有方法を検討してください。
- J-Quants API のレート制限（デフォルト 120 req/min）を超えると API エラーや一時停止のリスクがあります。jquants_client では簡単なレート制御とリトライを実装していますが、運用時は頻度に注意してください。
- シグナル生成は features / ai_scores / positions 等のデータ品質に依存します。ETL と品質チェックを確実に行ってください。
- 本リポジトリ内の設計ドキュメント参照（StrategyModel.md, DataPlatform.md 等）がある場合、実装仕様はそれらに一致します。プロジェクトに同梱されていれば併せて参照してください。

---

## 追加情報 / 貢献

- バグ報告・機能要望は Issue へお願いします。
- ローカルでのテストや CI の実装、さらに Execution 層（証券会社接続）や Risk モジュールの拡張などが想定されます。

---

この README はリポジトリ内のソースコード（src/kabusys）を参照して作成しています。実際の導入時は pyproject.toml / requirements.txt / .env.example 等も併せて確認してください。