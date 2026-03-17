# KabuSys

日本株自動売買（データプラットフォーム & ETL）用ライブラリ。  
J-Quants や各種 RSS を取り込み、DuckDB に生データ・加工データ・特徴量・監査ログを蓄積するためのモジュール群を提供します。  
設計思想は「冪等性」「トレーサビリティ」「外部 API に対する堅牢性（レート制御・リトライ・SSRF 対策）」です。

---

## 主な機能

- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期）、JPX カレンダーの取得
  - レート制限（120 req/min）の遵守、リトライ（指数バックオフ）、401 時のトークン自動更新
  - DuckDB への冪等保存（ON CONFLICT を使用）
  - 取得時刻（fetched_at）を記録し、Look-ahead Bias を防止

- ニュース収集（news_collector）
  - RSS フィード収集、前処理（URL 除去・空白正規化）
  - URL 正規化・トラッキングパラメータ除去、記事 ID を SHA-256 から生成（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - gzip / レスポンスサイズ上限（10MB）対策、defusedxml による安全な XML パース
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）

- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日から未取得分のみ取得、バックフィル対応）
  - 日次 ETL の統合エントリ（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損、スパイク、重複、日付不整合）を収集して報告

- マーケットカレンダー管理（calendar_management）
  - JPX カレンダーの差分更新ジョブ、営業日判定 / 前後営業日取得 / 期間内営業日列挙

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブルとインデックス定義
  - スキーマ初期化・接続ユーティリティ

- 監査ログ（data.audit）
  - シグナル→発注→約定に至るトレーサビリティ用テーブル群（UUID ベース）
  - 発注の冪等キー / ステータス履歴管理

---

## 動作要件

- Python 3.10 以上（型記法に union 演算子 `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- その他、実際の運用で使用する外部ライブラリ（例: Slack SDK、kabu API クライアント等）はプロジェクトに応じて追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最小例（pip）:
     - pip install duckdb defusedxml
   - 開発パッケージがある場合は requirements / pyproject を参照してインストールしてください。
   - パッケージを editable インストールする場合:
     - pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。自動読み込み機能があり、OS 環境変数よりも下位で `.env.local` は上書きされます。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
   - 自動 env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     - from kabusys.data import schema
       conn = schema.init_schema("data/kabusys.duckdb")
     - またはインメモリ:
       conn = schema.init_schema(":memory:")

6. 監査ログスキーマの初期化（必要時）
   - from kabusys.data import audit
     audit.init_audit_schema(conn)
   - または独立 DB:
     - conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（サンプル）

- 日次 ETL を実行する（基本）
  - from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブを個別に実行する
  - from kabusys.data import news_collector, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    results = news_collector.run_news_collection(conn)
    print(results)  # {source_name: saved_count, ...}

- カレンダーバッチ更新ジョブ
  - from kabusys.data import calendar_management, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    saved = calendar_management.calendar_update_job(conn)
    print("saved:", saved)

- J-Quants クライアントの直接利用例
  - from kabusys.data import jquants_client as jq, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    # トークンは settings から自動取得（.env に JQUANTS_REFRESH_TOKEN を設定）
    records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
    saved = jq.save_daily_quotes(conn, records)
    print("saved", saved)

- DuckDB 接続は必ず schema.init_schema で初期化するか、既存ファイルに接続してからジョブを実行してください。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化

注意: Settings を参照する API は、必須変数が未設定の場合 ValueError を送出します（.env.example を参考に .env を準備してください）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py             — RSS ニュース収集・前処理・保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — カレンダー管理・営業日ロジック
    - schema.py                     — DuckDB スキーマ初期化定義
    - audit.py                      — 監査ログ用スキーマ（signal/order/execution）
    - quality.py                    — データ品質チェック
  - strategy/                       — 戦略層（空のパッケージプレースホルダ）
  - execution/                      — 実行層（空のパッケージプレースホルダ）
  - monitoring/                     — 監視・メトリクス用（プレースホルダ）

---

## 注意事項 / 運用メモ

- J-Quants API 呼び出しはレート制御およびリトライ機構を備えていますが、運用時は API 利用規約・レート制限に注意してください。
- DuckDB に対する INSERT は冪等性を考慮してあり、同一 PK は ON CONFLICT で更新またはスキップされます。
- news_collector は外部 URL を扱うため SSRF や XML Bomb などに注意し、安全対策（すでに導入済み）を理解して運用してください。
- KABUSYS_ENV を "live" に設定すると is_live フラグが True になり、実運用向けの挙動（将来的な制御）を想定しています。テスト時は "development" または "paper_trading" を使用してください。
- 品質チェックは Fail-Fast ではなく問題を収集して返す設計です。ETL の継続/中断判断は呼び出し側で行ってください。

---

必要に応じて、README に実行スクリプト（CLI）の追加や、CI/CD、監視・アラートの導入方法を追記できます。README の補足（.env.example、依存関係一覧、起動用 systemd / Docker 構成など）が必要であれば教えてください。