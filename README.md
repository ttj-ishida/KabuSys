# KabuSys

日本株向けのデータパイプラインと研究・自動売買支援ライブラリ集です。  
DuckDB をデータレイヤに使い、J-Quants や RSS / OpenAI を組み合わせて ETL、品質チェック、ニュースセンチメント、マーケットレジーム判定、ファクター計算、監査ログなどを提供します。

## 特徴（概要）
- J-Quants API 経由の株価・財務・上場銘柄・市場カレンダーの差分 ETL（ページネーション・レート制御・自動トークンリフレッシュ対応）
- DuckDB へ冪等保存（ON CONFLICT DO UPDATE）する保存ユーティリティ
- データ品質チェック（欠損・スパイク・重複・将来日付／非営業日検出）
- ニュース収集（RSS）と LLM による銘柄別センチメント（gpt-4o-mini、JSON mode）
- マクロニュースと ETF（1321）MA200乖離の合成で市場レジーム判定（bull/neutral/bear）
- リサーチ用ユーティリティ（モメンタム・ボラティリティ・バリュー計算、将来リターン、IC、統計サマリ、Zスコア正規化）
- 監査ログスキーマ（signal → order_request → executions）の初期化ユーティリティ
- 安全設計（Look-ahead バイアス対策、リトライ／バックオフ、SSRF対策、レスポンスサイズ制限、タイムスタンプは UTC）

---

## 機能一覧（主要モジュール）
- kabusys.config: 環境変数 / .env 読み込み・設定ラッパー
- kabusys.data
  - pipeline: 日次 ETL 実行エントリ（run_daily_etl 等）
  - jquants_client: J-Quants API 呼び出し + DuckDB 保存関数
  - news_collector: RSS 収集と前処理（トラッキング除去・SSRF対策）
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: データ品質チェック（QualityIssue）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントの取得と ai_scores への保存
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースを合成した市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提条件
- Python 3.9+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース、OpenAI）

インストールはプロジェクトの pyproject / requirements に従ってください。最低限は:

pip install duckdb openai defusedxml

（用途に応じて他の依存を追加してください）

---

## 環境変数 / .env
kabusys.config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等で利用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（default: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）

自動 .env ロード:
- パッケージ起点(__file__ の親)からプロジェクトルートを .git または pyproject.toml で探索し、
  .env → .env.local の順で自動読み込みします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例: .env.example（プロジェクトルート）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## セットアップ（ローカル）
1. リポジトリをクローンし、仮想環境を作成・有効化
2. 依存をインストール
   pip install -r requirements.txt
   または最低限:
   pip install duckdb openai defusedxml

3. 環境変数を設定（.env または環境に直接）
   .env に上記キーを記載

4. データディレクトリ作成（必要なら）
   mkdir -p data

5. 監査ログ用 DuckDB 初期化（任意）
   Python REPL で:
   >>> import duckdb
   >>> from kabusys.data.audit import init_audit_db
   >>> conn = init_audit_db("data/audit.duckdb")
   >>> conn.execute("SELECT name FROM sqlite_master")  # DuckDB では不要だが接続確認

   または、既存の DuckDB 接続へスキーマだけ追加:
   >>> conn = duckdb.connect("data/kabusys.duckdb")
   >>> from kabusys.data.audit import init_audit_schema
   >>> init_audit_schema(conn, transactional=True)

---

## 使い方（主要な例）

- DuckDB 接続を用意する:
  Python から:
  >>> import duckdb
  >>> conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行（run_daily_etl）:
  >>> from kabusys.data.pipeline import run_daily_etl
  >>> from datetime import date
  >>> res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  >>> print(res.to_dict())

  run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックを順に実行し、ETLResult を返します。

- ニュースセンチメントのスコアリング（AI）:
  >>> from kabusys.ai.news_nlp import score_news
  >>> from datetime import date
  >>> n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使う場合 api_key=None
  >>> print(f"scored {n} codes")

- 市場レジーム判定:
  >>> from kabusys.ai.regime_detector import score_regime
  >>> from datetime import date
  >>> score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用

- ファクター計算（研究用）:
  >>> from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  >>> from datetime import date
  >>> mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  >>> vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  >>> val = calc_value(conn, target_date=date(2026, 3, 20))

- Zスコア正規化ユーティリティ:
  >>> from kabusys.data.stats import zscore_normalize
  >>> normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])

- ニュース収集（RSS）:
  >>> from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  >>> articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  >>> len(articles)

注意: AI 関連関数（score_news, score_regime）は OPENAI_API_KEY を参照するか api_key 引数でキーを与えます。API 呼出しはリトライやフォールバック（失敗時 0.0 を返すなど）を持ちますが、実行には料金が発生します。

---

## 実運用上の注意（設計思想・安全対策）
- Look-ahead バイアス防止: 多くの関数は内部で date.today() / datetime.now() を参照せず、target_date を明示的に受け取ります。ETL・研究コードはターゲット日を外部から与えて確定性を保ちます。
- 冪等性: DB 保存は可能な限り ON CONFLICT / DELETE→INSERT などで冪等化しています。
- リトライ/バックオフ: J-Quants / OpenAI 等の外部 API 呼び出しはリトライと指数バックオフを備えています。
- セキュリティ: RSS 取得は SSRF を避けるための検査・リダイレクト検証・プライベートアドレス拒否、XML の defusedxml 使用、レスポンスサイズ制限などを実装しています。
- ログ: 各モジュールは logger を使用。LOG_LEVEL 環境変数で設定。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記以外に strategy / execution / monitoring 等のパッケージが __all__ に想定されていますが、実装は該当ファイルに依存します）

---

## よくある操作（短いリファレンス）

- DuckDB 接続の作成:
  >>> import duckdb
  >>> conn = duckdb.connect("data/kabusys.duckdb")

- 監査 DB 初期化:
  >>> from kabusys.data.audit import init_audit_db
  >>> conn = init_audit_db("data/audit.duckdb")

- ETL を定期実行（cron / systemd タイマー等）:
  - スクリプトを作り run_daily_etl を呼ぶ。環境変数とデータパスの権限に注意。

---

## ライセンス / コントリビューション
この README はコードベースの説明を目的としたもので、実際の運用や配布に際しては LICENSE や CONTRIBUTING の指示に従ってください。

---

不明点や README に追加したい内容（実行スクリプト例、より詳しい .env.example、CI 設定例など）があれば教えてください。必要に応じてサンプルスクリプトやコマンドを追加します。