# KabuSys

日本株自動売買プラットフォームのライブラリ群（ライブラリ本体）。  
データ取得・ETL、ニュースNLP（LLM）によるセンチメント、ファクター計算、監査ログなどを含むモジュール群です。

主な設計方針：
- Look‑ahead バイアスを避ける（target_date を明示、datetime.today()/date.today() を無闘で使わない等）
- DuckDB を中心としたローカルデータレイヤ
- J-Quants / OpenAI 等外部 API 呼び出しは再試行・レート制御・フォールバックを実装
- ETL・保存は冪等（ON CONFLICT）で安全に運用可能

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成
- 注意事項 / テスト時のヒント

---

プロジェクト概要
- KabuSys は日本株向けのデータパイプライン・研究・監視・運用支援を行う Python モジュール群です。
- データ取得（J-Quants） → DuckDB に格納 → 品質チェック → ファクター計算 → ニュースセンチメント / レジーム判定 → 監査ログ といったワークフローを提供します。
- OpenAI を用いたニュースセンチメント（gpt-4o-mini，JSON mode）や、市場レジーム判定などの AI コンポーネントを内包します。

機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
  - KABUSYS_ENV / LOG_LEVEL の検証
- データ取得（kabusys.data.jquants_client）
  - J-Quants API から日次株価・財務・マーケットカレンダー等を取得（ページネーション対応）
  - レート制御、リトライ、401 トークンリフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実行（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル・品質チェック（quality）
  - ETL 実行結果を ETLResult として返却
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、SSRF 対策、記事 ID 正規化（SHA-256）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査スキーマ初期化（冪等）
  - 監査用 DuckDB 初期化ユーティリティ
- 研究モジュール（kabusys.research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI 関連（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄別に集約し OpenAI でセンチメントを算出 → ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
- 汎用ユーティリティ（kabusys.data.stats）
  - Zスコア正規化など

セットアップ手順（ローカルで使う場合）
1. 要求環境
   - Python 3.10+
   - 必要パッケージ（例）
     - duckdb
     - openai
     - defusedxml
   インストール例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb openai defusedxml

2. リポジトリをクローン（例）
   git clone <repo-url>
   cd <repo-root>

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置してください。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - 他（LINE 関連や監視設定など、settings 内で参照される項目）
   - .env の自動ロードはデフォルトで有効。無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化（監査テーブルなど）
   Python REPL で例:
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)  # DuckDB ファイルを作成してスキーマを初期化

使い方（代表的な操作の例）
- DuckDB 接続を作って ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコア取得（指定日）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すことも可。渡さない場合は環境変数 OPENAI_API_KEY を参照
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {n} codes")

- 市場レジームの算出（指定日）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB を別途初期化して利用する
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # or a separate path
  # 以降 audit_conn を通じて signal/order/execution を保存・参照

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースセンチメント（OpenAI 呼び出し・検証・DB 書き込み）
    - regime_detector.py             -- 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult の再エクスポート
    - calendar_management.py         -- 市場カレンダー管理・営業日判定
    - news_collector.py              -- RSS 収集・前処理
    - quality.py                     -- データ品質チェック
    - stats.py                       -- Zスコア等統計ユーティリティ
    - audit.py                       -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             -- Momentum / Volatility / Value 等
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリ等
  - monitoring/ (※ present in __all__ but implementation not shown here)
  - execution/ (※ present in __all__ but実装はここに含まれない場合あり)
  - strategy/ (※ strategy 層の実装は別途)

注意事項 / 補足
- 環境変数が不足していると Settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。.env.example を参照して .env を準備してください（リポジトリに .env.example があることを想定）。
- OpenAI 呼び出しは外部 API のため課金やレート制限に注意してください。テスト時は各モジュール内の _call_openai_api をパッチしてモックすることが想定されています（unittest.mock.patch で差し替え可能）。
- J-Quants クライアントは内部でレート制御（120 req/min）とトークン自動リフレッシュを行います。id_token を明示的に与えてページネーションを安定させることも可能です。
- DuckDB の executemany に関する互換性考慮（空パラメータの実行回避）や、ETL の部分失敗時に他データを保護する設計（コード絞り込み DELETE → INSERT）など運用上の配慮をしています。
- news_collector は SSRF 対策（リダイレクト時のホスト IP 検査）や RSS のサイズ制限等を実装しています。外部 RSS の取り扱い時は運用上の安全を確認してください。

テスト / 開発のヒント
- OpenAI 呼び出しや外部 HTTP を伴う部分はモックが前提です。関数単位で _call_openai_api をパッチするか、urllib / urllib.request の扱いを差し替えてテストを行ってください。
- settings 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからテストを起動してください。
- DuckDB を用いた単体テストは ":memory:" を使うと便利です（init_audit_db(":memory:") など）。

---

この README はコードベースの現状（提供されたモジュール群）に基づく概要と基本的な使い方をまとめたものです。実際の運用では .env の管理、OpenAI/J-Quants の API キー管理、ログ設定（LOG_LEVEL）、監視設定を適切に行ってください。必要があれば利用したいモジュールごとにより詳細なドキュメント（API 引数の説明、戻り値のスキーマ、例外挙動など）を追加できます。