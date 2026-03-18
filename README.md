# KabuSys

日本株自動売買システム用ライブラリ（パッケージ）KabuSysのリポジトリ用 README。

この README はコードベース（src/kabusys）を元に作成しています。開発者向けにプロジェクト概要、機能一覧、セットアップ手順、使い方（主な API の例）、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームの基盤ライブラリです。主に次の責務を持ちます。

- J-Quants API から市場データ（株価日足・財務データ・マーケットカレンダー）を取得するクライアント
- DuckDB を用いたデータスキーマ定義と永続化（Raw/Processed/Feature/Execution 層）
- ETL（差分更新・バックフィル・品質チェック）パイプライン
- RSS フィードからニュース記事を収集し、記事→銘柄紐付けを行うニュースコレクタ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

設計上のポイント（抜粋）:
- API リクエストはレート制限厳守（J-Quants: 120 req/min）とリトライ（指数バックオフ）を実装。
- データ取得時点（fetched_at）を UTC で記録して Look-ahead Bias を防止。
- DuckDB への保存は冪等に行い、ON CONFLICT 句で重複更新を処理。
- RSS 取得では SSRF/XML Bomb/サイズ上限などセキュリティ対策を実装。

---

## 機能一覧

主なモジュールと機能:

- kabusys.config
  - .env / .env.local / 環境変数から設定を読み込み。
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。無効化フラグあり。

- kabusys.data.jquants_client
  - J-Quants API クライアント（token refresh、ページネーション、リトライ、レート制限）。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）。

- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution 層）。
  - init_schema(db_path) でテーブルとインデックスを作成。

- kabusys.data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェック）を提供。
  - run_daily_etl() によりカレンダー→株価→財務→品質チェックを順に実行。
  - 差分取得ロジック: 最終取得日を基にバックフィル期間を自動計算。

- kabusys.data.news_collector
  - RSS 取得、記事正規化、記事ID生成（正規化URL の SHA-256 の先頭 32 文字）。
  - preprocess_text、extract_stock_codes（4桁銘柄コード抽出）。
  - save_raw_news / save_news_symbols（DuckDB への保存、トランザクション単位での処理）。

- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）と QualityIssue レポート。
  - run_all_checks() でまとめて実行。

- kabusys.data.calendar_management
  - market_calendar の夜間更新ジョブ、営業日判定と next/prev_trading_day 等のユーティリティ。

- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）初期化。
  - init_audit_schema / init_audit_db を提供。

---

## セットアップ手順

以下は開発環境でライブラリを利用するための推奨手順です。

1. リポジトリをクローン

   git clone <repository-url>
   cd <repository-root>

   （config モジュールは .git または pyproject.toml を見て自動で .env をロードするため、プロジェクトルートを適切に保ってください。）

2. Python 仮想環境を作成して有効化（任意だが推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール

   このコードベースで使用されている主な外部依存:
   - duckdb
   - defusedxml

   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。）

4. 環境変数（.env）の準備

   プロジェクトルートに .env（必要に応じて .env.local）を配置します。例:

   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   注意:
   - config.py は起動時に自動で .env をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能）。
   - .env.local は .env より優先して上書きされます。

---

## 使い方（主な API 例）

以下はライブラリの主要機能を呼び出すためのサンプルコード例です。実際はプロジェクト固有のランナーやジョブスケジューラから呼ぶことを想定しています。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- RSS ニュース収集ジョブの実行（ニュースを収集して raw_news, news_symbols に保存）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に用いる有効な銘柄コードの集合を渡す（省略可能）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count}
```

- 監査ログ用スキーマ初期化

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants から日足を直接取得して保存する（テストや単発実行向け）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

ログ出力レベルは環境変数 LOG_LEVEL で制御されます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 重要な挙動・注意点

- 環境変数の自動読み込み:
  - config.py はプロジェクトルートを .git または pyproject.toml から探し、.env と .env.local を自動で読み込みます。
  - 自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
  - settings オブジェクト（kabusys.config.settings）から各設定を取得できます。必須値がないと ValueError を送出します。

- J-Quants API:
  - レート制限（120 req/min）とリトライロジックを実装しています。
  - 401 受信時はリフレッシュトークンを使って id_token を自動更新して再試行します（1 回のみ）。
  - 取得データには fetched_at を UTC ISO8601 で保存しており、いつデータを知ったかを追跡できます。

- RSS ニュース収集:
  - URL 正規化（utm 等の追跡パラメータ除去）→ 正規化 URL の SHA-256（先頭32文字）で記事 ID を生成し、冪等性を確保します。
  - defusedxml を使い XML 攻撃を回避、SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）を実装。
  - レスポンスサイズ上限（10MB）を超える場合はスキップします。

- DuckDB スキーマ:
  - init_schema は冪等的にテーブル・インデックスを作成します。
  - audit スキーマは init_audit_schema / init_audit_db で追加できます（UTC タイムゾーン設定を行います）。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主要ファイルと簡単な説明:

- src/kabusys/__init__.py
  - パッケージ定義。バージョン情報等。

- src/kabusys/config.py
  - 環境変数 / .env 管理、Settings クラス（設定アクセス）。

- src/kabusys/data/
  - jquants_client.py
    - J-Quants API クライアント、fetch_* / save_* を実装。
  - news_collector.py
    - RSS 収集、前処理、記事ID生成、DuckDB 保存ロジック。
  - schema.py
    - DuckDB の DDL 定義（Raw/Processed/Feature/Execution 層）、init_schema/get_connection。
  - pipeline.py
    - ETL パイプライン（run_daily_etl 他）。
  - calendar_management.py
    - カレンダー更新と営業日ユーティリティ（is_trading_day 等）。
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）DDL と初期化。
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付整合性）。
  - __init__.py

- src/kabusys/strategy/
  - __init__.py（将来的な戦略実装場所）

- src/kabusys/execution/
  - __init__.py（発注/約定・ブローカー連携等の実装場所）

- src/kabusys/monitoring/
  - __init__.py（監視・アラート連携等の実装場所）

---

## 今後の拡張ポイント（参考）

- ブローカー連携（kabuステーション API）を execution パッケージに実装して注文送信/状態同期を行う。
- Slack 通知機能（設定は config に存在）を統合して ETL 結果や品質アラートを送る。
- テストカバレッジ拡張（jquants_client のネットワーク部分はモック可能な設計になっている）。
- ストラテジー層で feature / ai_scores を読み、signal を生成して execution 層に渡すフローの実装。

---

この README はコードから読み取れる実装に基づいて作成しました。実行環境や CI / デプロイ手順、追加の依存関係はプロジェクト固有の設定（pyproject.toml / requirements.txt）があればそれに従ってください。質問や追加したいドキュメント項目があれば教えてください。