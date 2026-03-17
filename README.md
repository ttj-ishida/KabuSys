# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。  
主にデータ取得／ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定トレース）などの基盤機能を提供します。

このリポジトリはコアのデータプラットフォーム部分を実装しており、戦略（strategy）・発注（execution）・監視（monitoring）などの拡張ポイントを持ちます。

主な設計方針（抜粋）
- J-Quants API のレート制限（120 req/min）準拠・リトライ・トークン自動リフレッシュ
- DuckDB を用いたローカル永続化（冪等な INSERT／ON CONFLICT ロジック）
- RSS ニュース収集での SSRF／XML-Bomb 対策、トラッキングパラメータ除去
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

---

## 機能一覧
- 環境変数ベースの設定管理（自動でプロジェクトルートの .env を読み込む。無効化可能）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット・再試行・401 リフレッシュ対応
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層のテーブル）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日・期間内営業日取得、夜間更新ジョブ）
- ニュース収集（RSS）と raw_news / news_symbols への保存、記事IDの正規化・重複排除
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（code 内で型ヒントに `X | None` を使用しているため）
- git 等の一般的な開発ツール

1. 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell では別コマンド)
   ```

2. 必要なパッケージをインストール
   本リポジトリには requirements ファイルが含まれていないので主要依存を手動でインストールします。
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクト配布時に setup.cfg / pyproject.toml があれば `pip install -e .` を推奨します）

3. 環境変数を設定
   プロジェクトルートの `.env` またはシステム環境変数で設定します。主な必須変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能利用時）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   オプション:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
   - DUCKDB_PATH: duckdb ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB など（デフォルト data/monitoring.db）

   自動で `.env` / `.env.local` がロードされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. DB スキーマ初期化（DuckDB）
   Python REPL やスクリプトで実行:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # 監査ログ用:
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

---

## 使い方（例）

以下は主な利用例とコードスニペットです。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  # 日次 ETL を今日で実行
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行して raw_news / news_symbols に保存
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 実行済みが前提
  # 既知の銘柄コードセットを渡すと自動で紐付け抽出を行います
  known_codes = {"7203", "6758", "8035"}
  res = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(res)
  ```

- マーケットカレンダーの夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- audit DB を別ファイルとして初期化
  ```python
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/audit.duckdb")
  ```

- 個別 API 呼び出し（J-Quants の token 取得・データ取得）
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を用いて取得
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

ログレベルは環境変数 LOG_LEVEL で制御します（例: LOG_LEVEL=DEBUG）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py  — マーケットカレンダー管理（営業日ロジック・更新ジョブ）
    - audit.py                — 監査ログスキーマ・初期化
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略実装用パッケージ（拡張ポイント）
  - execution/
    - __init__.py             — 発注・約定管理用パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・アラート用パッケージ（拡張ポイント）

---

## 重要な実装ノート / 運用上の注意

- 環境変数の自動読み込み:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を読み込みます。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアント:
  - 内部に固定間隔の RateLimiter を実装。120 req/min を守るようスロットリングします。
  - 408/429/5xx に対する指数バックオフリトライ、401 は自動で refresh_token から再取得して1回だけリトライします。
  - 取得時に fetched_at（UTC）を保存して Look-ahead bias を防止しています。
- ニュース収集:
  - defusedxml を使用して XML パースを安全化。
  - レスポンスサイズ制限（デフォルト 10MB）や gzip 解凍後チェック、リダイレクト先のスキーム/プライベートIP検査（SSRF対策）を実施しています。
  - 記事IDは正規化した URL の SHA-256（先頭32文字）で生成し、冪等性を確保しています。
- DuckDB スキーマ:
  - Raw〜Execution 層まで広範なテーブルを定義。DDL は冪等（CREATE IF NOT EXISTS）です。
  - 監査ログ（audit）テーブルは init_audit_schema / init_audit_db で追加できます。UTC タイムゾーン固定を行います。
- 品質チェック:
  - 各チェックは問題を列挙して返す設計（Fail-Fast ではなく全件検出）。呼び出し元でエラー基準に応じた判断を行ってください。

---

## 開発 / 拡張ポイント
- strategy、execution、monitoring パッケージはプレースホルダです。ここに各戦略やブローカ接続（kabuステーション連携）、監視処理を実装してください。
- duckdb の接続は軽量でスレッド/プロセス運用に注意が必要です。複数プロセスからの同時書き込み等の運用設計は検討してください。
- 本ライブラリはデータ基盤/監査の提供に重心があるため、実際の売買ロジックとブローカ接続実装では追加の安全チェック（資金管理、二重発注防止、障害時のロールバックなど）を実装する必要があります。

---

必要であれば README に含める CI、テスト実行方法や .env.example のテンプレート、具体的な Docker / systemd ジョブの例なども作成できます。どの情報を追加したいか指示してください。