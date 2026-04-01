KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買基盤のプロトタイプ実装です。  
主に以下を提供します。
- J-Quants API 経由のデータ取得（株価、財務、マーケットカレンダー）と DuckDB への冪等保存
- ニュース収集と LLM を用いたニュースセンチメント（銘柄別 / マクロ）評価
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- データ品質チェック、監査ログ（signal → order → execution のトレーサビリティ）
- 市場カレンダー管理（営業日判定、next/prev trading day 等）
設計方針の要点
- ルックアヘッドバイアス回避：関数は内部で datetime.today()/date.today() を不用意に参照しない設計
- 冪等性：DuckDB への保存は ON CONFLICT により上書き（再実行可能）
- フェイルセーフ：外部 API（OpenAI / J-Quants）失敗時は適切にフォールバックして継続
- テスト容易性：API 呼び出しや時間依存処理を差し替え可能に実装

主な機能一覧
- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: fetch_* / save_* 系（ページネーション・再試行・レートリミット対応）
- ニュース収集・NLP
  - news_collector.fetch_rss: RSS 取得・前処理・SSRF 対策
  - ai.news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ保存
- 市場レジーム判定
  - ai.regime_detector.score_regime: ETF(1321) MA200 とマクロセンチメントを合成して market_regime に書込
- 研究（Research）
  - research.factor_research: calc_momentum / calc_value / calc_volatility
  - research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- データ品質チェック
  - data.quality.run_all_checks（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー
  - data.calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 監査ログ（トレーサビリティ）
  - data.audit.init_audit_db / init_audit_schema: signal/order/execution テーブル初期化

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10+ を推奨（型ヒントに Union 代替記法等を使用）
2. リポジトリをチェックアウト
   - 例: git clone <repo> && cd <repo>
3. 仮想環境と依存パッケージ
   - 仮想環境作成: python -m venv .venv && source .venv/bin/activate
   - 依存例（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 実行例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt や pyproject.toml があればそちらを使用してください）
4. 環境変数
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（config モジュールがロード時に自動読み込み）。
   - 自動読み込みを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須の主要環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（jquants_client）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注周り）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - AI 関連:
     - OPENAI_API_KEY は score_news / score_regime で使用（関数呼び出し時に api_key を明示して渡すことも可）
5. データベース
   - デフォルトの DuckDB ファイル: data/kabusys.duckdb（settings.duckdb_path）
   - 監視用 SQLite: data/monitoring.db（settings.sqlite_path）
   - 監査ログ専用 DB は data.audit.init_audit_db(db_path) で初期化できます
6. プロジェクトルートの検出
   - config._find_project_root は .git または pyproject.toml を起点に .env を探します。パッケージ配布後も動作するように実装されています。

簡単な使い方（サンプル）
- DuckDB 接続を作り ETL を実行する（対話・スクリプト）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコアの生成（OpenAI API キー必要）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB 初期化
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(Path("data/audit.duckdb"))

- カレンダー操作例
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

設定 / 環境変数（まとめ）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (AI 機能用、関数引数でも渡せる)
- DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL など

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env 自動ロード・設定ラッパ
  - ai/
    - __init__.py
    - news_nlp.py             — 銘柄別ニュースセンチメント評価（OpenAI）
    - regime_detector.py      — マクロ + ETF MA200 を用いた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - calendar_management.py  — マーケットカレンダー管理・営業日判定
    - news_collector.py       — RSS 収集・前処理（SSRF 対策あり）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                — 監査ログ（signal/order/execution）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility 等の計算
    - feature_exploration.py  — forward returns, IC, summary, rank
  - その他（execution/strategy/monitoring 等のパッケージは __all__ で想定）

実装上の注意点（開発者向け）
- API キーの自動リフレッシュや再試行は jquants_client._request に組み込まれている。401 は一度だけトークンリフレッシュを試行。
- OpenAI 呼び出しは各 ai モジュールで独立実装されている（テストで差し替えやすいように内部 _call_openai_api をパッチ可能）。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため空リスト対策をしている箇所がある（news_nlp, pipeline 等）。
- news_collector は SSRF・巨大レスポンス・XML Bomb を考慮して実装済み（defusedxml・レスポンス上限・プライベートIPチェック等）。

よくある運用ユースケース
- 毎日バッチ（夜間）で run_daily_etl を実行してデータを更新
- 朝/取引前に score_news → score_regime を実行して研究・戦略に供給
- strategy 層でシグナルを生成し order_requests と executions を audit テーブルに残す
- 品質チェックを定期実行してデータ問題を検知（CI / Slack 通知等と連携）

トラブルシューティング
- .env が読み込まれない場合: プロジェクトルート判定は .git または pyproject.toml を基準に行われます。KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自分でロードするか、明示的に環境変数をセットしてください。
- J-Quants API の 429/5xx は自動リトライ＋指数バックオフで処理されますが、レート制限に注意してください（120 req/min）。
- OpenAI 呼び出しの失敗は設計上フェイルセーフでゼロスコア等にフォールバックします。テストでは _call_openai_api をモックしてください。

最後に
この README はコードベース（src/kabusys 以下）から主要 API と設計意図を抜粋したものです。詳細な関数仕様・引数・戻り値は各モジュールの docstring を参照してください。README に含める追加の例や運用手順が必要であれば教えてください。