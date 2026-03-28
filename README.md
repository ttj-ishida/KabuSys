# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
市場データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能群を備えた内部向けライブラリです：

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュース・マクロセンチメントのスコアリング（JSON Mode）
- ETF（1321）200日移動平均乖離とマクロセンチメントの合成による市場レジーム判定
- ファクター計算（モメンタム / ボラティリティ / バリュー）および研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ

設計上の特徴：
- ルックアヘッドバイアスを避ける（日時取得の使い方に注意）
- DuckDB を中心としたローカル永続化
- API 呼び出しでのリトライ／バックオフやレート制御を実装
- 冪等保存（ON CONFLICT / upsert）を基本方針

---

## 主な機能一覧

- ETL パイプライン: kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント: kabusys.data.jquants_client.fetch_* / save_*（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar 等）
- ニュース収集: kabusys.data.news_collector.fetch_rss / preprocess_text 等
- ニュース NLP（銘柄別スコア）: kabusys.ai.news_nlp.score_news
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 研究ユーティリティ: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- 統計ユーティリティ: kabusys.data.stats.zscore_normalize
- データ品質チェック: kabusys.data.quality.run_all_checks
- 監査ログ初期化: kabusys.data.audit.init_audit_db / init_audit_schema
- 環境設定管理: kabusys.config.settings（.env 自動ロード機能あり）

---

## 前提／必要環境

- Python 3.10+（型注釈で | 型を使用、適切なバージョンを推奨）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 外部 API キー / 認証情報:
  - J-Quants の refresh token（JQUANTS_REFRESH_TOKEN）
  - OpenAI API キー（OPENAI_API_KEY） — AI 機能を使う場合
  - kabuステーション用パスワード（KABU_API_PASSWORD） — 発注連携がある場合
  - Slack Bot トークン / チャンネル（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID） — 通知等がある場合

※ 実行環境に応じて追加パッケージや SDK が必要になる場合があります（例: 発注機能で証券会社 SDK を使用するケースなど）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   例（最低限）:
   ```
   pip install duckdb openai defusedxml
   ```

   パッケージ管理ファイルがある場合はそちらを利用してください（requirements.txt / pyproject.toml）。

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます（優先度: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 注意: `.env` は機密情報を含むためリポジトリにコミットしないでください。

---

## 使い方（代表的な操作）

以下は Python スクリプト／REPL からの利用例です。DuckDB のパスは settings.duckdb_path を使用することが推奨されます。

- DuckDB 接続の取得（例）:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（ファイルから直接呼び出す方法）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを作成（OpenAI キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定を実行
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの duckdb.DuckDBPyConnection
  ```

- JPX カレンダー更新ジョブを実行
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  saved = calendar_update_job(conn, lookahead_days=90)
  print("保存件数:", saved)
  ```

テストや CI では OpenAI などの外部呼び出しをモックして利用してください。news_nlp と regime_detector 内部の _call_openai_api はテスト時に差し替えやすく実装されています（unittest.mock.patch を推奨）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI) — OpenAI API キー（AI 機能を使う場合）
- KABU_API_PASSWORD (必須 for kabu) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) — Slack Bot トークン（通知等）
- SLACK_CHANNEL_ID (必須 for Slack) — 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite パス（監視用等、デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない

.env の自動パースは幾つかのルール（export 付き対応、クォート処理、コメント扱い等）に従います。

---

## テスト・開発時の注意点

- OpenAI 呼び出しはリトライ処理や JSON Mode を使った厳密パースを行いますが、外部 API を使わない単体テストではモック化してください。
  - news_nlp._call_openai_api / regime_detector._call_openai_api を patch することで容易にテスト可能です。
- DuckDB のバージョン差異により executemany の挙動が異なる場合があるため、モジュール内で互換性に配慮した実装になっています。
- データ品質チェックは Fail-Fast ではなく問題をすべて収集する設計です。ETL 呼び出し側で検出結果を見て対応してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: jquants_client など)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ファクター計算・探索用ユーティリティ）

（上記は主要モジュールのみを抜粋しています。実際のツリーはリポジトリの内容に従ってください。）

---

## 補足 / 注意事項

- 機密情報（API トークン等）は必ず安全に管理してください。`.env` をリポジトリに含めないでください。
- OpenAI の呼び出しや J-Quants API の利用にはそれぞれの利用規約とレート制限に従ってください（ライブラリ内部でもレート制御やリトライが組まれています）。
- 実運用（live 環境）では KABUSYS_ENV を `live` に設定し、発注周りの安全チェックやリスク管理を十分確認してから稼働させてください。

---

必要であれば README にサンプルスクリプト（ETL ランナー、ニューススコアリングバッチ、監査 DB 初期化スクリプト等）を追加で作成します。どの例を優先してほしいか教えてください。