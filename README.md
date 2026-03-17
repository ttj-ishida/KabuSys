# KabuSys

日本株向け自動売買基盤（KabuSys）のリポジトリ向け README。  
本ドキュメントはプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL・品質管理・監査・発注管理を含む自動売買基盤のライブラリ群です。  
主に以下を提供します。

- J-Quants API からの市場データ取得（株価日足・財務・マーケットカレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いた層化スキーマ（Raw / Processed / Feature / Execution）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 簡易な設定管理（.env 自動読み込み、環境別設定）

設計においては、API レート制御・リトライ・冪等性（ON CONFLICT）・SSRF 対策・XML 脆弱性対策（defusedxml）などの実運用を想定した耐性を重視しています。

---

## 主な機能一覧

- 設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
  - 環境（development / paper_trading / live）・ログレベルの検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価（日次 OHLCV）、財務データ、マーケットカレンダー取得
  - レート制限（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回、401 時トークン自動更新）
  - DuckDB への冪等保存関数（save_*）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応）、XML パースは defusedxml を使用
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策（スキーム/プライベートIP 排除）
  - 記事を raw_news に冪等保存、銘柄コード抽出と news_symbols への紐付け

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル定義
  - init_schema(), init_audit_schema() による初期化（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): 市場カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 差分取得、backfill による後出し修正吸収、品質チェックの集約結果返却

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比急変）、重複、日付不整合（未来日・非営業日）検出
  - QualityIssue を返却し呼び出し側でアクションを決定可能

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルを提供
  - 発注の冪等キー・ステータス遷移管理・UTC タイムスタンプ運用

---

## セットアップ手順

前提:
- Python 3.10 以上（型記法に | None 等を使用）
- pip が使える環境

1. リポジトリをクローンしてパッケージをインストール
   - 開発環境であればソース直下で editable インストール:
     - pip install -e .
   - 必要なパッケージ（例）
     - duckdb
     - defusedxml
   - （実際の requirements はプロジェクト側で管理してください）

2. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git がある位置）に `.env` または `.env.local` を配置すると自動で読み込まれます（起動時）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN=（必須）
     - KABU_API_PASSWORD=（必須）
     - KABU_API_BASE_URL=（任意、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN=（必須）
     - SLACK_CHANNEL_ID=（必須）
     - DUCKDB_PATH=（任意、デフォルト data/kabusys.duckdb）
     - SQLITE_PATH=（任意、デフォルト data/monitoring.db）
     - KABUSYS_ENV=development|paper_trading|live（デフォルト development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

3. DuckDB スキーマ初期化
   - 例: Python REPL やスクリプトで
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)
   - 監査ログ（audit）を追加する場合:
     - from kabusys.data.audit import init_audit_schema
     - init_audit_schema(conn)

4. ログ設定
   - 環境変数 LOG_LEVEL を設定してログ出力レベルを制御してください。

---

## 使い方（簡単なコード例）

以下はライブラリの主要な利用例です。実行は適切に環境変数をセットした上で行ってください。

- DuckDB 初期化（初回のみ）
  - from kabusys.data.schema import init_schema
    from kabusys.config import settings
    conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- ニュース収集を実行する
  - from kabusys.data.news_collector import run_news_collection
    # known_codes は有効な銘柄コードのセットを渡すと抽出と紐付けを行う
    stats = run_news_collection(conn, known_codes={"7203","6758"})
    print(stats)

- J-Quants の ID トークン取得 & API 呼び出し（テスト時）
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()
    rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=None)

注意点:
- run_daily_etl 等は内部で例外をキャッチして継続処理を行います。戻り値の ETLResult でエラー・品質問題を確認してください。
- テスト時に .env の自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（settings インスタンス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、レート制御、リトライ、save_* 関数
    - news_collector.py
      - RSS 取得・正規化・SSRF 対策・raw_news への保存、銘柄抽出
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）と init_audit_schema
  - strategy/
    - __init__.py
    - （戦略モジュールを配置する想定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携を実装するモジュールを配置する想定）
  - monitoring/
    - __init__.py
    - （監視・アラート用モジュールを配置する想定）

ファイルごとの概要は各モジュールの docstring を参照してください。スキーマは DataPlatform.md / DataSchema.md 等の設計文書に基づいています（リポジトリ内にある場合はそちらも参照してください）。

---

## 運用上の注意・ベストプラクティス

- 環境区分（KABUSYS_ENV）を正しく設定し、実運用（live）では十分なログ監視と安全弁（例えばポジション制限・ドローダウン検出）を実装してください。
- J-Quants のレート制限とトークン寿命に配慮してください。jquants_client はレート制御と自動トークン更新を備えていますが、上位でさらに制御する場合は id_token を注入して運用してください。
- ニュース収集では外部 RSS を取得するため SSRF・XML bomb に対する対策を実装済みですが、追加のネットワークポリシー（プロキシ・IP ホワイトリスト等）を検討してください。
- DuckDB のファイルはバックアップを取り、監査ログは削除しない方針で運用してください（監査トレースを保持するため）。

---

## 参考（よく使う API）

- 初期化
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.audit.init_audit_schema(conn)
- ETL
  - kabusys.data.pipeline.run_daily_etl(...)
- データ取得
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - kabusys.data.jquants_client.fetch_market_calendar(...)
- ニュース収集
  - kabusys.data.news_collector.run_news_collection(...)
- 品質チェック
  - kabusys.data.quality.run_all_checks(conn, ...)

---

必要に応じて README の補足（インストール手順の詳細、CI 設定、.env.example のテンプレート、実行時の推奨ログ設定や監視方法）を追加できます。どの項目を詳しく追記するか指定してください。