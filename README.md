KabuSys
=======

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター算出、監査ログ、J-Quants / kabu ステーション連携など、運用バッチおよびリサーチ用途に必要な機能をモジュール化しています。

主な特徴
--------
- J-Quants API からの差分取得（株価・財務・上場情報・カレンダー）および DuckDB への冪等保存
- RSS ベースのニュース収集（SSRF・XML注入対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_score / マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）と統計ユーティリティ（Z-score 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ
- 環境変数・設定管理（.env 自動読み込み、Settings オブジェクト）

機能一覧
--------
- データ取得 / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- ニュース関連
  - RSS フェッチと正規化（kabusys.data.news_collector）
  - 銘柄別ニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
  - マクロセンチメント合成による市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究（Research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（kabusys.research.factor_research）
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）
  - 統計ユーティリティ: zscore_normalize（kabusys.data.stats）
- データ品質・カレンダー
  - 品質チェック: run_all_checks（kabusys.data.quality）
  - 市場カレンダー管理・営業日判定（kabusys.data.calendar_management）
- 監査ログ（audit）
  - init_audit_db / init_audit_schema（kabusys.data.audit）
- 設定
  - Settings（kabusys.config.settings）: 環境変数経由で各種設定を取得

セットアップ手順
----------------
前提: Python 3.10+（typing 機能の利用に合わせて推奨）。プロジェクトルートに pyproject.toml / .git がある場合、config モジュールはそこを起点に .env/.env.local を自動読み込みします（無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です。パッケージを編集可能インストールする場合:
     - pip install -e .

3. 環境変数の設定
   - プロダクトで必須となる環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI スコア算出に必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注等）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - デフォルト的な DB パス（必要に応じて上書き可）
     - DUCKDB_PATH (既定: data/kabusys.duckdb)
     - SQLITE_PATH (既定: data/monitoring.db)
   - .env / .env.local をプロジェクトルートに配置すると自動読み込みされます（ロード順: OS env > .env.local > .env）。
   - サンプル（.env.example）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

- Settings を読む
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.env, settings.duckdb_path などで取得可能

- DuckDB 接続を作って ETL を実行する（一例）
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースの AI スコアリング
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → OPENAI_API_KEY を利用

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB 初期化（監査用 DuckDB を生成）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- ファクター計算 / リサーチ
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
    momentum = calc_momentum(conn, target_date=date(2026,3,20))

注意点・運用メモ
----------------
- Look-ahead バイアス防止: 多くのモジュールは date 引数を明示的に受け取り、内部で date.today() を直接参照しないよう設計されています。バックテストや再現性のため、常に target_date を明示してください。
- OpenAI 呼び出し: API の失敗時にはフェイルセーフとして 0.0 を返す等の挙動をする設計です（ログは出力されます）。API 使用量に注意してください。
- J-Quants クライアントは 120 req/min のレート制限を守るよう実装されています。get_id_token は自動リフレッシュを行います。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行います。テスト時に自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数/設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - news_collector.py              — RSS ニュース収集
  - calendar_management.py         — 市場カレンダー管理
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - audit.py                       — 監査ログスキーマ初期化
  - etl.py                         — ETLResult の公開エントリ
- research/
  - __init__.py
  - factor_research.py             — Momentum / Volatility / Value
  - feature_exploration.py         — 将来リターン / IC / 統計要約
- (その他) strategy/, execution/, monitoring/（パッケージ __all__ に含まれるよう設計）

開発・貢献
---------
- コードベースはモジュール毎にユニットテストを追加しやすい構造になっています。外部 API 呼び出しはラッパー関数を通しており、unittest.mock による差し替えが容易です。
- PR の際は、外部 API キーは含めないでください（.env.example を用意して管理）。

免責
----
本リポジトリは教育・研究目的のサンプル実装です。実際の資金運用や自動発注を行う前に、入念なテスト・監査・法的確認を行ってください。本ソフトウェアの利用により生じたいかなる損害についても一切の責任を負いません。

以上。必要であれば README に追加したいサンプルコマンドや .env.example を作成します。どのレベルの実装例（docker / systemd / ワークフロー）を追記しますか？