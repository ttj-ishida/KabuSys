# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・LLMによるニュースセンチメント、ファクター計算、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を備えた内部ライブラリです。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ページネーション・レートリミット・リトライ対応）
- DuckDB を用いたローカルデータプラットフォーム（ETL、品質チェック、監査テーブル）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄ごと／マクロ）
- 市場レジーム判定（ETF MA と LLM マクロセンチメントの合成）
- 研究用のファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）テーブル定義・初期化ユーティリティ

設計上のポイント：
- ルックアヘッドバイアス対策（内部処理は明示的な target_date を使い、date.today() 参照を避ける設計が多く採用されています）
- 冪等性（DuckDB への保存は ON CONFLICT を用いた上書き）
- フェイルセーフ（外部 API 失敗時は継続する実装方針が多い）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数読み込み（.env, .env.local）、必須設定チェック（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し／保存（fetch_*, save_*）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 取得 -> raw_news 保存（SSRF 等の対策あり）
  - calendar_management: マーケットカレンダーの判定／次営業日等ユーティリティ
  - audit: 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF (1321) MA とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

※ 実際の開発／運用では requirements.txt / Poetry / PDM 等で依存管理してください。

例（pip）:
pip install duckdb openai defusedxml

---

## 環境変数（主要）

kabusys.config.Settings で参照する主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（本コードでは参照のみ）
- SLACK_BOT_TOKEN — Slack 通知用（利用する場合）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 開発環境 ("development" / "paper_trading" / "live"), デフォルト "development"
- LOG_LEVEL — ログレベル（"DEBUG","INFO",...）デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に環境変数で注入可能）

.env の自動ロード順序（パッケージ起点でプロジェクトルートを探索）:
OS 環境変数 > .env.local > .env

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を作成（推奨: venv）
   python -m venv .venv
   source .venv/bin/activate

2. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. 環境変数を準備
   - プロジェクトルートに .env を置くか、OS 環境変数で必須値を設定します。
   - 最低限 JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD を設定してください。
   - OpenAI を使う場合は OPENAI_API_KEY を設定。関数呼び出しで api_key を直接渡すことも可能です。

4. DuckDB 初期化（監査用 DB 例）
   Python REPL / スクリプトで:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()

   またはアプリケーション起動時に同様の処理を行ってください。

---

## 使い方（基本的な呼び出し例）

以下は Python スクリプト内で呼ぶ例です。対象となる DuckDB 接続はプロジェクトの settings.duckdb_path を参照してください。

- 設定の読み込み・確認
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

- DuckDB 接続を開く
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング（AI）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY が環境変数にあるか、api_key 引数に渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)

- 市場レジーム評価（AI + MA）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（別 DB を使う場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  moment = calc_momentum(conn, date(2026, 3, 20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  zed = zscore_normalize(moment, ["mom_1m", "mom_3m", "mom_6m"])

注意:
- OpenAI への呼び出しは api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- score_news / score_regime は LLM 呼び出し失敗時にフォールバック処理を行う設計です（完全失敗時はスコア未保存や 0.0 フォールバックなど）。

---

## ディレクトリ構成

リポジトリの主要部分（src 配下）:

src/
  kabusys/
    __init__.py                # パッケージ初期化（__version__ 等）
    config.py                  # 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py              # ニュースセンチメント（銘柄別）
      regime_detector.py       # 市場レジーム判定（MA + マクロLLM）
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント + 保存関数
      pipeline.py              # ETL パイプライン（run_daily_etl 等）
      quality.py               # データ品質チェック
      news_collector.py        # RSS ニュース収集
      calendar_management.py   # 市場カレンダー管理 / 営業日ユーティリティ
      audit.py                 # 監査ログスキーマの定義と初期化
      stats.py                 # 汎用統計（zscore_normalize）
      etl.py                   # ETLResult 再エクスポート
    research/
      __init__.py
      factor_research.py       # Momentum / Value / Volatility 等の計算
      feature_exploration.py   # 将来リターン, IC, 統計サマリー 等

---

## 運用上の注意・ベストプラクティス

- Look-ahead バイアス対策として、研究（backtest）用途では ETL 実行日も含めたデータの取り扱いに注意してください。関数群は多くの場合 target_date を明示的に受け取る設計です。
- .env/.env.local に機密情報（API キー）を置く場合は、リポジトリにコミットしないでください。.gitignore を確認してください。
- OpenAI や J-Quants の API 呼び出しはコストとレート制限があります。テスト時はモック（unittest.mock.patch）で外部呼び出しを差し替えてください（コード内でもテスト差し替えを想定した設計になっています）。
- DuckDB のバージョン互換性に注意（特定の executemany の空リスト取り扱い等に関する記述あり）。

---

## 付録：よく使うスニペット

- settings を確認してから ETL を回す
  from kabusys.config import settings
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  res = run_daily_etl(conn)
  print(res.to_dict())

- OpenAI キーを関数に渡す例
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="sk-...")

---

もし README に追記したい項目（CI 設定、例データの投入手順、具体的な環境ファイルのテンプレート等）があれば教えてください。README をプロジェクトの実態に合わせてさらに詳細化します。