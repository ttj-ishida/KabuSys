# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL、ニュースNLP、AIによる市場レジーム判定、リサーチ用ファクター計算、監査ログなどを提供します。

主な用途
- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）
- RSS ニュース収集と OpenAI を使った銘柄別センチメント評価（AI/NLP）
- ETF + マクロニュースを組み合わせた市場レジーム判定（AI）
- ファクター計算 / 特徴量探索（Research）
- DuckDB を用いた監査ログ（order / signal / execution）管理と初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧

- config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と Settings による安全な取得
  - 必須環境変数未設定時に明示的なエラーを出すユーティリティ

- data
  - jquants_client: J-Quants API 呼び出し、レート制御、リトライ、DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl）や個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得、URL 正規化、SSRF 対策、raw_news への冪等保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: 市場カレンダーの管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査ログテーブル作成 & 初期化（init_audit_schema / init_audit_db）
  - stats: z-score 正規化ユーティリティ

- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に記録

- research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター算出）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（IC 計算や統計サマリー）

---

## セットアップ手順

推奨: Python 3.10+ を使用してください（タイプ注釈に対応しているため）。プロジェクト配布形態により仮想環境を作成して行ってください。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール
   - pip install -e .            （パッケージ化している場合）
   - または必要な依存を個別にインストール:
     - pip install duckdb openai defusedxml

   （上記はライブラリの使用に必要な代表例です。プロジェクトに requirements.txt があればそちらを使用してください。）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env / .env.local を置くことで自動ロードされます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主な環境変数（必須のものあり）:
   - JQUANTS_REFRESH_TOKEN  ← J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD      ← kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN        ← Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID       ← Slack チャネル ID（必須）
   - OPENAI_API_KEY         ← OpenAI を使用する場合（関数呼び出し時に api_key を渡すことも可）
   - DUCKDB_PATH            ← デフォルト: data/kabusys.duckdb
   - SQLITE_PATH            ← デフォルト: data/monitoring.db
   - PID_FILE_PATH          ← デフォルト: data/execution.pid
   - KABUSYS_ENV            ← development | paper_trading | live（デフォルト development）
   - LOG_LEVEL              ← DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方（例）

以下は代表的な利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を開いて日次 ETL を実行する:
  - Python 例:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect("data/kabusys.duckdb")
      result = run_daily_etl(conn, target_date=date(2026, 3, 20))
      print(result.to_dict())

- ニュースのスコアリング（OpenAI を使用）:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
    print(f"scored {n} codes")

- 市場レジーム判定:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- ファクター計算 / リサーチ:
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026, 3, 20))
    val = calc_value(conn, date(2026, 3, 20))
    vol = calc_volatility(conn, date(2026, 3, 20))

- 監査 DB の初期化:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # ファイルがなければ作成しスキーマを初期化

注意点 / ベストプラクティス
- OpenAI 呼び出しは API 料金が発生します。ローカルテストではモック（unittest.mock.patch）して _call_openai_api を差し替えてください（news_nlp と regime_detector それぞれ独立実装の _call_openai_api を持ちます）。
- run_daily_etl 等の内部はトランザクションとロールバックを行いますが、ETL 時はログと品質チェック結果（ETLResult.quality_issues）を確認してください。
- .env の取り扱い: .env.local は .env を上書きします。OS 環境変数が優先されます。
- Look-ahead バイアス対策: 多くの関数（score_news, score_regime, ETL 等）は明示的な target_date を受け取り、内部で date.today() を直接参照しない設計です。バックテスト用途では target_date を明示してください。

---

## 主要モジュールの説明（短評）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）
  - Settings クラス: 必須環境変数の取得とバリデーション、パスや閾値の取得

- kabusys.data.jquants_client
  - J-Quants API のリクエスト / レスポンス処理、トークン取得、自動リフレッシュ、レート制御、DuckDB への冪等保存

- kabusys.data.pipeline
  - 日次 ETL 実装（差分取得、保存、品質チェック）

- kabusys.data.news_collector
  - RSS 取得 / 前処理 / SSRF 対策 / raw_news への保存

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）

- kabusys.data.calendar_management
  - market_calendar の管理、営業日判定や next/prev_trading_day 等のユーティリティ

- kabusys.data.audit
  - 監査ログ (signal_events / order_requests / executions) の DDL と初期化

- kabusys.ai.news_nlp
  - 銘柄毎のニュース集合を LLM に渡して JSON モードでスコアリング。バッチ処理、リトライ、レスポンス検証あり。

- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュース（LLM）の重み付き合成で market_regime に判定を書き込む

- kabusys.research.*
  - ファクター計算、将来リターン、IC 計算、統計サマリーなどリサーチ用途の実装

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py                   -- ニュース NLP スコアリング
  - regime_detector.py            -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             -- J-Quants API クライアント + 保存関数
  - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
  - etl.py                        -- ETL インタフェース ETLResult 再エクスポート
  - news_collector.py             -- RSS 収集・前処理
  - quality.py                    -- データ品質チェック
  - calendar_management.py        -- 市場カレンダー管理
  - audit.py                      -- 監査スキーマ初期化
  - stats.py                      -- zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py            -- Momentum / Value / Volatility 計算
  - feature_exploration.py        -- 前方リターン / IC / summary / rank
- ai/、data/、research/ 等に含まれる補助モジュール多数

（README に記載のないサブモジュールも多数含まれます。詳しくはソースツリーを参照してください。）

---

## 追加メモ・運用上の注意

- 並列実行 / 本番稼働時は API レートや OpenAI 使用量に注意してください。
- DuckDB は単一ファイルの DB で軽量ですが、本番監査 DB はバックアップ運用を検討してください。
- audit.init_audit_schema は transactional 引数でトランザクション化できますが、DuckDB のトランザクション制約（ネスト不可）に注意してください。
- テスト時は外部 API 呼び出し（J-Quants / OpenAI / HTTP）をモックしてください。news_nlp と regime_detector は内部で _call_openai_api を定義しているため、テスト時はそれらをパッチすることで外部アクセスを防げます。

---

必要に応じて README にさらに「API リファレンス」や「運用手順（cron / systemd）」、より具体的な .env.example の例を追加できます。追加情報が必要であれば教えてください。