# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。J-Quants や kabuステーション など外部 API からデータを収集・保存し、ETL・品質チェック・カレンダー管理・ニュース収集・監査ログなどの基盤処理を提供します。

主な設計方針は「冪等性」「トレーサビリティ」「セキュリティ（SSRF / XML 脆弱性対策）」および「API レート制限・リトライ制御の厳守」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須項目チェック・環境別フラグ（development / paper_trading / live）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの取得
  - レート制限（120 req/min）・再試行（指数バックオフ）・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得・前処理（URL 除去・空白正規化）
  - トラッキングパラメータ除去、記事ID を SHA-256 先頭 32 文字で生成
  - defusedxml を使った XML 攻撃対策、SSRF 対応（リダイレクト検査 / プライベートIP拒否）
  - DuckDB への冪等保存（INSERT ... RETURNING）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分・バックフィル）→ 保存 → 品質チェック
  - 日次 ETL のエントリポイント（run_daily_etl）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（急騰/急落）、重複、日付不整合の検出
  - 問題は QualityIssue として収集（致命度に応じて呼び出し元で扱う）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema / get_connection を提供
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティテーブル／インデックス定義
  - init_audit_schema / init_audit_db を提供

---

## 必要条件 / 依存関係

（プロジェクトの packaging に依存しますが、主要なランタイム依存は以下です）

- Python 3.10+
- duckdb
- defusedxml

必要に応じて別途 duckdb のネイティブビルドが必要になる環境があります。依存関係は requirements.txt / pyproject.toml に記載してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成します。

   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)
     - python -m pip install -U pip

2. 依存パッケージをインストールします（プロジェクトに requirements.txt がある前提）。

   - python -m pip install -r requirements.txt

   最低限は:
   - pip install duckdb defusedxml

3. 環境変数を設定します。
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config の自動ロード）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨される環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=xxxxx         # 必須（J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD=xxxxx             # 必須（kabuステーション API のパスワード）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   - SLACK_BOT_TOKEN=xoxb-...            # 必須（通知用）
   - SLACK_CHANNEL_ID=C...               # 必須
   - DUCKDB_PATH=data/kabusys.duckdb     # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db      # 任意
   - KABUSYS_ENV=development             # development | paper_trading | live
   - LOG_LEVEL=INFO                      # DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env の書式は標準的な KEY=VALUE 形式に対応（export プレフィックスや引用符、インラインコメントの一部処理をサポート）。

4. データベースの初期化（DuckDB）

   - Python REPL / スクリプトで:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

   - 監査ログ（audit）用テーブルを追加する場合:
     - from kabusys.data.audit import init_audit_schema
     - init_audit_schema(conn)
     または専用 DB を初期化:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（サンプル）

以下は主要機能の簡単な利用例です。

- DuckDB スキーマ初期化

  - Python:
    - from kabusys.data.schema import init_schema
    - from kabusys.config import settings
    - conn = init_schema(settings.duckdb_path)

- J-Quants の ID トークンを取得（手動）

  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）

  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

  run_daily_etl は内部で J-Quants クライアントを呼び、差分取得・保存・品質チェックを行います。戻り値は ETLResult（取得件数・保存件数、品質問題・エラー一覧を含む）です。

- RSS ニュース収集と保存

  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  - print(res)  # {source_name: saved_count, ...}

  news_collector は RSS の取得 → 前処理 → raw_news への冪等保存 → 必要に応じて銘柄紐付けを行います。SSRF や XML 攻撃対策を組み込んでいます。

- カレンダー更新バッチ（夜間ジョブ）

  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print("saved:", saved)

- 監査ログの初期化（audit テーブル）

  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)

---

## 環境変数と挙動の注意点

- 自動 .env 読み込み
  - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して決定します。見つからない場合は自動ロードをスキップします。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 環境（KABUSYS_ENV）
  - 有効値: development / paper_trading / live
  - settings.is_live / is_paper / is_dev プロパティで参照できます。

- ログレベル（LOG_LEVEL）
  - DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## ディレクトリ構成

プロジェクトは src/kabusys 配下に実装されています。重要ファイル・モジュールは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                     # DuckDB スキーマ定義・初期化
    - jquants_client.py             # J-Quants API クライアント（取得・保存）
    - news_collector.py             # RSS ニュース収集モジュール（SSRF/defusedxml 対応）
    - pipeline.py                   # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py        # カレンダー（営業日）管理・夜間更新ジョブ
    - audit.py                      # 監査ログ（トレーサビリティ）テーブル
    - quality.py                    # データ品質チェック
  - strategy/
    - __init__.py                   # 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                   # 発注・実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                   # 監視・メトリクス（拡張ポイント）

（上記は現状の実装ファイル一覧です。strategy / execution / monitoring は拡張可能な箇所として用意されています。）

---

## セキュリティと運用上の注意

- ニュース収集では defusedxml を使用して XML に関する攻撃を防止しています。さらに HTTP(S) のみを許可し、リダイレクト先のスキームやプライベート IP を検査して SSRF を防ぎます。
- J-Quants API 呼び出しはレート制限（120 req/min）を守るため内部でスロットリングを行います。過剰アクセスを避けてください。
- DuckDB へは冪等性を保つインサート（ON CONFLICT）で保存する設計です。外部からの DB 操作は想定していないため、手動での改変は慎重に行ってください。
- すべてのタイムスタンプは原則 UTC を想定しています（監査ログなどでは明示的に SET TimeZone='UTC' を設定します）。

---

## 貢献・拡張

- 新たなデータソース、戦略、取引実行（ブローカー連携）を追加する場合はそれぞれのサブパッケージ（data / strategy / execution）にモジュールを追加してください。
- ETL のロギング、品質チェックルール、スキーマは運用に合わせて拡張可能です。データの一貫性を保つため、スキーマ変更時はマイグレーション方針を検討してください。

---

README は以上です。必要があれば以下を提供します：
- example .env.example のテンプレート
- 実行スクリプト（CLI）や systemd / cron のサンプルジョブ
- 詳細な API リファレンス（各関数のサンプル呼び出し）