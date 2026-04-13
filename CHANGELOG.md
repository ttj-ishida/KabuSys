# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠し、語調は日本語です。

現在のバージョン: 0.1.0  
リリース日: 2026-04-13

## [0.1.0] - 2026-04-13

### Added
- 初回公開: KabuSys 基本コンポーネントを実装。
  - パッケージメタ情報
    - __version__ を 0.1.0 に設定。
  - 実行エントリポイント
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。プロセス優先度を「high」に設定して起動し、SQLite / DuckDB 接続を確立して監視を実行。監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を使って本番 DB と完全分離して実行。起動時にプロセス優先度を「high」に設定。
  - 設定管理
    - config.py: 環境変数 / .env 自動読み込み機能を実装（.env.local が .env を上書き）。プロジェクトルート検出は .git または pyproject.toml を基準に探索するため、CWD に依存しない。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。多様な環境変数パース（export 構文、クォート、インラインコメント）に対応。Settings クラスに各種プロパティ（DB パス、API トークン、Paper Trading の挙動、監視閾値、PID/KILL フラグパス等）を実装し、値検証（列挙型・閾値等）を行う。
  - モニタリング関連
    - monitoring_db 初期化呼び出しを起動スクリプト側で実行（冪等）。
  - Execution コンポーネント群（起動時に組み立てる主要クラス）
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てロジックを run_execution に実装。RiskConfig により各種リスク閾値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定。ExecutionEngine は session を実行し、DuckDB と SQLite を利用。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全てが 0 の場合に等配分へフォールバック。
    - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジームはログ警告後にフォールバック 1.0。セクター未定義コード("unknown") は上限の適用対象外とする設計。
    - portfolio.position_sizing: allocation_method に応じた発注株数計算(calc_position_sizes)を実装（risk_based / equal / score）。単元株（lot_size）丸め、per-stock/max aggregate cap、cost_buffer を考慮したスケーリング処理、利用可能現金に基づくスケールダウンと残差分の lot 単位調整を実装。
  - ユーティリティ
    - utils.process_priority: プロセス優先度設定と CPU affinity 設定を実装。Windows / POSIX(Linux, Darwin, FreeBSD) の差分を吸収。アクセス権限や未対応 API 発生時は警告ログを出し安全にスキップ。
  - リサーチ / ファクター計算
    - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 経由で実装（prices_daily、raw_financials テーブル参照）。MA200・ATR・20 日平均売買代金等を計算し、データ不足時は None を返す設計。
    - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman ρ）計算(calc_ic)、ファクター統計サマリー(factor_summary)、ランク変換(rank) を実装。pandas 等に依存せず標準ライブラリ＋DuckDB で動作。
    - research.__init__: 外部公開 API を整理（zscore_normalize のエクスポート含む）。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を OpenAI (gpt-4o-mini) でセンチメント評価し ai_scores テーブルへ書き込む処理を実装。複数銘柄をチャンク（最大 20 銘柄）でバッチ送信、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフ付きリトライ、レスポンスバリデーション（厳格な JSON 構造検査）、スコア ±1.0 にクリップ。API キーは引数または環境変数 OPENAI_API_KEY から取得。部分失敗時に既存スコアを保護するため、更新は対象コードに限定して DELETE→INSERT を行う設計。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite DB を解析して検証レポートを標準出力に出力する CLI 実装。対象期間指定（--from/--to）対応。指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。閾値と Pass/Fail 判定（デフォルト閾値をソース内に定義）。DB 存在チェックとエラー時のフォールバック（テーブル欠損時の N/A 表示）を実装。
  - DB 利用
    - DuckDB と SQLite の併用設計（DuckDB は大規模分析向け、SQLite はトランザクションログ等）。起動時に両方の接続を確立し終了時にクローズ。

### Changed
- （設計上の明示）
  - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を参照する（監視データが paper/live に分離されないように統一）。※run_monitoring のドキュメント通り。
  - .env の読み込み優先順位を OS 環境変数 > .env.local > .env として明確化し、OS 環境変数を protected として .env/.env.local からの上書きを防止。
  - Settings における各種環境変数のバリデーションを強化（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。

### Fixed
- 環境変数パーサーでのクォート・エスケープ・インラインコメント処理を改善し、export 構文にも対応することで .env の互換性を向上。
- position_sizing の aggregate スケーリングで端数処理と単元株単位での再配分を実装し、コミット可能コストの過誤を低減。

### Security
- OpenAI API キーは明示的に提供されるか環境変数から取得する仕様とし、未設定時は ValueError を送出して意図せぬ API コールを防止。

---

注記:
- 本 CHANGELOG はコードベースから推測して作成したもので、リリースノートとしての正確性は開発履歴（コミットログ等）に基づく正式文書と比べて劣る可能性があります。正確な変更履歴・担当者情報・影響範囲は実際のコミットログ・リリース手順で補完してください。