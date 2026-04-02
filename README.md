KabuSys
=======

日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
ETL・ニュース収集・ニュースのAIスコアリング・市場レジーム判定・研究用ファクター計算・監査ログなどを含むモジュール群を提供します。

主な目的
- J-Quants / JPX などからのデータ取得・保存（DuckDB）
- RSS ニュース収集と LLM を使った銘柄別センチメントスコア付与
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（Research 用）
- ETL パイプラインとデータ品質チェック
- 発注・約定の監査ログスキーマ（監査用 DuckDB）

注意
- 本リポジトリは「データ基盤・研究・戦略生成」層を中心に実装しており、実際の発注（ブローカー送信）は別モジュールで扱う想定です。
- 本番（live）モードでの利用は細心の注意を払ってください（環境変数で env を切り替えられます）。

機能一覧
- データ取得 / ETL
  - J-Quants API から日次株価・財務データ・マーケットカレンダーを差分取得（ページネーション・レート制御・自動リフレッシュ）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（quality.run_all_checks）
- ニュース収集
  - RSS 取得・前処理・raw_news への冪等保存（SSRF対策・トラッキング除去・サイズ制限等）
- AI（LLM）によるスコアリング
  - 銘柄別ニュースセンチメント（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（ETF MA200 とマクロ記事の LLM センチメントを合成する kabusys.ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON mode で利用。API リトライ・バックオフ実装あり
- 研究用ユーティリティ
  - momentum/value/volatility 等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - クロスセクションの z-score 正規化（kabusys.data.stats.zscore_normalize）
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ定義、初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数と .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）

セットアップ手順（開発向け）
1. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型合成表記などを使用）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージインストール
   - 必要な主な依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必要な主な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（必須 for ETL）
     - SLACK_BOT_TOKEN        — Slack 通知（必要に応じて）
     - SLACK_CHANNEL_ID       — Slack チャンネル
     - KABU_API_PASSWORD      — kabuステーション API パスワード（必要に応じて）
     - OPENAI_API_KEY         — OpenAI API キー（AI スコアリング実行時）
   - 任意/デフォルト:
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            — 監視 DB（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU/MEM/DISK 閾値 など
5. データベース初期化（監査ログ例）
   - Python REPL またはスクリプトで:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - これで監査ログ用テーブルが作成されます。

.env 例（抜粋）
- .env.example（参考）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C12345678
  KABU_API_PASSWORD=your_kabu_password
  DUCKDB_PATH=data/kabusys.duckdb
  LOG_LEVEL=INFO
  KABUSYS_ENV=development

使い方（主要ユーティリティ例）
- DuckDB 接続を作って ETL を実行する（日次）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュースの LLM スコア付け（指定日）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {count} codes")

  - OPENAI_API_KEY は環境変数にセットするか、score_news の api_key 引数に渡してください。

- 市場レジーム判定
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（個別 DB）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター・指標
  - 例:
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value
    from kabusys.data.stats import zscore_normalize

    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026,3,20))
    value = calc_value(conn, date(2026,3,20))
    momentum_z = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

設計上の注意点 / 想定
- ルックアヘッドバイアス回避
  - 多くの関数は date.today() や datetime.today() を内部で参照せず、target_date を明示する設計です。バックテストや再現性のため、target_date を明示して呼ぶことを推奨します。
- 冪等性
  - ETL 保存処理は ON CONFLICT / DO UPDATE を用いて冪等性を確保しています。
- フェイルセーフ
  - LLM 呼び出し失敗時や API エラー時はスコアを 0 にフォールバックする等の設計が多く、処理が完全に停止しないよう配慮されています。
- DB 互換性
  - DuckDB を前提とした SQL と API を提供しています。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py               — パッケージ初期化（__version__ 等）
  - config.py                 — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント & 保存関数
    - news_collector.py       — RSS ニュース収集（SSRF対策・正規化など）
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化（init_audit_db 等）
    - etl.py                  — ETL 結果の公開型（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等

ログと実行モード
- LOG_LEVEL (環境変数) でログの詳細度を制御できます（DEBUG/INFO/...）。
- KABUSYS_ENV で実行モードを指定（development / paper_trading / live）。live モードでの実行は特に注意してください。

テスト / 開発メモ
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを停止できます。
- OpenAI 呼び出しや HTTP の外部アクセス部分は、モジュール内で関数単位に差し替え可能（テストでモック可能）となるよう実装されています（例: _call_openai_api、_urlopen）。

ライセンス / 貢献
- （ここにライセンス情報を記載してください）
- バグ報告やプルリクエストは歓迎します。設計方針や互換性についてはコード内 docstring を参照してください。

最後に
- 本 README はコードベースの主要機能と使い方を簡潔にまとめたものです。関数ごとに詳細な docstring を備えていますので、利用時は該当モジュールのドキュメントとコードコメントを参照してください。