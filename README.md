# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB ベースのスキーマ管理、ETL・品質チェック、マーケットカレンダー管理、監査ログ管理などを備えています。

## 概要
KabuSys は以下を目的としたコンポーネント群を提供します。

- J-Quants から株価・財務・カレンダーを安全かつ冪等に取得して DuckDB に保存する
- RSS フィードからニュースを安全に収集・正規化して保存する
- データ品質チェック（欠損・重複・スパイク・日付不整合）を行う
- マーケットカレンダーに基づく営業日計算・夜間更新ジョブを提供する
- 発注/約定フローの監査用スキーマを初期化する
- 環境変数管理（.env 自動読み込み）と設定アクセスを提供する

設計上の特徴:
- J-Quants API 用のレートリミッタ・リトライ・トークン自動リフレッシュを実装
- DuckDB に対する冪等な INSERT（ON CONFLICT ...）でデータの一貫性を確保
- RSS 収集で SSRF・XML ボム対策を実施（defusedxml、ホスト/IP検査、サイズ制限）
- ETL は差分更新・バックフィル・品質チェックを組み合わせた設計

---

## 主な機能一覧
- 環境設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルートから自動ロード（無効化可能）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、JPX カレンダー取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 自動リフレッシュ
  - DuckDB への冪等保存関数（save_*）
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS の取得・パース・前処理（URL除去・空白正規化）
  - URL 正規化と SHA-256 ベースの id の生成で冪等保存
  - SSRF 対策、gzip サイズ上限、XML パースの堅牢化
  - 銘柄コード抽出と news_symbols 紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義・初期化
  - インデックス定義を含む init_schema(db_path)
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー・株価・財務の差分取得、保存、品質チェック
  - 差分更新 + backfill による後出し修正吸収
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日計算、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査スキーマ初期化（init_audit_schema / init_audit_db）
- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合チェック（run_all_checks）

---

## セットアップ手順

1. Python 環境を準備（推奨: 3.10+）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージをインストール
   - 必要な主な依存: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. プロジェクト ルートに .env を作成
   - .env.example を参考にして以下のような必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - (任意) DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
   - .env はプロジェクトルート（.git や pyproject.toml がある場所）から自動読み込みされます。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB 用データディレクトリを用意（必要に応じて）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path で変更可能）

---

## 使い方（簡単なサンプル）

下記は基本的な利用例です。実行前に .env を準備し、DuckDB にスキーマを初期化してください。

- スキーマ初期化（DuckDB ファイルを作成）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集と銘柄紐付け
```python
from kabusys.data import news_collector
# known_codes は銘柄コードの集合（例: {"7203", "6758", ...}）
res = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data import calendar_management
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- 監査ログスキーマ初期化（監査専用DB）
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

- 設定の参照
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
```

注意点:
- jquants_client は内部でレート制御とリトライを行います。大量のリクエストを並列に投げないでください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- news_collector._urlopen などいくつかの内部関数はテストでモック可能です。

---

## ディレクトリ構成

主要なモジュールとファイル構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       # RSS ニュース収集・正規化・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（run_daily_etl など）
    - calendar_management.py  # マーケットカレンダー更新・営業日ロジック
    - audit.py                # 監査ログテーブル定義・初期化
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要な公開 API:
- kabusys.config.settings
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.jquants_client.fetch_* / save_*
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.calendar_management.calendar_update_job / is_trading_day / next_trading_day / prev_trading_day
- kabusys.data.audit.init_audit_schema / init_audit_db
- kabusys.data.quality.run_all_checks

---

## 運用上の注意・補足
- 環境変数は .env/.env.local から自動で読み込まれます。CI／テスト環境では自動ロードを無効化してください。
- J-Quants の認証はリフレッシュトークン経由です。get_id_token により idToken を取得し、内包のキャッシュでページネーション間の再利用を行います。
- DuckDB のトランザクション管理はモジュール内で適切に行われていますが、外部から複数処理を組み合わせる際はトランザクション境界に注意してください（audit.init_audit_schema は transactional オプションあり）。
- RSS 収集では外部リソースを扱うため、ネットワーク・パースエラーは想定内です。run_news_collection はソース単位でエラーを隔離します。

---

## 今後の拡張案（参考）
- 実際の発注連携（kabuステーション / ブローカー接続）の execution 層の実装
- Slack / モニタリング用通知ラッパーの実装（monitoring）
- 各種バッチの CLI / cron ラッパー提供
- テレメトリ・メトリクス収集（Prometheus 等）

---

ご不明な点や README に加えたいサンプルがあれば教えてください。README の補足（例: .env.example の具体例、CI 設定、ユニットテストの実行例）も作成できます。