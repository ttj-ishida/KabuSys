# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）など、取引およびバックテスト／運用に必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止

- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層を含む詳細な DDL
  - 冪等なテーブル作成・インデックス作成機能（init_schema）

- ETL パイプライン
  - 差分更新（最終取得日からの差分自動計算）
  - backfill による後出し修正への耐性
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集（RSS）
  - RSS フィードの安全な取得（SSRF/圧縮体制御/XML インジェクション対策）
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - 銘柄コード抽出と news_symbols への紐付け

- マーケットカレンダー管理
  - JPX の営業日/半日/SQ 日管理、営業日判定ヘルパー（next/prev/get など）
  - calendar_update_job による夜間差分更新

- 監査ログ（Audit）
  - シグナル → 発注リクエスト → 約定 のトレーサビリティを保持する監査テーブル群
  - order_request_id による冪等性、すべて UTC タイムスタンプ保存

- データ品質チェックモジュール
  - 欠損・異常スパイク・重複・日付不整合チェック（run_all_checks）

---

## セットアップ手順

前提：
- Python 3.9+（型ヒントや一部機能を利用しているため）を推奨
- system により DB ファイルを保存する権限が必要

1. リポジトリをクローン／配置
   - 既にプロジェクトルート（.git または pyproject.toml）を置いておくことで `.env` 自動ロードが機能します。

2. インストール（開発環境）
   ```
   # プロジェクトルートで
   python -m pip install -e .[all]
   ```
   ※ pyproject.toml / setup.cfg がある想定です。最低限必要な外部依存は:
   - duckdb
   - defusedxml
   - （標準ライブラリ以外の HTTP ライブラリは使っていません）

3. 環境変数の準備
   - プロジェクトルートに `.env` や `.env.local` を置くと自動的に読み込まれます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

   主要な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxx
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 省略可（デフォルト）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb        # 省略時のデフォルト
   SQLITE_PATH=data/monitoring.db        # 省略時のデフォルト
   KABUSYS_ENV=development               # development|paper_trading|live
   LOG_LEVEL=INFO                        # DEBUG|INFO|WARNING|ERROR|CRITICAL
   ```

---

## 使い方（主要 API と実行例）

以下は Python スクリプトや REPL からの利用例です。import はパッケージ名 `kabusys` を使用します。

- DuckDB スキーマ初期化（フルスキーマ）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # :memory: も可
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の ID トークン取得（自動で settings から refresh token を使う）
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token が必須
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema してある前提
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL ジョブを手動で実行
  ```python
  # 株価だけ
  from kabusys.data import pipeline
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

  # カレンダー更新ジョブ
  from kabusys.data import calendar_management as cm
  saved = cm.calendar_update_job(conn)
  ```

- ニュース収集
  ```python
  from kabusys.data import news_collector as nc
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")

  # フィードから取得して raw_news へ保存
  articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = nc.save_raw_news(conn, articles)

  # 新規記事に対して銘柄紐付けを行う（known_codes: 有効な銘柄コード集合）
  known_codes = {"7203", "6758", "9984"}  # 例
  for nid in new_ids:
      # 仮に extract_stock_codes を使うなら記事本文を渡して抽出する実装例
      pass

  # または一括ジョブ
  nc.run_news_collection(conn, known_codes=known_codes)
  ```

- データ品質チェック（手動）
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None, reference_date=None)
  for i in issues:
      print(i)
  ```

- 設定（settings）参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env, settings.is_live, settings.log_level)
  ```

備考：
- J-Quants API は 120 req/min の制限があります。クライアント側で固定間隔レートリミッタとリトライを内蔵しています。
- get_id_token はリフレッシュトークンから ID トークンを取得し、401 発生時は自動で一回リフレッシュして再試行します。

---

## 環境変数と自動 .env ロードの挙動

- 自動ロード対象ファイル（プロジェクトルート検出時）:
  - `.env`（override=False、既存 OS 環境変数は上書きされない）
  - `.env.local`（override=True、ただし OS 環境変数は上書きされない）
- 自動ロードを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 必須環境変数の取得関数は settings がラップしており、未設定時は ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。

有効な KABUSYS_ENV の値:
- development
- paper_trading
- live

LOG_LEVEL は標準的なログレベル文字列（DEBUG/INFO/...）を期待します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / 設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - schema.py                  # DuckDB スキーマ定義と init_schema
      - jquants_client.py          # J-Quants API クライアント（取得・保存ロジック）
      - pipeline.py                # ETL パイプライン（run_daily_etl 等）
      - news_collector.py          # RSS ニュース収集・保存・銘柄抽出
      - calendar_management.py     # マーケットカレンダー管理・営業日ヘルパー
      - quality.py                 # データ品質チェック
      - audit.py                   # 監査ログ / トレーサビリティ初期化
      - pipeline.py                # ETL orchestration
    - strategy/                     # 戦略関連（未実装ファイル群のエントリ）
      - __init__.py
    - execution/                    # 発注・約定等（未実装ファイル群のエントリ）
      - __init__.py
    - monitoring/                   # 監視用（空の __init__）
      - __init__.py

---

## 運用上の注意点 / 実装に関する重要事項

- API レート制限とリトライ
  - jquants_client は 120 req/min に合わせた固定間隔レートリミットを実装しています（モジュール単位のスロットリング）。
  - リトライは最大 3 回、指数バックオフ、408/429/5xx が対象。429 の場合は Retry-After ヘッダを優先します。

- セキュリティ対策（news_collector）
  - defusedxml を使った XML パースで XXE 等を防止
  - リダイレクト先やホストを検査しプライベートアドレス（SSRF）をブロック
  - レスポンスサイズ上限（10 MB）と Gzip 解凍後のサイズチェック（Gzip bomb 対策）

- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を利用して冪等性を確保
  - 監査ログでは order_request_id を冪等キーとして使用

- 日付・タイムゾーン
  - 監査スキーマではタイムゾーンを UTC に固定（init_audit_schema は SET TimeZone='UTC' を実行）
  - fetch 時刻や fetched_at は UTC（ISO8601）で記録されます

---

## 開発・拡張のヒント

- テスト時に環境の自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- news_collector のネットワーク呼び出しは `_urlopen` をモックして差し替え可能
- jquants_client は id_token を引数で注入できるため、テストで固定トークンを渡して API 呼び出しを分離できます
- DuckDB を :memory: で使用すると単体テストが容易になります

---

以上が README の概要です。必要であれば以下の追加を作成できます：
- .env.example のテンプレート
- よくあるトラブルシューティング（例: token 無効時の対処）
- CI 用のスクリプトサンプル（ETL の定期実行、監査 DB のローテーション等）