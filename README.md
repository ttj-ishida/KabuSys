# KabuSys

日本株自動売買プラットフォームのコアライブラリ（データ収集・ETL・スキーマ・監査・ニュース収集など）。

このリポジトリは、J-Quants API 等から市場データや財務データ、RSS ニュースを取得して DuckDB に格納し、品質チェックやカレンダー管理、監査ログ（発注→約定のトレーサビリティ）を提供するモジュール群を含みます。

---

## 主な特徴（機能一覧）

- 環境変数/設定管理
  - .env / .env.local を自動ロード（プロジェクトルートは `.git` または `pyproject.toml` を探索）
  - 必須設定値チェック（未設定時は ValueError）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務、JPX マーケットカレンダー取得
  - レート制限（120 req/min）を守る RateLimiter
  - 401 の自動トークンリフレッシュ、リトライ（指数バックオフ）
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT … DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、XML の安全パース（defusedxml 使用）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ハッシュで記事ID生成
  - SSRF 対策（スキーム/ホスト検証、リダイレクト時の検査、受信サイズ制限）
  - raw_news に冪等保存、news_symbols に銘柄紐付け

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含むテーブル群を定義・初期化
  - インデックス作成、init_schema による自動作成

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日 + backfill 日数の差分）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック呼び出し（欠損/スパイク/重複/日付不整合）
  - 日次 ETL の統合 run_daily_etl

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日算出、トレーディングデイズ取得
  - カレンダー夜間更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル、トレーサビリティ設計
  - init_audit_db による監査DB初期化（UTC タイムゾーン設定）

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合を検出し QualityIssue オブジェクトで返却

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部記法から）
- pip が利用可能

1. リポジトリをクローン
   - 例:
     git clone <your-repo-url>
     cd <repo>

2. 仮想環境を作成（推奨）
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（アプリ実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - オプション:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite (data/monitoring.db)
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…
   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

---

## 使い方（主要 API / 実行例）

以下は Python REPL やスクリプトから呼ぶ例です。

- DuckDB スキーマ初期化
  - すべてのテーブルを作成して DuckDB 接続を返します。
  - 例:
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー + 品質チェック）
  - 例:
    from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブ
  - RSS フィードを取得して raw_news に保存します。
  - 例:
    from kabusys.data import news_collector, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
    print(results)

- カレンダー夜間更新ジョブ
  - 例:
    from kabusys.data import calendar_management, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    saved = calendar_management.calendar_update_job(conn)
    print(f"saved={saved}")

- 監査用 DB 初期化（監査ログ専用 DB を使う場合）
  - 例:
    from kabusys.data import audit
    conn = audit.init_audit_db("data/audit.duckdb")

- J-Quants からの生データ取得（低レベル API）
  - 例:
    from kabusys.data import jquants_client as jq
    id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
    records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点:
- J-Quants API のレート制限（120 req/min）を尊重するため、jquants_client は内部でスロットリングを行います。
- jquants_client は 401 を検知すると内部でリフレッシュトークンを使って id_token を更新し自動リトライします（ただし無限再帰を避ける設計）。
- news_collector は SSRF や XML ボム対策を多数実装していますが、外部入力・カスタムフィードには注意してください。

---

## ディレクトリ構成

リポジトリの主要ファイル／モジュール（抜粋）:

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得 + DuckDB 保存）
  - news_collector.py        — RSS ニュース収集・前処理・DB 保存
  - schema.py                — DuckDB スキーマ定義と init_schema
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py   — 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py                 — 監査ログ（signal / order / execution）の定義と初期化
  - quality.py               — データ品質チェック（欠損/スパイク/重複/日付不整合）
- strategy/
  - __init__.py              — 戦略レイヤ（未実装のプレースホルダ）
- execution/
  - __init__.py              — 発注/実行レイヤ（未実装のプレースホルダ）
- monitoring/
  - __init__.py              — 監視関連（プレースホルダ）

（上記は実装済みファイルを中心に示しています。strategy/execution/monitoring はパッケージ用の初期化ファイルを含みます）

---

## 環境変数の自動読み込みの挙動

- 読み込み優先順位:
  OS 環境変数 > .env.local > .env
- 自動読み込みはプロジェクトルート（__file__ の親から .git または pyproject.toml を探索）を基準に行います。見つからない場合は自動ロードをスキップします。
- テスト等で自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 開発上の注意 / 設計ポリシー（抜粋）

- API クライアントはレート制限・リトライ・トークン更新の自動化を行い、Look-ahead Bias を避けるため取得時刻（fetched_at）を UTC で記録します。
- DuckDB への挿入は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING 等）。
- ニュース収集では URL の正規化・トラッキングパラメータ除去で同一記事の検出精度を向上させ、XML 関連の攻撃に対する防御を実装しています。
- 品質チェックは Fail-Fast ではなく全チェックを実行し、呼び出し側で結果に応じた対処（アラート・停止等）を行う設計です。

---

## ライセンス・貢献

- 本リポジトリのライセンス情報がある場合はプロジェクトルートの LICENSE を参照してください。
- バグ報告・改善提案は Issue を立ててください。

---

必要であれば、README に以下を追加できます:
- 具体的な .env.example ファイル（テンプレート）
- CI 用の実行コマンド例（cron で ETL 実行など）
- 戦略・発注フローの使用例（strategy/execution レイヤのサンプルコード）