# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータプラットフォーム、リサーチ、ニュースNLP、マーケットレジーム判定、監査ログ等を含む自動売買/リサーチ基盤のライブラリ群です。DuckDB をデータストアに使用し、J-Quants / OpenAI / kabuステーション 等の外部サービスと連携する設計になっています。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE などで上書き）
- フェイルセーフ（外部 API 失敗時は安全側のデフォルトで継続）
- テストしやすい（API 呼び出し箇所は差し替え可能）

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを取得・保存（差分更新・ページネーション対応）
  - ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などのチェック（quality モジュール）
- ニュース収集・前処理
  - RSS 取得・正規化・SSRF 対策・記事ID生成・raw_news への冪等保存支援
- ニュース NLP（OpenAI）
  - 銘柄別ニュースセンチメントスコア生成（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライ/バックオフ等の堅牢化
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等の計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）、IC 計算、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- ユーティリティ
  - Zスコア正規化、カレンダー管理（営業日判定・next/prev/get_trading_days）、J-Quants クライアント等

---

## 要件

- Python 3.10 以上（PEP 604 の型記法（|）を使用）
- 主な依存パッケージ（実プロジェクトでは requirements.txt / pyproject.toml を確認してください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで実装されている部分が多いですが、上記は必須／推奨）

---

## 環境変数（設定）

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を自動読み込みします（ルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数：
- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API のリフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID
- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)  
  有効値: development | paper_trading | live （デフォルト development）
- LOG_LEVEL (任意)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

必須の環境変数が未設定の場合は Settings のプロパティで ValueError が発生します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...（プロジェクトルートには .git または pyproject.toml が必要）

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   - 開発インストール: pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成して必要なキーを設定
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
   - .env.local があれば .env の上書きとして読み込まれます（OS 環境変数が優先、.env.local は .env より優先）

5. DuckDB 用ディレクトリの作成（必要なら）
   - mkdir -p data

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL からの呼び出し例です。

- ETL を日次実行（DuckDB 接続を渡す）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（OpenAI を使って銘柄別にスコア化）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を渡すか、OPENAI_API_KEY 環境変数を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored:", n_written)

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- ファクター計算 / リサーチ関数
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- RSS 取得（ニュース収集）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

これらはライブラリ API の一例です。各関数の docstring を参照してください。

---

## 自動 .env 読み込みの挙動

- パッケージ import 時に（kabusys.config）プロジェクトルートを基準に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` の上書き（override=True）
- 無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- ルート判定は .git または pyproject.toml を上位ディレクトリから探索して行います

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン
- config.py — 環境変数 / 設定管理（Settings クラス、自動 .env ロード）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save, 認証、レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETL 公開インターフェース
  - news_collector.py — RSS 収集・前処理・SSRF 対策
  - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
  - stats.py — Zスコア正規化などの統計ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマの初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
- ai/、data/、research/ はそれぞれのユースケースごとに細かく分割されています。

---

## 開発 / テストについての注意

- OpenAI / J-Quants の外部依存呼び出しはリトライやフェイルセーフを組んでいますが、テストでは API キーや実ネットワークに依存しないように該当関数（_call_openai_api など）を mock に差し替えてテストする設計になっています。
- DuckDB を用いているためテスト用に :memory: 接続を使うことが可能です（init_audit_db(":memory:") 等）。
- 自動 .env ロードはテスト時に副作用となる場合があるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化してください。

---

## 補足

- 各モジュールの docstring に実装の前提・設計方針・フェイルセーフ動作が詳述されています。実運用前に必ず該当箇所を読み、環境変数や API 制限、DB スキーマの要件を確認してください。
- 本 README はコードベースからの抽出に基づく概要です。実行環境ごとに追加の設定（SSL, プロキシ, OS レベルの制約など）が必要になる場合があります。

もし README の英語版、Docker / systemd 用の起動スクリプト例、CI 設定例、あるいは具体的な .env.example を生成することをご希望であれば教えてください。必要に応じて追記します。