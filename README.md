KabuSys — 日本株向け自動売買 / データ基盤ライブラリ
=================================================

概要
----
KabuSys は日本株のデータ取得・品質管理・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ管理などを提供する、バックテスト／運用に使えるユーティリティ群です。主に DuckDB をデータストアとして想定し、J-Quants API や RSS、OpenAI（gpt-4o-mini など）を用いた処理を含みます。

特徴（主な機能）
----------------
- データ ETL（J-Quants からの日次株価・財務・市場カレンダー取得、差分更新）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI による銘柄別センチメント算出 → ai_scores）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- ファクター計算（Momentum / Value / Volatility 等）
- 特徴量探索（将来リターン、IC、統計サマリー）
- 監査ログスキーマ（シグナル → 発注 → 約定のトレーサビリティ）
- 環境変数管理（.env/.env.local の自動読込、設定ラッパー）

セットアップ
-----------

前提
- Python 3.10 以上（typing の | 型注釈を利用）
- DuckDB を利用するための環境
- J-Quants / OpenAI の API キー（利用機能に応じて）

インストール（例）
- ソースを開発インストール:
  python -m pip install -e .

- 必要パッケージ（最低限の例）:
  pip install duckdb openai defusedxml

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env と .env.local を置くと自動でロードされます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

代表的な環境変数
- JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン（必須: データ取得時）
- OPENAI_API_KEY         … OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD      … kabuステーション API のパスワード（実行モジュールで参照）
- KABUSYS_ENV            … 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL              … ログレベル ("DEBUG","INFO",...)
- DUCKDB_PATH            … メイン DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE        … Paper Trading の fill モード ("instant","partial","never","reject")
- PAPER_TRADING_SQLITE_PATH … Paper Trading 用 SQLite ファイル（デフォルト data/paper_trading.db）
- その他 PID/kill フラグや監視閾値など多数（config.Settings で参照可）

簡易 .env 例
- プロジェクトルート/.env:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

使い方（よく使う API）
--------------------

1) DuckDB 接続の準備
- 例:
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL の実行（データ取得・品質チェック）
- 例:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースセンチメントスコア算出（ai_scores へ書き込み）
- 例:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

4) 市場レジーム算出（market_regime へ書き込み）
- 例:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または引数で指定可

5) 監査ログ DB 初期化
- 監査用に別 DB を使う:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/monitoring_audit.duckdb")

6) ファクター計算 / 研究用ユーティリティ
- 例:
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])

注意点 / 実装に関する重要事項
- Look-ahead バイアス対策:
  - AI モジュールや ETL の多くは内部で date を引数として受け取り、datetime.today()/date.today() を直接参照しない設計です。バックテストや再現性のために target_date を明示してください。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI Chat Completions（JSON モード）を使い、レスポンスの検証やリトライを備えています。
  - API キーの供給は api_key 引数または環境変数 OPENAI_API_KEY を使用。
- .env パース:
  - quotes、エスケープ、インラインコメントなどを比較的厳密にパースし、.env.local で上書き可能です。OS の現行環境変数は保護されます。
- J-Quants クライアント:
  - ページネーション対応、レートリミット（120 req/min）遵守、401 のトークン自動リフレッシュ、リトライと指数バックオフを実装しています。
- ニュース収集:
  - SSRF 対策、受信サイズ制限、XML の安全なパース（defusedxml）を実施しています。
- トランザクション:
  - 重要な書き込みは BEGIN/DELETE/INSERT/COMMIT で冪等性と整合性を保つよう実装されています。エラー時は ROLLBACK を試みます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                - パッケージ初期化、バージョン
- config.py                  - 環境変数 / 設定ラッパー（settings）
- ai/
  - __init__.py              - ai パッケージ公開 API
  - news_nlp.py              - ニュース NLP（ai_scores 生成）
  - regime_detector.py       - 市場レジーム判定（market_regime 生成）
- data/
  - __init__.py
  - jquants_client.py        - J-Quants API クライアント / DB 保存関数
  - pipeline.py              - ETL パイプライン（run_daily_etl 等）
  - quality.py               - データ品質チェック
  - news_collector.py        - RSS 収集・正規化
  - calendar_management.py   - 市場カレンダー・営業日判定
  - stats.py                 - 統計ユーティリティ（zscore）
  - audit.py                 - 監査ログスキーマ初期化
  - etl.py                   - ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py       - Momentum/Value/Volatility 等
  - feature_exploration.py   - 将来リターン / IC / サマリー
- research/...               - 研究用ユーティリティ群
- その他ユーティリティ群（監視 / 実行 / strategy 等は将来的に追加想定）

開発・運用ヒント
----------------
- ローカルでのデバッグ:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読込を無効にできます（テスト等）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading に設定し、PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等で挙動を調整してください。
- ロギング:
  - LOG_LEVEL を設定してログの詳細度を調整できます（DEBUG 推奨で内部挙動を確認）。
- テスト:
  - OpenAI / HTTP 呼び出し部分はモックしやすい実装になっています（内部の _call_openai_api や _urlopen 等を patch ）。

ライセンス / 貢献
----------------
- 本リポジトリのライセンス情報・貢献方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
----------
- 実装上の意図や設計方針、API の詳細な挙動については各モジュールの docstring を参照してください。追加の使い方やサンプルが必要であれば、具体的なユースケース（ETL の定期実行、研究ワークフロー、リアル口座発注フローなど）を指定して問い合わせてください。