# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、研究用ファクター計算、マーケットカレンダー管理、監査ログ（約定トレーサビリティ）などを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 必要な環境変数（.env）
- 基本的な使い方（サンプルコード）
- よく使う API / モジュール一覧（簡易説明）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株のデータ取得・品質管理・特徴量生成・ニュースセンチメント評価・市場レジーム判定・監査ログなど、自動売買プラットフォームの基盤機能を提供する Python パッケージです。
- データソースは主に J-Quants API（株価、財務、マーケットカレンダー）。ニュースは RSS から収集し、OpenAI（gpt-4o-mini 等）で自然言語処理を行います。
- データ保存は DuckDB（オンディスク / インメモリ）を主に想定。監視用に SQLite を使う部分が設定で用意されています。

機能一覧
- ETL（差分取得 + 保存 + 品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（ページネーション・レート制限・リトライ・トークンリフレッシュ対応）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメント付与: score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離 と マクロセンチメントを合成: score_regime）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、Z スコア正規化 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマの初期化（signal_events / order_requests / executions）と DB 初期化ユーティリティ

前提・依存関係
- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで多くを実装していますが、OpenAI や DuckDB は必須で利用する機能に合わせてインストールしてください。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・アクティベート（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
3. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発用）pip install -e .
4. 環境変数を設定
   - プロジェクトルートに `.env`（および `.env.local` があれば優先）を置くと自動で読み込まれます。
   - 自動ロードを無効化したい場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須 / 任意の環境変数（.env 例）
- 必須（多くの機能がこれらを要求します）
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - SLACK_BOT_TOKEN=your_slack_bot_token
  - SLACK_CHANNEL_ID=your_slack_channel_id
  - KABU_API_PASSWORD=your_kabu_api_password
- OpenAI 関連
  - OPENAI_API_KEY=your_openai_api_key  # score_news / score_regime のデフォルト参照先
- データベースパス（デフォルト値あり）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
- 実行環境モード / ログレベル
  - KABUSYS_ENV=development|paper_trading|live  (default: development)
  - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)

例 .env の行（簡易）
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=./data/kabusys.duckdb

自動 .env の読み込みについて
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で自動ロードします。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。テスト時等は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。

基本的な使い方（サンプル）

- DuckDB 接続を作って日次 ETL を実行する
  - サンプル:
    - import duckdb, datetime
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 25))
    - print(result.to_dict())

- ニュースセンチメントを生成する（score_news）
  - サンプル:
    - import duckdb, datetime, os
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - # 環境変数 OPENAI_API_KEY が設定されていることを確認
    - n_written = score_news(conn, datetime.date(2026, 3, 25))
    - print(f"Scored {n_written} symbols")

- 市場レジームをスコアリングする（score_regime）
  - サンプル:
    - import duckdb, datetime
    - from kabusys.ai.regime_detector import score_regime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_regime(conn, datetime.date(2026, 3, 25))  # OpenAI キーは環境変数参照

- 監査（audit）DB を初期化する
  - サンプル:
    - from kabusys.data.audit import init_audit_db
    - conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

よく使う API / モジュール（簡易説明）
- kabusys.config
  - settings: 環境変数から各種設定を取得（J-Quants, kabu, Slack, DB パス, env 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token (refresh token を使い id_token を取得)
- kabusys.data.pipeline
  - run_daily_etl: 日次の ETL をまとめて実行（カレンダー → 株価 → 財務 → 品質チェック）
  - ETLResult: 実行結果を保持する dataclass
- kabusys.data.news_collector
  - fetch_rss / preprocess_text など RSS の安全な取得・正規化
- kabusys.ai.news_nlp
  - score_news: 銘柄ごとにニュースをまとめ、OpenAI でスコア化して ai_scores に保存
- kabusys.ai.regime_detector
  - score_regime: ETF 1321 の MA200 乖離＋マクロセンチメントで市場レジームを判定・保存
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility 等）、forward returns、IC、summary
- kabusys.data.quality
  - run_all_checks: 欠損、重複、スパイク、日付不整合などを検出して QualityIssue を返す
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL まわりの再エクスポート
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — マーケットカレンダー関連
    - stats.py — 汎用統計 (zscore_normalize)
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（モメンタム/ボラティリティ/バリュー等）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等

開発上の注意点
- ルックアヘッドバイアス回避のため、多くの関数は内部で date.today() を直接参照せず、target_date を引数で受け取る設計です。バックテスト等では target_date を意図的に指定してください。
- OpenAI 呼び出しは外部 API を利用するため、キーと課金設定に注意してください。API 呼び出し失敗時はフェイルセーフ（多くはスコア 0 やスキップ）となるよう実装されていますが、運用ポリシーを検討してください。
- DuckDB に対する executemany 等はバージョン依存の挙動を考慮した実装（空リストの扱いなど）がなされています。DuckDB のバージョンに注意してください。

貢献・拡張
- 新たな ETL ソース追加、ニュースソース拡張、モデルやプロンプトの調整、監査スキーマの拡張など、拡張ポイントが多数あります。変更はユニットテストと実データでの検証を推奨します。

ライセンス・その他
- （リポジトリに LICENSE があればそちらに従ってください。README に特定のライセンス記載が必要であれば追記してください）

---

何か特定の使い方（例: ETL の詳細な実行手順、OpenAI のプロンプト調整、監査 DB の運用方法）についてドキュメント化やサンプルコードが必要であれば教えてください。必要に応じて README に追加の実行例や運用チェックリストを追記します。