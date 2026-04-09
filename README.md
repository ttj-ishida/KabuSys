# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
ETL・ニュース収集・AIによるニュース/レジーム判定・ファクター計算・監査ログ等を含む、バックテスト／実運用用の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主目的とする Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分ETL
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム）のスコアリング
- ファクター（モメンタム/バリュー/ボラティリティ等）計算・特徴量探索用ユーティリティ
- データ品質チェック、監査ログ（signal → order → execution のトレーサビリティ）
- DuckDB をデータストアとして利用

設計上の特徴:
- ルックアヘッドバイアス回避（内部で datetime.now() を無闘に参照しない等）
- 冪等性（ETL 保存は ON CONFLICT DO UPDATE）
- API 呼び出しのリトライ・レート制御・フォールバックを備える
- セキュリティ注意（ニュース収集における SSRF 防止や XML 攻撃対策）

---

## 主な機能一覧

- data/
  - ETL pipeline（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save）
  - market calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - データ品質チェック（missing, duplicates, spike, date consistency）
  - news_collector（RSS 取得・前処理・保存用ユーティリティ）
  - audit（監査ログテーブルの初期化: init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースから市場レジームを判定し market_regime に書き込む
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理 (kabusys.config)
  - .env 自動読み込み（.env, .env.local、環境変数優先）
  - settings オブジェクト経由で設定取得

---

## セットアップ手順

前提:
- Python 3.9+（typing の union 表記や型ヒントを利用）
- duckdb, openai, defusedxml などの依存ライブラリ

推奨手順（開発環境）:

1. 仮想環境を作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   補足: 実行環境によっては追加で urllib、requests などが必要になる場合があります（本コードは標準ライブラリ urllib を利用）。

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数（または .env）を用意する
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` を配置すると自動で読み込まれます（.env.local は上書き）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - OPENAI_API_KEY (推奨) — OpenAI API キー（ai モジュールで使用）
   - KABUSYS_ENV (任意) — development / paper_trading / live（default: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（default: data/kabusys.duckdb）
   - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下はパッケージ内の主要関数の利用例です。実行前に環境変数を設定しておいてください。

- DuckDB 接続を作る（デフォルトパスを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl は ETLResult を返す）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  run_daily_etl の挙動:
  - カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の順に実行
  - id_token を渡さない場合は内部で settings.jquants_refresh_token から取得

- ニュースセンチメントのスコアリング（OpenAI 必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI 必要）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/monitoring.duckdb")  # ディレクトリ自動作成
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- RSS 取得（ニュース収集ユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
  for a in articles[:5]:
      print(a['id'], a['datetime'], a['title'])
  ```

注意点:
- OpenAI 呼び出しは API キーが必要です。api_key 引数で明示的に渡すこともできます。
- ETL / save_* 系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）を前提とします。最初にスキーマを作る手順が別途用意されている場合はそれに従ってください（本リポジトリのスキーマ初期化関数を呼ぶなど）。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。ETL の認証に使用。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード。
- OPENAI_API_KEY
  - OpenAI API のキー（ai モジュールで使用）。
- KABUSYS_ENV (default: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (default: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_FILL_MODE (default: "instant")
  - 有効値: instant, partial, never, reject
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default: 0)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視用しきい値（パーセンテージ）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env の自動ロードを無効化（テスト用）

設定は kabusys.config.settings 経由で取得できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（score_news）
  - regime_detector.py           — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch / save）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult 再エクスポート
  - calendar_management.py       — マーケットカレンダー管理
  - news_collector.py            — RSS 収集 / 前処理
  - quality.py                   — データ品質チェック
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - audit.py                     — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー

（上記以外に execution, monitoring, strategy 等のサブパッケージが想定されていますが、現コード抜粋では data / ai / research が主要な実装です。）

---

## 開発・運用上の注意

- データベーススキーマ（テーブル名・カラム名）に依存するコードが多いため、スキーマの初期化手順を必ず確認してください（audit.init_audit_db 等）。
- OpenAI 呼び出しはレートや費用が発生します。実運用ではバッチサイズ・頻度を調整してください。
- news_collector は SSRF 対策や XML の安全側防御を実装していますが、外部フィードの追加時は信頼できるソースのみを使用してください。
- run_daily_etl は一部ステップが失敗しても他のステップを継続する設計です。戻り値の ETLResult を確認してエラー/品質問題に応じた運用判断を行ってください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って外部 .env の自動読み込みを抑制できます。

---

問題報告・コントリビュート方法はプロジェクトの ISSUE を利用してください。README の補足（実行例スクリプトや schema 初期化手順、requirements.txt 等）を追加する PR は歓迎します。