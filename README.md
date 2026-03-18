# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ部分）

このリポジトリは、データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDBスキーマおよび監査ログなど、自動売買システムの基盤機能を提供します。戦略・実行・モニタリングの各レイヤはモジュール化されており、独自の戦略やブローカー実装を組み込めるよう設計されています。

主な設計方針
- データの冪等性（INSERT ... ON CONFLICT）を重視
- API レート制限やリトライ（指数バックオフ）を組み込み
- Look-ahead bias 防止のため取得時刻（UTC）を記録
- RSS ニュース収集で SSRF・XML Bomb・サイズ上限など安全対策を実施
- DuckDB をメインのローカルデータストアとして使用

---

## 機能一覧

- J-Quants クライアント（jquants_client）
  - ID トークン取得（自動リフレッシュ対応）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミッタ（120 req/min）・リトライロジック（408/429/5xx）・401時のトークン再取得
  - DuckDB への冪等保存（save_* 関数）

- ETL パイプライン（data.pipeline）
  - 差分更新ロジック（最終取得日からの自動判定、backfill 対応）
  - 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - ETL 結果を表す ETLResult（問題検出やエラーの収集）

- スキーマ定義（data.schema）
  - Raw / Processed / Feature / Execution 層を含む DuckDB テーブル定義
  - インデックス作成、初期化ユーティリティ（init_schema / get_connection）

- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理（URL 除去・空白正規化）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
  - SSRF 対策、gzip 解凍サイズチェック、XML パースのセーフ実装（defusedxml）
  - raw_news / news_symbols への保存ユーティリティ

- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定 / 前後営業日取得 / 期間内営業日取得
  - 夜間バッチでのカレンダー差分更新ジョブ

- 品質チェック（data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性（未来日付・非営業日）検出
  - チェック結果は QualityIssue のリストで返す（severity: error | warning）

- 監査ログ（data.audit）
  - シグナル → 発注要求 → 約定までをトレースするテーブル群（監査向け）
  - すべて UTC タイムスタンプで保存、冪等キーや状態管理をサポート

- その他
  - config モジュールで .env または OS 環境変数を自動読み込み（自動無効化可）
  - strategy / execution / monitoring ためのパッケージプレースホルダ

---

## セットアップ手順

1. 必須環境
   - Python 3.9+（typing の一部表記や型ヒントのため）
   - pip

2. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```

   （プロジェクトで使用する追加パッケージは環境や運用に応じて導入してください。HTTPクライアントやSlack連携等は別途必要です。）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` または `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（Settings で _require() されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトを持つ設定:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — sqlite 用監視 DB（デフォルト: data/monitoring.db）

   - 例 .env（テンプレート）
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. データベース初期化
   - DuckDB スキーマを作成する:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB（または同じ接続）を初期化する:
     ```python
     from kabusys.data import audit
     # 既存 conn に監査スキーマを追加
     audit.init_audit_schema(conn)
     # あるいは専用 DB ファイル
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要ユースケース）

以下は代表的な利用方法の抜粋です。実運用用の CLI やジョブスケジューラは適宜用意してください。

1. 日次 ETL を実行する
   - ETL のメインエントリポイントは data.pipeline.run_daily_etl です。
   ```python
   from datetime import date
   import duckdb
   from kabusys.data import schema, pipeline

   conn = schema.init_schema("data/kabusys.duckdb")
   # 今日の ETL を実行
   result = pipeline.run_daily_etl(conn)
   print(result.to_dict())
   ```

   - run_daily_etl は市場カレンダー、株価、財務データを差分取得し、品質チェックを実施します。内部で J-Quants クライアントのレート制限・リトライ・トークンリフレッシュが働きます。

2. J-Quants API を直接利用する
   - ID トークン取得:
     ```python
     from kabusys.data.jquants_client import get_id_token
     token = get_id_token()  # settings.jquants_refresh_token を使用
     ```
   - 株価データ取得:
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes
     records = fetch_daily_quotes(code="6758", date_from=date(2023,1,1), date_to=date(2023,12,31))
     ```
   - DuckDB に保存:
     ```python
     from kabusys.data.jquants_client import save_daily_quotes
     saved = save_daily_quotes(conn, records)
     ```

3. RSS ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection  # or init_schema

   conn = get_connection("data/kabusys.duckdb")
   # known_codes に有効な銘柄コードセットを渡すと銘柄紐付けを実行する
   stats = run_news_collection(conn, known_codes={"7203", "6758"})
   print(stats)
   ```

4. 品質チェック単体で実行
   ```python
   from kabusys.data import quality
   issues = quality.run_all_checks(conn)
   for i in issues:
       print(i)
   ```

---

## 実装上の注意点 / セキュリティ

- .env 自動読み込み
  - kabusys.config はプロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

- J-Quants クライアント
  - レート制限: 固定間隔スロットリング（120 req/min）で制御
  - リトライ: 最大 3 回、指数バックオフ。HTTP 408/429/5xx を対象
  - 401 の場合はリフレッシュトークンで自動的に ID トークンを更新して 1 回だけリトライ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を防止

- ニュース収集の安全対策
  - defusedxml で XML パース、gzip の展開後サイズチェック（Gzip bomb対策）
  - SSRF 対策: URL スキーム検査（http/https のみ）、ホストがプライベートアドレスかチェックして拒否、リダイレクト時も検査
  - レスポンスの最大読み取りサイズを制限（10 MB）
  - トラッキングパラメータ除去と URL 正規化で同一記事の冪等性確保

- DuckDB スキーマ
  - 多数の CHECK 制約・PRIMARY KEY を設けてデータ整合性を保っています
  - ON CONFLICT 句を利用して ETL の冪等性を担保

---

## ディレクトリ構成

リポジトリの主要ファイル／モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存）
      - news_collector.py      -- RSS ニュース収集・保存
      - schema.py              -- DuckDB スキーマ定義・初期化
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py -- 市場カレンダー管理
      - quality.py             -- データ品質チェック
      - audit.py               -- 監査ログ（signal / order / execution）
    - strategy/                -- 戦略実装用プレースホルダ
    - execution/               -- 発注・ブローカー連携用プレースホルダ
    - monitoring/              -- 監視・メトリクス用プレースホルダ

---

## テスト / モックについて

- ネットワーク呼び出し（特に RSS の _urlopen や jquants_client の HTTP）はユニットテスト時にモック可能です。news_collector は _urlopen をモックして HTTP レスポンスを差し替えることを想定しています。
- jquants_client の関数群は id_token を引数で注入できるので、テスト時は固定トークンやテスト用モックを渡して挙動を検証できます。

---

## 今後の拡張案（参考）

- strategy モジュールに戦略実装テンプレートやバックテスト機構を追加
- execution にブローカー（kabu/stub）プラグイン実装
- モニタリング（Prometheus Exporter 等）、Alerting（Slack通知）の統合
- CI 用のテストスイート、型チェック、静的解析の導入

---

お問い合わせ・貢献
- バグ報告や機能追加は Issue を作成してください。Pull Request は歓迎します。

以上。README は適宜プロジェクトの運用に合わせて更新してください。