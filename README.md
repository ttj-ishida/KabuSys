# KabuSys

KabuSys は日本株のデータ基盤・リサーチ・自動売買のためのライブラリ群です。J-Quants / DuckDB を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

## 主な特徴
- データ ETL（J-Quants API から株価 / 財務 / カレンダー取得、DuckDB への冪等保存）
- ニュース収集（RSS）とニュースに基づく銘柄センチメント（OpenAI を利用）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュース LLM 評価）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions のテーブル群と初期化ユーティリティ）
- 環境変数管理（.env / .env.local の自動読み込み、必要な設定を Settings で提供）

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env/.env.local 自動読み込み、Settings クラス（JQUANTS_REFRESH_TOKEN / KABU_API_* / OPENAI_API_KEY / Slack / DB パス等）
- kabusys.data
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・ページネーション）
  - news_collector: RSS 収集・正規化・raw_news への保存ロジック
  - calendar_management: JPX カレンダーの判定・更新ユーティリティ（is_trading_day 等）
  - quality: データ品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査（signal_events, order_requests, executions）テーブル定義と初期化関数
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で評価して ai_scores に保存
  - regime_detector.score_regime: MA とマクロニュースを合成して market_regime に保存
- kabusys.research
  - factor_research (calc_momentum, calc_value, calc_volatility)
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
- その他ユーティリティや設定ファイル

---

## 必要な環境・依存
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI API）
- 環境変数 / .env に API トークン等を設定

（実際の requirements.txt / packaging はプロジェクト側で管理してください）

---

## 環境変数（主なもの）
プロジェクトは .env / .env.local を自動的にルート（.git または pyproject.toml を探す）から読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数例:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---

## セットアップ手順（開発環境向け）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - もしくはプロジェクトの requirements.txt があれば pip install -r requirements.txt
4. .env を作成
   - リポジトリルートに .env を置き、上の環境変数を設定します。
   - 自動読み込みはデフォルトで有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
5. ローカル DB ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

- DuckDB 接続の作成（例）
  - import duckdb
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL の実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースの NLP スコアリング（ai_scores へ保存）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key 省略時は OPENAI_API_KEY を使う

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- ファクター計算・解析（研究用）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  - momentum = calc_momentum(conn, date(2026,3,20))
  - fwd = calc_forward_returns(conn, date(2026,3,20))
  - ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")

- 監査ログスキーマ初期化（監査 DB を作成）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

注意:
- OpenAI 呼び出しは network/料金が発生します。モデルは gpt-4o-mini を想定しています。
- J-Quants API 呼び出しはレート制御・認証が組み込まれています（JQUANTS_REFRESH_TOKEN を設定）。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル・モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py (パッケージ定義、__version__)
  - config.py (環境変数読み込み、Settings)
  - ai/
    - __init__.py (score_news のエクスポート)
    - news_nlp.py (ニュースの LLM スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - pipeline.py (ETL パイプライン: run_daily_etl など)
    - jquants_client.py (J-Quants API クライアント: fetch / save 関数)
    - news_collector.py (RSS 収集・正規化)
    - calendar_management.py (マーケットカレンダー管理)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize 等)
    - audit.py (監査テーブル DDL と初期化)
    - etl.py (ETLResult の再エクスポート)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)

（実際のプロジェクトルートは .git または pyproject.toml を基準に自動検出されます）

---

## 運用上の注意・設計方針（抜粋）
- Look-ahead バイアス対策: 各モジュールは内部で date.today() を不必要には参照せず、target_date ベースで計算します。ETL/スコアは明示的な日付を入力してください。
- 冪等性: J-Quants の保存関数や監査スキーマの初期化は冪等に設計されています（ON CONFLICT 等）。
- フェイルセーフ: LLM/API 失敗時は致命的に止めず、スコアのフォールバック（0.0）や処理スキップで継続できるようになっています。
- セキュリティ: news_collector は SSRF 対策、XML パーサ保護（defusedxml）、レスポンスサイズ制限などを実装しています。

---

## よくある質問 / トラブルシュート
- .env が読み込まれない
  - プロジェクトルートの判定は `.git` または `pyproject.toml` を上位ディレクトリから探索します。自動読み込みを無効化している場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。
- OpenAI 呼び出しが失敗する
  - 環境変数 `OPENAI_API_KEY` をセットするか、各関数の api_key 引数にキーを渡してください。rate-limit やタイムアウトはリトライ実装がありますが、料金やモデルのアクセス可否を確認してください。
- J-Quants の認証エラー
  - `JQUANTS_REFRESH_TOKEN` が正しいか、ネットワークや API 利用権限を確認してください。jquants_client は自動リフレッシュを行いますが、設定が必要です。

---

## 貢献・ライセンス
- 本 README はコードベースの簡易ドキュメントです。改良・補足があれば Pull Request を歓迎します。
- ライセンス情報はリポジトリ内の LICENSE を参照してください（本 README には記載がありません）。

---

README に書かれている関数名・設定名はソース内実装に基づいています。実運用では適切な権限設定・秘密情報管理、バックアップ、監視を行ってください。