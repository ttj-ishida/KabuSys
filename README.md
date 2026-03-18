# KabuSys

日本株自動売買プラットフォーム向けライブラリ（KabuSys）。  
J-Quants / kabuステーション 等の外部APIと連携して、データ取得（ETL）・品質チェック・ニュース収集・監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 要件（依存関係）
- セットアップ手順
- 環境変数（必須/任意）
- 使い方（サンプル）
- よく使うAPI一覧（関数・目的）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。  
主に以下を目的としています。

- J-Quants API からの市場データ（日足・財務・マーケットカレンダー等）の差分取得と DuckDB への冪等保存
- RSS からのニュース収集と記事の銘柄紐付け（SSRF・XML攻撃対策、トラッキングパラメータ除去など）
- ETL パイプライン（差分取得、バックフィル、品質チェック）の提供
- 市場カレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（signal → order → execution のトレース可能なテーブル群）用スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント：
- API レート制御（J-Quants: 120 req/min 固定間隔スロットリング）
- リトライ（指数バックオフ、401 の場合はトークン自動リフレッシュ）
- Look-ahead-bias 回避（fetched_at の記録）
- DuckDB への保存は冪等（ON CONFLICT を利用）

---

## 主な機能

- data.jquants_client: J-Quants API クライアント／取得関数／DuckDB への保存
- data.news_collector: RSS フィード取得、前処理、raw_news への冪等保存、銘柄抽出
- data.schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
- data.pipeline: 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
- data.calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ／カレンダー夜間更新ジョブ
- data.quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- data.audit: 監査ログ用スキーマと初期化（signal / order_requests / executions）
- strategy, execution, monitoring: パッケージ枠（将来的に戦略・発注・監視ロジックを配置）

---

## 要件（依存関係）

推奨 Python バージョン: 3.10 以上（typing における | 型などを利用）  

主要 Python パッケージ（例）:
- duckdb
- defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を記載してください。）

インターネット接続が必要（J-Quants API / RSS フィード）。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動
   - 本コードは src/ 配下のパッケージ構成を想定しています。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - その他必要なパッケージがある場合は追記してください。

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化可能）。
   - 必須の環境変数については次節を参照。

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで init_schema() を実行して DB ファイルを作成します（デフォルトは data/kabusys.duckdb）。例は「使い方」セクション参照。

---

## 環境変数（主要）

必須（動作に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で ID トークンを取得するため）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

任意 / デフォルトあり:
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")。デフォルト "development"
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")。デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動読み込みを抑止

データベースパス（環境変数未指定時はデフォルト）:
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"

※ .env.example がある場合はそれを参考に .env を作成してください（コード内で .env.example が参照される記述はありますが、実装によりファイル名はプロジェクトに合わせてください）。

---

## 使い方（サンプル）

以下は簡単な利用例です。Python スクリプトや REPL で実行します。

1) スキーマ初期化（DuckDB 作成）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants から差分取得して保存、品質チェックまで実行）
```python
from kabusys.data.pipeline import run_daily_etl
# conn は上で init_schema した DuckDB 接続
result = run_daily_etl(conn)  # オプションで target_date, id_token, etc. を指定可
print(result.to_dict())
```

3) ニュース収集ジョブを実行（RSS フィードを収集して raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# sources を None にすればデフォルト RSS ソースを使用
res_map = run_news_collection(conn, known_codes={"7203", "6758", "9432"})
print(res_map)  # {source_name: 新規保存件数}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

5) 監査ログスキーマ初期化（必要に応じて）
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で取得した接続
init_audit_schema(conn, transactional=True)
```

---

## よく使うAPI（抜粋）

- kabusys.data.schema.init_schema(db_path)  
  DuckDB スキーマを初期化して接続を返す。

- kabusys.data.jquants_client.get_id_token(refresh_token=None)  
  J-Quants の ID トークンを取得（refresh token から）。

- kabusys.data.jquants_client.fetch_daily_quotes(...)  
  株価日足を API から取得（ページネーション対応）。

- kabusys.data.jquants_client.save_daily_quotes(conn, records)  
  raw_prices テーブルへ冪等保存。

- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)  
  日次 ETL のメイン関数（calendar → prices → financials → 品質チェック）。

- kabusys.data.news_collector.fetch_rss(url, source, timeout=30)  
  指定 RSS を取得して記事リストを返す。

- kabusys.data.news_collector.save_raw_news(conn, articles)  
  raw_news に記事を冪等保存（挿入された article id のリストを返す）。

- kabusys.data.quality.run_all_checks(conn, target_date=None, reference_date=None)  
  全品質チェックを実行して QualityIssue のリストを返す。

- kabusys.data.calendar_management.is_trading_day(conn, d) / next_trading_day / prev_trading_day / get_trading_days  
  市場カレンダー関連のユーティリティ。

- kabusys.data.audit.init_audit_db(db_path) / init_audit_schema(conn)  
  監査ログ用 DB / スキーマ初期化。

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）をモジュール内で制御しています。長時間の大量取得や並列化には注意してください。
- get_id_token はリフレッシュトークンから ID トークンを取得します。401 発生時は自動で一度リフレッシュしますが、リフレッシュ失敗時のハンドリングは呼び出し側でログを確認してください。
- ニュース収集は SSRF・XML ボム対策（スキーム検証、プライベートIPブロック、defusedxml、最大受信バイト制限）を実装していますが、運用時は許可するソースの管理を行ってください。
- DuckDB に対する DDL / インデックス作成は初回に時間を要する場合があります。init_schema を定期的に呼ばないでください（冪等ですが不要なオーバーヘッドになります）。
- ETL は各ステップで個別に例外を捕捉して継続する設計です。ETLResult.errors / quality_issues を見てシステム側でアクションを取ってください。

---

## ディレクトリ構成

以下は主要ファイル一覧（src/kabusys 配下）です。将来的に strategy / execution / monitoring に機能追加される想定です。

- src/kabusys/
  - __init__.py
  - config.py                              # 環境変数・設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py                     # J-Quants API クライアント（取得・保存）
    - news_collector.py                     # RSS 取得・記事処理・raw_news 保存
    - schema.py                             # DuckDB スキーマ定義・初期化
    - pipeline.py                           # ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py                # カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                              # 監査ログスキーマ（signal/order_requests/executions）
    - quality.py                            # データ品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py                            # 将来的に戦略ロジックを配置
  - execution/
    - __init__.py                            # 発注・約定管理・ブローカー連携等を配置
  - monitoring/
    - __init__.py                            # 監視用ユーティリティ（稼働監視やメトリクス）

---

以上が README のサマリです。  
必要であれば、以下を追記できます（希望があれば指示してください）:
- pyproject.toml / requirements.txt の具体例
- CI / テストの実行方法
- 実運用のデプロイ例（cron / Airflow / prefect など）やシークレット管理のベストプラクティス
- 詳細な API ドキュメント（各関数の引数・戻り値の表）