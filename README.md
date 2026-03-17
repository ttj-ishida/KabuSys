# KabuSys

日本株自動売買プラットフォームのコアライブラリ。データ取得（J-Quants、RSS 等）、ETL、データ品質チェック、DuckDB スキーマ、監査ログ管理などを提供します。戦略・発注・モニタリング層の骨組みを含み、実運用（paper/live）および開発（development）環境での利用を想定しています。

---

## 主な目的（概要）
- J-Quants API や RSS から市場データ／ニュースを取得して DuckDB に保存する ETL 基盤
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（JPX）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマと初期化機能
- 将来的な戦略（strategy）、発注（execution）、モニタリング（monitoring）モジュールのための API

---

## 機能一覧
- 環境設定管理（.env 自動ロード、必要環境変数の検証）
- J-Quants クライアント
  - 日足 (OHLCV)、財務データ（四半期 BS/PL）、マーケットカレンダーの取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ対応
  - データ取得日時（fetched_at）記録による Look-ahead Bias 防止
- News Collector
  - RSS フィードの取得・前処理（URL除去・空白正規化）
  - SSRF 対策、XML の安全パース、レスポンスサイズ制限、記事ID の SHA-256 ベース生成
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING）
  - 銘柄コード抽出（テキストから 4 桁コード）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化（init_schema）と接続取得ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日からの差分、バックフィルオプション）
  - 市場カレンダーの先読み
  - 品質チェック統合（quality モジュール）
  - 日次 ETL エントリポイント（run_daily_etl）
- カレンダー管理
  - 営業日判定、前/次営業日検索、夜間カレンダー更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions など監査テーブルの初期化とインデックス
  - UTC タイムゾーン固定、冪等キー設計
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合を検出し QualityIssue リストで返却

---

## 必要な環境変数
以下の環境変数を設定してください（必須は明記）。

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

注意:
- 自動でプロジェクトルートの .env、.env.local を読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## 依存パッケージ（例）
リポジトリに requirements.txt は含まれていませんが、主に以下が必要です：
- Python 3.9+
- duckdb
- defusedxml

お使いの環境に合わせてインストールしてください：
```
pip install duckdb defusedxml
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順（ローカル開発用）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
4. .env を作成（または環境変数を設定）
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き可）。
   - 必須変数を設定してください（上記参照）。
5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで実行：
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
   conn.close()
   ```
6. 監査ログ専用 DB 初期化（必要なら）
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要な API と例）

- 日次 ETL 実行
  - 株価・財務・カレンダーを差分取得して保存し、品質チェックを実行します。
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 市場カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data import schema, calendar_management

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- RSS ニュース収集
  ```python
  from kabusys.data import schema, news_collector

  conn = schema.get_connection("data/kabusys.duckdb")
  # sources は {source_name: rss_url}。省略時は DEFAULT_RSS_SOURCES。
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  conn.close()
  ```

- J-Quants からの日足取得（低レベル）
  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- DuckDB 接続だけ取得して操作したい場合
  ```python
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # SQL 実行
  rows = conn.execute("SELECT COUNT(*) FROM raw_prices").fetchall()
  ```

注意点:
- jquants_client はレート制限、再試行、401 自動更新等の処理を内部で行います。長時間のページネーションでも ID トークンを共有します。
- ニュース収集は SSRF / XML 攻撃 / Gzip Bomb 対策を考慮した実装になっています。

---

## ディレクトリ構成
（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py           # RSS ニュース収集・前処理・保存
      - schema.py                   # DuckDB スキーマ定義・初期化
      - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py      # マーケットカレンダー管理・判定関数
      - audit.py                    # 監査ログテーブル定義・初期化
      - quality.py                  # データ品質チェック
    - strategy/
      - __init__.py                 # 戦略層（将来的な実装場所）
    - execution/
      - __init__.py                 # 発注・ブローカー連携層（将来的な実装場所）
    - monitoring/
      - __init__.py                 # モニタリング層（将来的な実装場所）

---

## 運用／開発上の注意事項
- 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれかに設定してください。is_live/is_paper/is_dev 判定プロパティが提供されています。
- DuckDB の初期化は idempotent（何度呼んでも安全）です。
- ETL は可能な限り idempotent に設計されています（ON CONFLICT DO UPDATE / DO NOTHING を使用）。
- 品質チェックは Fail-Fast ではなく検出結果を返す設計です。呼び出し側で結果に応じたアクション（通知・停止等）を行ってください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト時に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 今後の拡張ポイント（想定）
- strategy パッケージで特徴量からシグナル生成する実装
- execution パッケージで証券会社 API（kabu/station 等）との具体的連携
- monitoring パッケージで Prometheus / Slack 通知や稼働監視
- unit/integration テスト、CI 用設定、パッケージ配布設定（pyproject.toml）

---

もし README に含めてほしい追加の例（cron 設定、Dockerfile、CI ワークフローのサンプルなど）があれば教えてください。必要に応じてサンプルファイルも作成します。