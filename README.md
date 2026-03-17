# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）等の基盤機能を提供します。  
（戦略層・実行層・監視層向けのパッケージ構成を持ち、戦略やブローカー連携は別モジュールで実装できます。）

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境/設定管理
  - .env ファイルと OS 環境変数から自動的に読み込み（プロジェクトルート検出）
  - 必須値未設定時は明示的エラー

- J-Quants データクライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - エラー時の自動リトライ（指数バックオフ、最大3回）
  - 401 の場合はリフレッシュトークンで自動再取得して再試行
  - 取得時刻（fetched_at）を UTC で記録、DuckDB へ冪等保存（ON CONFLICT で更新）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集・前処理・DuckDB へ冪等保存
  - URL 正規化（トラッキングパラメータ除去）と SHA-256 を用いた記事ID生成
  - SSRF 対策（スキーム検証・リダイレクト先検査・プライベートIP拒否）
  - レスポンスサイズ上限・gzip 解凍後サイズチェック、defusedxml を使用した安全な XML パース
  - 記事と銘柄コードの紐付け（簡易的な4桁銘柄コード抽出）

- DuckDB スキーマ管理（kabusys.data.schema / audit）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックスと制約を含む初期化 API（init_schema / init_audit_db）
  - 監査ログ（信号→発注要求→約定）用の専用スキーマを提供

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日から必要分のみ取得）、バックフィルによる後出し修正吸収
  - 日次 ETL のエントリ（run_daily_etl）: カレンダー取得 → 株価取得 → 財務取得 → 品質チェック
  - 品質チェックの結果を集約して呼び出し元で対処可能

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）、重複、スパイク（前日比）、日付不整合（未来日・非営業日）の検出
  - 問題は QualityIssue のリストで返却（error/warning）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日検索・期間内営業日列挙
  - データ有無に応じたフォールバック（market_calendar 未取得時は土日を非営業日扱い）
  - 夜間バッチ更新ジョブ（calendar_update_job）

- 設定 / ロギング
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証
  - 自動で .env / .env.local を読み込み（無効化フラグあり）

---

## 必要条件

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - defusedxml

パッケージはプロジェクトの packaging 設定に依存します。必要に応じて requirements ファイルを用意してください。

---

## セットアップ手順

1. リポジトリをチェックアウト / コピー

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最小）
   ```bash
   pip install duckdb defusedxml
   # または開発用に editable install
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置することで自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意 / デフォルトあり
   - KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   例（.env の一部）
   ```
   JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - プログラムから呼び出す方法（例）:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイルパス or ":memory:"
     conn.close()
     ```
   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     audit_conn.close()
     ```

---

## 使い方（主要な API / 実行例）

- 日次 ETL の実行（Python から直接）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブの実行
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "8306"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- J-Quants の日足取得（テストや単体実行用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(quotes))
  ```

- スキーマ初期化（CLI 風に）
  - 上記の Python スクリプトを使って初期化処理を呼び出してください。プロジェクトに CLI がある場合はそちらを利用できます（本コードベースには CLI 実装は含まれていません）。

---

## 設計上の注意点 / 実装のポイント

- J-Quants クライアントは API レート制御とリトライを備え、安全にページネーション取得を行います。401 は自動でリフレッシュを試みます（ただし無限再帰を防ぐ設計）。
- ニュース収集は SSRF・XML爆弾・メモリDoS 等に配慮した実装（スキームチェック、プライベートIPブロック、最大バイト数制限、defusedxml）です。
- データ保存はいずれも冪等性を重視（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING / INSERT RETURNING を活用）。
- ETL は差分更新とバックフィルを組み合わせ、品質チェックを行いつつ長時間の Fail-Fast を避ける方針です。
- すべてのタイムスタンプは UTC で扱うことを基本としています（監査 DB は TimeZone を UTC に固定）。

---

## ディレクトリ構成

以下はこのコードベースの主要なファイル構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得・保存）
      - news_collector.py          # RSS ニュース収集・前処理・保存
      - schema.py                  # DuckDB スキーマ定義 / init_schema
      - pipeline.py                # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     # マーケットカレンダー管理
      - audit.py                   # 監査ログスキーマ（signal / order / execution）
      - quality.py                 # データ品質チェック
    - strategy/
      - __init__.py                # 戦略層のためのプレースホルダ
    - execution/
      - __init__.py                # 発注 / ブローカー連携 レイヤーのプレースホルダ
    - monitoring/
      - __init__.py                # 監視・メトリクス用プレースホルダ

---

## 今後の拡張ポイント（参考）

- broker 実装（kabuステーション連携）を execution レイヤに追加
- 戦略の実行・バックテストフレームワークの追加（strategy パッケージ）
- Slack 等への通知・アラート機能の実装（monitoring）
- マルチプロセス / 分散 ETL のジョブ管理（Airflow / Prefect 等の統合）
- unit / integration テストの整備（外部 API はモック化してテスト可能）

---

ご不明点や README の追加項目（例: CLI コマンド一覧、サンプル .env.example、デプロイ手順など）をご希望であれば教えてください。