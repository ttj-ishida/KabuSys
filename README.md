# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるニュースセンチメント解析、マーケットレジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（発注→約定トレーサビリティ）などのユーティリティを提供します。

---

## 概要

KabuSys は以下の役割を持つモジュール群を備えたパッケージです。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダーを取得して DuckDB に保存）
- ニュース収集（RSS）と前処理
- LLM（OpenAI）を用いたニュースセンチメント算出（銘柄別 / マクロ）
- 市場レジーム判定（ETF とマクロセンチメントの合成）
- 研究用のファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマの初期化・管理（signal → order_request → execution のトレーサビリティ）

設計上の重要点:
- ルックアヘッドバイアス防止のため、内部処理は date / target_date を明示的に受け取り、datetime.today() に依存しない実装が多用されています。
- 多くの DB 操作は冪等（ON CONFLICT / DELETE→INSERT 等）を意識して実装されています。
- ネットワーク/API 呼び出しはリトライ・バックオフ・レート制御を備えた堅牢な実装です。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：fetch / save 機能（ページネーション、トークン自動リフレッシュ、レートリミット）
- ニュース収集
  - RSS フィード取得・前処理・raw_news への保存（kabusys.data.news_collector）
  - URL 正規化・SSRF 対策・gzip/サイズチェック 等を実装
- ニュースNLP / LLM
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ（kabusys.ai.news_nlp）
  - score_regime: マクロセンチメントと ETF (1321) の MA200 乖離を合成して market_regime に書き込み（kabusys.ai.regime_detector）
- 研究（research）
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- データ品質（quality）
  - 欠損・スパイク・重複・日付不整合チェック（kabusys.data.quality）
- 監査ログ（audit）
  - 監査用スキーマ作成（signal_events, order_requests, executions）と初期化ユーティリティ（kabusys.data.audit）

---

## セットアップ手順

以下は最小限の例です。実際のプロジェクト環境に合わせて調整してください。

1. Python 仮想環境を作成・有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布に pyproject.toml / requirements.txt があればそれに従ってください）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config で読み込み）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（少なくともこれらを設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

オプション/デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込み無効化（1 を設定）

例 .env（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単な例）

以下はライブラリ関数の利用例です。実行前に必要な環境変数・DB ファイル等を用意してください。

- DuckDB 接続を作る（例）
  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL を実行する（全データ取得・品質チェック）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))

- ニュースセンチメント（OpenAI API キーは環境変数 OPENAI_API_KEY に設定）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026, 3, 20))

- 市場レジーム判定（OpenAI API キーを引数指定も可能）
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY が使われる

- 監査ログ用 DB 初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # または既存の conn に対してスキーマ作成:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 研究用ファクター計算
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  mom = calc_momentum(conn, date(2026, 3, 20))

注意点:
- 多くの関数は target_date を明示的に受け取り、内部で現在時刻を参照しないよう設計されています（バックテストでの look-ahead バイアスを防止）。
- OpenAI 呼び出しはネットワークエラー等にフォールバックを組んでおり、失敗時はゼロやスキップで継続する実装になっています（例外が上がる場合もありますのでログを確認してください）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースは `src/kabusys` 配下にあります。以下は主要モジュールの概観です。

- src/kabusys/
  - __init__.py (パッケージ定義, __version__)
  - config.py (環境変数/設定の読み込み・検証)
  - ai/
    - __init__.py
    - news_nlp.py (銘柄別ニュースセンチメント -> ai_scores)
    - regime_detector.py (ETF MA200 とマクロセンチメントの合成 -> market_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント: fetch/save の実装)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 取得・前処理・raw_news 保存)
    - calendar_management.py (市場カレンダー管理、営業日判定)
    - stats.py (zscore_normalize 等の統計ユーティリティ)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility 等)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - ai/
    - （上記と同様）

各モジュールは docstring と設計方針を詳細に含んでおり、関数単位での使い方はソースの docstring を参照してください。

---

## 開発・デバッグのヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行われます。CI やテストで環境を明示的にコントロールしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続を使ったユニットテストではインメモリ DB (`":memory:"`) を使うと便利です。
- OpenAI API / J-Quants API 呼び出しはモジュール内で `_call_openai_api` / `_request` などを経由しているため、ユニットテストではパッチして疑似レスポンスを返すことができます（ソース内のコメントにモック箇所のヒントあり）。
- 大きなデータ操作（ETL / bulk insert）ではトランザクション管理や executemany の扱いに注意してください（コード内に DuckDB のバージョン固有の注意書きがあります）。

---

## ライセンス・貢献

（この README にライセンスや貢献方法を追記してください。プロジェクトポリシーに従って適切に記載してください）

---

README の内容はソースコードの docstring と実装を元に作成しています。実際の運用に入れる前に、環境変数・API トークン・DB 設定・Slack などの接続先情報を正しく準備し、テスト環境で十分に動作検証を行ってください。