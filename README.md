# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データプラットフォーム向けライブラリ群です。  
データの ETL、ニュース NLP による銘柄スコアリング、市場レジーム判定、リサーチ用ファクター計算、監査ログ管理などを提供します。

---

## 概要

本プロジェクトは以下の責務を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API 経由で株価・財務・カレンダー等を取得し DuckDB に保存）
- ETL パイプライン（差分取得、品質チェック）
- ニュース収集・NLP（RSS 取得、OpenAI によるセンチメント分析）
- 市場レジーム判定（ETF の MA とマクロ記事センチメントの合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数・設定管理（.env 自動読み込み等）

設計上、バックテスト時のルックアヘッドバイアスを避けるために
date/datetime の扱いに配慮した実装になっています（多くの処理で明示的な target_date を受け取る）。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API との通信（認証トークン自動リフレッシュ、ページネーション、レート制御、リトライ）
  - fetch / save の冪等的保存（DuckDB への ON CONFLICT 実装）
- data.pipeline
  - run_daily_etl: カレンダー、日足、財務データの差分ETLと品質チェックの統合実行
  - 個別の ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector
  - RSS 収集、前処理、raw_news への保存（SSRF対策・Gzip制限・トラッキングパラメータ除去）
- ai.news_nlp
  - OpenAI（gpt-4o-mini）を用いた銘柄単位ニュースセンチメントの生成（ai_scores へ保存）
  - バッチ処理、JSON Mode のレスポンス検証、リトライロジック
- ai.regime_detector
  - ETF 1321（日経225連動型）の200日移動平均乖離とマクロニュースLLMスコアを合成して市場レジーム判定（bull / neutral / bear）
- research
  - calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- data.quality
  - 欠損、重複、スパイク、日付不整合などの品質チェック
- data.audit
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）と DB 初期化ユーティリティ
- config
  - .env（.env.local）自動読み込み（プロジェクトルート検出）、必須設定チェック、環境フラグ管理

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントで | を使用）
- DuckDB と OpenAI SDK、defusedxml などが必要

例: pip を使ったインストール（仮想環境推奨）

1. 仮想環境作成 & 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt がある場合はそれを使用してください。

3. パッケージを編集モードでインストール（任意）
   - pip install -e .

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（代表例）
- JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY：OpenAI API キー（ai モジュールを使う場合必須）
- KABU_API_PASSWORD：kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN：Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID：Slack 通知用チャンネル ID
- DUCKDB_PATH（任意）：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（任意）：監視などで使用する SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV（任意）：development / paper_trading / live（デフォルト development）
- LOG_LEVEL（任意）：DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env の書式は一般的な KEY=VALUE に対応し、export プレフィックスやクォート・コメントも扱えます。

---

## 使い方（代表的な例）

以下はライブラリを直接インポートして使用する例です。実運用ではスクリプトやジョブから呼ぶことを想定しています。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
  - 例:
    - python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); r=run_daily_etl(conn, target_date=datetime.date(2026,3,20)); print(r.to_dict())"

- ニュースの NLP スコアリングを実行（ai.news_nlp.score_news）
  - 例:
    - python -c "import duckdb, datetime, os; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); os.environ['OPENAI_API_KEY']='sk-...'; print(score_news(conn, datetime.date(2026,3,20)))"

  - score_news の挙動:
    - 対象ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTCに変換して DB と照合）
    - OpenAI にバッチ送信（最大 20 銘柄/リクエスト）、JSON Mode で結果を検証し ai_scores に書き込み

- 市場レジーム判定（ai.regime_detector.score_regime）
  - 例:
    - python -c "import duckdb, datetime, os; from kabusys.ai.regime_detector import score_regime; conn=duckdb.connect('data/kabusys.duckdb'); os.environ['OPENAI_API_KEY']='sk-...'; print(score_regime(conn, datetime.date(2026,3,20)))"

  - 計算内容:
    - ETF 1321 の 200 日 MA 乖離（重み 70%） + マクロ記事の LLM センチメント（重み 30%）を合成して regime_score を算出し market_regime テーブルへ冪等書き込み

- 監査ログスキーマ初期化
  - 監査用の DuckDB を初期化して接続を取得する:
    - python -c "from kabusys.data.audit import init_audit_db; conn = init_audit_db('data/audit.duckdb'); print('OK')"

- リサーチ用関数例
  - calc_momentum / calc_volatility / calc_value:
    - python -c "import duckdb, datetime; from kabusys.research.factor_research import calc_momentum; conn=duckdb.connect('data/kabusys.duckdb'); print(calc_momentum(conn, datetime.date(2026,3,20))[:5])"

注意点:
- OpenAI API を使う関数は api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError が発生します。
- ETL / API 呼び出しはリトライとログ出力を備えていますが、実運用ではログ監視・監査を組み合わせてください。

---

## 設定 & 環境変数の自動読み込み挙動

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）を特定し、以下の順で .env を自動ロードします:
  - OS 環境変数（既存） > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースは export KEY=val、クォート、インラインコメント、エスケープシーケンスに対応しています。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py  -- パッケージ定義（バージョン等）
- config.py    -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py         -- ニュース NLP（score_news）
  - regime_detector.py  -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   -- J-Quants API クライアント（fetch/save）
  - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
  - etl.py              -- ETLResult 再エクスポート
  - news_collector.py   -- RSS 収集・前処理
  - quality.py          -- データ品質チェック
  - stats.py            -- 統計ユーティリティ（zscore_normalize）
  - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
  - audit.py            -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py      -- モメンタム・バリュー・ボラティリティ計算
  - feature_exploration.py  -- 将来リターン、IC、統計サマリー等
- monitoring / strategy / execution / ... （__all__ で公開される可能性のあるパッケージ群）

（注）ここに示したファイルは本コードベースに含まれる主要モジュールです。詳細は各ファイルの docstring を参照してください。

---

## 実運用での注意点

- 実際に発注・約定を伴う機能を組み合わせる場合は paper_trading/live の切替や厳格なリスク管理を実装してください（KABUSYS_ENV）。
- OpenAI や J-Quants の API キーは安全に管理してください。ソース管理に直接コミットしないこと。
- DuckDB ファイルや監査 DB のバックアップ戦略、ログローテーションを検討してください。
- ニュース収集・外部 URL 取得には SSRF 対策・サイズ制限・XML 脆弱性対策（defusedxml）を実装済みですが、運用環境のネットワークポリシーも合わせて確認してください。

---

## サポート / 開発者向け情報

- ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/...）。
- 開発環境では KABUSYS_ENV=development を使用してください。
- テストや CI で自動環境読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 関数の多くは外部副作用を最小化する設計（引数で conn / target_date / api_key を受ける）なので、ユニットテストが容易です。モック注入用に内部の _call_openai_api や _urlopen を差し替えられる箇所があります。

---

README は以上です。特定の機能の使い方（例: ETL の細かい引数、news_nlp の出力形式、監査ログスキーマの詳細など）についてサンプルコードや運用手順が必要であれば、用途に応じた章を追加して詳細を提供します。どの機能の例が欲しいか教えてください。