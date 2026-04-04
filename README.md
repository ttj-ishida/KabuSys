KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株のデータ取得・ETL・データ品質チェック、ファクター計算、ニュースNLP（LLM を使ったセンチメント評価）、市場レジーム判定、監査ログ（シグナル→発注→約定のトレース）などを含む研究／自動売買プラットフォーム向けの Python モジュール群です。内部では DuckDB をローカルデータベースとして利用し、J-Quants API や OpenAI（gpt-4o-mini 等）を外部データ・モデルの取得に使用します。

主な機能
-------
- データ ETL（J-Quants からの株価日足・財務・カレンダー取得）
  - 差分取得・バックフィル・ページネーション・トークン自動更新・レート制御
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
- ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を使った銘柄ごとのニュースセンチメント算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 監査ログ（signal_events / order_requests / executions テーブル、スキーマ初期化）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Z スコア正規化 等）
- 汎用統計ユーティリティ（zscore_normalize 等）

前提（想定依存）
----------------
（実プロジェクトでは pyproject.toml / requirements.txt に記載しますが、主要な外部依存は下記）
- Python 3.9+
- duckdb
- openai（OpenAI v1 SDK）
- defusedxml
- （標準ライブラリ多数）

セットアップ
------------
1. リポジトリをクローン / 作業ディレクトリへ移動
   - 例: git clone ... && cd kabusys

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （実プロジェクトでは pip install -e . または poetry/poetry lock を使用）

4. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY         — OpenAI の API キー（AI モジュールを使う場合必須）
     - KABU_API_PASSWORD      — kabuステーション API パスワード（注文系）
     - KABU_API_BASE_URL      — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
     - DUCKDB_PATH            — デフォルト data/kabusys.duckdb
     - SQLITE_PATH            — 監視 DB: data/monitoring.db
     - その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              — DEBUG/INFO/…（デフォルト INFO）

使い方（主要 API と実行例）
--------------------------

基本的な DuckDB 接続
- 設定からパスを取得して接続する例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

ETL（デイリー ETL）
- 日次 ETL を実行して株価・財務・カレンダーを取得・保存・品質チェックを実行します:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

個別 ETL ジョブ（例）
- 株価差分 ETL:
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
- 財務差分 ETL:
  from kabusys.data.pipeline import run_financials_etl
  fetched, saved = run_financials_etl(conn, target_date=date.today())

ニュース NLP（銘柄ごとの AI スコアリング）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定、あるいは api_key 引数で渡す:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"Scored {n_written} codes")

市場レジーム判定
- ETF 1321 の MA とマクロニュースを合成して market_regime テーブルへ書き込みます:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

監査スキーマ初期化
- 監査ログ用テーブルを作成:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成します

ニュース収集（RSS）
- RSS を取得して raw_news へ挿入するユーティリティは news_collector にあります（fetch_rss 等）。
  - fetch_rss は SSRF 対策、コンテンツ長チェック、XML パース注意を実装済みです。
  - 実際の raw_news 保存処理や銘柄紐付けは別関数で行います（実装に依存）。

研究用ユーティリティ
- ファクター計算:
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  m = calc_momentum(conn, date(2026,3,20))
- 将来リターン、IC、サマリー:
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

設定の自動読み込みについて
------------------------
- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動で読み込みます。
- 読み込み順は OS 環境変数 > .env.local > .env（.env.local は既存値を上書き可）。
- テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

トラブルシューティング（よくある注意点）
---------------------------------
- OpenAI / J-Quants のキーが未設定だと API を呼ぶ関数は ValueError を投げます。必ず環境変数か引数でキーを渡してください。
- DuckDB の executemany は空リストを受け取れない箇所があるため、ETL 実装側で空チェックが入っています（そのまま使えば問題ありません）。
- news_collector は RSS の最終 URL を再検証し、プライベートアドレスや非 http(s) スキームを拒否します。社内プロキシや特別なネットワーク環境では注意してください。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は本コードベースで提供されている主要モジュールのツリー（抜粋）です:

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   -- ニュースセンチメント（LLM）
  - regime_detector.py            -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             -- J-Quants API クライアント & DuckDB 保存
  - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
  - quality.py                    -- データ品質チェック
  - calendar_management.py        -- 市場カレンダー管理
  - news_collector.py             -- RSS 収集
  - stats.py                      -- 統計ユーティリティ（zscore_normalize）
  - audit.py                      -- 監査ログスキーマ初期化
  - etl.py                        -- ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py            -- ファクター計算
  - feature_exploration.py        -- 将来リターン / IC / summary
- research/... (ほかユーティリティ)

開発協力／拡張のヒント
---------------------
- テスト: 各モジュールは外部 API 呼び出し箇所を差し替えやすい設計（関数注入・モジュールレベルのラッパ）になっています。unittest.mock.patch で OpenAI / HTTP をモックしてテストを作成できます。
- レート制限・リトライ: jquants_client と AI 呼び出しはリトライ・バックオフ設計が組み込まれています。商用利用時はレート制御の挙動を本番条件で確認してください。
- データスキーマ: DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, …）は ETL / audit 初期化処理で作成・期待されます。独自にスキーマを変更するとパイプラインが動作しなくなる可能性があります。

ライセンス・貢献
----------------
- この README はコード内容に基づくドキュメントです。実際の配布時はライセンスファイル（LICENSE）をプロジェクトに追加してください。
- バグ報告や機能提案は issue を通じてお願いします。

以上。必要があれば、具体的な実行コマンド（CLI ラッパがない場合の Python スクリプト例）や .env.example のテンプレート、各テーブルのスキーマ一覧（DDL 抜粋）などを追加で作成します。どの情報が必要か教えてください。