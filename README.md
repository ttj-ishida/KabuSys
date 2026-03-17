# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群。データ取得（J-Quants）、ETL、データスキーマ（DuckDB）、ニュース収集、品質チェック、監査ログなど、アルゴリズムトレーディング基盤の主要機能を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT / DO UPDATE）で安全に保存
- API レート制御・リトライ・自動トークン更新を実装
- ニュース収集は SSRF / XML 攻撃対策や受信サイズ制限を実施
- データ品質チェックを組み込み、ETL の信頼性を高める

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得
  - レートリミッタ、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存用の save_* 関数
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック（quality モジュール連携）
  - 日次 ETL 実行エントリポイント run_daily_etl
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - init_schema / get_connection
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（URL 正規化 → SHA-256 ハッシュ）
  - SSRF 対策、defusedxml を用いた安全な XML パース、受信サイズ制限
  - raw_news, news_symbols への冪等保存ロジック
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・範囲内営業日取得・夜間更新ジョブ
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue による問題レポート
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル群
- パッケージ分割
  - strategy / execution / monitoring のためのプレースホルダ（拡張用）

---

## 必要条件

- Python 3.9+
- 主要依存ライブラリ（抜粋）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt がある場合はそちらを使用してください）

例（pip）:
```
pip install duckdb defusedxml
```

---

## 環境変数（主要なもの）

以下はコード内で参照される主要環境変数です。必須は README 内で明示します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション用 API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先: OS 環境 > .env.local > .env
  - 自動読み込みを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. (推奨) 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   ※ プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用
4. 環境変数を設定
   - 例: プロジェクトルートに `.env` を作成
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 機密情報は `.env.local` に置き、`.gitignore` で管理することを推奨
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログを別 DB に分ける場合:
     ```python
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```
   - 既存接続に監査スキーマを追加する場合:
     ```python
     from kabusys.data import schema, audit
     conn = schema.init_schema("data/kabusys.duckdb")
     audit.init_audit_schema(conn)
     ```

---

## 使い方（主要な API と実行例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```python
  from kabusys.data import pipeline, schema
  from datetime import date

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集とデータベース保存
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # 既知の有効銘柄コードセット（例）
  known_codes = {"7203", "6758", "6501"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants から日次株価を直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(saved)
  ```

注意点:
- run_daily_etl / 各 run_* 関数は内部で例外を捕捉して継続する設計です。返り値の ETLResult.errors / quality_issues を確認して運用判断してください。
- J-Quants API へのリクエストはレート制御・自動リトライ・401 の自動トークン更新を行います。id_token の明示注入も可能（テスト時など）。

---

## ディレクトリ構成

大まかなパッケージ構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース取得・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - calendar_management.py — 市場カレンダー管理・ヘルパ
    - audit.py               — 監査ログ（signal/order/execution）
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略ロジック（拡張用）
  - execution/                — 発注・ブローカー連携（拡張用）
  - monitoring/               — 監視・アラート（拡張用）

各モジュールに詳しい docstring と設計方針が含まれているため、コードを参照してください。

---

## セキュリティと運用上の注意

- ニュース収集:
  - defusedxml を使い XML の脆弱性を低減
  - リダイレクト先のスキーム検査、プライベートアドレス判定で SSRF を防止
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）でメモリ DoS を回避
- J-Quants クライアント:
  - API レート制限（120 req/min）を固定間隔スロットリングで遵守
  - 401 を受けた場合はトークン自動リフレッシュ（1 回）して再試行
- DB:
  - スキーマは冪等性を重視（ON CONFLICT / DO UPDATE / DO NOTHING）
  - 監査ログは削除しない前提（FK と制約）でトレース性を確保
- テスト:
  - 自動 .env 読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
  - news_collector._urlopen などはモック可能に設計されています

---

## 参考・今後の拡張

- strategy / execution / monitoring パッケージは拡張ポイントです。独自の投資戦略、発注戦略、監視ルールを実装してください。
- Slack 通知、Prometheus などの監視連携は monitoring に追加できます。
- ブローカー接続（kabu ステーション等）との統合は execution レイヤーに実装してください。

---

不明点があれば、どの機能についてのサンプルが欲しいか（例: ETL フローの細かい使い方、news_collector のテスト方法、監査ログの活用方法など）を教えてください。必要に応じて具体的なコード例や運用手順を追加で作成します。