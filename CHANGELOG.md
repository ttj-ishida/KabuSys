# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本リリースはソースコードから推測した初期機能・挙動のまとめです。実装上の注記や既知の制約も併せて記載しています。

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開用のトップレベル __all__ を設定。

- 環境設定・ローディング（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（"#" の前がスペース/タブの場合のみコメントとみなす）。
  - Settings クラスを提供し、環境変数の取得・型変換・妥当性検証を集中管理:
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - 環境（KABUSYS_ENV: development/paper_trading/live）
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - 監視用しきい値（CPU/MEMORY/DISK）や PID / kill flag のパス等

- 実行ランナー
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 起動前または実行中に停止フラグを検知すると安全に停止処理を実行。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine に PID ファイルパスを渡す（data/execution.pid 等）。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装し、Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収。
  - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定可能。
  - アクセス権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）で選出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率での重み付け。全てのスコアが 0.0 の場合は等配分にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: 既存保有からセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバックし警告を出す。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算。
    - 単元株（lot_size）で丸め、per-position 上限と aggregate cap を実装。投資総額が利用可能現金を超える場合はスケールダウンし、残余キャッシュで残差に基づく再配分を行う。
    - cost_buffer（手数料・スリッページ見積り）を考慮して保守的に算出。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（ウィンドウの行数が不足する場合は None）を DuckDB SQL で計算。
    - calc_volatility: ATR20, 相対 ATR, 20日平均売買代金, 出来高比率を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新報告期間を参照）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons の妥当性チェックあり（1..252）。
    - calc_ic: Spearman ランク相関（IC）を計算。有効サンプルが 3 未満の場合は None。
    - rank / factor_summary: ランク生成（同順位は平均ランク）と主要統計量（count/mean/std/min/max/median）を純粋 Python 実装（pandas 非依存）。
  - DuckDB を用いて prices_daily / raw_financials テーブルから集計を実行する設計。

- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析フローを実装（注: ファイル末尾は切れているがコアロジックを含む）。
  - 機能要点:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づく記事収集（UTC 換算）。
    - 銘柄ごとに記事を集約し、1 銘柄あたりの最大記事数・文字数でトリム。
    - 最大 _BATCH_SIZE（20）銘柄ずつバッチ送信、JSON Mode で厳密な JSON レスポンスを期待。
    - 429/ネットワーク/タイムアウト/5xx はエクスポネンシャルバックオフでリトライ（上限 _MAX_RETRIES）。
    - レスポンスバリデーション・スコアクリッピング（±1.0）。
    - 部分更新（対象コードのみ削除→挿入）で既存スコアを保護する設計。
    - OpenAI API キーが未指定の場合はエラーを返す。

- ツール類
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI。
    - オプション: --from / --to（YYYY-MM-DD）、--db（DB パス）。
    - 評価指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - デフォルト DB パスは data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
    - テーブル欠落やデータ不足に対して堅牢（OperationalError をキャッチして N/A を返す）。

- DB 初期化補助
  - monitoring テーブルの存在を保証する init_monitoring_db がランナーから呼び出される（冪等）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- .env パーサの堅牢化:
  - クォート内のエスケープや export プレフィックス、インラインコメントの扱いを改善して実運用での .env 設定ミス耐性を向上。

### Known issues / Notes / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価でフォールバックする案が示されている。
- ai.news_nlp のファイルは末尾が切れている（コード断片で終了）。実運用前に完全実装／単体テストが必要。
- duckdb/SQLite のスキーマ依存: 特定テーブル（prices_daily, raw_financials, system_status, trade_logs, risk_logs, ai_scores, raw_news, news_symbols 等）が存在することを前提としている。ツールはテーブルがない場合に一部 N/A で動作するが、完全機能のためには適切なスキーマ準備が必要。
- run_monitoring は監視用 DB を本番 sqlite_path に固定して利用するため、監視用途での DB 分離が不要であることを想定している（paper_trading 環境でも同様）。
- set_process_priority / set_cpu_affinity は権限や OS に依存する操作のため、実行環境によっては警告を出してスキップされる。

---

以上。必要であればセクションの追記（セキュリティ、互換性、マイグレーション手順など）や、未実装箇所の詳細な課題一覧を追加します。どの形式で追記しますか？