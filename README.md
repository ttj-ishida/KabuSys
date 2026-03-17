# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買 / データプラットフォーム向けライブラリです。J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB ベースのスキーマと ETL パイプライン、データ品質チェック、監査ログ（発注〜約定トレーサビリティ）などを提供します。

主な設計方針：
- API レート制御・リトライ・トークン自動更新を組み込んだ堅牢なデータ取得
- DuckDB を用いた冪等性のある永続化（ON CONFLICT / RETURNING 等を活用）
- SSRF / XML Bomb / メモリ DoS 等に対するセキュリティ対策を考慮した実装
- ETL と品質チェックを切り分け、運用でのエラー耐性を重視

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` 自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL 除去・空白正規化）
  - URL 正規化と SHA-256 ベースの冪等記事 ID
  - SSRF 保護（リダイレクト検査・プライベートIP拒否）
  - defusedxml を使用した XML パース
  - DuckDB への冪等保存・銘柄紐付け（news_symbols）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 必要なインデックス定義
  - 初期化ユーティリティ（init_schema / get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェックの順
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・期間内営業日列挙
  - 夜間カレンダー更新ジョブ（calendar_update_job）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル
  - order_request_id を冪等キーとして設計
  - init_audit_schema / init_audit_db を提供

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue 型で問題を集約し呼び出し側が判定可能

- strategy / execution / monitoring: パッケージプレースホルダ（拡張用）

---

## 動作環境・依存

- Python 3.10 以上（型記法に | を使用）
- 主な依存パッケージ（プロジェクトで利用する場合）
  - duckdb
  - defusedxml

（実装によっては標準ライブラリの urllib 等のみで動作する箇所もありますが、DuckDB と defusedxml は必須で使うことを想定しています。）

インストール例（pip）:
```
pip install duckdb defusedxml
```

パッケージ配布がある場合は requirements.txt / pyproject.toml を使ってインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を用意すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（kabusys.config.Settings に依存）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabu API パスワード（実行系で使用）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - 任意（デフォルトあり）
     - KABUSYS_ENV            — development / paper_trading / live（default: development）
     - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
     - DUCKDB_PATH            — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite パス（default: data/monitoring.db）

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   conn.close()
   ```

6. 監査DB（分離して管理したい場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/kabusys_audit.duckdb")
   conn_audit.close()
   ```

---

## 使い方（簡易例）

- J-Quants の ID トークンを取得する
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して取得
  ```

- 日次 ETL を実行する（例: 今日分）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # スキーマ初期化済み接続を取得
  result = run_daily_etl(conn)  # target_date を指定することも可
  print(result.to_dict())
  conn.close()
  ```

- カレンダー更新ジョブ（夜間バッチ向け）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- RSS ニュース収集と保存
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.quality import run_all_checks

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue)
  conn.close()
  ```

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py               — J-Quants API クライアント（取得・保存）
      - news_collector.py               — RSS ニュース収集と保存
      - schema.py                       — DuckDB スキーマ定義・初期化
      - pipeline.py                     — ETL パイプライン（日次 ETL 等）
      - calendar_management.py          — マーケットカレンダー管理
      - audit.py                         — 監査ログスキーマ初期化
      - quality.py                       — データ品質チェック
    - strategy/
      - __init__.py                      — 戦略レイヤ（拡張用）
    - execution/
      - __init__.py                      — 発注実装（拡張用）
    - monitoring/
      - __init__.py                      — 監視関連（拡張用）

その他:
- .env.example（プロジェクトルートに置く想定、存在しない場合は .env.example を参照して作成）
- pyproject.toml または setup.py（パッケージ配布用）

---

## 開発・運用上の注意点

- 設定読み込み:
  - デフォルトで OS 環境変数 > .env.local > .env の順で適用されます。
  - テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- API レート制御:
  - J-Quants は 120 req/min を想定しています。jquants_client は固定間隔のスロットリングでこれに従いますが、運用負荷が高い場合は ETL スケジュール調整が必要です。

- セキュリティ:
  - news_collector は SSRF・XML 脅威を軽減する実装を含みますが、運用ネットワークの制約（プロキシや内部フィルタ）に応じた追加検証を推奨します。

- DuckDB:
  - init_schema は冪等に設計されています。既存データベースでも安全に呼べますが、運用時にはバックアップを推奨します。

- トランザクション:
  - news_collector の保存処理や audit の初期化にはトランザクション管理があります。DuckDB のトランザクションモデル（ネスト不可等）に注意してください。

---

## 貢献・拡張

- strategy / execution / monitoring パッケージは拡張ポイントとして空のパッケージを用意しています。独自戦略・ブローカー連携・監視機能を実装してください。
- バグ修正・機能追加は PR を歓迎します。テストや docstring を充実させていただけると助かります。

---

この README はリポジトリ内のソースコード（config / data/*.py）を元に作成しています。追加で CLI スクリプトやユーティリティを用意することで運用が容易になります。必要であれば、起動スクリプト例や systemd / cron ジョブのサンプルも作成しますのでお知らせください。