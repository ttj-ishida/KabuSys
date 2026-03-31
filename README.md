# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）のコードベース README。

このリポジトリはデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター研究、監査ログなど自動売買とリサーチに必要な共通モジュール群を含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に格納する ETL パイプライン
- RSS ベースのニュース収集と OpenAI を用いたニュース NLP（銘柄別センチメント）スコアリング
- マーケットレジーム（bull / neutral / bear）判定（ETF MA とマクロニュースの LLM スコアの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル → 発注 → 約定）を DuckDB に永続化するスキーマと初期化機能
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」「外部依存は最小（DuckDB + OpenAI 等）」が取られています。

---

## 主な機能一覧

- データ取得 / ETL
  - 日次 ETL（run_daily_etl）：市場カレンダー → 日足 → 財務 → 品質チェック
  - J-Quants クライアント（fetch / save 機能）・レートリミット・リトライ付き
- データ品質
  - 欠損検出 / スパイク検出 / 重複チェック / 日付整合性チェック
- ニュース収集 / NLP
  - RSS 収集（SSRF 防止・トラッキング除去・前処理）
  - OpenAI を用いた銘柄別センチメントスコア（score_news）
- マーケットレジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成（score_regime）
- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー、Z スコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions 等の DDL と初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 必要条件（依存関係）

最低限必要な Python バージョンと主要ライブラリの例（実際のバージョンはプロジェクトの packaging に依存します）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（その他、標準ライブラリを多用しています。パッケージ化時の requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - パッケージ管理ファイルがある場合はそれに従ってください（例: requirements.txt / pyproject.toml）。
   - 参考（例）:
     ```
     pip install duckdb openai defusedxml
     # またはパッケージを editable install
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` として必要な環境変数を置けます。
   - 自動ロード順序は OS 環境変数 > .env.local > .env です。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（AI モジュールで参照）
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL
   - `.env` の例:
     ```
     JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
     OPENAI_API_KEY="sk-..."
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C0123456789"
     DUCKDB_PATH="data/kabusys.duckdb"
     ```

5. データベース作成（監査 DB 初期化例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（簡単な例）

各機能はモジュール関数として利用できます。以下は代表的な使い方例です。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を省略すると今日が使われます
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（対象日を指定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書込銘柄数:", n_written)
  ```
  - OpenAI API キーは引数 `api_key` で渡すか、環境変数 `OPENAI_API_KEY` を設定してください。

- マーケットレジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算・リサーチ関数
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

注意点:
- 多くの関数は Look-ahead バイアス防止のため内部で現在時刻を参照せず、必ず `target_date` を引数に取ります。
- OpenAI の呼び出しはリトライを含む安全策が実装されていますが、APIキーは必須です。
- J-Quants API を利用する処理（ETL / fetch）では `JQUANTS_REFRESH_TOKEN` を必ず設定してください。

---

## 自動環境変数読み込みの挙動（補足）

- モジュール `kabusys.config` はプロジェクトルート（.git または pyproject.toml の存在）を探索して、プロジェクトルート直下の `.env` と `.env.local` を自動読み込みします。
- OS 環境変数が優先され、`.env.local` が `.env` を上書きします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` パーサはシェル形式（export やクォート、コメント）に対応しています。

---

## ディレクトリ構成（主なファイル）

以下は主要モジュールの概観（パスは src/kabusys 配下）:

- kabusys/
  - __init__.py  — パッケージ定義（version 等）
  - config.py    — 環境変数 / 設定読み込みユーティリティ（Settings）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py        — ETL パイプライン（run_daily_etl など）
    - etl.py             — ETL インターフェース（ETLResult 再エクスポート）
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - quality.py         — データ品質チェック（各種チェック）
    - calendar_management.py — 市場カレンダーの管理と判定ロジック
    - news_collector.py  — RSS からのニュース収集（SSRF 対策等）
    - audit.py           — 監査ログ DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - ai/, data/, research/ のそれぞれにある詳細な実装はソースコードの docstring を参照してください。

---

## 補足 / 注意事項

- 本リポジトリに含まれる関数群は、主に ETL・研究用途のユーティリティです。リアルマネーで運用する場合は十分なテスト・リスク管理が必須です。
- OpenAI との連携部分は外部 API に依存するため、レート制限やコストに注意してください。
- J-Quants API 利用には API キー（リフレッシュトークン）が必要です。取得・利用規約に従ってください。
- セキュリティ上の配慮（SSRF、トラッキングパラメータ除去、ファイル/ネットワークの扱いなど）が実装されていますが、運用環境に応じた追加対策を推奨します。

---

必要であれば具体的な導入手順（requirements.txt の生成、Docker コンテナ化例、CI/CD ワークフロー例、詳しい .env.example）や各モジュールごとの API 参照ドキュメントを作成します。どの情報を優先的に出力しますか？