# KabuSys

日本株の自動売買プラットフォーム向けユーティリティライブラリ群です。  
データ取得（J-Quants）、ニュース収集、ETL パイプライン、DuckDB スキーマ/初期化、品質チェック、マーケットカレンダー管理、監査ログなど、戦略実行に必要な基盤機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 特徴 (機能一覧)

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数を Settings から取得

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット制御（120 req/min）
  - リトライ（指数バックオフ、最大 3 回）、401 のトークン自動リフレッシュ
  - フェッチ時間（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードから記事を取得し前処理して raw_news に保存
  - URL 正規化（トラッキングパラメータ削除）および記事 ID を SHA-256 で生成
  - SSRF 対策、受信サイズ制限、defusedxml による XML 攻撃防御
  - 記事と銘柄コードの紐付け機能（news_symbols）

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層を含む完全な DDL 集
  - テーブル作成、インデックス作成、接続取得ユーティリティ

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新（最終取得日ベース）、バックフィル（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック呼び出し（欠損・重複・スパイク・日付不整合）
  - 日次 ETL のエントリポイント `run_daily_etl`

- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - 営業日判定、前後営業日の取得、期間の営業日リスト取得
  - 夜間バッチ更新 job（calendar_update_job）

- 品質チェック (`kabusys.data.quality`)
  - 欠損データ検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - 検出結果は QualityIssue オブジェクトで返却

- 監査ログ（トレーサビリティ）(`kabusys.data.audit`)
  - signal_events / order_requests / executions の監査テーブル定義と初期化
  - 発注から約定までの UUID ベースのトレーサビリティ確保

---

## 要件

- Python 3.10 以上（型ヒントの Union 表記などに依存）
- 主要依存ライブラリ:
  - duckdb
  - defusedxml

（標準ライブラリのみで動く機能もありますが、DuckDB・XML関連機能を使うには上記が必要です）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境作成（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - pip で最低限の依存を入れる例:
     ```
     pip install duckdb defusedxml
     ```
   - もし requirements.txt / pyproject.toml がある場合はそちらを利用してください。

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、自動で読み込まれます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト時など）。
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動ロードを無効化（値が設定されていれば無効）
     - KABUSYS_* 等は Settings で拡張可能
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

5. データベース初期化（DuckDB）
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # パスは任意
     ```
   - 監査ログテーブルを別 DB に作る場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（例）

- J-Quants のトークン取得（明示的に呼ぶ場合）
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 日次 ETL を実行する（DuckDB 接続を渡す）
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集を実行
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # sources を省略すると DEFAULT_RSS_SOURCES が使われます
  counts = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
  print(counts)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 簡易的なクイックスタート（スクリプトの流れ）
  1. init_schema() で DuckDB を初期化
  2. run_daily_etl() を呼んでデータ取得→保存→品質チェック
  3. run_news_collection() を呼んでニュース収集

---

## 設計上の注意点 / 実装のポイント

- レート制限とリトライ
  - J-Quants クライアントは 120 req/min（最小間隔 0.5s）を守る固定スロットリング実装があります。
  - ネットワークエラー / 408 / 429 / 5xx に対する指数バックオフリトライ（最大 3 回）。
  - 401 を検出した場合、リフレッシュトークンで ID トークンを再取得して 1 回だけ再試行します。

- データの冪等性
  - DuckDB への保存は基本的に ON CONFLICT（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。ETL の再実行に対し安全です。

- ニュース収集の安全性
  - XML パースに defusedxml を使用して XML-based 攻撃対策。
  - SSRF 対策としてリダイレクト先のスキーム・ホスト検査、内部アドレスの拒否。
  - レスポンスサイズ上限（10 MB）や Gzip 解凍後のチェックもあります。

- マーケットカレンダーの扱い
  - market_calendar が未取得のときは曜日ベース（土日除外）のフォールバック。
  - DB に値があれば優先して使用します。next/prev_trading_day は最大探索日数制限があります。

- 環境変数自動ロード
  - プロジェクトルートはこのファイル位置から .git または pyproject.toml をさかのぼって検出します。見つからない場合は自動ロードをスキップします。

---

## トラブルシューティング

- 環境変数が読み込まれない
  - `.env` をプロジェクトルートに置くか、`KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認してください。
  - 自動ロードを無効にしている場合は手動で export / set を行う必要があります。

- J-Quants の認証エラー
  - `JQUANTS_REFRESH_TOKEN` が正しいか、期限切れでないか確認してください。
  - 401 を受けた場合は自動で refresh を試みますが、refresh が失敗すると例外になります。

- DuckDB のテーブルが見つからない
  - 初回は `kabusys.data.schema.init_schema()` を実行してテーブルを作成してください。

---

## ディレクトリ構成

このリポジトリの主要ファイル/モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（取得 + DuckDB 保存）
      - news_collector.py  — RSS ニュース収集・保存・銘柄抽出
      - schema.py  — DuckDB スキーマ定義と init_schema
      - pipeline.py  — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — カレンダー管理 / calendar_update_job
      - audit.py  — 監査ログ用スキーマ初期化
      - quality.py  — データ品質チェック
    - strategy/
      - __init__.py  — 戦略層（拡張ポイント）
    - execution/
      - __init__.py  — 発注/実行層（拡張ポイント）
    - monitoring/
      - __init__.py  — 監視用（将来的な拡張ポイント）

上記以外に設定ファイル（.env.example など）やドキュメント（DataPlatform.md 等）をプロジェクトに追加して運用してください。

---

## 今後の拡張ポイント（参考）

- 実際の発注実装（kabu ステーション / ブローカー連携）
- Slack 等への通知ラッパー（monitoring モジュール）
- 戦略実装例（strategy モジュールに複数戦略）
- 単体テスト・統合テストの充実（外部 API をモックしてテスト可能な設計）

---

必要であれば README にチュートリアル的なフルワークフロー（初期化 → ETL → 戦略 → 発注）や .env.example のテンプレートを追加します。どの情報を優先的に追記したいか教えてください。