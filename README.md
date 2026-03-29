# KabuSys — 日本株自動売買プラットフォーム (README)

このリポジトリは、日本株向けのデータプラットフォーム / リサーチ / 自動売買の共通ライブラリ群です。DuckDB ベースのデータ層、J-Quants API 経由の ETL、ニュース収集と LLM を用いた NLP、ファクター計算・リサーチ、そして監査ログ（発注／約定のトレーサビリティ）を備えます。

主な設計方針（抜粋）
- ルックアヘッドバイアスを避ける：内部実装は date.today()/datetime.today() を直接参照しない/参照を最小限にする設計
- 冪等性：DB への保存は ON CONFLICT / DELETE→INSERT により再実行可能
- フェイルセーフ：外部 API 失敗時はスキップやデフォルト値で継続する（致命的な停止を避ける）
- セキュリティ：ニュース収集で SSRF 等の攻撃対策、XML パースに defusedxml を使用
- レート制御・リトライ：J-Quants 等の API 呼び出しはレートリミットと指数バックオフを実装

---

## 機能一覧

- 環境設定/読み込み
  - `.env` / `.env.local` の自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）
  - 必須設定の取得とバリデーション（`kabusys.config.settings`）

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（認証・ページネーション・リトライ・レート制限）
  - Daily prices / Financials / Market calendar の差分取得と DuckDB への保存（冪等）
  - ETL パイプライン（`run_daily_etl`）と個別ジョブ（prices/financials/calendar）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - ニュース収集（RSS → raw_news、URL 正規化・SSRF 対策・XML 保護）
  - 監査ログ（signal_events / order_requests / executions）のスキーマ初期化・DB 初期化

- AI / NLP（kabusys.ai）
  - ニュースの銘柄別センチメント評価（`score_news`）
  - 市場レジーム判定（MA200 とマクロニュース LLM を組合せ、`score_regime`）
  - OpenAI（gpt-4o-mini）を JSON mode で利用、レスポンス検証・リトライ実装

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- ユーティリティ
  - DuckDB ベースの audit DB 初期化（UTC タイムゾーン固定）
  - カレンダー／営業日管理（is_trading_day / next_trading_day 等）

---

## セットアップ手順（開発環境向け）

以下は一般的な Python 開発環境でのセットアップ例です。プロジェクトに pyproject.toml 等のパッケージ設定がある前提で記載します。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install -U pip
   - 必要ライブラリ（例）
     - duckdb
     - openai
     - defusedxml
     - 例: pip install duckdb openai defusedxml
   - プロジェクトがパッケージ化されている場合:
     - pip install -e .

   注意: 実際の requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（`kabusys.config`）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須となる設定（使用する機能により必須が変わります）:
   - JQUANTS_REFRESH_TOKEN（J-Quants 認証）
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - KABU_API_PASSWORD（kabu ステーション API を使うなら）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知を使うなら）
   - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）

5. データベースの初期化（監査ログ用など）
   - 監査DBを作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（よく使う API と実行例）

以下は主要な公開関数の利用例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- 日次 ETL 実行（株価・財務・カレンダー取得と品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（AI）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"スコアを保存した銘柄数: {n_written}")
  ```

- 市場レジーム判定（MA200 とマクロニュースの LLM 合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants API を直接使ってデータ取得（トークン自動リフレッシュ・ページング対応）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  data = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

注意点
- AI 呼び出し（OpenAI）にはレスポンス検証・リトライが入っていますが、API キーや料金に注意してください。
- ETL / DB 更新処理は基本的に冪等設計ですが、運用時はバックアップや運用手順を整備してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注を行うなら必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- SLACK_BOT_TOKEN — Slack ボットトークン（通知）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）データベースパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は `1` を設定

kabusys.config は .env と .env.local をプロジェクトルートから自動読み込みします（プロジェクトルートは .git または pyproject.toml を基準に探索）。テスト時等に自動読み込みをオフにしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM によるセンチメント解析
    - regime_detector.py  — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL 型の公開エントリ（ETLResult）
    - news_collector.py   — RSS 取得 → raw_news 保存
    - calendar_management.py — マーケットカレンダー / 営業日ロジック
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore 等）
    - audit.py            — 監査ログ（発注／約定）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / summary 等
  - monitoring/ (※コード上で参照される可能性があるが今回は省略)

付記:
- 各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数で受け取り、外部副作用を明確にしています。
- AI モジュールは OpenAI クライアント（openai.OpenAI）を内部で生成しますが、API キーは引数で注入可能です（テスト容易化）。

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリはバックテスト・実運用ともに利用想定ですが、取引（発注）を行う際は必ず paper_trading 環境で十分に検証してください（KABUSYS_ENV=paper_trading）。
- OpenAI 等の外部 API 利用は料金が発生します。バッチサイズや頻度を適切に設定してください（news_nlp は銘柄チャンク処理、regime_detector は最大記事数等を制限）。
- ETL は再実行可能ですが、データ破損に備えて定期的なバックアップを推奨します。
- ログレベル (LOG_LEVEL) を適切に設定し、監視・アラートの仕組みを整えてください。
- ニュース収集や RSS 処理は公開ソースの利用規約に従ってください。

---

## サポート / 開発に関するヒント

- 単体テストでは環境変数の自動ロードが邪魔になることがあるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからテスト中に明示的に環境変数を inject することを推奨します。
- AI 呼び出しやネットワーク周りはモック可能なように `_call_openai_api` / `_urlopen` 等の関数が分離してあります。ユニットテストではこれらを patch して外部依存を切り離してください。

---

この README はコードベースの主要機能と運用手順をまとめたものです。詳細な API 仕様や運用手順（CI/CD、バックアップ、シークレット管理等）は別途ドキュメントにまとめることを推奨します。必要であれば、特定モジュール（例: ETL のログ出力形式、news_collector の RSS ソース設定、監査スキーマの拡張方法 等）の詳細ドキュメントも作成します。