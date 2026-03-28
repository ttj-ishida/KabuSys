# KabuSys

日本株自動売買プラットフォームのライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などをモジュール化しています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けのデータプラットフォーム及び研究／自動売買の基盤ライブラリです。主な責務は以下です。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理、OpenAI によるニュースセンチメント評価
- マーケットレジーム判定（ETF + マクロニュースの複合）
- ファクター（モメンタム／バリュー／ボラティリティ等）計算および研究用ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）用スキーマ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上、バックテスト等でのルックアヘッドバイアスを避けるために日付の扱いや API 呼び出しの位置に注意が払われています。

---

## 機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch/save for daily quotes, financial statements, market calendar）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース処理・NLP
  - RSS 取得・前処理・保存（news_collector）
  - OpenAI を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - マクロニュース＋ETF MA による市場レジーム判定（regime_detector.score_regime）
- 研究用（research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴探索: calc_forward_returns, calc_ic, factor_summary, rank
  - 共通統計: zscore_normalize
- データユーティリティ
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - データ品質チェック（missing, spike, duplicates, date consistency）
- 監査（audit）
  - 監査用スキーマ初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / 環境変数の自動読み込み（kabusys.config.settings）

---

## セットアップ手順

1. リポジトリをクローン

   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install -e .   # パッケージが setuptools/pyproject で管理されている前提

   または最低限の依存を直接入れる場合:

   pip install duckdb openai defusedxml

   ※ 実運用ではさらに requests 等が必要になる可能性があります。pyproject.toml / requirements.txt がある場合はそちらを参照してください。

4. 環境変数／.env の準備

   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。

   必須環境変数（kabusys.config.Settings で要求されるもの）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意 / デフォルト値あり:

   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API base URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）

   例 .env:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pwd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

以下は主要なユースケースのサンプルです。

- DuckDB 接続を作る（設定のパスを利用）

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（デフォルトは今日）

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）をスコアリングして ai_scores に書き込む

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n} stocks")

- 市場レジーム判定を実行

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- 監査 DB の初期化

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- データ品質チェックを実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点:
- score_news / score_regime は OpenAI API を使用します。API キーの管理と料金に注意してください。
- 多くの処理は日付の扱いに注意して実装されており、内部で datetime.today() を直接参照しない設計です（バックテスト向け）。
- J-Quants API はレート制限と認証が必要です。J-Quants からの ID トークン自動更新を備えています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         # 銘柄別ニュースセンチメント（OpenAI）
  - regime_detector.py  # ETF + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   # J-Quants API クライアント（fetch/save）
  - pipeline.py         # ETL パイプライン（run_daily_etl 等）
  - etl.py              # ETLResult のエクスポート
  - news_collector.py   # RSS 収集・前処理
  - calendar_management.py # マーケットカレンダー管理
  - stats.py            # 統計ユーティリティ（zscore_normalize）
  - quality.py          # データ品質チェック
  - audit.py            # 監査ログスキーマ（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py  # モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py  # 将来リターン / IC / 統計サマリー等

各モジュールは DuckDB 接続を引数に受け取ることが多く、直接外部発注や本番口座へアクセスする処理は分離されています（安全性・テスト容易性向上）。

---

## 実運用上の注意

- 機密情報（API トークン）は .env に保存する際にもアクセス権に注意してください。CI/CD ではシークレット管理を利用してください。
- OpenAI / J-Quants の呼び出し回数は料金・レート制限の観点でコスト管理が必要です。news_nlp と regime_detector にはリトライ・バックオフが実装されていますが、運用時は呼び出し頻度を制御してください。
- DuckDB のバージョン差異に起因する挙動（executemany の空リスト等）に注意して、テスト環境で検証してください。
- 自動売買（発注）を組み合わせる場合はリスク管理（ポジション制限、二重発注防止、監査ログの確認）を必ず組み込んでください。

---

## よくある質問 / トラブルシュート

- .env が読み込まれない
  - プロジェクトルートの検出はソースファイル位置から起点で .git または pyproject.toml を探しています。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境変数をセットしてください。

- OpenAI のレスポンスでパースエラーが出る
  - モジュールは JSON モードを期待していますが、LLM が余分なテキストを返す場合があります。news_nlp と regime_detector はパース失敗時にログを残してフェイルセーフ（スコア 0 等）で継続します。API の温度を 0 に固定している点にも注意してください。

- J-Quants の 401 が発生する
  - jquants_client は 401 発生時にリフレッシュトークンで ID トークンを再取得して最大 1 回リトライします。refresh token が無効な場合は get_id_token で明示的に refresh token を渡して確認してください。

---

README への追加要望（例: サンプルデータの用意、CI 設定、詳細な API ドキュメント生成など）があればお知らせください。必要に応じてサンプルスクリプトやユニットテストの説明も追記します。