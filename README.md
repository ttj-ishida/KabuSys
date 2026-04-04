KabuSys — 日本株自動売買プラットフォーム
===================================

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・AI評価・監査・ETL を備えた自動売買基盤のコードベースです。  
主に以下を目的としています。

- J-Quants からの市場データ（株価・財務・カレンダー等）の差分取得と DuckDB への保存（ETL）
- ニュース記事収集と LLM による銘柄センチメント（ai_score）算出
- マーケットレジーム判定（ETF の MA とマクロニュースの LLM スコアの合成）
- 研究用ファクター計算・特徴量解析（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order_request → execution）用スキーマ初期化・運用ユーティリティ
- データ品質チェック、マーケットカレンダー管理、ニュース収集の安全対策

主な機能一覧
-------------
- data
  - ETL パイプライン（run_daily_etl 等）: 株価・財務・カレンダーの差分取得・保存・品質チェック
  - jquants_client: J-Quants API 呼び出し、レートリミット・リトライ・トークン自動リフレッシュ対応
  - news_collector: RSS 収集・前処理・SSRF 対策・冪等保存
  - calendar_management: 営業日判定、next/prev_trading_day、calendar 更新ジョブ
  - audit: 監査ログテーブル作成・初期化（DuckDB）
  - quality: データ品質チェック群（欠損、スパイク、重複、日付不整合）
  - stats: z-score 正規化等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュース記事を LLM でスコアリングし ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュース LLM スコアを合成して market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数 / .env 自動読み込み・検証ロジック

セットアップ手順
----------------

前提
- Python 3.10+（typing 注釈に依存）
- DuckDB（Python パッケージとして利用）
- OpenAI SDK（OpenAI クライアントを利用する機能があるため）
- ネットワークアクセス（J-Quants / RSS / OpenAI）

1) リポジトリをクローン（例）
   git clone <repo-url>
   cd <repo-root>

2) 仮想環境作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell など)

3) 依存パッケージをインストール（例: requirements.txt がある想定）
   pip install -r requirements.txt

   主要な依存パッケージ（参考）
   - duckdb
   - openai
   - defusedxml

   または開発インストール:
   pip install -e .

4) 環境変数設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必要な（または利用可能な）環境変数例:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（news/regime モジュールで使用）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env 例（最小）:
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_kabu_password

使い方（コード例）
------------------

※ 以下は Python REPL / スクリプトでのサンプルです。実運用では適切なエラーハンドリング・ログ設定が必要です。

- DuckDB 接続の作成
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # :memory: も可

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（LLM 必要）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {count}")

- 市場レジーム判定（LLM 必要）
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算・研究ツール
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- 監査スキーマ初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これにより監査テーブルが作成されます

- データ品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

自動 .env ロードの挙動
---------------------
パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を特定できれば自動的に .env（優先度低） → .env.local（上書き）の順で読み込みます。テストや明示的制御のために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py              # パッケージ初期化、__version__
  - config.py                # 環境変数 / .env ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの LLM スコアリング（score_news）
    - regime_detector.py     # マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # マーケットカレンダー管理
    - news_collector.py      # RSS 収集・前処理
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログテーブル定義・初期化
    - etl.py                 # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリー

運用上の注意
------------
- Look-ahead バイアス対策が多くのモジュールで考慮されています。target_date は明示的に渡すか、内部で date.today() を使用する箇所に注意してください（AI モジュールや ETL はルックアヘッドに注意）。
- OpenAI / J-Quants 呼び出しには API レート制限・課金・キー管理の注意が必要です。プロダクション環境では鍵を安全に管理してください。
- news_collector には SSRF 対策や受信サイズの制限を導入していますが、外部フィードの扱いには注意してください。
- DuckDB に対する executemany の空パラメータやバージョン依存の挙動について、コメントや実装上の回避がなされています。DuckDB のバージョン互換性には注意してください。

開発・テスト
-------------
- 自動 .env ロードはテストで影響することがあるため、テスト実行時に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することを推奨します。
- OpenAI 呼び出し等はテストでモック化する設計（_call_openai_api は patch 可能）になっています。
- J-Quants API への実ネット接続に依存しない単体テストは、jquants_client の _request 部分や外部呼び出しをモックしてください。

ライセンス・貢献
----------------
（リポジトリに LICENSE ファイルがあればここに記載してください）

最後に
------
この README はソースコードの docstring と実装方針に基づいて作成しています。具体的なセットアップ（requirements.txt の内容、CI/CD、運用ジョブの cron/systemd 設定など）は導入環境に合わせて追加してください。必要であれば README の補足（例: .env.example、docker-compose 構成、運用手順）を追記します。