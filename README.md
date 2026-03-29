# KabuSys

日本株のデータプラットフォーム・研究・自動売買支援ライブラリ群。  
DuckDB をデータ層に用い、J-Quants / OpenAI / RSS 等と連携してデータ収集（ETL）、品質チェック、特徴量算出、ニュース/NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）を提供します。

主な設計方針は「ルックアヘッドバイアスの回避」「冪等性」「フェイルセーフ（API 失敗時は安全側で継続）」です。

バージョン: 0.1.0

---

## 機能一覧

- データ取得・ETL（J-Quants API）  
  - 株価日足（OHLCV）・財務データ・マーケットカレンダーの差分取得・保存（冪等）
  - レート制限、トークン自動リフレッシュ、リトライ（指数バックオフ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（URL 正規化、SSRF 対策、サイズ制限）
- ニュース NLP スコアリング（OpenAI + JSON Mode、バッチ処理・リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索（将来リターン・IC・サマリー）
- 汎用統計ユーティリティ（Z-score 正規化）
- 監査ログ用スキーマ・初期化（signal → order_request → executions のトレーサビリティ）
- 環境設定管理（.env, .env.local の自動読み込み、環境別フラグ）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS フィード 等）

（上記パッケージはプロジェクトの packaging / requirements に合わせてインストールしてください）

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境を作成してアクティベート（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに `pyproject.toml` / `requirements.txt` があればそれを使ってください）
4. 環境変数を設定（.env を作成）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（注文連携）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
     - OPENAI_API_KEY — OpenAI を使う場合に必要（score_news / regime 判定など）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB データベースディレクトリ（デフォルト `data/`）を作成
   ```bash
   mkdir -p data
   ```

※ 自動で `.env` を読み込むロジックについて  
- 読み込み順: OS 環境変数 > .env.local > .env  
- テスト等で自動読み込みを無効化したければ環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトから直接呼び出す例です。DuckDB の接続は `duckdb.connect(path)` で生成します。

- ETL（日次パイプライン）実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path オブジェクト
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_score 書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("scored:", n_written)
  ```

- 市場レジームスコア算出
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 必要なディレクトリは自動作成
  ```

- 監査スキーマを既存接続に適用
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注:
- OpenAI を使う機能（score_news, score_regime）は `OPENAI_API_KEY` を環境変数、または関数引数 `api_key` で指定してください。
- ETL の実行は初回時にスキーマが整っていること（テーブル定義）が必要です。スキーマ初期化用のユーティリティが別途存在する場合はそちらを先に実行してください（このコードベースではデータ格納ロジックが想定するテーブルが存在する前提です）。

---

## 簡単なワークフロー例

1. ETL を nightly で実行して raw_prices/raw_financials/market_calendar を更新（run_daily_etl）。
2. 品質チェック結果を監視（ETLResult.quality_issues）。
3. news_collector で raw_news を更新 → score_news で ai_scores を作成。
4. research モジュールで特徴量を作成し、バックテストやストラテジーに利用。
5. strategy 層でシグナル生成 → execution 層で発注（監査ログは audit スキーマへ保存）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使用する SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development, paper_trading, live)、デフォルト development
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

settings オブジェクト（kabusys.config.settings）を通じてこれらにアクセスできます。必須変数が未設定の場合は ValueError が発生します。

---

## 注意事項 / 補足

- ルックアヘッドバイアス対策として、ライブラリ内の多くの処理は `date` / `target_date` を明示的に受け取り、内部で `datetime.today()` を参照しない設計になっています。バックテスト用途ではこの点に注意して利用してください。
- J-Quants の API 呼び出しはレートリミット・リトライ・トークン自動更新を組み込んでいますが、API 利用規約に従ってください。
- OpenAI への問い合わせは JSON Mode（厳密な JSON 出力）を用いるため、レスポンスパースに失敗した場合はフェイルセーフとして該当銘柄をスキップしたり中立値を採る設計です。
- news_collector は SSRF / XML Bomb / gzip 脆弱性対策を実装していますが、運用時のセキュリティポリシーに従ってください。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン等
  - config.py — 環境変数 / 設定管理（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（is_trading_day, next/prev_trading_day 等）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント（fetch_*/save_*）
    - news_collector.py — RSS ニュース収集
    - quality.py — データ品質チェック（check_missing_data, check_spike, ...）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ定義・初期化（init_audit_db / init_audit_schema）
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai, research, data 以下はそれぞれの責務に沿ったユーティリティ・実装を収めています。

---

もし README に追加したい使用例（CI 向けのコマンド、cron/airflow のサンプル、schema 初期化スクリプト、requirements.txt など）があれば、具体的な要求を教えてください。README を用途に合わせて拡張します。