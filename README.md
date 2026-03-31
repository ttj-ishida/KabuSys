# KabuSys

日本株向けのデータ処理・リサーチ・簡易自動売買プラットフォームのライブラリ群です。  
主に以下を提供します。

- J-Quants からのデータ ETL（株価・財務・カレンダー）
- ニュース収集 / ニュースに基づく LLM センチメント評価
- 市場レジーム判定（MA + マクロニュースの LLM 評価）
- ファクター計算・特徴量探索（リサーチ用）
- データ品質チェック
- 監査ログ（シグナル→オーダー→約定のトレース）
- DuckDB ベースの冪等保存・運用ユーティリティ

設計上の重要ポイント：
- ルックアヘッドバイアス防止（内部で現在時刻に依存する処理を避ける）
- DuckDB への冪等保存（ON CONFLICT / UPDATE）
- J-Quants / OpenAI 呼び出しに対するリトライ・バックオフ、レート制御
- ニュース収集の SSRF 対策・入力正規化
- ETL / 品質チェックは Fail-Fast ではなく問題収集型

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・前処理・raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化 / 専用 DB 作成（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP による銘柄センチメント（score_news）
  - 市場レジーム判定（score_regime）：ETF 1321 の 200 日 MA とマクロニュースの LLM スコアを合成
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込みと Settings（自動 .env ロード、必須キー判定、各種パス・閾値）

---

## セットアップ手順

前提：
- Python 3.10 以上（typing の | 形式を使用）
- システムに pip と仮想環境ツールがあること

1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt があればそれを使用してください。ない場合の最小例：
     - pip install duckdb openai defusedxml
   - 開発インストール（パッケージとして使う場合）
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートの .env または .env.local に必要項目を設定します。Settings で参照する主要な環境変数：
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - OPENAI_API_KEY (LLM を使う機能がある場合必須)
     - KABU_API_PASSWORD (kabuステーション API 用)
     - KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (Slack 通知)
     - SLACK_CHANNEL_ID (Slack チャンネル)
     - DUCKDB_PATH (任意、デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (任意、デフォルト data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development | paper_trading | live (デフォルト development)
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト INFO)
   - 自動 .env ロードを無効にする:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB ディレクトリの作成（必要に応じて）
   - settings.duckdb_path の親ディレクトリが自動作成されますが、手動で準備しておくことも可能です。

---

## 使い方（主要な例）

以下は簡単な Python スクリプト / REPL 例です。

- 共通：設定と DuckDB 接続
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(res.to_dict())

- ニュースセンチメントスコア生成
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026,3,20))
  - print(f"written {n} codes")

- 市場レジーム判定
  - from datetime import date
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key=YOUR_OPENAI_KEY)

- 監査ログ DB 初期化（専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # audit_conn を使って監査テーブルにアクセス可能

- ファクター計算 / リサーチ
  - from datetime import date
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - m = calc_momentum(conn, target_date=date(2026,3,20))
  - v = calc_value(conn, target_date=date(2026,3,20))
  - vol = calc_volatility(conn, target_date=date(2026,3,20))

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

注意点：
- OpenAI 呼び出しを行う関数は api_key 引数で直接渡すことができます（テストやキーマネジメントのため）。
- ETL・API 呼び出しは外部サービスに依存するため、適切な API キーとネットワーク環境が必要です。
- 各種関数は DuckDB 接続を受け取ります（接続の生成/クローズは呼び出し側で行ってください）。

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
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 data 関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各ファイルの役割（要約）
- config.py: .env / 環境変数のパースと Settings クラス（自動 .env ロード、必須キー検査）
- ai/news_nlp.py: raw_news を集約して OpenAI に投げ、ai_scores を更新するロジック（バッチ/バリデーション/リトライ）
- ai/regime_detector.py: ETF 1321 の MA200 乖離とニュース LLM スコアを合成して market_regime を更新
- data/pipeline.py: ETL のトップレベル（run_daily_etl 等）
- data/jquants_client.py: J-Quants API との通信（レート制御、認証、自動リフレッシュ、save_* 関数）
- data/news_collector.py: RSS 取得と前処理（正規化・SSRF 防御・圧縮対応）および raw_news 保存
- data/quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）
- data/audit.py: 監査ログ用テーブル DDL と初期化ユーティリティ
- research/*: ファクター計算・特徴量探索・IC 計算など

---

## 運用上の注意 / 実装上の特徴

- Look-ahead バイアス対策：ほとんどの処理は target_date を引数に受け、datetime.today()/date.today() を直接参照しない実装になっています（ETL の場合は明示的に today を渡すことが可能）。
- 冪等性：DuckDB への保存は ON CONFLICT を用いた更新式で行われ、再実行に耐える設計です。
- 再試行とバックオフ：J-Quants および OpenAI 呼び出しはリトライ/指数バックオフのロジックを持ち、5xx や接続障害、429 等に対処します。
- レート制御：J-Quants は固定間隔スロットリング（120 req/min）で保護されています。
- セキュリティ：news_collector は URL 正規化、トラッキングパラメータ削除、SSRF 対策（プライベートアドレス拒否、リダイレクト検査）を実装しています。
- ロギング：各モジュールで logger を使用。LOG_LEVEL は環境変数で設定します。

---

## 既知の前提／制限

- DuckDB を内部 DB として想定しているため、大量の同時書き込み等の特殊な運用は別途検討が必要です。
- OpenAI のレスポンスは JSON mode を想定してパースしていますが、稀に余計なテキストが含まれる場合の復元処理を実装しています（ただし完全保証はしません）。
- J-Quants API のスキーマ変更や OpenAI SDK の将来変更により細部の修正が必要になる場合があります。

---

この README はコードベースの概要説明と基本的な使用法を示しています。実際の運用では .env.example を参考に必要な環境変数を設定し、テスト環境（paper_trading / development）で動作確認した上で live 環境に移行してください。

必要であれば、README に含めるサンプルスクリプトや詳細な API リファレンス（関数一覧・引数説明）を追記します。どの部分を詳細化したいか教えてください。