# KabuSys

日本株向けの自動売買 / データパイプラインライブラリ。  
J-Quants からのデータ取得、DuckDB ベースの ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に格納する ETL パイプライン
- RSS ニュース収集と OpenAI を使ったニュースセンチメントスコアリング（銘柄別 ai_score）
- 市場レジーム（bull / neutral / bear）判定（ETF の MA とマクロニュースの LLM スコアを合成）
- 研究（ファクター計算・将来リターン・IC 計算・統計ユーティリティ）
- 監査ログ（signal → order_request → execution のトレーサビリティ）向けのスキーマ初期化・ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計方針として、Look-ahead ビアス防止、冪等性、外部 API の堅牢なリトライ、DuckDB を中心としたローカルデータ運用を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
  - J-Quants API クライアント（レートリミット・トークン自動リフレッシュ・リトライ）
- データ品質
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- ニュース処理
  - RSS 取得（SSRF 対策・トラッキングパラメータ除去）
  - news_nlp.score_news：銘柄別ニュースセンチメントを ai_scores テーブルへ格納（OpenAI）
- レジーム判定
  - ai.regime_detector.score_regime：ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を更新
- 研究用ユーティリティ
  - factor_research (momentum/value/volatility)
  - feature_exploration (forward returns, IC, factor summary)
  - data.stats.zscore_normalize
- 監査ログ
  - init_audit_schema / init_audit_db：監査テーブル（signal_events / order_requests / executions）を作成
- 設定管理
  - kabusys.config.settings：.env や環境変数から主要設定を取得（自動 .env ロード機能あり）

---

## 要件

- Python 3.10+
- 必須パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- その他（標準ライブラリでまかなえる箇所あり）

※ 実行環境に応じて追加パッケージが必要となる場合があります。setup.py/pyproject.toml があればそれを参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置

   git clone / unpack 等でリポジトリを取得し、プロジェクトルートに移動します（.git または pyproject.toml により自動 .env ロードが有効になります）。

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（例）

   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）

4. 環境変数を設定

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - OPENAI_API_KEY        : OpenAI を使う処理（news_nlp / regime_detector）で必要

   DB パス（任意、デフォルトあり）:
   - DUCKDB_PATH : DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

   .env をプロジェクトルートに置くと自動的に読み込まれます（読み込み優先順: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. サンプル .env（プロジェクトルート）

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（代表的な実行例）

以下は Python REPL やスクリプトから利用する例です。README では CLI は定義していないため、Python から関数を呼び出します。

- DuckDB 接続の作成（デフォルトパスを settings から取得）

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

  run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行し、ETLResult を返します。

- ニュースのセンチメントスコアを計算して ai_scores に書き込む

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", written)

  OpenAI API キーが環境変数 OPENAI_API_KEY に設定されていることを確認してください。api_key 引数で直接渡すことも可能です。

- 市場レジームを判定して market_regime に書き込む

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

  内部で ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成してテーブルに冪等書き込みします。

- 監査ログ用 DB を初期化する

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings
  conn_audit = init_audit_db(settings.duckdb_path)  # または別 DB path

  init_audit_db は監査テーブルとインデックスを作成します（UTC タイムスタンプ設定含む）。

- データ品質チェックを個別実行する

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

---

## 自動 .env ロードについて

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、.env/.env.local を自動で読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要なディレクトリ構成

（src/kabusys 配下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI による銘柄別スコアリング（score_news）
    - regime_detector.py
      - ETF MA とマクロニュースを合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数、認証、レート制御）
    - pipeline.py
      - ETL パイプラインと run_daily_etl 等のエントリ
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダーの判定・更新・ユーティリティ（is_trading_day 等）
    - news_collector.py
      - RSS 収集と前処理（SSRF 対策含む）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック
    - audit.py
      - 監査ログスキーマ初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value の計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー、rank 等

---

## 開発上の注意点 / 設計上のポイント

- Look-ahead bias を防ぐため、各モジュールは内部で date.today() を安易に参照しない設計になっています。関数呼び出し側が明示的に target_date を渡すことを想定しています。
- DuckDB を中心に冪等性（ON CONFLICT）を保ちながらデータを保存します。ETL は差分更新／バックフィルを行います。
- OpenAI 呼び出しにはリトライとフェイルセーフ（API エラー時はスコアを 0 にフォールバック、例外をあげず処理継続）を実装しています。
- ニュース収集では SSRF 対策、レスポンスサイズ上限、XML パースの安全化（defusedxml）を行っています。

---

## よくある運用フロー（例）

1. 毎朝（夜間バッチ）に run_daily_etl を実行してデータを更新
2. ETL 後に news_nlp.score_news を呼んで当日分のニューススコアを生成
3. research モジュールでファクター計算→ランキング→シグナル生成
4. 生成シグナルを戦略層で監査ログへ記録（signal_events）し、発注ログ（order_requests）経由で執行
5. ブローカーからの約定は executions に記録してトレーサビリティを保持

---

## サポート / 貢献

本 README はコードベースから自動的に要点を抜粋して記述しています。実行時の詳細な設定や追加依存はプロジェクトの pyproject.toml / requirements.txt を参照してください。バグ報告や改善提案は issue を立ててください。

---

以上。必要があれば README にサンプルスクリプトや更に詳しい API 使用例（関数別の引数説明サンプル）を追加します。どの情報を優先して追記しますか？