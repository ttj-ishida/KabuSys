# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（内部モジュール群）。  
このリポジトリはデータ取得・ETL・品質チェック・ニュース収集・監査ログなど、売買戦略の基盤となる機能を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えたバックエンドライブラリです。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を使ったデータスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定・次営業日/前営業日）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 環境設定管理（.env の自動読み込み、必須環境変数の提供）

設計上の要点：
- API レート制限・リトライ（J-Quants）
- 冪等性を重視した DB 書き込み（ON CONFLICT 句）
- SSRF / XML Bomb 等の安全対策（news_collector）
- 品質チェックでデータ品質を可視化（欠損・スパイク・重複・日付不整合）

---

## 機能一覧

- data/
  - jquants_client.py：J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - schema.py：DuckDB スキーマ（Raw/Processed/Feature/Execution 層）と初期化関数
  - pipeline.py：差分ETL（prices / financials / calendar）の実装と run_daily_etl エントリ
  - news_collector.py：RSS 収集・正規化・DB 保存・銘柄抽出
  - calendar_management.py：営業日判定・カレンダー更新ジョブ
  - quality.py：データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py：監査ログテーブル（signal_events / order_requests / executions）
- config.py：環境変数読み込み・Settings オブジェクト（必須チェック / デフォルト値 / env 判定）
- strategy/, execution/, monitoring/：戦略・実行・監視用の名前空間（拡張ポイント）
- パッケージメタ情報（__version__ など）

---

## セットアップ手順

前提：
- Python 3.9+（typing の一部記法を使用）
- システムに必要なライブラリ：duckdb, defusedxml（その他標準ライブラリを利用）

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用）
   ```bash
   pip install duckdb defusedxml
   # なおローカル開発であれば:
   # pip install -e .
   ```
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。
   - 必須環境変数（config.Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API パスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
   - オプション・デフォルト:
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL      — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH            — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH            — デフォルト: data/monitoring.db

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な API と実行例）

以下はライブラリをインポートして DB 初期化・ETL・ニュース収集等を実行する例です。

- DuckDB スキーマ初期化（初回）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ自動作成
```

- 日次 ETL 実行（J-Quants からデータを差分で取得して保存、品質チェックを実行）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 戻り値は ETLResult
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved calendar records: {saved}")
```

- RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出のための有効銘柄コード集合（例: 全上場銘柄）
known_codes = {"7203", "6758", ...}  # 実際は外部データから準備
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # source_name -> 新規保存記事数
```

- 監査ログテーブル（監査用スキーマ）を追加する
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

- J-Quants API を直接呼んでデータ取得（テストや一括取得）
```python
from kabusys.data import jquants_client as jq

# トークンは settings から自動取得/リフレッシュされる
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
jq.save_daily_quotes(conn, records)
```

ログの詳細度は環境変数 LOG_LEVEL で制御します。

---

## 設計上の注意点 / 運用メモ

- J-Quants のレート制限（120 req/min）をコード内で遵守する実装があります（固定間隔スロットリング）。
- API リトライロジックは 408/429/5xx などのエラーに対して指数バックオフで最大 3 回試行します。401 受信時は一度だけトークンを自動リフレッシュしてリトライします。
- news_collector は入力 URL のスキーム検証、リダイレクト先のプライベートアドレス防止、受信サイズ上限（10MB）、defusedxml による XML 脆弱性対策を行います。
- DB への書き込みは冪等性を考慮しており、重複時は ON CONFLICT で更新/スキップします。
- ETL の品質チェックは Fail-Fast ではなく問題を収集して戻す方針です。呼び出し元で判断してください。
- 自動で .env をロードします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## ディレクトリ構成

プロジェクトの主要ファイル / ディレクトリは次の通りです（ルートはリポジトリ）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存）
      - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - schema.py              — DuckDB スキーマ定義と init_schema/get_connection
      - calendar_management.py — カレンダー更新・営業日ロジック
      - quality.py             — データ品質チェック群
      - audit.py               — 監査ログ用テーブル初期化
    - strategy/
      - __init__.py            — 戦略関連の名前空間（拡張ポイント）
    - execution/
      - __init__.py            — 発注・執行関連の名前空間（拡張ポイント）
    - monitoring/
      - __init__.py            — 監視/メトリクス関連の名前空間（拡張ポイント）
- pyproject.toml (想定)
- .env.example (想定)

---

## 開発 / テスト時のヒント

- Settings による自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。CI 等でカスタムルートを使う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、環境変数を直接提供してください。
- DuckDB の初期化には init_schema を使ってください。スキーマは冪等なので複数回呼んでも安全です。
- news_collector のネットワーク呼び出しは _urlopen を通しているため、テストではこの関数をモックして HTTP 呼び出しを差し替えられます。
- run_daily_etl 等は id_token を外部から注入可能なので、ユニットテストでトークンや API 呼び出しを差し替えやすくなっています。

---

必要に応じて README の拡張（例: CI 設定、Docker イメージ例、運用手順、Slack 通知フロー、kabuステーション接続例など）を追加できます。追加して欲しい項目があれば教えてください。