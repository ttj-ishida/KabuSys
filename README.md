KabuSys — 日本株自動売買基盤 (README)
==================================

概要
----
KabuSys は日本株向けのデータプラットフォーム / リサーチ / 自動売買基盤のコアライブラリです。
主に以下を提供します。

- J-Quants API を使ったデータ取得（株価日足、財務、JPX カレンダー）
- DuckDB を用いた ETL・品質チェック・監査ログの保存処理
- ニュースを LLM（OpenAI）で解析して銘柄ごとのセンチメントを算出
- ETF とニュースを組み合わせた市場レジーム判定
- 研究用ファクター計算・特徴量解析ユーティリティ

特徴
----
主な機能一覧（抜粋）:

- data/jquants_client
  - J-Quants から株価・財務・カレンダーを取得し DuckDB に冪等保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- data/pipeline, data/etl
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - ETLResult による実行結果の集約
- data/news_collector
  - RSS フィードからニュースを収集し raw_news に保存（SSRF 対策・トラッキングパラメータ除去）
- ai/news_nlp, ai/regime_detector
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（銘柄ごと、ウィンドウ指定）
  - ETF（1321）の MA200 乖離とニュースセンチメントを組み合わせた市場レジーム判定
  - API 呼び出しは堅牢なリトライ / フェイルセーフ実装
- data/quality, data/stats
  - 欠損、重複、スパイク、日付不整合などの品質チェック
  - ファクターの Z スコア正規化等の統計ユーティリティ
- data/audit
  - シグナル→発注→約定までトレーサビリティを保証する監査テーブルの初期化ユーティリティ

要件
----
- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセス）J-Quants API、OpenAI API（利用する機能に応じて）

セットアップ手順
----------------

1) 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt や pyproject.toml がある場合はそちらを利用してください。
   開発時は pip install -e . を使ってローカルインストールできます。）

3) 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます。
   - 自動読み込みを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL で使用）
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等の監視関連
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル（DEBUG, INFO, …）

例 .env（最小）
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxx
    DUCKDB_PATH=data/kabusys.duckdb
    KABU_API_PASSWORD=your_kabu_password
    KABUSYS_ENV=development

使い方（主要な例）
-----------------

以下は Python REPL やスクリプト内で利用する際の例です。

1) DuckDB 接続を作り日次 ETL を実行
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

2) ニュースセンチメントを算出して ai_scores に保存
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print(f"wrote {written} scores")

   - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
   - 処理は前日 15:00 JST ～ 当日 08:30 JST の記事を対象に集約して評価します。

3) 市場レジーム判定
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

   - ETF 1321 の 200 日 MA 乖離（70%）とニュースセンチメント（30%）を合成して
     market_regime テーブルへ保存します。

4) 監査テーブル初期化（監査 DB を独立して作成）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events, order_requests, executions テーブルが作成されます

5) カレンダー関連ユーティリティ（サンプル）
    from datetime import date
    import duckdb
    from kabusys.data.calendar_management import is_trading_day, next_trading_day

    conn = duckdb.connect("data/kabusys.duckdb")
    d = date(2026, 3, 20)
    print(is_trading_day(conn, d))
    print(next_trading_day(conn, d))

注意点 / 動作方針
-----------------
- ルックアヘッドバイアスの防止: 多くの関数は内部で date.today() や datetime.now() を直接用いず、
  呼び出し側が target_date を渡す設計です。バックテスト等では明示的に date を指定してください。
- OpenAI / J-Quants の呼び出しはリトライ・バックオフ・フェイルセーフが組み込まれていますが、
  API 利用量・料金に注意して運用してください。
- news_collector は SSRF / XML Bomb 等の攻撃対策を組み込んでいますが、外部 URL を扱うため運用時は監視を推奨します。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため一部コードは空チェックを行っています。

テストに関して
---------------
- OpenAI API 呼び出しやネットワーク依存部分はモックしやすいように内部呼び出し関数を分離しています。
  例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替えれば API を叩かずにテスト可能です。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（ユニットテストでの環境制御に便利）。

ディレクトリ構成
----------------

src/
  kabusys/
    __init__.py                -- パッケージ定義（__version__）
    config.py                  -- 環境変数 / 設定管理
    ai/
      __init__.py
      news_nlp.py              -- ニュースを元に銘柄センチメントを算出
      regime_detector.py       -- 市場レジーム判定
    data/
      __init__.py
      jquants_client.py        -- J-Quants API クライアント & DuckDB 保存関数
      pipeline.py              -- ETL パイプライン（run_daily_etl 等）
      etl.py                   -- ETLResult 再エクスポート
      news_collector.py        -- RSS ニュース収集
      calendar_management.py   -- マーケットカレンダー管理
      quality.py               -- データ品質チェック
      stats.py                 -- 統計ユーティリティ（zscore 等）
      audit.py                 -- 監査ログテーブル初期化
    research/
      __init__.py
      factor_research.py       -- モメンタム・バリュー・ボラティリティ計算
      feature_exploration.py   -- 将来リターン・IC・統計サマリ等

貢献 / 変更
-----------
- コードを修正する際は既存の設計方針（ルックアヘッド防止、冪等性、フェイルセーフ）を尊重してください。
- 外部 API を直接呼び出すユニットテストは避け、モックで代替してください。

ライセンス
---------
- 本リポジトリに付与されるライセンス情報に従ってください（ここには明記されていません）。

問い合わせ
----------
- 実装仕様や利用方法で不明点があればソース内の docstring を参照してください。各関数・モジュールに詳細なドキュメントが含まれています。

以上。README に含めたい追加情報（例: requirements.txt の正確な内容、CI 手順、デプロイ手順等）があれば教えてください。