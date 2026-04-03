KabuSys
=======

概要
----
KabuSys は日本株のデータ基盤・リサーチ・AI・監査ログを含む自動売買補助ライブラリです。  
主に以下を提供します：

- J-Quants からの株価・財務・カレンダー等の差分ETL（DuckDB に保存）
- ニュース収集（RSS）と LLM によるニュースセンチメント集約（ai_scores）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定管理（.env の自動読み込み等）

設計方針は「ルックアヘッドバイアス回避」「DuckDB を用いた高速なローカル永続化」「外部API呼び出しは堅牢なリトライ／レート制御付き」「フェイルセーフ（API失敗時は継続）」です。

主な機能一覧
-------------
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）: 認証、ページネーション、保存（冪等）
- ニュース
  - RSS 収集と前処理（kabusys.data.news_collector）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント（kabusys.ai.news_nlp）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュース LLM を合成（kabusys.ai.regime_detector）
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリ（kabusys.research）
- データ品質チェック
  - 欠損 / スパイク / 重複 / 日付整合性チェック（kabusys.data.quality）
- 監査ログ
  - audit スキーマ生成 / 初期化（kabusys.data.audit）
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）と Settings（kabusys.config）

セットアップ手順
----------------

1. 必要パッケージをインストール（例）:
   - Python 3.10+ を想定
   - 主要依存（最低限、プロジェクトのコードで利用されるもの）:
     - duckdb
     - openai
     - defusedxml

   例（pip）:
   pip install duckdb openai defusedxml

   （実際のプロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

2. リポジトリをクローンしてインストール（開発時）:
   git clone <repo>
   cd <repo>
   pip install -e .

3. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。
   - 自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（必須/任意）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注連携利用時）
   - OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（score_news, score_regime を使う場合）
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — development|paper_trading|live（デフォルト development）
   - LOG_LEVEL (任意) — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - その他監視用フラグ（PID/KILL ファイルパス、閾値など）

   サンプル .env（例）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

4. データディレクトリ作成:
   mkdir -p data

基本的な使い方（コード例）
-------------------------

- DuckDB 接続作成例:

  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- ETL（日次実行）:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日が対象（日次バッチ想定）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング:

  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")

  ※ OPENAI_API_KEY が環境変数または api_key 引数で必要

- 市場レジーム判定:

  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))

- 監査DB 初期化（監査専用 DB を使う場合）:

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます

- ファクター計算（研究用途）:

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

実装上の注意点と挙動
--------------------
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env → .env.local の順で行います。OS 環境変数を上書きしない（.env.local は上書き可）実装です。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode を使って厳密な JSON レスポンスをパースします。API エラー時のリトライ、パース失敗時のフェイルセーフ（0.0 などのフォールバック）があります。
- J-Quants API はレート制御（120 req/min）とリトライ（408/429/5xx）を実装。401 はトークンリフレッシュを試行します。
- DuckDB への保存は可能な限り冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を担保しています。
- 日付処理では「ルックアヘッドバイアス防止」のために datetime.today()/date.today() を直接参照しない設計が多く採用されています（関数呼び出し時に target_date を渡すことを想定）。

主要ディレクトリ構成
-------------------

src/kabusys/
- __init__.py — パッケージ初期化（version 等）
- config.py — 環境変数・設定管理（Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン / run_daily_etl 等
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理・保存
  - calendar_management.py — 市場カレンダー管理・営業日判定・更新ジョブ
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - stats.py — zscore_normalize 等
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 等
  - feature_exploration.py — forward returns / IC / rank / summary

開発・運用上の補足
-----------------
- テスト時: 環境変数の自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはテストでモック化可能（各モジュールで _call_openai_api を差し替える設計）。
- DuckDB のバージョン差異（executemany の空リスト扱いなど）に配慮した実装が一部にあります。
- news_collector は SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）を実装しています。
- 監査テーブルは削除前提ではない設計のため、データ保持とトレーサビリティを重視しています。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスと貢献ガイドを記載してください。例：MIT / CONTRIBUTING.md の参照等）

問い合わせ
--------
問題や質問があれば Issue を立てるか、リポジトリの管理者に連絡してください。

--- 
README は以上です。必要であれば「実際の .env.example」や「requirements.txt」「起動スクリプト（systemd, cron）」のサンプルを追加できます。どの追加情報が欲しいか教えてください。