# KabuSys

日本株向け自動売買基盤ライブラリ — データ取得・ETL・品質チェック・監査ログまでをカバーするモジュール群

バージョン: 0.1.0

概要
---
KabuSys は日本株の自動売買システム構築を支援する Python モジュール群です。主に以下を提供します。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS ニュース収集と記事の前処理、銘柄紐付け
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間更新ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査（signal→order→execution のトレーサビリティ）用テーブル群

主な設計方針
- API レート制限遵守（J-Quants: 120 req/min）
- リトライ（指数バックオフ）、401 はトークン自動リフレッシュして再試行
- DuckDB への保存は冪等（ON CONFLICT を使用）
- NewsCollector は SSRF / XML Bomb / Gzip Bomb 対策を実装
- 品質チェックは Fail-Fast ではなく問題を収集して呼び出し元に判断を委譲

機能一覧
---
- 環境設定管理（.env 自動ロード、必須変数チェック）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - マーケットカレンダー取得
  - トークン取得（リフレッシュトークン経由）
- News Collector
  - RSS 取得、正規化、前処理
  - 記事ID生成（URL正規化→SHA-256）
  - DuckDB への冪等保存、銘柄抽出と紐付け
- スキーマ管理
  - DuckDB の全テーブル／インデックス定義と初期化（init_schema）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）: カレンダー→株価→財務→品質チェック
  - 差分更新、バックフィル対応
- カレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）
- 監査ログ（signal_events / order_requests / executions）初期化
- 品質チェック（欠損・スパイク・重複・日付不整合）

前提（Prerequisites）
---
- Python 3.9+（型注釈には union types や typing 拡張を使用）
- 必要ライブラリ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

セットアップ手順
---
1. リポジトリをチェックアウトし、パッケージをインストール（開発モードなど）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[all]"  # requirements が用意されている場合
   # または最低限
   pip install duckdb defusedxml
   ```

2. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須の環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意／デフォルト:
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : environment（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL             : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

3. DuckDB スキーマ初期化
   - 初回はスキーマを作成します:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリも作成されます
   ```

使い方（代表的な例）
---

- J-Quants の ID トークンを取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って POST して取得
  ```

- 日次 ETL を実行（市場カレンダーの先読み、差分取得、品質チェック）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  print(result.to_dict())
  ```

- 単体 ETL ジョブ（株価のみ差分取得）:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date

  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- RSS ニュース収集と保存:
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes はテキストから抽出する有効銘柄コードの集合（任意）
  result = run_news_collection(conn, known_codes={"7203", "6758"})
  print(result)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved {saved} calendar records")
  ```

- 監査ログ用 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

環境設定（重要）
---
- 自動 .env 読み込み:
  - パッケージ起点（__file__ の親ディレクトリ群）で .git または pyproject.toml を見つけ、プロジェクトルートの .env / .env.local を読み込みます。
  - テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- settings API:
  - from kabusys.config import settings でアクセス可能。プロパティとして各種設定（トークン・パスワード・DB パス・env 等）を取得できます。
  - settings.env は "development" / "paper_trading" / "live" のいずれかで、is_live / is_paper / is_dev プロパティも提供します。

ディレクトリ構成
---
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存関数）
    - news_collector.py       — RSS 収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py  — マーケットカレンダー管理・夜間更新ジョブ
    - audit.py                — 監査ログ（signal/order/execution）定義と初期化
    - quality.py              — データ品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py             — 戦略レイヤ（実装箇所）
  - execution/
    - __init__.py             — 発注・約定管理（実装箇所）
  - monitoring/
    - __init__.py             — 監視（実装箇所）

注意事項・運用のヒント
---
- API 呼び出しはレート制御を厳守する実装ですが、運用時は J-Quants のポリシーに従ってください。
- ETL の品質チェックは問題を収集して返す設計です。重大（error）な問題発見時に ETL を中断するかどうかは運用側で制御してください。
- NewsCollector は外部 URL をフェッチするため、社内ネットワークから外部に出る許可やプロキシ設定を確認してください。
- DuckDB ファイルはアクセス並列性に注意してください（運用環境でのバックアップ方針を検討してください）。
- 監査ログは削除しない前提の設計です。容量管理・アーカイブ戦略を検討してください。

開発・拡張
---
- strategy/ および execution/ は拡張ポイントです。新しい戦略やブローカー連携はこれらの層に実装します。
- テスト容易性のため、jquants_client の id_token 注入や news_collector._urlopen のモックが想定されています。
- 追加の RSS ソースや品質チェックを追加することでシステムを強化できます。

ライセンス / 貢献
---
（ここにライセンス記載・貢献方法を追加してください）

問い合わせ
---
実装や運用に関する質問があれば README の issue やプロジェクトの連絡先に問い合わせてください。

--- 

この README は現状のコードベース（src/kabusys 配下）を基に作成しています。実運用前に .env の整備、API クレデンシャルの管理、ログ設定、DB バックアップ方針を必ず整備してください。