KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータ収集・ETL・品質チェック、ニュース NLP（LLM）による銘柄センチメント評価、マーケットレジーム判定、ファクター計算、監査ログ管理までをカバーする内部ライブラリ群です。DuckDB をデータプラットフォームに用い、J-Quants API / OpenAI（gpt-4o-mini 等）を外部データ・解析に利用します。ライブラリ設計は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を重視しています。

主な機能一覧
-------------
- データ ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（ページネーション対応、レート制御、トークンの自動リフレッシュ）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付整合性チェック（kabusys.data.quality）
- ニュース収集・前処理
  - RSS 取得（SSRF 対策、XML 防御）、前処理、raw_news への冪等保存（kabusys.data.news_collector）
- ニュース NLP（LLM ベース）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメントを算出 → ai_scores に保存（kabusys.ai.news_nlp）
  - 日次のマーケットレジーム判定（ETF 1321 の ma200 とマクロニュースの LLM センチメントを合成）（kabusys.ai.regime_detector）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー系ファクターの計算（kabusys.research.factor_research）
  - 将来リターン計算、IC、統計サマリ（kabusys.research.feature_exploration）
  - Z スコア正規化等の統計ユーティリティ（kabusys.data.stats）
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution を追跡する監査スキーマの初期化 / DB 用ユーティリティ（kabusys.data.audit）
- 設定管理
  - .env 自動読み込み（プロジェクトルートの検出）と Settings オブジェクト（kabusys.config）

セットアップ手順
----------------
以下はローカル開発用の最小セットアップ例です。

1. Python 環境（推奨: 3.10+）を用意して仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 必要パッケージをインストールします（プロジェクトに requirements.txt が無い場合は最低限これら）。
   - pip install duckdb openai defusedxml

   （実装は標準ライブラリ urllib を使用しているため requests は必須ではありませんが、追加ツールが必要なら別途追加してください。）

3. パッケージを開発モードでインストール（オプション）。
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定すると自動読み込みを無効化できます）。
   - 必須：
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用、settings.jquants_refresh_token が参照）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（settings.kabu_api_password が参照）
   - あると便利／任意：
     - OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime の api_key 引数を省略した場合に参照）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知などで使用する場合
     - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
     - SQLITE_PATH （モニタリング DB のデフォルト data/monitoring.db）
     - KABU_API_BASE_URL （デフォルト http://localhost:18080/kabusapi）
     - KABUSYS_ENV （development / paper_trading / live、デフォルト development）
     - LOG_LEVEL （DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）
     - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（CPU/MEM/DISK）

   例 .env（最低限の例）
   - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   - OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   - KABU_API_PASSWORD=secret
   - DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な API と簡単なコード例）
------------------------------------

準備: DuckDB 接続を作成
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))  # settings は kabusys.config.settings

1) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

2) ニュースのセンチメントスコア（LLM を使って ai_scores テーブルに書き込む）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n = score_news(conn, target_date=date(2026, 3, 20))  # api_key を渡さない場合は OPENAI_API_KEY 環境変数を参照
- print(f"書込み件数: {n}")

3) マーケットレジーム判定（日次）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- r = score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success

4) ファクター計算 / リサーチ
- from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
- from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
- mom = calc_momentum(conn, date(2026,3,20))
- vol = calc_volatility(conn, date(2026,3,20))
- val = calc_value(conn, date(2026,3,20))
- fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])

5) 監査 DB スキーマ初期化（order/exec の監査テーブル）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

設定 (kabusys.config)
---------------------
設定は kabusys.config.Settings 経由で取得できます（settings オブジェクトを透過的に利用）。
自動で .env / .env.local をプロジェクトルートから読み込み（OS 環境変数 > .env.local > .env の順）。自動読み込みを止めるには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（コード内デフォルトを含む）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (ai 関数で使用、引数で上書き可)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (デフォルト: 0)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live。デフォルト development)
- LOG_LEVEL (DEBUG/INFO/...、デフォルト INFO)

ディレクトリ構成（主要ファイル）
----------------------------
以下はこのリポジトリに含まれる主要なモジュールとファイル（抜粋）です。実際のファイル群に合わせて参照してください。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save 関数）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult 再エクスポート
    - news_collector.py        — RSS 収集、前処理
    - quality.py               — データ品質チェック
    - calendar_management.py   — 市場カレンダー管理
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・summary
  - ai/、data/、research/ 以下にさらにサブ機能が含まれます。

設計上の注意点 / 運用上の注意
----------------------------
- 外部 API（J-Quants / OpenAI）を使う機能は API キーやトークンが必要です。ローカルで試す際はダミーデータやモックを使うことを推奨します。
- LLM をコールする箇所はリトライ／フェイルセーフを実装していますが、API 使用コストやレート制限に注意してください。
- ETL は差分更新・バックフィル設計になっているため、本番的に運用する場合は定期ジョブ（cron や Airflow 等）から日次で実行するのが想定です。
- DuckDB の executemany の仕様（空リスト不可など）に注意した実装になっています。
- audit.init_audit_schema は transactional 引数により BEGIN/COMMIT を制御します（DuckDB のトランザクション特性に留意）。

トラブルシューティング
----------------------
- .env が読み込まれない場合:
  - プロジェクトルートの検出ロジックは .git または pyproject.toml を探します。パッケージ配布後やテスト環境ではカレントディレクトリが異なる場合があるため、必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自分で環境変数をセットしてください。
- OpenAI / J-Quants の認証エラーやネットワークエラー:
  - ログ（設定した LOG_LEVEL）を上げて詳細を確認してください。J-Quants クライアントは 401 時にトークンを自動更新する仕組みがあります。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献ガイドラインを記載してください。README 等に合わせて追記を推奨します。）

付記
----
この README はコードベースの重要な機能を要約したものです。個々の関数やモジュールは docstring に詳細な設計／動作仕様が書かれていますので、実装・拡張・テスト時にはそちらを参照してください。必要があれば README に具体的な運用例や cron / systemd の設定例、docker-compose 例を追記できます。