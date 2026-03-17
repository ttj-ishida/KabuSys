# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ / ミニフレームワークです。  
主にデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ管理、監査ログなどの基盤機能を提供します。

---

## 主な機能

- 環境変数・設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
  - 必須項目は Settings プロパティ経由で取得（未設定時は例外）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ、ページネーション対応
  - データ取得時刻（fetched_at）を保存して Look-ahead Bias を回避
- ニュース収集
  - RSS フィードの取得、前処理、記事ID生成（URL 正規化 → SHA-256）、DuckDB への冪等保存
  - SSRF 対策、gzipサイズチェック、XML パース安全化（defusedxml）
  - 記事と銘柄コードの紐付け（テキスト中の4桁銘柄コード抽出）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit レイヤのテーブル定義と初期化
  - インデックス作成、冪等なスキーマ初期化
- ETL パイプライン
  - 差分更新（最終取得日に基づく自動差分算出）、バックフィル対応、カレンダー先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行して報告
- マーケットカレンダー管理
  - 営業日判定・前後営業日計算・期間内営業日の取得
  - 夜間バッチ（calendar_update_job）による差分更新
- 監査ログ（audit）
  - シグナル→発注→約定までのトレース用テーブル群（order_request_id を冪等キーとして扱う）
  - UTC タイムゾーン、削除抑止（FK は RESTRICT）などトレーサビリティ重視の設計

---

## 必要条件 / 依存パッケージ

- Python 3.10+
  - 型注釈に `X | None` などの構文を使用しているため 3.10 以降を推奨
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```
pip install duckdb defusedxml
```

（プロジェクト実装に応じて他のライブラリが必要になる場合があります。requirements.txt があればその利用を推奨します。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を置く（ライブラリはプロジェクトルートから `.env` / `.env.local` を自動で読み込みます）
   - 主な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化（初回のみ）
   - 例: Python REPL / スクリプトで
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査用スキーマを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（例）

- 設定取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- DuckDB 初期化と日次 ETL 実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルト: 今日を対象に ETL 実行
  print(result.to_dict())
  ```

- J-Quants から株価を直接取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes は銘柄抽出に使う有効な銘柄コードの集合（任意）
  saved_by_source = run_news_collection(conn, known_codes={"7203", "6758"})
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 自動環境読み込みを無効化する（テスト等）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 重要な設計上の注意点 / 動作方針

- J-Quants API のレート制限（120 req/min）に従うため内部でスロットリングを行います。
- ネットワーク障害や一時的なサーバエラーに対してリトライを行い、401 はトークン自動リフレッシュで1回だけ再試行します。
- DuckDB への保存は可能な限り冪等に設計（ON CONFLICT ...）して二重保存を回避します。
- ニュース収集は SSRF・XML Bomb・gzip ブロート等の攻撃を考慮した防御を行っています。
- カレンダー情報がない場合でも曜日ベースのフォールバックを使用して営業日判定を行います。
- ETL／品質チェックは「全件収集」方針で、重大な品質問題が見つかってもできる限り他の処理は継続する設計です（呼び出し元が停止の判断を行う）。

---

## ディレクトリ構成（主要ファイル）

（ソース内の構成を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py            — ETL パイプライン / run_daily_etl 等
    - calendar_management.py — マーケットカレンダーのヘルパーとアップデートジョブ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal/order/execution 系）スキーマ
  - strategy/                 — 戦略モジュール（プレースホルダ）
  - execution/                — 発注実行モジュール（プレースホルダ）
  - monitoring/               — 監視モジュール（プレースホルダ）

---

## 追加情報 / 今後の拡張案

- 発注実行層（execution）と戦略層（strategy）はプレースホルダとして用意されています。実運用での注文送信・ブローカ連携ロジックやリスク管理実装はここに実装します。
- Slack 通知や監視ジョブとの連携機能を追加して、ETL 結果や品質アラートを自動通知する運用が想定されます。
- AI/特徴量レイヤ（features / ai_scores）用のバッチ処理やモデル推論パイプラインを組み込む余地があります。

---

問題点の報告・改善提案や使い方で不明点があれば、収集したいユースケース（ローカル実行、CI、運用サーバ等）を教えてください。具体的な実行スクリプト例や unit-test の雛形も提供できます。