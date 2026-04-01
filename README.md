# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
このリポジトリはデータの取得・品質管理、特徴量計算、ニュースNLP / LLM を用いたセンチメント評価、監査ログ、ETL パイプラインなどを提供するモジュール群から構成される Python パッケージです。バックテスト／リサーチ領域と本番運用（発注・監視）を分離しつつ、Look-ahead bias を避ける設計方針を採用しています。

バージョン: 0.1.0

---

## 主要機能

- データ取得・ETL
  - J-Quants API から株価・財務情報・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT / INSERT … DO UPDATE）
  - ETL の結果を ETLResult として集約
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合の検出
  - QualityIssue による詳細レポート
- ニュース収集
  - RSS フィード取得（SSRF 対策、応答サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（LLM 統合）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント評価（ai.news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（ai.regime_detector.score_regime）
  - JSON Mode / リトライ・フォールバックを備えた堅牢な実装
- 研究・ファクター計算
  - Momentum / Volatility / Value / Liquidity 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化ユーティリティ
- カレンダー管理
  - market_calendar の取得・更新、営業日判定・前後営業日の探索
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル、インデックス、初期化ユーティリティ
  - 発注のトレーサビリティを UUID で連鎖保存
- 設定管理
  - .env / .env.local / 環境変数から設定を自動ロード（プロジェクトルートを自動検出）
  - 必須設定のバリデーション

---

## 必要条件

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI 等へ接続する場合）
- DuckDB ファイル保存用のファイルシステム権限

（実際のバージョンや追加依存はプロジェクトの packaging / requirements を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   ```bash
   git clone <this-repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストールします（開発モード推奨）。

   ```bash
   pip install -U pip
   pip install -e ".[all]"  # 依存定義がある場合
   ```

   もし extras が用意されていない場合は最低限以下をインストールしてください。

   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数（または .env）を設定します。必須の環境変数:

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーションAPIのパスワード（発注用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - OPENAI_API_KEY        : OpenAI API キー（ai モジュールを使う場合）

   オプション（デフォルト値あり）:

   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG | INFO | …)

   .env の自動読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます。
   - 読み込み順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB データベース初期化（監査ログ用例）:

   Python REPL で:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要なサンプル）

- 日次 ETL 実行

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI 必須）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター／研究機能

  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)

  momentum = calc_momentum(conn, d)
  volatility = calc_volatility(conn, d)
  value = calc_value(conn, d)

  forward = calc_forward_returns(conn, d, horizons=[1,5,21])
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- カレンダー操作

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意: これらの例は DuckDB に必要テーブル（raw_prices / raw_financials / raw_news / news_symbols / market_calendar / ai_scores / market_regime 等）が存在することを前提とします。ETL パイプラインや save_* 関数は必要に応じてテーブルを作成する準備をしておくか、スキーマ初期化ユーティリティを実行してください。

---

## ディレクトリ構成

以下はパッケージの主要ファイル・モジュール構成（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュースセンチメント（OpenAI 統合）
    - regime_detector.py    -- マクロ + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（取得 & 保存）
    - pipeline.py           -- ETL パイプライン実装（run_daily_etl 等）
    - etl.py                -- ETL インターフェース再エクスポート
    - news_collector.py     -- RSS 収集・前処理
    - calendar_management.py-- マーケットカレンダー管理、営業日判定
    - stats.py              -- zscore_normalize 等統計ユーティリティ
    - quality.py            -- データ品質チェック
    - audit.py              -- 監査ログ（signal/order/execution）初期化
  - research/
    - __init__.py
    - factor_research.py    -- Momentum / Value / Volatility 等
    - feature_exploration.py-- 将来リターン / IC / 統計サマリー 等

---

## 設計上の注意・ポリシー

- Look-ahead bias を避ける設計
  - モジュールは内部で datetime.today() / date.today() を参照しないよう設計（引数で date を受け取る）。これによりバックテストでの正当性を保ちます。
- フェイルセーフ
  - LLM/API が失敗した場合はゼロやスキップで継続する実装が多く、単一障害で全処理が止まらないようになっています。
- 冪等性
  - DuckDB への保存は可能な限り冪等（ON CONFLICT 句等）で実装し、再実行可能にしています。
- セキュリティ
  - RSS 取得に SSRF 対策（ホスト検査、リダイレクト検査）や XML の安全パーサを使用します。

---

## 貢献・開発者向けメモ

- 自動 .env 読み込みはプロジェクトルートを .git / pyproject.toml から検出します。パッケージを別場所へ移してテストする際は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- テスト時には外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックしてください。モジュール内部で外部呼び出しをラップした関数が切り替え箇所になっています（例: news_nlp._call_openai_api を patch）。
- DuckDB 接続は並列書き込みやトランザクションに注意してください（DuckDB の制約を理解して利用すること）。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。実際の運用では API キー管理、シークレットの保護、監視（monitoring）や発注モジュール（execution）の安全設計などを十分に行ってください。追加の説明や具体的なセットアップ手順が必要であれば教えてください。