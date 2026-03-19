# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマム実装）。  
データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、DuckDB スキーマ・監査ログなど、戦略研究〜実運用までの各レイヤーをカバーします。

---

## 目次
- プロジェクト概要
- 機能一覧
- 要求事項 / 依存関係
- セットアップ手順
- 環境変数（.env）の扱い
- 使い方（主要ワークフローの例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株のデータパイプラインと戦略基盤を提供する Python パッケージです。  
主な目的は以下です。
- J-Quants などの外部 API から市場データ（株価・財務・カレンダー等）を取得して DuckDB に保存
- 研究用ファクター群の計算、クロスセクション正規化（Z スコア）を行い features テーブルを生成
- features と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- ニュース収集（RSS）と記事と銘柄コードの紐付け
- 市場カレンダー管理、ETL ジョブ、監査ログ（発注〜約定のトレーサビリティ）

設計上の注意点:
- ルックアヘッドバイアス防止のため、各処理は target_date 時点のデータのみを使用
- DuckDB を主なローカル DB として想定し、冪等（idempotent）な保存ロジックを採用
- 発注 / execution 層は抽象化し、戦略層は直接発注 API に依存しない

---

## 機能一覧
- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション、再試行、トークン自動リフレッシュ）
  - raw_prices / raw_financials / market_calendar / raw_news への冪等保存
- ETL / パイプライン
  - 日次 ETL（calendar / prices / financials）
  - 差分取得、バックフィル、品質チェック（quality モジュール）
- スキーマ管理
  - DuckDB 用のスキーマ初期化（各レイヤーのテーブル定義）
- 研究・特徴量
  - momentum / volatility / value 等のファクター計算
  - Z スコア正規化ユーティリティ
  - ファクター探索用ユーティリティ（Forward Returns / IC / summary）
- 特徴量作成 & シグナル生成
  - features テーブルへの正規化済みファクター書き込み（build_features）
  - final_score 計算による BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム時の BUY 抑制、ストップロスなどのエグジット判定
- ニュース収集
  - RSS フィード取得、安全対策（SSRF / XML Bomb / サイズ制限）
  - 記事の正規化・ID 化、raw_news への保存、銘柄コード抽出と紐付け
- カレンダー管理
  - market_calendar の差分更新、営業日判定、次/前営業日の取得
- 監査ログ
  - signal_events / order_requests / executions など、発注〜約定の監査テーブル

---

## 要求事項 / 依存関係
- Python 3.10 以上（型ヒントに `|` を多用）
- インストールが推奨されるパッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトで requirements.txt を用意している場合はそれを使ってください:
```bash
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 環境（3.10+）を準備し、依存パッケージをインストール
3. 環境変数を設定（.env を推奨）
   - 必須: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD
   - 任意・デフォルトあり: KABUSYS_ENV (development|paper_trading|live, default: development), LOG_LEVEL (default: INFO), DUCKDB_PATH (default: data/kabusys.duckdb), SQLITE_PATH (default: data/monitoring.db)
   - テスト用に自動 .env ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. DuckDB スキーマ初期化
   - 例: パッケージの API を使って初期化する
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
     ```
   - またはメモリ DB でテストする場合:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema(":memory:")
     ```
5. ETL 実行、特徴量生成、シグナル生成などを呼び出す

---

## 環境変数（.env）の扱い
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` を上書きできます（override=True）。
- 自動ロードを無効化したい場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- `.env` のフォーマット: KEY=VALUE、シングル/ダブルクォート対応、`export KEY=VALUE` 形式も扱えます。
- 必須キーは実行時に参照すると ValueError が発生します（例: settings.jquants_refresh_token）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要ワークフローの例）

以下は代表的な操作例です。いずれも Python API を通して行います。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # デフォルトは data/kabusys.duckdb
```

2) 日次 ETL を実行（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得→DB 保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes: 抽出対象の有効銘柄コードセット（例: 全コードセット）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar records saved: {saved}")
```

注意:
- 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema は作成＆接続、get_connection は既存 DB へ接続します。
- J-Quants API 呼び出しは settings.jquants_refresh_token を利用します。事前に環境変数を設定してください。
- generate_signals / build_features はそれぞれ features / signals テーブルを更新します（日付単位で置換するため冪等）。

---

## よく使う API と説明（抜粋）
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.schema
  - init_schema(db_path) : DuckDB ファイルを初期化して接続を返す
  - get_connection(db_path) : 既存 DB への接続

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) : 日次 ETL を実行し ETLResult を返す

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

- kabusys.data.news_collector
  - fetch_rss(url, source) / save_raw_news(conn, articles) / run_news_collection(conn, ...)

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要ファイル・モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義と init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — features 公開インターフェース（再エクスポート）
    - calendar_management.py — 市場カレンダー管理
    - audit.py               — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py     — momentum / value / volatility 計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成ロジック（build_features）
    - signal_generator.py    — シグナル生成ロジック（generate_signals）
  - execution/               — 発注 / execution 関連（空ディレクトリや拡張ポイント）
  - monitoring/              — 監視・Slack 通知等（拡張ポイント）

---

## 開発・運用上の注意
- 本ライブラリは「データ取得・戦略評価」までの機能に重点を置いており、直接の実ブローカー発注は抽象化されています。実際に発注を行う場合は execution 層を実装し、監査ログの要件を満たすよう設計してください。
- DuckDB の型制約や CHECK 制約を多用しています。データの整合性に注意して ETL を設計してください。
- J-Quants の API レートやエラーハンドリング（429 / 5xx）の取り扱いを組み込んでいますが、大量取得や並列化時は追加のレート管理が必要です。
- ニュース取得では SSRF / XML Bomb / サイズ制限などの安全対策を実装しています。外部 RSS を追加する場合はホワイトリスト運用を推奨します。

---

必要に応じて README に含めるサンプル .env.example、CI 実行手順、テストの実行方法（pytest 等）を追加できます。追加希望があれば教えてください。