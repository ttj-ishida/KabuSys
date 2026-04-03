KabuSys — 日本株自動売買プラットフォーム（README）
================================================

概要
----
KabuSys は日本株向けのデータ収集・ETL、データ品質チェック、ファクター研究、ニュースNLP（LLM を使ったセンチメント）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを含む自動売買基盤のコアライブラリ群です。  
設計上の特徴として、DuckDB をデータレイク／DB として利用し、J‑Quants API（株価・財務・カレンダー）や OpenAI（gpt-4o-mini）を外部データソースとして扱います。バックテストや本番運用での「ルックアヘッドバイアス防止」や「冪等保存」「フェイルセーフ（API失敗時のフォールバック）」を重視した実装になっています。

主な機能
--------
- データ収集／ETL
  - J‑Quants からの日次株価（OHLCV）・財務・上場情報・マーケットカレンダーの差分取得 & 保存（冪等）
  - ETL の一括実行（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク、重複、将来日付・非営業日の存在チェック（QualityIssue を返却）
- ニュース収集
  - RSS 取得、テキスト前処理、記事ID生成（URL 正規化＋SHA-256）、raw_news への冪等保存
  - SSRF 対策・受信サイズ制限・XML セキュリティ対策（defusedxml）等の安全対策
- ニュース NLP（LLM）
  - 銘柄単位にニュースを統合して OpenAI に JSON Mode で投げ、ai_scores テーブルへ書き込み（score_news）
  - 再試行やレスポンスバリデーション、スコアクリッピング
- 市場レジーム判定
  - ETF 1321 の 200日MA乖離（70%）とマクロニュースセンチメント（30%）を合成してレジーム（bull/neutral/bear）を判定・記録（score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research パッケージ）
  - 将来リターン、IC 計算、統計サマリ（外部依存なし）
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 を UUID による階層トレースで保存するスキーマ初期化ユーティリティ（init_audit_db / init_audit_schema）
- 環境設定ハンドリング
  - .env / .env.local 自動読込（プロジェクトルート探索）、必要変数のラップ（kabusys.config.settings）

前提・依存関係
--------------
- Python >= 3.10
- 主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- OS ネットワークアクセス（J‑Quants / OpenAI への HTTP(S)）

セットアップ手順
---------------

1. リポジトリをクローン（既にパッケージソースがある前提）
   - git clone ... （省略）

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml
   - 開発インストール（プロジェクトに setup/pyproject がある場合）:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます（.env.local は上書き）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development  (valid: development, paper_trading, live)
     - LOG_LEVEL=INFO

使い方（短いコード例）
---------------------

- 基本的な DuckDB 接続と ETL 実行
  - Python REPL やスクリプトで:
    - from datetime import date
      import duckdb
      from kabusys.config import settings
      from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect(str(settings.duckdb_path))
    - result = run_daily_etl(conn, target_date=date(2026,3,20))
    - print(result.to_dict())

- ニューススコアリング（OpenAI キーは環境変数または api_key 引数で指定）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str("data/kabusys.duckdb"))
  - n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY 必須（環境変数か引数）

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # conn を使って order_requests / signal_events / executions を操作可能

- config の利用例
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.is_live)

設計上の注意点
--------------
- ルックアヘッドバイアスの回避:
  - 日付を自動参照せず、関数呼び出し時に明示的に target_date を渡す設計になっています（ETL・NLP・レジーム判定等）。
- 冪等性:
  - DB への保存は可能な限り ON CONFLICT / INSERT ... DO UPDATE / 個別 DELETE→INSERT の形で冪等にしています。
- フェイルセーフ:
  - 外部 API の失敗（OpenAI / J‑Quants 等）は適切にログを残し、可能であればフォールバック（ゼロスコア等）して継続します。
- セキュリティ:
  - ニュース収集の SSRF・XML インジェクション対策・受信サイズ制限・URL 正規化等を実装しています。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主なファイル一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数処理・Settings
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュースNLP（score_news）
    - regime_detector.py              -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               -- J‑Quants API クライアント（fetch/save）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py                          -- ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py               -- RSS 収集・前処理
    - calendar_management.py          -- 市場カレンダー管理（営業日判定等）
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                        -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py              -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py          -- 将来リターン / IC / 統計サマリ

ライセンス・貢献
----------------
- 本コードベースのライセンス表記はリポジトリ内の LICENSE を参照してください（該当しない場合は利用前にライセンスを定義してください）。
- バグ報告や機能提案は Issue を立ててください。Pull Request はテスト・説明付きで歓迎します。

付録: よくある質問
-------------------
Q: .env の自動読み込みを止めたい  
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します。

Q: OpenAI のレスポンスが想定外のフォーマットの時の挙動は？  
A: レスポンスの JSON パースに失敗した場合やバリデーションに失敗した場合はログに WARNING を出し、該当タスクはスキップまたはゼロスコアでフォールバックします（例: score_news / score_regime）。

Q: DuckDB ファイルのデフォルト場所は？  
A: settings.duckdb_path のデフォルトは data/kabusys.duckdb です。必要に応じて環境変数 DUCKDB_PATH で上書きしてください。

お問い合わせ
------------
実装方針や利用方法に関する質問があればリポジトリの Issue または直接ご連絡ください。