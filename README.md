# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL、ニュースNLP（LLM を用いた銘柄センチメント）、市場レジーム判定、データ品質チェック、監査ログ等を提供します。設計上は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を重視しています。

概要
- ETL：J-Quants API から株価・財務・マーケットカレンダーを差分取得し DuckDB に保存
- ニュース収集：RSS から記事を収集して raw_news に保存（SSRF 対策・正規化）
- AI スコアリング：OpenAI（gpt-4o-mini）を用いて銘柄ごとのニュースセンチメント（ai_scores）やマクロセンチメントを算出
- リサーチ：ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 品質チェック：データ欠損・スパイク・重複・日付不整合を検出
- 監査ログ：signal→order_request→execution のトレーサビリティを DuckDB に構築

主な設計方針（抜粋）
- 日付処理は明示的に target_date を渡し、datetime.today()/date.today() に依存しない実装を推奨（バックテストでのルックアヘッド防止）
- DB 操作は可能な限り冪等（ON CONFLICT）で行う
- 外部 API 呼び出しはリトライ・バックオフ・レート制御あり
- ネットワーク/API 障害時はフェイルセーフ（例：スコアリング失敗時は 0 にフォールバック）で継続

機能一覧
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：ページネーション・認証・レート制御・保存関数
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- ニュース & NLP
  - RSS 収集（kabusys.data.news_collector）: URL 正規化、SSRF 対策、XML 安全パース
  - ニューススコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ
  - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - 環境変数の自動読み込み (.env/.env.local) と Settings（kabusys.config）

セットアップ手順（開発環境向け・例）
1. 前提
   - Python 3.10+
   - ネットワークアクセス（J-Quants / OpenAI）および DuckDB（Python パッケージ）を使用可能な環境

2. パッケージのインストール（プロジェクトルートで）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必須パッケージ（例）
     - pip install duckdb openai defusedxml
   - （オプション）プロジェクトのインストール
     - pip install -e .

   ※ 実際の requirements はプロジェクト配布時の requirements.txt / pyproject.toml に従ってください。

3. 環境変数設定
   - プロジェクトルートの .env / .env.local を用意すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須例（.env.example）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - OPENAI_API_KEY=your_openai_api_key
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development

使い方（簡易サンプル）
- 共通準備
  - Python から DuckDB を使う例：
    - import duckdb
    - from kabusys.config import settings
    - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(res.to_dict())

- ニューススコアリング（OpenAI API キーが必要）
  - from kabusys.ai.news_nlp import score_news
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定（OpenAI API キーが必要）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリを自動作成

- 品質チェック（結果は QualityIssue のリスト）
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

設定（主な環境変数）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注系利用時）
- 推奨 / デフォルトあり
  - OPENAI_API_KEY: OpenAI 呼び出しで使用（AI スコアリング）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

注意点・設計メモ（運用上のポイント）
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必須。API 障害時はフェイルセーフで処理継続しますが、結果は欠落する可能性があります。
- jquants_client はレート制御とリトライ、401 時のトークン自動更新に対応しています。ETL は差分更新 + backfill を行います。
- ニュース収集は SSRF 対策や XML パースの安全化（defusedxml）を行っています。
- DuckDB の executemany に関する互換性（空リスト不可）等、実装上の注意が散見されます。実行前に DB スキーマを用意してください（スキーマ初期化関数等を追加実装することを推奨）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（score_news）
    - regime_detector.py         — マクロ+MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                — ETL パイプライン & run_daily_etl
    - jquants_client.py          — J-Quants API クライアント + 保存関数
    - news_collector.py          — RSS 収集 / 前処理
    - calendar_management.py     — 市場カレンダー管理・営業日判定
    - quality.py                 — データ品質チェック（QualityIssue）
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - audit.py                   — 監査ログ DDL / init_audit_db
    - etl.py                     — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility ファクター
    - feature_exploration.py     — 将来リターン / IC / summary / rank
  - ai/, data/, research/ の他に strategy/, execution/, monitoring/（内部モジュール領域）

テスト・モックについて
- OpenAI 呼び出しやネットワーク処理はテストで差し替え可能に設計されています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch）。
- news_collector._urlopen などもモック可能（SSRF 検査を含むネットワーク層の置換）。

貢献
- バグ修正・改善は PR を歓迎します。設計方針（ルックアヘッド回避・冪等性・フェイルセーフ）を尊重してください。

ライセンス
- 本リポジトリに別途 LICENSE ファイルがない場合は、使用・配布はリポジトリ管理者の指示に従ってください（公開プロジェクトにする場合は明記を推奨）。

以上。必要であれば README に「インストール要件の具体的な requirements.txt」「スキーマ初期化 SQL」「実運用向けワークフロー（cron / systemd の例）」などを追記します。どの情報を追加しますか？