# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。主な変更はコードベースから推測してまとめています。

## [Unreleased]

### Added
- 実行/監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB に分離して MockBrokerClient を利用する動作を想定。起動時にプロセス優先度を High に設定し、停止フラグ（data/stop_requested.flag）や pid ファイル（data/execution.pid）で制御する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視テーブル初期化処理を含む）。

- 設定管理の拡張（kabusys.config）
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込みを追加。
  - .env パースの改善: export 句対応、クォート／エスケープ処理、行内コメントの扱いを実装。
  - OS 環境変数保護（既存の OS 環境変数を上書きしない）と .env.local の上書き機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - 多数の設定プロパティを追加（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値 / LOG_LEVEL / KABUSYS_ENV 等）。PAPER_FILL_MODE の検証（有効値チェック）を実装。

- ポートフォリオ構築ユーティリティ（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等比率・スコア加重の重み計算（calc_equal_weights, calc_score_weights）を追加。スコア全てが 0 の場合は等分配にフォールバック。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing: 株数決定ロジック（calc_position_sizes）を追加。risk_based / equal / score の各配分方式、単元（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的コスト見積り等を実装。

- 監視・実行共通ユーティリティ
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows と POSIX の差分吸収）と CPU affinity 設定ユーティリティを追加。アクセス権限不足等の失敗時は warn でスキップするフォールトトレラント設計。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: DuckDB を用いたモメンタム（mom_1m/mom_3m/mom_6m, MA200乖離）、ボラティリティ（ATR20, 相対ATR, 20日平均売買代金, 出来高比率）、バリュー（PER/ROE）ファクター計算関数を実装。SQL ベースで営業日ウィンドウを考慮。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンのランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）を実装。外部ライブラリに依存しない純粋 Python 実装。

- AI ニュース NLU（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI API（gpt-4o-mini）でセンチメント評価して ai_scores に書き込む処理を追加（score_news, calc_news_window 等）。時間ウィンドウ計算、バッチ送信（銘柄ごと最大 _BATCH_SIZE）、エラーハンドリング（429/タイムアウト/5xx の指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）等の設計方針を実装。
  - （注）ファイル末尾が切れているため score_news の内部処理の一部は途中で終わっています。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（P95 含む）を出力し、閾値に基づく PASS/FAIL 判定を行う。P95 計算ロジックと SQL フィルタリングを実装。

- パッケージ初期化 / エクスポート整理
  - kabusys.__init__ に __version__ を追加（"0.1.0"）。portfolio / research の __all__ エクスポートを整備。

### Changed
- DB の利用ポリシーを明示
  - 監視(run_monitoring) は環境に関係なく本番 sqlite_path を使用する仕様を明記（監視データは本番 DB を参照/書き込み）。
  - 実行(run_execution) は paper_trading モード時に paper_sqlite_path を使用して本番 DB と完全分離する動作を実装。

- ExecutionEngine 起動フロー
  - ExecutionEngine はスレッドで起動し、停止フラグをポーリングして安全に停止させる仕組みを採用。起動前に監視テーブル初期化処理（監視DBスキーマの冪等初期化）を呼ぶように変更。

### Fixed
- .env パーサの堅牢性向上
  - export 句・引用符内のバックスラッシュエスケープ・インラインコメントなどの正しい処理を実装し、環境変数読み込みの誤動作を防止。

## [0.1.0] - 2026-04-17

初期リリース（コードベースから推測）。
- 基本的な自動売買システムのコア機能を追加:
  - 設定管理（.env 自動ロード、各種環境設定プロパティ）
  - 実行エンジン起動スクリプト / 監視ポーリングスクリプト
  - ポートフォリオ構築（選定、重み付け、リスク調整、ポジションサイズ計算）
  - リサーチ（ファクター計算、将来リターン、IC、統計サマリ）
  - AI ニューススコアリング（OpenAI 統合の設計と一部実装）
  - 運用ツール（Paper Trading 検証レポート生成）
  - プロセス優先度/CPU 固定ユーティリティ

### Notes / 注意事項
- AI ニュース処理モジュールの score_news はファイル末尾が切れており、記事フェッチや API 呼び出し結果の最終処理（DuckDB への書き込み）が途中の状態であるため、そのまま運用するには未完成箇所の補完が必要です。
- run_monitoring/run_execution はファイルベースの停止フラグ・PID 管理を前提としており、実行環境のファイルパス（data ディレクトリ等）が存在することを前提としています。
- .env 自動ロードはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（将来的に変更履歴を充実させる際は、個々のコミットや PR 単位で Added/Changed/Fixed/Removed/Deprecated/Security に分類して追記してください。）