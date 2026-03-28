# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集、ニュース・マクロの NLP/LLM スコアリング、ファクター計算、監査ログ（発注→約定トレーサビリティ）など、運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴:
- DuckDB をデータ層に利用（軽量で高速）
- J-Quants API 経由の差分 ETL（レート制御・リトライ・トークン自動更新）
- ニュース RSS の安全な収集（SSRF／XML爆弾対策、トラッキング除去）
- OpenAI（gpt-4o-mini）によるニュースセンチメント / マクロ判定（JSON mode）
- 研究用ファクター計算・統計ユーティリティ（pandas 非依存で標準ライブラリ実装）
- 発注・約定の監査ログスキーマ（冪等性とトレーサビリティ重視）
- 環境変数／.env 自動読み込み（プロジェクトルートを探索）

---

## 機能一覧

- データ収集・ETL
  - run_daily_etl: 市場カレンダー / 株価日足 / 財務データ の差分取得と保存
  - jquants_client: API 呼び出し・ページネーション・保存関数 (save_daily_quotes 等)
- ニュース処理
  - news_collector.fetch_rss: RSS 取得と前処理、raw_news への保存向けの整形
  - preprocess_text / URL 正規化 / 記事ID生成（SHA-256短縮）
- NLP / LLM
  - score_news: ニュースを銘柄ごとにまとめて LLM でセンチメント評価し ai_scores に書込
  - regime_detector.score_regime: ETF（1321）MA200 乖離 と マクロニュースセンチメントを合成して市場レジーム判定（bull/neutral/bear）
- 研究（Research）
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・IC 計算等
  - zscore_normalize（data.stats で提供）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db：監査用テーブル・インデックスの初期化

---

## 必要条件 (依存パッケージ)

最低限必要な Python パッケージ（抜粋）:
- duckdb
- openai
- defusedxml

その他、標準ライブラリのみで多くを実装しています。プロジェクトに合わせて requirements.txt を用意してください。

---

## 環境変数

主要な環境変数（必須 → 処理で require される場合あり）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY : OpenAI API キー（LLM 呼び出しで使用。score_news/score_regime は引数でも渡せます）
- KABU_API_PASSWORD : kabu ステーション API パスワード（実行系で必要）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知対象チャンネル ID
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",... )

自動で .env / .env.local をプロジェクトルートから読み込みます（プロジェクトルートは .git または pyproject.toml を基準）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の書式は一般的な KEY=VALUE や export KEY=VALUE に対応し、クォートやコメントの扱いも考慮されています。

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. .env の作成
   - プロジェクトルートに .env を作成し、上記の環境変数を設定してください。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb

4. データベースディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な呼び出し例）

以下は Python スクリプトまたは REPL での簡単な使用例です。

- DuckDB 接続の作成（デフォルトパスを使用する場合）:
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング（LLM を使う）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で渡す

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, date(2026, 3, 20))  # OpenAI API キーは env または引数で指定

- RSS を取得（ニュース収集の個別操作）:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])

- 監査ログ DB の初期化:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- 監査スキーマの既存接続への初期化:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # transactional=True も選択可

注意点:
- score_news / score_regime は OpenAI を呼ぶため API キーとレート、コストに注意してください。
- run_daily_etl 等は DB スキーマが事前に整っていることを想定します（必要なテーブル作成はスキーマ初期化用ユーティリティを用意する想定）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（自動 .env ロードを含む）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — マクロ + MA200 を混合した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save / 認証 / rate limit）
    - pipeline.py        — ETL パイプラインと run_daily_etl, run_*_etl
    - calendar_management.py — マーケットカレンダー管理（is_trading_day など）
    - news_collector.py  — RSS 収集・前処理
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - quality.py         — データ品質チェック群
    - etl.py             — ETLResult の再エクスポート
    - audit.py           — 監査ログ（発注・約定）スキーマと初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/*、data/*、research/* はそれぞれのドメインロジックを提供

---

## 補足・運用上の注意

- Look-ahead バイアス回避: モジュールの多くは date 引数ベースで動作し、内部で date.today() を直接参照しないよう設計されています。バックテストやバッチ運用時は target_date の扱いに注意してください。
- 冪等性: ETL / 保存関数は可能な限り ON CONFLICT / DELETE→INSERT の手法で冪等的に動作します。
- LLM 呼び出し: レートやエラーに対するリトライやフォールバック（失敗時スコア=0 など）が組込まれていますが、運用時のコストやレスポンスの安定性に留意してください。
- セキュリティ: news_collector は SSRF 対策・XML 脆弱性対策（defusedxml）・受信サイズ制限を実装しています。外部 URL を扱う際は追加ポリシー（ホワイトリスト等）の適用を検討してください。

---

もし README に追加したい具体的なセットアップ手順（CI / Docker / requirements.txt の内容）やサンプルスクリプトがあれば教えてください。README をその内容に合わせて拡張します。