KabuSys — 日本株自動売買プラットフォーム（README）
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買基盤です。  
主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダーの ETL（差分取得・冪等保存）
- ニュース収集 (RSS) と LLM（OpenAI）を使ったニュースセンチメントスコアリング
- 市場レジーム判定（MA200 と マクロニュースセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック・監査ログ（トレーサビリティ用テーブル群）
- DuckDB を中心としたオンプレ／ローカル分析基盤

機能一覧
--------
主な機能（抜粋）:

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API ページネーション・認証・レート制御・リトライ対応
- ニュース処理:
  - RSS 取得（SSRF 対策・受信サイズ制限・トラッキング除去）
  - news_nlp.score_news: OpenAI で銘柄別ニュースセンチメント算出・ai_scores に書込
- レジーム判定:
  - ai.regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロセンチメント合成
- リサーチ:
  - research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - data.stats.zscore_normalize
- データ品質:
  - data.quality.run_all_checks（欠損・スパイク・重複・日付不整合検出）
- 監査ログ:
  - data.audit.init_audit_db / init_audit_schema（signal_events, order_requests, executions）

前提条件（推奨）
----------------
- Python 3.10+
- DuckDB
- OpenAI SDK（openai）
- defusedxml
- その他標準ライブラリ

インストール（開発環境）
-----------------------
1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（プロジェクトに requirements.txt が無い場合は下記を参考に個別にインストールしてください）:
   pip install duckdb openai defusedxml

4. パッケージを編集可能モードでインストール（任意）:
   pip install -e .

環境変数と設定
--------------
自動でプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文実装時に使用）
- KABU_API_BASE_URL: kabu API のベース URL（省略可, default=http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB のデータベースファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（monitoring）パス
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

基本的な使い方
--------------
以下は簡単な利用例です。Python スクリプトや REPL から直接呼び出します。

- DuckDB 接続を開く:
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（市場カレンダー・価格・財務を差分取得して品質チェックまで実行）:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコア生成（OpenAI API キーが環境変数にあること）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n} symbols")

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI の APIキーは環境変数 OPENAI_API_KEY か api_key 引数で指定

- 監査ログ DB を初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター取得:
  from kabusys.research.factor_research import calc_momentum
  momentum = calc_momentum(conn, target_date=date(2026,3,20))

注意点 / 設計ポリシー
-------------------
- ルックアヘッドバイアス防止: 各モジュールは内部で date.today() や datetime.now() を不必要に参照しない設計（ターゲット日を明示して処理）。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml のある場所）から読み込みます。
- OpenAI 呼び出しはリトライ・フォールバック（失敗時はスコア 0.0）等の安全策がありますが、API 利用負荷に注意してください。
- DuckDB の executemany では空リストが問題になるバージョンがあるため内部でチェックしています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント（OpenAI）
  - regime_detector.py            — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存ロジック
  - pipeline.py                   — ETL パイプライン（run_daily_etl など）
  - etl.py                        — ETLResult の再エクスポート
  - news_collector.py             — RSS 収集・正規化
  - calendar_management.py        — 市場カレンダー管理
  - quality.py                    — データ品質チェック
  - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py            — ファクター計算（momentum/value/volatility）
  - feature_exploration.py        — forward_returns / IC / rank / summary

ライセンス / 貢献
----------------
- 本プロジェクトのライセンス・貢献ルールはリポジトリ上の LICENSE / CONTRIBUTING を参照してください（存在しない場合はリポジトリ管理者に確認してください）。

サポート / 問い合わせ
--------------------
- 実運用・本番接続（kabuステーションでの発注、実口座接続）を行う場合は十分なテスト・監査と手動チェックを行ってください。  
- セキュリティ関連（API鍵漏洩、SSRF対策、DBアクセス管理）に関する問い合わせはリポジトリ管理者へ。

以上。README に必要な追加情報（CI、requirements.txt の中身、実行用 CLI など）を提供いただければ、より詳しい手順やコマンド例を追記します。