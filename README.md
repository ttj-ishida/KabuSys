KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ / シグナル生成 / 監査ログ機能を備えたライブラリ群です。
主に以下を目的としています。

- J-Quants API からの株価・財務・マーケットカレンダー等の ETL
- ニュース収集・NLU による銘柄別センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA + マクロニュースの LLM 評価）
- ファクター計算・特徴量探索（リサーチ用途）
- データ品質チェックと監査ログ（監査テーブル／監査 DB 初期化）
- DuckDB を中心としたローカルデータ管理

主な機能
--------
- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）：取得・保存・ページネーション・リトライ・レート制御
- ニュース収集
  - RSS 収集・前処理・raw_news 保存（kabusys.data.news_collector）
  - URL 正規化 / SSRF 対策 / gzip サイズ制限 等の堅牢化
- ニュース NLP（OpenAI）
  - 銘柄別ニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ（ファクター計算）
  - momentum / value / volatility 等のファクター（kabusys.research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（kabusys.data.audit）

前提（推奨）
------------
- Python 3.10+（ソースで | 型ヒントを使用）
- 必要なライブラリ（少なくとも以下）
  - duckdb
  - openai
  - defusedxml

セットアップ手順
----------------
1. リポジトリをクローンしてパッケージをインストール（開発環境想定）

   - 開発インストール（ソースのトップに pyproject / setup がある想定）
     - pip install -e .

2. 必要パッケージのインストール（個別に）
   - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動でロードされます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID: Slack 通知用チャンネル ID
- OPENAI_API_KEY: OpenAI を使う関数（news_nlp/regime_detector）を呼ぶ場合に必要
- （任意）KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- （任意）LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- データベースパス（デフォルト値）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

使い方（簡単な例）
-----------------

1) DuckDB 接続を作って日次 ETL を実行する

    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の順で実行し ETLResult を返します。

2) ニュース NLP（AI）で銘柄別スコアを付ける

    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # 環境変数 OPENAI_API_KEY を設定しておくか、api_key 引数で渡す
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {n_written}")

3) 市場レジーム判定を実行する

    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB の初期化（監査用 DuckDB を別ファイルで作る場合）

    from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # これで signal_events, order_requests, executions 等が作成されます

5) ファクター / リサーチ関数の利用例

    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026,3,20))
    # records は各銘柄ごとの辞書リスト

設定（.env の自動ロード挙動）
---------------------------
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を自動検出して .env を読み込みます。
- 読み込み順:
  1. OS 環境変数（既存）
  2. .env（プロジェクトルート）
  3. .env.local（上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト時に便利）。

主な API と挙動のポイント
------------------------
- ETL は差分更新が基本。最終取得日から未取得分のみを取得・保存します（バックフィルオプションあり）。
- jquants_client:
  - レート制御（120 req/min）とリトライ（429/408/5xx等）実装。
  - 401 時に refresh token による自動再取得を行う（1 回）。
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実行。
- news_collector:
  - RSS 取得は SSRF やサイズ制限、gzip 解凍の堅牢化を施しています。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を使用して冪等性を確保。
- AI モジュール（news_nlp / regime_detector）:
  - OpenAI（gpt-4o-mini）を利用し JSON mode で厳密な JSON を期待します。
  - API エラーやパース失敗時はフェイルセーフ（基本的にスコア 0.0 やスキップ）で処理を継続します。
  - テストしやすいように OpenAI 呼び出し部分を差し替え可能な設計。

ディレクトリ構成（主要ファイル）
-----------------------------
（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — 銘柄別ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント + 保存
    - news_collector.py       — RSS ニュース収集
    - calendar_management.py  — 市場カレンダー管理・営業日判定
    - quality.py              — データ品質チェック
    - stats.py                — z-score 等の統計ユーティリティ
    - audit.py                — 監査ログ DDL / 初期化
    - etl.py                  — ETLResult の公開エントリ
  - research/
    - __init__.py
    - factor_research.py      — モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py  — 将来リターン・IC・統計サマリー

注意事項 / 開発上のヒント
------------------------
- Look-ahead bias を避ける設計上、ほとんどの関数は内部で date.today() 等に依存せず、必ず target_date を外部から渡す設計になっています（テストやバックテストで重要）。
- DuckDB の executemany に空リストを渡せないバージョンの互換性対策があるため、空チェックが入っています。
- OpenAI API 呼び出し部分はテストのためモックしやすいように分離されています（ユニットテストでは差し替えてください）。
- データベースや API トークンは厳重に管理し、外部に漏洩しないようにしてください。

ライセンス / 貢献
-----------------
本 README はコードベースに基づく簡易ドキュメントです。実際のプロジェクトでのライセンス表記・貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING を参照してください。

お問い合わせ
------------
実装や利用に関する質問があれば、リポジトリの issue や開発チームの連絡チャネルをご利用ください。