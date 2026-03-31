KabuSys — 日本株向けデータプラットフォーム＆自動売買リサーチツールキット
================================================================================

概要
----
KabuSys は日本株向けのデータ収集（ETL）・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ構築などを目的とした内部ライブラリ群です。DuckDB を主要なストレージに用い、J-Quants API や RSS、OpenAI（LLM）を利用してデータ取得・解析を行います。バックテストや自動売買基盤のデータ基盤・研究モジュールとして設計されています。

主な特徴（機能一覧）
-------------------
- データ取得（J-Quants API）
  - 株価日足（OHLCV）, 財務（四半期）データ, 上場銘柄一覧, JPX マーケットカレンダー
  - レート制限対応・トークン自動リフレッシュ・リトライロジック搭載
- ETL パイプライン
  - 差分更新・バックフィル・品質チェックを含む日次 ETL run_daily_etl
- データ品質チェック
  - 欠損・スパイク（急騰・急落）・重複・日付整合性チェック
- ニュース収集・NLP（OpenAI）
  - RSS フィード収集（SSRF 対策、トラッキング除去）、raw_news 保存
  - 記事群を銘柄別にまとめて OpenAI（gpt-4o-mini）でセンチメントスコアを算出（score_news）
- 市場レジーム判定
  - ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算、Forward returns、IC 計算、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの作成・初期化（init_audit_db / init_audit_schema）
- 高い設計方針
  - ルックアヘッドバイアスへの配慮、冪等性（INSERT ... ON CONFLICT）、フェイルセーフな設計

セットアップ手順
----------------

前提
- Python 3.10+（コードは型注釈で new union 等を使用）
- DuckDB を利用（pip パッケージ）
- OpenAI SDK（LLM を使う場合）
- defusedxml（RSS 解析時）

インストール（開発環境）
1. リポジトリルートに移動（src 配下がパッケージ）
2. 仮想環境作成・有効化（推奨）
3. インストール例:
   - pip install -e . もしくは
   - pip install duckdb openai defusedxml

必要な主要ライブラリ（例）
- duckdb
- openai
- defusedxml

環境変数 / .env
- プロジェクトはプロジェクトルート（.git または pyproject.toml）を探索して自動で .env/.env.local を読み込みます（優先順位: OS env > .env.local > .env）。
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（または主要）環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API Key（score_news / score_regime で必要）
- KABU_API_PASSWORD : kabu API パスワード（場外での発注等に使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知に使用
- DUCKDB_PATH : デフォルト "data/kabusys.duckdb"（settings.duckdb_path）
- SQLITE_PATH : デフォルト "data/monitoring.db"
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例: .env（参考）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C12345...
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=DEBUG

使い方（コード例）
-----------------

基本的な DuckDB 接続例
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
    from kabusys.data.pipeline import run_daily_etl

    result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
    print(result.to_dict())

ニューススコアリング（OpenAI を利用）
    from kabusys.ai.news_nlp import score_news
    from datetime import date

    # target_date はスコアを作成する「日付」 (ニュースウィンドウは前日15:00JST〜当日08:30JST)
    n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

市場レジーム判定（MA とマクロニュースの合成）
    from kabusys.ai.regime_detector import score_regime
    from datetime import date

    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

監査ログスキーマ初期化（監査用 DB 作成）
    from kabusys.data.audit import init_audit_db

    audit_conn = init_audit_db("data/audit.duckdb")
    # またはインメモリ:
    # audit_conn = init_audit_db(":memory:")

ファクター計算（研究）
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    from datetime import date

    momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
    volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
    value = calc_value(conn, target_date=date(2026, 3, 20))

その他ユーティリティ
- zscore_normalize: kabusys.data.stats.zscore_normalize
- calc_forward_returns, calc_ic, factor_summary, rank: kabusys.research.feature_exploration

注意点（運用・トラブルシュート）
- OpenAI 呼び出しはモデル gpt-4o-mini を想定（JSON mode を利用）。API レートや応答フォーマットに注意してください。API エラー時はフェイルセーフでスコア0.0にフォールバックする実装が多く取り入れられています。
- J-Quants API はレート制限（120 req/min）に対応するため内部でスロットリングしています。大量取得時は処理時間に注意。
- DuckDB executemany に空リストを渡すと問題になるバージョンがあるため、ETL は空パラメータチェックを行っています。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索するため、ソース配布後やテスト時に挙動が変わる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてください。
- 監査スキーマ初期化時に transactional=True を指定すると BEGIN/COMMIT で実行されますが、DuckDB はネストトランザクションをサポートしていないため、既にトランザクション中の接続での呼び出しは注意が必要です。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースNLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント / 保存関数
    - pipeline.py                   — ETL パイプライン / run_daily_etl
    - etl.py                        — ETL の公開インターフェース（ETLResult）
    - news_collector.py             — RSS ニュース収集
    - calendar_management.py        — 市場カレンダー管理
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ
    - audit.py                      — 監査ログ（schema 初期化）
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 計算
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - ai/ (上記)
  - research/ (上記)

開発メモ / 設計上のポイント
----------------------------
- ルックアヘッドバイアス対策を意識して設計（各所で target_date の未満/以前のデータのみを参照）。
- 冪等性: ETL と保存処理は ON CONFLICT DO UPDATE を基本としており、再実行可能。
- フェイルセーフ: LLM や外部 API の障害はスコアのデフォルト化やログ出力で上位処理に影響を与えないようにしている。
- テスト容易性: OpenAI 呼び出しや RSS のネットワーク部分は差し替え（mock）しやすい設計。

ライセンス・貢献
----------------
（ここにはプロジェクトのライセンスや貢献ガイドラインを追記してください）

以上。導入時の具体的な実行やカスタマイズ（Slack 通知連携、発注ロジック、バックテスト統合など）が必要であれば、用途に合わせた利用例やサンプルコードを追って提供できます。