CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点のリリースはありません）

## [0.1.0] - 2026-04-13

Added
- 初回公開リリース。
- 全体
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
- 実行系 / デーモン
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するランナー。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 不正な値（0 以下・非整数）はログに警告を出してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定する（utils.process_priority を使用）。
  - run_execution.py を追加。ExecutionEngine を起動するランナー。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading 時はモッククライアントが利用される想定）。
    - ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager の初期化と run_session 呼び出しを実装。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境読み込み
  - config.Settings を実装。
    - .env ファイル自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーは `export KEY=val` 形式、クォート、エスケープ、行末コメントの扱い等に対応。
    - 必須変数取得用の _require() を実装（未設定時に ValueError）。
    - 各種設定プロパティを実装（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEMORY/DISK 閾値 等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）。
- モニタリング・ツール
  - monitoring_db 初期化呼び出しを runners から行う（init_monitoring_db を用いて冪等に監視テーブルを保証）。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 向け検証レポート生成 CLI。
    - 日付フィルタ（--from / --to）対応。
    - DB パス指定は --db オプション / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの順に解決。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ 等を集計し、閾値（PASS/FAIL）判定を出力。
    - SQL 実行時にテーブルが存在しない場合でも安全にハンドリング（OperationalError をキャッチして N/A 扱い）。
- ポートフォリオ構築
  - portfolio.portfolio_builder: BUY シグナルからの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックし WARNING を出す。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は売却予定コードを除外して既存エクスポージャーを計算。未知セクター("unknown")は上限の対象外。
    - calc_regime_multiplier は 'bull'/'neutral'/'bear' を 1.0/0.7/0.3 にマッピングし、未知値はワーニングを出して 1.0 にフォールバック。
  - portfolio.position_sizing: 発注株数算出ロジック（calc_position_sizes）を実装。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - lot_size 単位での丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash でスケールダウン）、cost_buffer（手数料・スリッページ想定）を考慮。
    - 不正な価格データはスキップしてログ出力。
- リサーチ（duckdb ベースのファクター計算）
  - research.factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出。
    - 欠損・データ不足時の扱い（条件付きで None を返す）を明記。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンを複数ホライズンで算出（SQL で LEAD を利用）。
    - calc_ic: Spearman（ランク相関）ベースの IC を実装（レコード数が不足する場合は None）。
    - rank, factor_summary: ランク付け・統計サマリユーティリティを提供。
  - research パッケージの __all__ を整備して主要機能をエクスポート。
- AI / ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングして ai_scores に書き込むモジュールを追加。
    - ニュースウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 銘柄ごとに記事を集約し、1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズ 20 銘柄で API 呼び出しを行い、429/接続エラー/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密な JSON 検証、スコアを ±1.0 にクリップ、部分成功時は対象コードのみ置換してテーブル更新（DELETE → INSERT の形で保護）。
    - OpenAI API キー未指定時は ValueError を送出。
    - 実装方針としてルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度・CPU affinity 設定を提供。
    - Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX 系（Linux/Mac/FreeBSD）の nice 値を吸収。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能。権限不足や未対応 OS の場合は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count) で先頭 N コアに固定可能。引数検証・権限エラーを適切にハンドリング。

Changed
- 初回リリースのため過去の変更なし。

Fixed
- .env パーサーの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、クォートなし時の '#' コメント解釈などに対応。
- SQLite / DuckDB 接続について:
  - monitoring 用 DB 初期化を冪等に行う（init_monitoring_db を runners で呼び出し）。

Security
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。`.env.local` の override 時でも OS 環境は上書きされない。

Notes / Known limitations
- 一部関数は外部リソース（DuckDB の prices_daily/raw_financials、ブローカークライアント等）に依存するため、実行には適切なデータベーススキーマや外部クレデンシャルが必要。
- calc_position_sizes の price 欠損時のフォールバックは将来的な改善（前日終値や取得原価の利用）をコメントで示しています。
- ai.news_nlp は OpenAI API 呼び出しを伴うため、API 使用料およびレート制限に注意してください。

---

リリースに関する問い合わせや不具合報告はリポジトリの issue へお願いします。