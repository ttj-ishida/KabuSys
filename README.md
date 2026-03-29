# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants / kabuステーション / Slack / OpenAI などと連携し、データ取得（ETL）・品質チェック・ニュース NLP・市場レジーム判定・監査ログ管理・リサーチ用ファクター計算等を提供します。

> 注: このリポジトリは自動売買の一部機能を含みます。実運用（特に実口座での発注）を行う場合は十分なレビュー・テスト・リスク管理を行ってください。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務情報、上場銘柄情報、JPXカレンダーを差分取得・保存
  - DuckDB を用いた冪等保存（ON CONFLICT DO UPDATE）
  - 差分取得・バックフィル・ページネーション対応・トークン自動リフレッシュ・レート制御

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、主キー重複、日付不整合（未来日・非営業日）など

- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策・URL 正規化・トラッキング除去）
  - OpenAI (gpt-4o-mini) を用いた銘柄別ニュースセンチメント分析（ai_scores テーブルへ保存）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメントの複合）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ保存

- 研究用ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化、統計サマリー

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数経由での設定取得ラッパー（kabusys.config.settings）

---

## セットアップ手順

前提: Python 3.9+ を利用してください（注: ソースは型ヒントに Python 3.10+ 機能を使用していますが、互換性はご確認ください）。

1. 仮想環境の作成（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要なパッケージをインストール
   - 最低限の依存例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用途でパッケージとしてインストールする場合（プロジェクトルートに pyproject.toml がある想定）:
     ```
     pip install -e .
     ```
   - 追加で必要なライブラリがあれば pyproject.toml / requirements.txt を参照してください（本コード例では標準ライブラリと上記パッケージが主に使われます）。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi   # optional
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（News/Regime 機能を利用する場合）など。`kabusys.config.settings` 経由で取得します。

4. データベースディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下は主要なユーティリティ関数の呼び出し例です。実行前に .env を用意し、`OPENAI_API_KEY` や `JQUANTS_REFRESH_TOKEN` を設定してください。

- DuckDB 接続と ETL の実行例
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア付け（OpenAI を使用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # 引数 api_key が None の場合は OPENAI_API_KEY を参照
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済み DuckDB 接続
  ```

- 研究用ファクター計算例
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

---

## 設定と環境変数の挙動

- 自動 .env ロード
  - 起点はパッケージ内の config モジュールの位置（.git または pyproject.toml のある親ディレクトリ）を探索してプロジェクトルートを特定します。CWD に依存しないため、パッケージ配布後も正しく動作します。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化します（テスト時等に利用）。

- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知
  - OPENAI_API_KEY: OpenAI 呼び出し（news_nlp / regime_detector）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境（development, paper_trading, live）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定値は `kabusys.config.settings` 経由で取得できます。必須値が未設定の場合は ValueError が発生します。

---

## ディレクトリ構成（概要）

以下は主要モジュールの階層（src/kabusys 配下）。細かなサブモジュールはコメント・ドキュメント内の機能を参照してください。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py            # ニュースセンチメント解析（OpenAI）
      - regime_detector.py     # 市場レジーム判定（MA200 + マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（fetch / save）
      - pipeline.py            # 日次 ETL パイプライン
      - etl.py                 # ETLResult 再エクスポート
      - news_collector.py      # RSS 収集（SSRF 対策・正規化）
      - calendar_management.py # 市場カレンダー管理（営業日判定等）
      - quality.py             # 品質チェック
      - stats.py               # 統計ユーティリティ（zscore_normalize 等）
      - audit.py               # 監査ログ（テーブル定義・初期化）
    - research/
      - __init__.py
      - factor_research.py     # Momentum / Value / Volatility 等
      - feature_exploration.py # 将来リターン, IC, factor_summary, rank
    - ai/ (上記)
    - research/ (上記)

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアス対策
  - 多くのモジュールは内部で `datetime.today()` や `date.today()` を直接参照せず、呼び出し元から `target_date` を渡す設計です。バックテストや再現性を保つため、常に明示的な日付を渡すことを推奨します。

- OpenAI 呼び出しとエラー処理
  - news_nlp と regime_detector は LLM 呼び出しにリトライ・フェイルセーフを備えています。API失敗時はスコアを 0.0 にフォールバックする等の設計方針です。それでも本番利用時はコスト・レイテンシ・エラー挙動を十分に検証してください。

- DuckDB の executemany 空リスト制約
  - DuckDB のバージョンによっては executemany に空リストを渡すとエラーになるため、コード内で事前に空チェックを行っています。独自コードを追加する際も注意してください。

- セキュリティ
  - news_collector は SSRF 対策（スキーム検証・プライベートIPブロック・リダイレクト検査）や XML パースの安全化（defusedxml）を実装しています。外部 URL を扱う部分は必ずレビューしてください。

---

## 貢献 / 開発

- ローカル開発では仮想環境を使い、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動ロードをオフにしてテストを行うと便利です。
- ユニットテストは外部 API をモックすることを推奨します（コード内でもテスト差し替えポイントを設けています）。
- 新機能追加や修正はモジュールの設計方針（ルックアヘッドバイアス回避・冪等性・フェイルセーフ設計）に従って行ってください。

---

README に記載の無い詳細な API 使用方法やテーブルスキーマの完全な仕様は、各モジュールの docstring / コメントを参照してください。必要であれば、特定モジュールの詳細な README セクションを追加しますので、対象モジュールを指定してお知らせください。