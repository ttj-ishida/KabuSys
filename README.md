# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォームの核となるライブラリ群です。  
J-Quants API からの市場データ取得、DuckDBベースのスキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、監査ログ（発注→約定のトレース）などを提供します。

主な目的は「再現可能で安全なデータ収集」「冪等な DB 保存」「監査可能な発注トレーサビリティ」を実現することです。

---

## 機能一覧

- 設定・環境変数管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須変数チェック（settings オブジェクト）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制御（120 req/min 固定スロットリング）
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、XML デコード安全化（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、受信サイズ制限
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁コード）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に分離したテーブル定義
  - インデックス、外部キー、整合性チェックを考慮した初期化関数
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からバックフィル）
  - 市場カレンダーの先読み
  - 品質チェック連携（欠損・重複・スパイク・日付不整合）
  - 日次 ETL エントリ（run_daily_etl）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日取得、期間内営業日リスト
  - 夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定をトレースする監査テーブル群（冪等キー、UTC タイムスタンプ）
  - 監査テーブル初期化・専用 DB 初期化 API
- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠損）／スパイク（前日比閾値）／重複／日付不整合チェック
  - QualityIssue のリストを返し、呼び出し側で対応を判断可能

---

## セットアップ手順

前提:
- Python 3.9+ を想定（typing の一部機能を利用）
- duckdb, defusedxml が必要

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （必要に応じてプロジェクトに requirements.txt を追加して pip install -r requirements.txt を利用してください）

4. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード（発注系機能で使用）
- SLACK_BOT_TOKEN : Slack 通知を使う場合
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID

任意 / デフォルトあり
- KABUS_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH : デフォルト "data/monitoring.db"
- KABUSYS_ENV : one of "development", "paper_trading", "live"（デフォルト "development"）
- LOG_LEVEL : "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）

サンプル .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API・例）

以下は主要なユースケースの簡単な例です。実際はロギング設定や例外処理を加えてください。

1) DuckDB スキーマ初期化（デフォルトパスを使う場合）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（既知の銘柄リストがある場合）
```python
from kabusys.data import news_collector
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 例
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) J-Quants の ID トークン取得（明示的に使う場合）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使う
```

5) 監査ログテーブルの初期化（監査専用 DB を作る）
```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

6) カレンダー操作の例
```python
from kabusys.data import calendar_management, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
d = date(2025, 1, 1)
is_trading = calendar_management.is_trading_day(conn, d)
next_day = calendar_management.next_trading_day(conn, d)
```

注意点:
- jquants_client は内部でレート制限とリトライを実施します。アプリ側からは追加の制御が不要な設計です。
- news_collector は外部 URL の検証（スキーム・プライベートホストチェック・最大応答サイズ）を行い、SSRF や XML Bomb に配慮しています。
- save_* 関数群は冪等性（ON CONFLICT）を担保します。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys）:

- __init__.py
- config.py
  - settings: 環境変数の読み込み・検証・自動 .env ロード
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、fetch_* / save_* 関数、get_id_token
  - news_collector.py
    - RSS 収集・前処理・DB 保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl、run_prices_etl、…）
  - calendar_management.py
    - マーケットカレンダー管理（is_trading_day, next_trading_day 等）
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）の初期化
  - quality.py
    - データ品質チェック（欠損、スパイク、重複、日付不整合）
- strategy/
  - __init__.py
  - （戦略実装用のモジュールを配置する想定）
- execution/
  - __init__.py
  - （発注・約定処理の実装を配置する想定）
- monitoring/
  - __init__.py
  - （監視・メトリクス周りの実装を配置する想定）

---

## 設計上の注意点・セキュリティ

- 環境変数の自動読み込みはプロジェクトルートを .git / pyproject.toml で検出します。CI やテストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API クライアントは 120 req/min のレート制限に合わせたスロットリングを行います。外部実装でさらに複雑なキュー制御が必要なら上位で調整してください。
- news_collector は SSRF、XML Bomb、レスポンスサイズ上限などの保護を実装していますが、運用環境では更にネットワークレベルの制限（アクセス先の最小化）を推奨します。
- DuckDB に保存する際は多くの操作が ON CONFLICT / トランザクションで冪等化されています。外部からの DB 書き換えやスキーマ変更は注意してください。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されています。データ保持ポリシーに基づいて運用してください。

---

## 今後の拡張案（参考）

- execution モジュールに実際の証券会社 API（kabuステーション等）統合と発注リトライ/状態管理を追加
- strategy モジュールに複数戦略のバージョン管理・評価用 API を追加
- モニタリング / アラート（Slack 連携など）の実装強化
- テスト向けユーティリティ（モック用 hook など）の整備

---

質問や README の追加要望（インストール手順の詳細、CI 設定例、環境変数のテンプレート化など）があれば教えてください。README をより利用しやすく調整します。