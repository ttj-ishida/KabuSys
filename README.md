KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム＋リサーチ／自動売買のためのライブラリ群です。  
主に以下を提供します。

- J-Quants からの株価・財務・カレンダー等の ETL パイプライン（DuckDB への保存・品質チェック）
- ニュース収集（RSS）と LLM を用いたニュースセンチメントスコアリング
- マーケットレジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム／ボラティリティ／バリュー等）
- 監査ログ（signal → order → execution のトレーサビリティ）スキーマ初期化ユーティリティ
- 各種ユーティリティ（市場カレンダー管理、品質チェック、統計関数 等）

主な機能一覧
-------------
- data.jquants_client: J-Quants API とのやりとり（認証・ページネーション・保存）
- data.pipeline/run_daily_etl: 日次 ETL（カレンダー・株価・財務・品質チェック）
- data.news_collector.fetch_rss: RSS からのニュース収集（SSRF 対策・前処理）
- ai.news_nlp.score_news: OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント計算
- ai.regime_detector.score_regime: ETF（1321）の MA と LLM を合成した市場レジーム判定
- research.*: ファクター計算（momentum/value/volatility）、将来リターン・IC 計算等
- data.quality: ETL 後のデータ品質チェック（欠損・スパイク・重複・日付不整合）
- data.audit: 監査ログ向けテーブル定義・初期化（冪等・UTC タイムスタンプ）
- config.Settings: 環境変数管理（.env 自動ロード、必須変数チェック）

動作要件（目安）
----------------
- Python 3.10+
- duckdb（Python パッケージ）
- openai（OpenAI API クライアント）
- defusedxml（RSS パース用）
- （ネットワークアクセス: J-Quants API / OpenAI / RSS ソース）

セットアップ手順
----------------

1. リポジトリを取得
   - ソースが src/ にある前提でインストール可能です（開発インストール推奨）。
   - 例:
     - git clone <repo>
     - cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -e .  # package 配布設定がある場合
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の環境変数（config.Settings を参照）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants の refresh token
     - KABU_API_PASSWORD      — kabuステーション API のパスワード（発注等を使う場合）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - OpenAI API キー:
     - OPENAI_API_KEY を環境変数に設定するか、score_news/score_regime の api_key 引数で渡します。
   - 任意の設定（デフォルト値あり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - .env の記述例 (.env.example):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

使い方（簡易サンプル）
--------------------

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニューススコア（LLM）を実行する
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("scored:", n_written)
  ```
  - テストでは kabusys.ai.news_nlp._call_openai_api をモックしてレスポンスを差し替えることが推奨されています。

- マーケットレジーム判定を実行する
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB の初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等が作成される
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点 / 運用上のポイント
------------------------
- Look-ahead バイアス防止:
  - ライブラリの多くは date 引数を明示的に受け取り、内部で datetime.today() を参照しない設計です。バックテストや再現性のため target_date を明示してください。
- OpenAI 呼び出し:
  - API のリトライやエラー時フォールバック（score = 0.0 等）が入っており、フェイルセーフ設計です。
  - テスト時は _call_openai_api をパッチして呼び出しを差し替えられます。
- J-Quants API:
  - rate limit を守るため内部でスロットリングとリトライを実装しています。401 受信時は refresh token を使って自動リフレッシュします。
- RSS ニュース収集:
  - SSRF 対策（ホスト検証・リダイレクト検査）や受信サイズ上限を実装しています。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント（LLM）
  - regime_detector.py            — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント / 保存ロジック
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETL インターフェース再エクスポート
  - news_collector.py             — RSS 収集 / 前処理
  - calendar_management.py        — 市場カレンダー管理 / next/prev / update job
  - quality.py                    — 品質チェック
  - stats.py                      — 統計ユーティリティ（zscore_normalize）
  - audit.py                      — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            — Momentum/Value/Volatility 等
  - feature_exploration.py        — 将来リターン / IC / summary / rank
- research/*（その他ユーティリティ）

開発・テスト時のヒント
---------------------
- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。テストで自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI など外部 API 呼び出しはユニットテストでモックする前提の設計（各モジュール内の _call_openai_api を patch）。
- DuckDB を使ったテストは ":memory:" を使えばメモリ DB で高速に実行できます。

貢献・ライセンス
----------------
- （ここにプロジェクトの貢献フローやライセンス表記を追加してください）

以上。必要であれば、README に含める .env.example の完全なテンプレートや具体的な ETL スケジュール（cron / systemd timer 例）、運用チェックリストも作成します。どれを追加しますか？