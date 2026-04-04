KabuSys — 日本株自動売買プラットフォーム
===================================

概要
----
KabuSys は日本株向けデータプラットフォームと研究・シグナル生成・監査ログの基盤を提供するライブラリ群です。  
主要機能は次の通りです。

- J-Quants からの株価・財務・カレンダーの差分 ETL（DuckDB に保存）
- ニュース収集（RSS）と LLM を用いたニュースセンチメント評価（銘柄別 ai_score）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定の監査ログスキーマ（監査テーブルの初期化、冪等化設計）
- 安全性・実運用向け設計（API リトライ・レート・SSRF ガード・Look-ahead バイアス対策）

主な設計方針
- Look-ahead bias を避けるため内部処理で date.today()/datetime.today() をバックテスト向けに直接参照しない実装に配慮
- J-Quants / OpenAI 呼び出しはリトライ・バックオフ・タイムアウトを備える
- ETL / 保存は冪等（ON CONFLICT / UPDATE）で安全
- DuckDB をデータ層に利用しローカルで簡易に運用可能

機能一覧
--------
- data
  - jquants_client: J-Quants API からのデータ取得・DuckDB への保存（raw_prices, raw_financials, market_calendar など）
  - pipeline: 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）と ETLResult
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 防御・トラッキング除去）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management: 営業日判定・次/前営業日・カレンダー更新バッチ
  - audit: 発注〜約定までを追跡する監査テーブル定義と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを LLM で銘柄ごとにセンチメント化して ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM を合成して market_regime を作成
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: .env 自動読み込み・環境設定管理（settings オブジェクトでアクセス）

前提 / 必要パッケージ
--------------------
少なくとも以下が必要です（バージョンは適宜調整してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例 (開発環境)
- 仮想環境を作成して有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb openai defusedxml

（本リポジトリに setup.py / pyproject.toml がある場合）
  - pip install -e .

環境変数（主要）
----------------
config.Settings からアクセスされる主要な環境変数と既定値（可能な場合）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token() で ID トークンを得るために使われます。

- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード（発注周りで使用）。

- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi

- OPENAI_API_KEY (必須 for AI 呼び出し)  
  OpenAI API キー。news_nlp.score_news / regime_detector.score_regime で参照されます（関数引数に api_key を渡すことも可）。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  通知用（未設定でも動作可）。

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT  
  監視・プロセス管理関連設定

- KABUSYS_ENV  
  有効値: development, paper_trading, live（デフォルト development）

自動 .env ロード
- パッケージ import 時に .env と .env.local（プロジェクトルートの .git または pyproject.toml を基準）を自動で読み込みます。  
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境と依存のインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
     （requirements.txt が無ければ pip install duckdb openai defusedxml）

3. 環境変数設定
   - プロジェクトルートに .env を作成する（.env.example を参考に）。例:
     JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - .env の自動読み込みは import 時に行われます（必要に応じて .env.local に上書き可能）。

4. データベース初期化（監査用 DB）
   - Python REPL またはスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（クイックスタート）
------------------------

基本的な DuckDB 接続と日次 ETL 実行例:

- スクリプト例 run_etl.py:
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

news スコアリング（銘柄別 ai_scores 生成）:

- score_news を使う例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} scores")

市場レジーム判定（market_regime テーブル更新）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡す
  score_regime(conn, target_date=date(2026,3,20))

監査ログ DB 初期化（独立 DB を作る例）:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を渡して audit テーブルを利用

研究 API の例（モメンタム計算など）:

  from kabusys.research import calc_momentum
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]

主要な API の注意点
- score_news / score_regime: OpenAI API キーが必要（api_key 引数で注入可）。API 呼び出しはリトライ実装あり。レスポンス不整合時はフェイルセーフでスコアをスキップまたは 0.0 とする設計。
- jquants_client.fetch_*: レート制御・リトライ・401 の自動トークンリフレッシュを備えています。ID トークンは JQUANTS_REFRESH_TOKEN を用いて取得されます。
- ETL: run_daily_etl は複数ステップを順序実行し、各ステップは個別に例外ハンドリングされます。結果は ETLResult に格納され、品質チェックの結果やエラーを確認できます。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン対策が実装されています（params チェックあり）。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境設定 / .env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch/save）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py                        — ETL 型の再エクスポート
  - news_collector.py             — RSS 収集 / 前処理
  - calendar_management.py        — マーケットカレンダー管理
  - quality.py                    — データ品質チェック
  - stats.py                      — zscore_normalize 等
  - audit.py                      — 監査ログテーブルの DDL / 初期化
- research/
  - __init__.py
  - factor_research.py            — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank
- research/... (上記)

運用上の注意 / ベストプラクティス
--------------------------------
- API キー・秘密情報は .env に保存する際はアクセス制御に注意してください。CI/CD ではシークレットマネージャを利用してください。
- バックテストでの Look-ahead を避けるため、本ライブラリは日付の取り扱いに注意した実装になっています。バックテスト開始前に必要なデータを事前にロードしてから利用してください。
- OpenAI の呼び出し部分は費用が発生します。実行頻度やバッチサイズを運用に合わせて調整してください。
- ETL は idempotent に設計されていますが、重要な操作・DB マイグレーションはバックアップを取ってから実行してください。

開発 / 貢献
------------
- クローン、仮想環境の作成、依存インストール後にユニットテストとスタイルチェックを実行して下さい（テストは同梱されていない可能性があります）。
- 変更提案は Pull Request を通じて行ってください。API 互換性・Look-ahead バイアス・データ整合性に特に注意して下さい。

ライセンス
--------
- 本 README にはライセンス情報が含まれていません。リポジトリ内の LICENSE ファイルを参照してください。

付録：よく使うコードスニペット
---------------------------
- DuckDB 接続取得（設定を使う）:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- ETL 実行:
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)
  print(res.to_dict())

- ニューススコア:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date)

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date)

問い合わせ・サポート
--------------------
- バグ報告、機能要望はリポジトリの Issue に記載してください。具体的な再現手順とログを添付いただけると対応が早くなります。

以上。README に不足している点があれば、使用目的（運用用 / 研究用 / バックテスト）や導入環境を教えてください。それに応じて導入手順やサンプルを調整します。