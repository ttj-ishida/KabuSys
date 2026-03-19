# KabuSys

日本株向けの自動売買 / データプラットフォームのコアライブラリです。  
DuckDB をデータ層に用い、J-Quants API や RSS ニュースを取り込み、特徴量生成・品質チェック・監査ログまでを含む ETL / 研究 / 実行基盤の基礎実装を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API クライアント、RSS ニュース収集）
- DuckDB スキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、保存、品質チェック）
- マーケットカレンダー管理（JPX カレンダー）
- 監査ログ（シグナル→注文→約定のトレーサビリティ）
- 研究・特徴量モジュール（モメンタム、バリュー、ボラティリティ、IC 計算など）
- 実行・戦略・モニタリングのための名前空間（骨組み）

設計方針の要点：
- DuckDB を単一の事実源（single source of truth）として扱う
- J-Quants API のレート制御・リトライ・トークン自動更新を実装
- ETL は冪等（ON CONFLICT）で安全に実行
- 研究コードは本番口座や発注 API にアクセスしない（データ参照のみ）
- セキュリティ対策（RSS の SSRF 防止、XML の安全パース等）

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API からの株価・財務・カレンダー取得
  - ページネーション対応、レートリミット、リトライ、トークン自動更新
  - DuckDB へ冪等保存（save_* 関数群）
- data/news_collector
  - RSS 収集、URL 正規化（トラッキング除去）、SSRF/サイズ/圧縮対策
  - raw_news / news_symbols への冪等保存
- data/schema / data/audit
  - DuckDB 用の包括的なテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_db による初期化
- data/pipeline
  - 日次 ETL（run_daily_etl）：カレンダー取得→株価差分→財務差分→品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
- data/quality
  - 欠損チェック、重複チェック、スパイク検出、日付不整合検出
  - QualityIssue により重大度別で結果を返す
- research
  - factor_research: モメンタム、ボラティリティ、バリュー等の計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
  - data.stats: zscore_normalize（Zスコア正規化ユーティリティ）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型記法（|）を利用）
- pip が利用可能

1. リポジトリをクローン / 取得
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   （本リポジトリの requirements.txt がある場合はそちらを利用してください。最低限必要なパッケージ例）
   ```
   pip install duckdb defusedxml
   ```
   - duckdb: データベース
   - defusedxml: 安全な XML パーサ（RSS 処理で使用）

   ※ 実際の運用では他に requests 等が必要なことがあります。 packaging / setup に合わせてインストールしてください。

4. 環境変数設定  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主に必要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - SLACK_BOT_TOKEN: Slack 通知に使用（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）※デフォルトを使用する場合は不要
   - SQLITE_PATH: 監視 DB 等の SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL かスクリプトで次を実行してください:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # 監査ログ DB を別ファイルで初期化する場合:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下はライブラリの主要ユースケースの使い方サンプルです。

1. 環境設定値を参照する
   ```python
   from kabusys.config import settings
   print(settings.jquants_refresh_token)
   print(settings.duckdb_path)
   ```

2. DuckDB スキーマ初期化（前述）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)
   ```

3. 日次 ETL を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

4. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   # known_codes は銘柄コードのセット（抽出に使用）
   res = run_news_collection(conn, known_codes={"7203", "6758"})
   print(res)
   ```

5. 研究用のファクター計算例
   ```python
   import duckdb
   from datetime import date
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

   conn = duckdb.connect("data/kabusys.duckdb")
   d = date(2024, 1, 31)
   mom = calc_momentum(conn, d)
   vol = calc_volatility(conn, d)
   val = calc_value(conn, d)
   fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   summary = factor_summary(mom, ["mom_1m", "ma200_dev"])
   normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
   ```

6. 品質チェックを個別に実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date.today())
   for i in issues:
       print(i)
   ```

---

## 主要モジュールと API 一覧（抜粋）

- kabusys.config.settings
  - jquants_refresh_token, kakbu_api_*, slack_*, duckdb_path, env, is_live, is_dev など
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py

主なテーブル定義や DDL は `src/kabusys/data/schema.py` にまとまっています。  
研究用ユーティリティは `src/kabusys/research/` 以下に配置されています。

---

## 注意点 / 運用上のヒント

- 自動で .env を読み込む機能が有効です。テストやカスタムロードが必要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- J-Quants の API レート制限（120 req/min）やエラーハンドリング（リトライ、401→トークンリフレッシュ）を組み込んでいます。大量データ取得時はレートに注意してください。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップやファイル配置は運用ポリシーに合わせてください。
- RSS 収集では外部入力を扱うため、SSRF・XML Bomb・大サイズレスポンスなどに対する防御策を実装していますが、さらに厳密な検証が必要な環境では追加制約を検討してください。
- 研究 / Strategy モジュールは本番注文処理に影響を与えないように分離されています。実際に発注を行う場合は別途 execution 層の実装・統合が必要です。

---

## 貢献 / 開発

- 機能追加やバグ修正はプルリクエストで受け付けます。コードスタイルはプロジェクトのコントリビュートガイドに従ってください（未定義なら PEP8 準拠推奨）。
- ユニットテストを充実させることで安全性が向上します。特に ETL の品質チェックやニュース抽出ロジックに対するテストを推奨します。

---

必要であれば、この README に「CI/CD」「デプロイ手順」「運用監視」「Slack 通知の使い方」などのセクションを追加します。どの情報を優先的に追加しますか？