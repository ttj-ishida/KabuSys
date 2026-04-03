KabuSys — 日本株自動売買プラットフォーム（README）
====================================

概要
----
KabuSys は日本株向けのデータパイプライン／リサーチ／アルゴリズム取引支援機能を提供する Python パッケージです。  
主に以下を目的としています。

- J-Quants API からの差分 ETL（株価・財務・JPX カレンダー等）
- ニュース収集と LLM（OpenAI）を用いたニュースセンチメント評価
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を格納する DuckDB スキーマ

パッケージ情報
---------------
- パッケージ名: kabusys
- バージョン: 0.1.0
- 主要依存（代表例）: Python 3.10+（typing の | 演算子を利用）、duckdb、openai、defusedxml 他

主な機能（機能一覧）
------------------
- data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証、ページネーション、保存処理）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・トラッキング除去）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理・営業日ロジック（next_trading_day 等）
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
  - stats: 汎用統計ユーティリティ（zscore 正規化 など）
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントを LLM でスコアリングし ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュース（LLM）を合成して market_regime に記録
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - settings: .env / 環境変数から設定を読み込み（自動ロード機能あり）

セットアップ手順
----------------

1. リポジトリをクローン／ダウンロード
   - プロジェクトルートに pyproject.toml または .git がある想定です。

2. Python 環境の準備（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主に必要な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（必須）
     - OPENAI_API_KEY : OpenAI（news_nlp / regime_detector の呼び出しに必要）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必要に応じて）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL
   - .env.example を参照して作成してください（コード内で .env.example を参照するよう指示が出ます）。

5. データベース格納先ディレクトリ作成
   - デフォルトでは data/ 以下にファイルが作られます。必要に応じて作成してください:
     - mkdir -p data

使い方（簡単な例）
-----------------

（1）DuckDB に接続して日次 ETL を実行する例
- Python REPL やスクリプトで:

  from kabusys.config import settings
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)
  print(result.to_dict())

  - run_daily_etl は market_calendar / raw_prices / raw_financials の差分取得 → 保存 → 品質チェックまで行い、ETLResult を返します。

（2）ニュースセンチメントのスコア付け（ai.news_nlp）
- 事前に OPENAI_API_KEY を設定してください。

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

（3）市場レジーム判定（ai.regime_detector）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

（4）監査ログスキーマを初期化（audit）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

注意点 / 設計方針
-----------------
- Look-ahead bias 防止:
  - ai モジュール／ETL／research の各関数は内部で date.today()/datetime.today() を無闇に参照しないよう設計されています。必ず target_date を明示的に与えることを想定しています。
- フェイルセーフ:
  - LLM/API 失敗時は例外投げっぱなしにせず、ログ記録のうえ安全側のデフォルト（例: マクロセンチメント = 0.0）で継続する設計です。呼び出し側でエラー検出や再実行を行ってください。
- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT を用いて冪等に実装されています。
- セキュリティ:
  - news_collector は SSRF 対策（プライベート IP 拒否、リダイレクト検査）や XML の defusedxml を利用して安全に RSS をパースします。

ディレクトリ構成
----------------
プロジェクトの主要なファイル / モジュール一覧（src/kabusys 配下）:

- __init__.py
- config.py                     : 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                 : ニュースセンチメント計算（score_news）
  - regime_detector.py          : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py           : J-Quants API クライアント（fetch_* / save_*）
  - pipeline.py                 : ETL パイプライン（run_daily_etl 等）
  - etl.py                      : ETL 結果型の公開（ETLResult）
  - news_collector.py           : RSS 収集／正規化／保存
  - quality.py                  : データ品質チェック
  - stats.py                    : 汎用統計ユーティリティ（zscore_normalize）
  - calendar_management.py      : 市場カレンダー管理（is_trading_day 等）
  - audit.py                    : 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py          : ファクター計算（momentum/value/volatility）
  - feature_exploration.py      : 将来リターン / IC / 統計サマリー 等

その他
-----
- 自動で .env を読み込む挙動:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テスト等で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギングレベルは LOG_LEVEL で制御（デフォルト INFO）。
- KABUSYS_ENV によって is_live / is_paper / is_dev の動作フラグが提供されます。

貢献 / 開発
-----------
- テストや CI を行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して意図しない .env 読み込みを避けると便利です。
- OpenAI / J-Quants の呼び出し部分は差し替え（モック）しやすいように実装で抽象化してあります。ユニットテスト時は該当関数をパッチしてください（例: kabusys.ai.news_nlp._call_openai_api）。

ライセンス
--------
- このリポジトリ内のライセンス情報はソースに含まれていません。利用・配布時はリポジトリのライセンス方針に従ってください。

お問い合わせ
------------
- 実運用や API キー管理には十分注意してください。追加の利用例や導入手順が必要であれば教えてください。README の拡張やサンプルスクリプトを提供します。