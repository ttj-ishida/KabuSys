KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants からのデータ取得・差分 ETL、ニュース収集と LLM によるニュースセンチメント評価、マーケットレジーム判定、ファクター計算・探索、データ品質チェック、監査ログ（トレーサビリティ）など、トレーディングシステム構築に必要な基盤機能群を提供します。設計上、バックテスト時のルックアヘッドバイアスを避ける取り回しや、API のレート制御・リトライ、冪等保存（ON CONFLICT）など堅牢性を重視しています。

主な特徴
--------
- J-Quants API クライアント（差分取得・ページネーション・トークン自動更新・レート制御）
- ETL パイプライン（run_daily_etl によるカレンダー・価格・財務の差分取得および品質チェック）
- ニュース収集（RSS → raw_news、前処理、SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント評価、AI スコアの ai_scores テーブル保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索（forward returns, IC, summary）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 監査ログスキーマと DB 初期化ユーティリティ（signal / order_request / execution のトレーサビリティ）
- DuckDB を主な内部 DB に使用（軽量でパフォーマンスの良い分析向けDB）

セットアップ
-----------
※ Python 3.10+ を想定（X | Y 型などの構文を使用しています）。

1. 仮想環境作成（任意）
   - macOS / Linux
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell)
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. pip の更新と依存パッケージのインストール（最低限）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. パッケージを開発モードでインストール（リポジトリルートで）
   - pip install -e .

環境変数 / .env
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます（自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知統合）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネルID
- OPENAI_API_KEY        : OpenAI（LLM）呼び出しに使用（score_news / score_regime など）

任意/デフォルト環境変数:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — デフォルト "data/monitoring.db"
- PID_FILE_PATH — デフォルト "data/execution.pid"
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値

例 (.env)
----------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

基本的な使い方
--------------

- DuckDB 接続を作って日次 ETL を実行する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント（銘柄別）を計算して ai_scores に書き込む
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"wrote {n_written} scores")

  - 注意: OPENAI_API_KEY が必要（score_news の api_key 引数で明示も可）。失敗した場合は安全にスキップする設計です。

- 市場レジーム判定（regime）を実行する
  - 例:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB を初期化する
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って order/signal/execution の CRUD を行う

- RSS を取得する（ニュース収集の一部）
  - 例:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    # 返り値は NewsArticle 型のリスト。raw_news テーブルへ保存する処理はアプリ側で行ってください。

テスト・開発のヒント
-------------------
- 自動で .env を読み込む機能は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（ユニットテストで環境制御する際に便利）。
- OpenAI 呼び出しは内部で _call_openai_api を使用しており、テスト時は unittest.mock.patch で差し替え可能です（kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api）。
- DuckDB に対する executemany の空パラメータなど一部バージョン依存の振る舞いに配慮した実装がなされています。DuckDB のバージョンによっては挙動が異なる場合があるため、CI で環境を固定してください。

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                      - 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   - ニュースセンチメント（銘柄別）処理
  - regime_detector.py            - 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py             - J-Quants API クライアント（取得/保存関数）
  - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
  - etl.py                        - ETL 結果型の公開 (ETLResult)
  - calendar_management.py        - マーケットカレンダー管理（営業日判定等）
  - news_collector.py             - RSS ニュース収集・前処理
  - quality.py                    - データ品質チェック
  - stats.py                      - 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      - 監査ログ（スキーマ初期化 / DB 作成）
- research/
  - __init__.py
  - factor_research.py            - ファクター計算（momentum/volatility/value）
  - feature_exploration.py        - 将来リターン・IC・サマリ等
- ai、data、research 以下にさらに細かい関数群があります（README 内の「使い方」参照）。

設計上の注意点
--------------
- ルックアヘッドバイアス防止: 多くのモジュールは date.today() を直接使わない、対象日以前のデータのみ参照する等の配慮がされています。バックテストで使用する際は「どの時点でそのデータが得られたか（fetched_at）」にも注意してください。
- 冪等性: ETL / save_* 関数は ON CONFLICT を用いて冪等に保存します。
- API 呼び出し: J-Quants と OpenAI 呼び出しはリトライやレート制御を備えていますが、それでも API キーやレート制限に注意してください。

貢献 / 改良
------------
バグ修正や機能追加、ドキュメント改善は歓迎します。Pull Request の前に簡単な説明とユニットテスト（可能なら）を添えてください。

ライセンス
---------
（ここにプロジェクトのライセンスを記載してください。README に明記されていない場合はリポジトリ管理者に問い合わせてください。）

以上。README に不足している利用ケースや具体的なコード例などがあれば、どの部分を詳細化したいか教えてください。