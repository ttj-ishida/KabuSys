# KabuSys

日本株向けの自動売買基盤ライブラリ。J-Quants / kabuステーション 等の外部 API からデータを取得して DuckDB に保存し、ETL・品質チェック・ニュース収集・監査ログなどを提供します。戦略（strategy）・発注（execution）・監視（monitoring）モジュールを組み合わせて自動売買システムを構築するための基盤です。

バージョン: 0.1.0

## 概要（Project Overview）

- J-Quants API から株価日足・財務データ・市場カレンダーを取得し、DuckDB に階層化されたスキーマ（Raw / Processed / Feature / Execution）で保存します。
- RSS フィードからニュース記事を収集して正規化・保存し、記事と銘柄コードの紐付けを行います。
- ETL パイプライン（差分取得・バックフィル・品質チェック）を提供し、運用での後出し修正やデータ品質管理を想定しています。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用のスキーマ初期化をサポートします。
- セキュリティ・堅牢性を重視した設計（API レート制御・再試行・トークン自動リフレッシュ・SSRF 対策・XML デフューズ等）。

## 主な機能（Features）

- 環境変数 / .env 自動ロード（.env、.env.local、優先順位あり、無効化オプションあり）
- J-Quants API クライアント
  - レートリミット（120 req/min）の厳守
  - 再試行（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 株価（daily_quotes）、財務（statements）、マーケットカレンダー取得
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（RSS）
  - URL 正規化（トラッキングパラメータ削除）、記事 ID を SHA-256 で生成（先頭32文字）
  - XML デフューズ（defusedxml）で安全にパース
  - SSRF 対策（スキーム検証、プライベートホストブロック、リダイレクト検査）
  - 読み込みサイズ制限（メモリ DoS 防止）、gzip 解凍、DB へのチャンク挿入（トランザクション）
  - 記事と銘柄コードの紐付け（news_symbols）
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（run_daily_etl）
  - カレンダー → 株価 → 財務 の順に差分取得・保存
  - バックフィル（既存最終日から数日前まで再取得）で後出し修正を吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定・次/前営業日探索・夜間アップデートジョブ）
- 監査ログ（audit）用スキーマ初期化（init_audit_db）
- データ品質チェック（quality.run_all_checks）

## 要件（Requirements）

- Python 3.10+
- 必要なパッケージ（例）:
  - duckdb
  - defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml に依存を記載してください）

## 環境変数（主な設定）

Settings クラスで参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL (任意) — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` → `.env.local` の順で読み込みます。
- テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ手順（Setup）

1. Python と依存パッケージをインストール
   - Python 3.10 以上を用意
   - pip で依存をインストール（例）
     pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）

2. リポジトリをクローン / チェックアウトし、開発環境にインストール（任意）
   - pip install -e . など（パッケージ化している場合）

3. 環境変数を設定
   - ルートに .env を作成するか、環境変数を直接設定します。
   - 必須項目（上記）を設定してください。

4. DuckDB スキーマ初期化
   - データベースファイルを指定してスキーマを作成します（親ディレクトリがなければ自動作成）。
   - 例: Python REPL / スクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("/path/to/data/kabusys.duckdb")

5. 監査ログ（audits）専用 DB（任意）
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("/path/to/data/kabusys_audit.duckdb")

## 使い方（Usage）

以下は代表的な利用例です。

- 設定読み込み・接続初期化:
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)

- J-Quants の id_token を取得する:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得

- 日次 ETL を実行する（カレンダー・株価・財務・品質チェック）:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数で日付や id_token を指定可能
  print(result.to_dict())

- ニュース収集ジョブを実行する:
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット（抽出に使用）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}

- 市場カレンダー夜間更新ジョブ（個別呼び出し）:
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- 監査スキーマを既存接続に追加する:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # transactional オプションあり

- 品質チェックを単体で実行する:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

注意:
- jquants_client は内部で API レート制御と再試行・トークン自動リフレッシュを行います。
- news_collector は SSRF 対策・XML De-fuse・受信サイズ制限などの安全策を講じています。
- 多くの保存関数は冪等（ON CONFLICT）になっています。繰り返し実行しても重複は回避される設計です。

## ディレクトリ構成（Directory Structure）

プロジェクト内の主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       # RSS ニュース収集・前処理・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py  # マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py                # 監査ログ（signal/order_request/execution）スキーマ初期化
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py             # 戦略実装用プレースホルダ（拡張ポイント）
  - execution/
    - __init__.py             # 発注ロジック用プレースホルダ（拡張ポイント）
  - monitoring/
    - __init__.py             # 監視・メトリクス・通知用プレースホルダ

（実際のリポジトリでは tests/ や scripts/ などが追加されることが想定されます）

## 開発上の注意事項 / 補足

- 型ヒントに Python 3.10 のユニオン演算子（|）を使用しています。Python 3.10 以上を推奨します。
- 自動 .env ロードはプロジェクトルート検出（.git または pyproject.toml）に依存します。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の接続はスレッドセーフ性や同時トランザクションに関して注意が必要です。長時間のバックグラウンドジョブや並列処理時には接続管理を設計してください。
- news_collector._urlopen は単体テストのために差し替え可能な設計になっています（モック可能）。
- jquants_client はページネーション対応およびモジュールレベルでのトークンキャッシュを持ちます。必要に応じて id_token を明示的に注入できます（テスト容易化）。

## ライセンス / コントリビューション

この README はコードベースに基づく概要説明です。実運用での利用・変更はプロジェクトのライセンス・セキュリティ要件に従ってください。貢献・バグ報告はリポジトリの issue にて受け付けてください。

---

何か特定の使い方（ETL のスケジュール化、kabu API 連携例、Slack 通知の実装例など）について詳しいサンプルが必要であれば教えてください。