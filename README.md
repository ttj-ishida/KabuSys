# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
DuckDB をデータ層に用い、J-Quants API や RSS を取り込む ETL、ファクター計算、品質チェック、ニュース収集、監査ログなどを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・カレンダー情報を安定的に取得して DuckDB に保存する ETL（差分更新・冪等保存を実現）
- RSS を使ったニュース収集と記事 → 銘柄紐付け
- DuckDB 上でのスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索（将来リターン／IC 等）
- 発注/監査用のスキーマ構築（監査ログの初期化機能など）

設計上の要点:
- DuckDB をメインの永続化基盤とする
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュを内蔵
- 外部ライブラリへの依存は最小限（duckdb, defusedxml 等）
- 本番口座や発注 API には直接アクセスしない層分離（データ取得・特徴量・戦略・発注/実行は明確に分離）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env ファイル / 環境変数読み込み、自動ロード（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ
- kabusys.data
  - jquants_client:
    - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
    - fetch/save 関数（daily_quotes / financials / market_calendar）
  - schema:
    - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline:
    - 日次 ETL（差分更新・バックフィル・品質チェックを含む run_daily_etl）
  - news_collector:
    - RSS フェッチ、前処理、記事ID生成、DB 保存、銘柄抽出・紐付け
    - SSRF 対策・gzip/サイズ制限・XML ディフェンス対応
  - quality:
    - 欠損・スパイク・重複・日付不整合チェック
  - audit:
    - 監査ログ（signal_events / order_requests / executions 等）のDDLと初期化
  - stats / features:
    - zscore_normalize などの共通統計ユーティリティ
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value（DuckDB 上で計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

その他:
- 市場カレンダー管理（search/next/prev/is_trading_day 等）
- ETL の結果を保持する ETLResult データクラス（品質問題やエラーを集約）

---

## 要件

- Python 3.10 以上（typing の `X | Y` 構文を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じて他パッケージ（例: ロギング設定や Slack 通知用ライブラリなど）を追加してください。

---

## セットアップ手順

1. リポジトリをクローン（省略可）
2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   - 開発用に requirements.txt / poetry 等があればそちらを使用してください。
4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（ただしテスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必要な環境変数は次の節「環境変数一覧」を参照してください。
5. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   - ":memory:" を指定すればインメモリ DB を使用できます。
6. （任意）監査ログ用スキーマ初期化
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 環境変数（主なもの）

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化します。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（execution モジュールで使用）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL: kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

備考:
- settings オブジェクト（kabusys.config.settings）からプログラム内で取得できます。

---

## 使い方（例）

以下は主要ユースケースの最小例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からデータ取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) J-Quants から株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
recs = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 12, 31))
saved = jq.save_daily_quotes(conn, recs)
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) 研究用ファクター計算（モメンタム等）
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
from datetime import date

target = date(2025, 1, 31)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target)
# zscore 正規化
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
# IC 計算例
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) 設定の取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- J-Quants API はレート制限（120 req/min）に従います。jquants_client は内部で固定間隔スロットリングとリトライを実装しています。
- news_collector は SSRF 考慮、gzipサイズ制限、XML の脆弱性対策（defusedxml）を実装しています。
- ETL は差分取得・バックフィルロジックを持ち、品質チェックは Fail-Fast ではなく問題を収集して返します。

---

## ディレクトリ構成

（主要部分のみ抜粋）

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
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要ファイルの役割
- config.py: 環境変数管理・Settings クラス
- data/schema.py: DuckDB の DDL 定義と初期化処理
- data/jquants_client.py: J-Quants API クライアント + DuckDB 保存ユーティリティ
- data/pipeline.py: ETL の差分更新ロジックおよび run_daily_etl
- data/news_collector.py: RSS 取得・前処理・DB 保存・銘柄抽出
- data/quality.py: 各種データ品質チェック
- research/*: ファクター計算・特徴量探索（DuckDB を参照して純粋 Python 実装）

---

## 開発・運用上の注意

- 環境変数に API トークン等の機密情報を置く場合は適切に管理してください（`.env.local` を .gitignore に入れる等）。
- DuckDB ファイルのバックアップ/運用設計は運用要件に応じて行ってください（:memory: は永続化されません）。
- ETL のスケジューリング（cron / Airflow / Prefect 等）を行う場合、run_daily_etl をラップしてログ・通知を組み込むと良いです。
- 本パッケージはデータ取得・特徴量計算までを中心に実装しています。実際の発注ロジックやブローカー連携は別モジュール／オペレーション層で安全に実装してください（paper_trading/live 切替・リスク管理など）。

---

## ライセンス等

本リポジトリ内に LICENSE ファイルがない場合、使用・公開ルールは明記されていません。公開・配布する際は適切なライセンスをリポジトリに追加してください。

---

必要があれば README に追加したい内容（例: CI / テスト実行コマンド、より詳しい API ドキュメント、.env.example のテンプレート等）を教えてください。