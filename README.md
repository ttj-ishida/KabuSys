# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュースセンチメント（LLM）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを一貫して提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータパイプラインとリサーチ・オートメーションを目的としたモジュール群です。主な機能は以下の通りです。

- J-Quants API からの差分データ取得（株価日足・財務・上場リスト・市場カレンダー）
- DuckDB ベースの ETL パイプライン（差分取得、冪等保存、品質チェック）
- ニュース収集（RSS）と LLM による銘柄別センチメント評価（gpt-4o-mini の JSON Mode 想定）
- マクロニュース + ETF（1321）の MA200乖離を用いた市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算 (momentum, volatility, value) と特徴量解析（forward returns, IC, summary）
- 監査ログスキーマ（signal / order_request / execution）と監査DB初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴:
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない処理設計）
- API のリトライ・レート制御・フェイルセーフ（失敗時のフォールバック）を組み込み
- DuckDB を用いた軽量かつ高速な分析 / 永続化基盤

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env 自動ロード（プロジェクトルート基準）、環境変数ラッパー（settings）
- kabusys.data
  - jquants_client: API クライアント + DuckDB への保存関数
  - pipeline: ETL のエントリポイント（run_daily_etl）と ETLResult
  - calendar_management: 市場カレンダーと営業日ユーティリティ
  - news_collector: RSS 収集と前処理
  - quality: データ品質チェック
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログスキーマ初期化 / init_audit_db
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント取得（OpenAI）
  - regime_detector.score_regime: マクロ + MA200 を合成した市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: Python 3.10+（typing 用の構文を利用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください。

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C...
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO

4. DuckDB ファイル用フォルダを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（サンプル）

以下はライブラリの主要な利用例（対話的 / スクリプト）です。適宜 import して使用します。

- DuckDB 接続を作成する例:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（LLM）をスコアする:
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"ai_scores に書き込んだ銘柄数: {n_written}")

  - 注意: OPENAI_API_KEY が環境変数または api_key 引数で必要です。

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key 必須

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  - momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  - volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  - value = calc_value(conn, target_date=date(2026, 3, 20))

- 監査DB の初期化（監査用 DuckDB を作る）:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # これで signal_events/order_requests/executions テーブルが作成されます

- デバッグ / テスト向け:
  - 自動 .env ロードを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - OpenAI 呼び出しをモックしてユニットテストを実行する設計（モジュール内で _call_openai_api を差し替え可能）

---

## 重要な設計上の注意点

- Look-ahead バイアス防止:
  - 多くの関数は内部で現在時刻を直接参照せず、target_date を明示的に受け取ります。バックテストや再現性のため、target_date を明示して使用してください。

- 冪等性:
  - jquants_client の保存関数（save_*）や ETL は ON CONFLICT / DELETE→INSERT の形で冪等に設計されています。

- エラーハンドリング:
  - API 呼び出しはリトライ・フォールバックの扱いが組み込まれています（429 / ネットワーク / 5xx 対応）。ただし、外部 API のレスポンス変更等は考慮が必要です。

- テスト可能性:
  - OpenAI 呼び出しやネットワーク部分はモックしやすいように設計されています（内部関数を patch して差し替え可能）。

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
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: pipeline の ETLResult を etl から再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主要な API（抜粋）
- kabusys.config.settings
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token
- kabusys.data.news_collector.fetch_rss
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value

---

## よくある運用タスク（例）

- 夜間バッチ（ETL）ジョブ
  - run_daily_etl を cron / Airflow 等から呼び出し（target_date を渡すか省略で当日処理）。
  - ETLResult の has_errors / has_quality_errors で監視・アラートを行う。

- ニューススコアリング
  - 毎朝のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を対象に score_news を実行。

- レジーム判定
  - 毎営業日に score_regime を実行して market_regime テーブルを更新。戦略のモード切替に使用。

- 監査ログ
  - 取引実行フローでは audit.init_audit_db で DB を初期化し、シグナル→発注→約定をすべて記録する。

---

## トラブルシューティング

- 環境変数が読み込まれない:
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI / J-Quants API エラー:
  - ライブラリ内でリトライ・バックオフを行いますが、APIキーやレート制限状況、ネットワークの問題をまず確認してください。

- DuckDB での INSERT 実行時エラー:
  - executemany に空リストを渡すと DuckDB の一部バージョンでエラーになる箇所があるため、関数内で空チェックを行っています。独自に呼ぶ場合は空パラメータに注意してください。

---

必要であれば、README に「起動スクリプト」「CI 設定例」「.env.example」等を追加できます。どのドキュメントを優先して拡張しますか？