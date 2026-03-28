# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータ層に、J-Quants と RSS でデータ取得、OpenAI（gpt-4o-mini）でニュース解析を行い、ファクター計算・品質チェック・監査ログを備えた研究／ETL／監視・実行のユーティリティ群を提供します。

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得（差分 ETL、ページネーション対応、レートリミット遵守）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、冪等保存）
- OpenAI を用いたニュースセンチメント解析（銘柄ごとの ai_score、マクロセンチメント）
- 研究用ファクター計算（Momentum / Value / Volatility 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（シグナル→発注→約定追跡）のスキーマ初期化ユーティリティ
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）

設計上の特徴：
- DuckDB を使った高速なローカル DB 操作
- Look-ahead bias に対する配慮（内部で date.today()/datetime.today() を直接用いない等）
- 冪等性を重視した DB 保存ロジック
- 外部 API 呼び出しはリトライ/バックオフとフォールバック実装あり

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、id_token 自動リフレッシュ、レートリミット）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - 品質チェック（missing_data, spike, duplicates, date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に保存）
  - レジーム判定（score_regime: MA200 とマクロニュースを合成して market_regime に保存）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理（kabusys.config: .env 自動読み込み、Settings 経由で環境変数アクセス）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法などを使用）
- 系列パッケージ: duckdb, openai, defusedxml

1. リポジトリをクローン、あるいはプロジェクトルートで作業する（src 配下がパッケージ）:

   git clone <repo>
   cd <repo>

2. 仮想環境を作成して有効化（推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)

3. 必要パッケージをインストール:

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと、自動でロードされます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な環境変数の例（.env）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   .env.example を参考に作成してください（パッケージ内で参照メッセージあり）。

---

## 使い方（基本例）

下記は Python REPL / スクリプトでの利用例です。すべての API は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

1. DuckDB 接続を作成して日次 ETL を実行する

   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())

2. ニュースセンチメントのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または引数で指定）

   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   count = score_news(conn, target_date=date(2026, 3, 20))
   print(f"scored {count} codes")

   - api_key を引数で渡すことも可能:
     score_news(conn, date(2026,3,20), api_key="sk-...")

3. 市場レジーム判定（MA200 とマクロニュースの合成）

   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   # market_regime テーブルに書き込まれます

4. 監査ログ DB の初期化（監査用の独立 DB を作る）

   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # テーブルとインデックスが作成される

5. 市場カレンダー関連ユーティリティ

   from datetime import date
   import duckdb
   from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

   conn = duckdb.connect("data/kabusys.duckdb")
   print(is_trading_day(conn, date(2026,3,20)))
   print(next_trading_day(conn, date(2026,3,20)))
   print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))

6. 品質チェックを実行する

   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2026,3,20))
   for i in issues:
       print(i)

注意点:
- OpenAI を利用する機能は API 利用料が発生します。API キーと利用上の制約に注意してください。
- J-Quants の API 呼び出しにはレート制限があるため、ETL は内部で制御されますが、並列で大量呼び出しを行う場合は注意が必要です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージ定義・公開モジュールリスト（data, strategy, execution, monitoring）
- config.py — 環境変数 / .env の自動読み込みと Settings API

src/kabusys/ai/
- __init__.py
- news_nlp.py — 銘柄別ニュースセンチメント（score_news）
- regime_detector.py — 市場レジーム判定（score_regime）

src/kabusys/data/
- __init__.py
- calendar_management.py — 市場カレンダー管理（is_trading_day 等）
- etl.py — ETL 型（ETLResult の再エクスポート）
- pipeline.py — ETL パイプライン（run_daily_etl 等）
- stats.py — zscore_normalize 等の統計ユーティリティ
- quality.py — データ品質チェック（check_missing_data, check_spike, ...）
- audit.py — 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
- jquants_client.py — J-Quants API クライアント（fetch/save, get_id_token）
- news_collector.py — RSS ニュース収集（fetch_rss, 前処理、SSRF 対策）
- pipeline.py — ETL のエントリポイントと各ジョブ（run_prices_etl 等）
- etl.py — ETLResult 型のエクスポート

src/kabusys/research/
- __init__.py
- factor_research.py — calc_momentum, calc_value, calc_volatility
- feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

その他
- README.md — このファイル
- .env.example — 環境変数の例（リポジトリにあれば参照してください）

（補足）strategy / execution / monitoring などのモジュールは __all__ に含まれていますが、このスナップショットには一部の実装が含まれていない場合があります。必要に応じて該当ディレクトリを確認してください。

---

## 開発・テスト時のヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト環境で自動ロードさせたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI 呼び出しや外部 API は unittest.mock.patch で内部の _call_openai_api や _urlopen を置き換えることでユニットテストが容易です（コード内にその旨のコメントがあります）。
- DuckDB の executemany は空リストの渡し方に注意（コード内でガードあり）。

---

## ライセンス / 貢献

（このテンプレートにライセンス情報や貢献方法を追記してください）

---

README の内容に関して補足や、具体的なセットアップスクリプト（requirements.txt / Dockerfile / CI 設定）のテンプレートが必要であればお知らせください。