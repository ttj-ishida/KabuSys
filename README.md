README
======

概要
----
KabuSys は日本株のデータプラットフォームとリサーチ／自動売買基盤向けのライブラリ群です。本コードベースは以下を提供します。

- J-Quants API を使った株価・財務・マーケットカレンダーの ETL（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と LLM（OpenAI）によるニュースセンチメント集約（銘柄別 ai_score）
- マーケットレジーム判定（ETF + マクロニュースの LLM スコアを合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック、監査ログ（監査用 DuckDB スキーマ）等のユーティリティ
- 環境変数管理（.env 自動読み込み / 必須値チェック）

主な機能
--------
- ETL: daily_etl（kabusys.data.pipeline.run_daily_etl）で市場カレンダー／株価／財務データを差分取得して保存、品質チェックを実行
- ニュース収集: RSS から raw_news を作成、news_symbols で銘柄紐付け
- ニュース NLP: OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア算出（kabusys.ai.news_nlp.score_news）
- レジーム検出: ETF（1321）の200日MA乖離とマクロニュース（LLM）の重み合成で市場レジームを判定（kabusys.ai.regime_detector.score_regime）
- 監査ログ: シグナル → 発注 → 約定のトレーサビリティ用テーブルを初期化（kabusys.data.audit.init_audit_db / init_audit_schema）
- データ品質チェック: 欠損、重複、スパイク、日付不整合の検出（kabusys.data.quality）
- 研究ユーティリティ: ファクター計算、IC 計算、Z スコア正規化等（kabusys.research, kabusys.data.stats）

要件
----
- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース）

インストール
------------
1. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml

3. 開発インストール（パッケージとして扱う場合）:
   - pip install -e .

環境変数 / .env
----------------
パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）から自動的に .env を読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（一例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで使用）

使い方（代表的な例）
-------------------

準備: DuckDB 接続
- DuckDB ファイルに接続して conn を作成します。
  例:
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")

ETL を実行（日次）
- 日次 ETL を実行して、カレンダー／株価／財務／品質チェックをまとめて行います。
  例:
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn, target_date=date(2026,3,20))
    print(res.to_dict())

ニューススコアリング（OpenAI を使う）
- raw_news / news_symbols が整備されている前提で、銘柄別 ai_score を生成します。
  例:
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定

マーケットレジーム判定
- ETF（1321）とマクロニュースを用いて日次レジームを判定・保存します。
  例:
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))  # api_key を引数で渡すことも可

監査ログ DB 初期化
- 監査テーブルを持つ専用 DuckDB を初期化するユーティリティがあります。
  例:
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")  # 必要に応じて ":memory:" も指定可

カレンダー更新バッチ（単体）
- JPX カレンダーを J-Quants から差分取得して market_calendar テーブルを更新します。
  例:
    from kabusys.data.calendar_management import calendar_update_job
    calendar_update_job(conn)

設定値取得（プログラム内）
- 環境変数は kabusys.config.settings を通してアクセスできます。
  例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token

注意点 / テスト用フック
----------------------
- news_nlp と regime_detector は OpenAI 呼び出し部分を内部的にラップしており、単体テストではそれらの内部関数（_call_openai_api など）を unittest.mock.patch で差し替えてテストする設計になっています。
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テスト等で便利です）。
- LLM 呼び出しや外部 API 呼び出しは失敗時にフェイルセーフ（0.0 を返す / スキップする）実装が多く、処理全体が致命的に止まらないよう設計されています。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py                      パッケージ公開（version 等）
- config.py                        環境変数 / 設定管理（.env 自動読み込み・必須チェック）
- ai/
  - __init__.py
  - news_nlp.py                     ニュースセンチメント（OpenAI 経由・バッチ処理）
  - regime_detector.py              マーケットレジーム判定ロジック（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py               J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py                     ETL パイプライン（run_daily_etl 等）
  - etl.py                          ETLResult のエクスポートラッパー
  - news_collector.py               RSS 取得 / 前処理 / raw_news 保存ロジック
  - calendar_management.py          マーケットカレンダー管理（営業日ロジック・更新ジョブ）
  - quality.py                      データ品質チェック（欠損/重複/スパイク/日付不整合）
  - stats.py                        汎用統計（Z スコア正規化等）
  - audit.py                        監査ログスキーマ初期化（signal/order/execution テーブル）
- research/
  - __init__.py
  - factor_research.py              モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py          将来リターン計算、IC、統計サマリー等

開発メモ
--------
- SQL は DuckDB を前提に作られています。ETL 実行前に必要なスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_calendar, news_symbols 等）が用意されていることを確認してください（プロジェクトの別ドキュメントにスキーマ定義がある想定です）。
- audit.init_audit_db は監査用テーブルを自動で初期化します（UTC タイムゾーンの設定を含む）。
- ログレベルは LOG_LEVEL 環境変数で制御できます。

ライセンス
---------
（ソースにライセンス表記がないため、利用時はリポジトリのライセンスを確認してください）

参考
----
- 環境変数の自動読み込みロジックや .env のパースは kabusys.config に実装されています。テストや CI で環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。
- OpenAI 呼び出しは gpt-4o-mini + JSON Mode を期待する設計になっています。API レスポンスのバリデーションは厳格に行われますが、実運用ではリクエスト制限・課金に注意してください。

お問い合わせ
------------
プロジェクト内の各モジュールにログ出力（logger）があります。動作確認やトラブルシュートはまずログを参照してください。README に不明点があれば、ソースの docstring（各モジュールの冒頭コメント）が詳細な動作仕様を記載しています。