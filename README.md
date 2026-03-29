KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（オーダー/約定トレーサビリティ）などを提供します。

特徴
----
- データ取得 & ETL
  - J-Quants API から株価日足 / 財務データ / JPX カレンダーを差分取得・保存（DuckDB）  
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集 & NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム判定（score_regime）
- 研究ユーティリティ
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - Zスコア正規化ユーティリティ
- 監査 & トレーサビリティ
  - signal_events / order_requests / executions の監査スキーマを DuckDB に初期化
  - 冪等性・トランザクション考慮済み（order_request_id を冪等キーとして利用）
- 設定管理
  - .env / .env.local / 環境変数による設定読み込み（自動ロード、プロジェクトルート検出）

必須（主要）機能一覧（モジュール）
------------------------------
- kabusys.config
  - settings: 環境変数読み込み / 必須チェック
  - 自動 .env ロード（.git または pyproject.toml を検出してプロジェクトルートを特定）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュ、レート制御、リトライ）
- kabusys.data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括実行（ETLResult）
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - RSS 取得・正規化・raw_news 保存（SSRF・サイズ上限・トラッキング除去）
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None): ニュースを銘柄別にまとめ、LLM によるセンチメントを ai_scores に書き込む
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None): ETF(1321) の MA200 乖離 + マクロニュースセンチメントで市場レジームを market_regime テーブルへ書き込む
- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.quality
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
- kabusys.data.audit
  - init_audit_schema / init_audit_db: 監査ログのテーブル・インデックスを初期化

セットアップ
-----------
前提
- Python 3.10+（typing の union 表記等を想定）
- インターネット接続（J-Quants / OpenAI / RSS）

推奨パッケージ（最低限）
- duckdb
- openai
- defusedxml

インストール例
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)
2. パッケージをインストール（プロジェクトに requirements.txt がない場合は最低限を入れる）:
   - pip install duckdb openai defusedxml

プロジェクトを開発モードでインストール（パッケージ配布がある場合）:
- pip install -e .

環境変数 / .env
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探し、.env → .env.local の順で自動読み込みします（既存の OS 環境変数は上書きされません）。
- 自動ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（settings で参照）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) — 監視用 DB 等（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY — OpenAI を使う関数（score_news/score_regime）で参照される（関数呼び出し時に api_key を与えることも可能）

使い方（簡単な例）
----------------

※ 下記は Python REPL またはスクリプト内で実行する例です。

1) DuckDB 接続を作る（デフォルトのファイルパスを利用）
- from kabusys.config import settings
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

2) 監査 DB を初期化する
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も利用可

3) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

4) ニュースをスコアリングして ai_scores に書き込む
- from kabusys.ai.news_nlp import score_news
- n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

5) 市場レジームを評価して market_regime に書き込む
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

6) 研究用ファクター計算（例: モメンタム）
- from kabusys.research.factor_research import calc_momentum
- recs = calc_momentum(conn, target_date=date(2026, 3, 20))

運用上の注意
-------------
- Look-ahead バイアス防止: モジュールの多くは date / target_date を明示的に受け取り、datetime.today() を直接参照しない設計です。バックテストでの利用時は取得日付に注意してください。
- OpenAI API 呼び出しはリトライやフォールバック（失敗時は中立スコア等）を備えていますが、コスト管理・レート制限に注意してください。
- J-Quants API はレート制限（120 req/min）を尊重する実装が含まれます。大量取得の際は注意してください。
- 自動 .env ロードはプロジェクトルートを検出して行います。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて制御できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                     — ニュース NLP スコアリング（score_news）
  - regime_detector.py              — マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント（fetch/save）
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等、ETLResult）
  - etl.py                          — ETLResult 再エクスポート
  - news_collector.py               — RSS 取得 / 前処理 / raw_news 保存
  - calendar_management.py          — 市場カレンダー管理・営業日計算
  - quality.py                      — 品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py                        — 監査ログスキーマ初期化（signal/order/execution）
  - stats.py                        — 汎用統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py              — Momentum/Value/Volatility 等
  - feature_exploration.py          — 将来リターン / IC / 統計サマリ等
- ai/ (上記)
- research/ (上記)
- その他モジュール（strategy / execution / monitoring 等はパッケージ __all__ に含まれる想定）

サンプル .env（例）
------------------
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

デバッグ / テストのヒント
------------------------
- 自動 .env の読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテストでモックしやすいように設計されています（内部の _call_openai_api / _urlopen 等をパッチ）。
- DuckDB を使った単体テストでは ":memory:" を渡してインメモリ DB を利用できます。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス・貢献方法を追記してください）

お問い合わせ
------------
問題報告・機能要望はリポジトリの Issue をご利用ください。README に書かれていない使い方や設計意図の説明が必要であれば別途お知らせください。