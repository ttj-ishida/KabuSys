KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。
主に以下を提供します。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）と DuckDB への ETL
- ニュース収集／NLP による銘柄センチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースを組合せ）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック、監査ログ（トレーサビリティ）テーブルの初期化
- RSS ニュース収集の SSRF 対策・前処理・冪等保存ロジック

設計上の重点
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない等）
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション）を意識
- 外部API呼び出しはリトライ・バックオフ・レート制限を組込
- セキュリティ配慮（RSS の SSRF 防止、defusedxml 使用）
- テスト可能性（APIキー注入や内部関数の差替えを想定）

機能一覧
--------
主要な機能（モジュール別）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）
  - 環境変数ベースの設定ラッパ（settings オブジェクト）
  - 必須キー未設定時は明示的な例外

- kabusys.data
  - jquants_client: J-Quants API クライアント（rate limiter / retry / token refresh）
  - pipeline: 日次 ETL (run_daily_etl) と個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 取得・正規化・raw_news 保存（SSRF/サイズ制限）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログテーブル作成・初期化（init_audit_db / init_audit_schema）
  - stats: zscore_normalize 等の統計ユーティリティ
  - ETLResult: ETL 実行結果型

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを組合せ市場レジーム判定

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats の再利用（zscore_normalize）

セットアップ手順
--------------
前提
- Python 3.10+ を推奨（typing の union 等を使用）
- DuckDB, OpenAI SDK, defusedxml 等が必要

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - （プロジェクトに requirements.txt/pyproject.toml がある想定）
   - pip install duckdb openai defusedxml

   必要に応じて他パッケージ（requests 等）を追加してください。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

  主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注関連）
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知等に使用
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — モニタリング用 SQLite（デフォルト data/monitoring.db）
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

使い方（簡単な例）
----------------

- settings の参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- DuckDB 接続と日次 ETL 実行
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア算出（OpenAI API キーが必要）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査データベース初期化（監査ログ用）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db(settings.duckdb_path)  # ファイル作成とスキーマ初期化

- ファクター計算（研究用途）
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  res = calc_momentum(conn, target_date=date(2026,3,20))

運用上の注意・設計ノート
-----------------------
- Look-ahead バイアス対策
  - AI / リサーチ モジュールは target_date 未満のデータのみ参照する等、未来データ参照を避ける設計です。
- 冪等性
  - jquants_client の保存関数や ETL は ON CONFLICT / DELETE→INSERT 等で冪等性を保つ設計です。
- API 呼び出し
  - J-Quants: 固定間隔レート制限（120 req/min）を組込。401 を受けたらトークン自動更新を試みます。
  - OpenAI: レート制限・タイムアウトなどに対するリトライとフォールバック（失敗時は 0.0 を返す等）を実装。
- セキュリティ
  - RSS 取得では SSRF 防止（リダイレクト検査、プライベートIP拒否）や受信サイズ制限、defusedxml を利用。
- ロギングとモニタリング
  - settings.log_level によるログ制御、ETLResult による品質チェックの結果保持を行います。

ディレクトリ構成
----------------
主要なソース配置（概要）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS 取得・前処理
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログ（テーブル作成 / init）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

補足
----
- 自動で .env を読み込む機能はプロジェクトルート（.git または pyproject.toml）を起点に探します。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出しや外部 API 呼び出しはテスト容易性のために内部関数をモック可能な形で実装しています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

ライセンスや貢献方法
-------------------
（リポジトリの LICENSE / CONTRIBUTING を参照してください）

お問い合わせ
------------
実運用や導入に関する質問がある場合は、リポジトリの issue または社内担当者にお問い合わせください。

--- 
以上。README に追加したい具体的な使用例や .env のテンプレート（.env.example）を提供希望であれば、必要な項目を列挙してサンプルを作成します。