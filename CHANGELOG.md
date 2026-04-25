# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

現在のバージョン: 0.1.0（初回リリース）

## [Unreleased]
- 特になし

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーションと CLI
  - 実行スクリプト
    - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用して本番 DB と分離して動作する。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルの存在検知で行う。
  - 設定関連
    - config_setup: 対話式 .env ウィザード。初期 .env を生成・更新する機能を提供（.env を絶対にコミットしないよう注意喚起を出力）。
    - validate_config: .env および config/*.yaml の存在・簡易整合性検証 CLI。--strict オプションで警告を失敗扱いにできる。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を行う。
- 設定管理（kabusys.config）
  - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。優先度は OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの強化: export プレフィックス、シングル/ダブルクォート中のエスケープ、インラインコメントの扱いをサポート。
  - Settings クラスを実装し、各種環境変数（DB パス、API トークン、監視閾値、PAPER_FILL_MODE 等）をプロパティとして提供。PAPER_FILL_MODE の有効値チェックを実装。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: position サイズ決定ロジック（calc_position_sizes）。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）単位で切り捨て・スケール調整する機能を実装。aggregate cap（available_cash で総投資額を調整）や cost_buffer（手数料・スリッページの保守見積）に対応。
- ロギング/プロセス周りのユーティリティ
  - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。LOG_DIR/LOG_LEVEL の環境変数に対応。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils.process_priority: Windows / POSIX（Linux/macOS/FreeBSD）向けにプロセス優先度（high/normal/low）設定と CPU affinity 設定を提供。psutil が提供する定数差異を吸収し、権限不足等の失敗は警告ログで無効化する。
- research.factor_research（骨組み）
  - Momentum、Value、Volatility、Liquidity などのファクター計算設計と calc_momentum の実装（計算対象・ウィンドウ等の定義）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを用いて計算する方針。
- 監視（monitoring）との統合
  - init_monitoring_db 呼び出しで監視テーブルの存在を保証（冪等）。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計を採用（監視データは本番 DB に集約）。
- Paper Trading 検証基準の導入
  - tools.paper_verification_report にて、稼働率、注文成功率、送信率、P95 レイテンシなどの閾値（例: 稼働率 >= 99.0%、P95 <= 200ms 等）を定義し、PASS/FAIL を出力。

### Changed
- 多くの起動スクリプトで起動直後にプロセス優先度を "high" に設定するようにした（set_process_priority を呼び出し）。これにより実運用時の優先度を明示。
- logging_setup: コンソール出力を stderr ではなく stdout に変更（Task Scheduler/cron 等でのログリダイレクトを考慮）。
- run_execution: エンジン起動前に停止フラグの存在を確認し、既に停止フラグがある場合は起動を回避する安全措置を導入。
- run_monitoring: 環境変数 MONITOR_POLL_INTERVAL の読み取り処理を追加（不正値は警告を出してデフォルト 60 秒にフォールバック）。

### Fixed
- ログディレクトリ作成失敗時にアプリが致命的に停止しないようにファイルハンドラ作成を保護（stream-only フォールバック）。
- .env 読み込み時に発生しうるファイル読み取りエラーを警告化して処理継続するよう改善。

### Notes / Known limitations
- price の欠損時の取り扱い:
  - risk_adjustment.apply_sector_cap および position_sizing.calc_position_sizes 内で price が 0 や欠損の場合に一部処理がスキップされるコメント付き TODO が残っており、前日終値や取得原価でのフォールバック実装が未着手。
- research.factor_research の calc_momentum 実装はファイル末尾で切れている（断片が存在）ため、完全実装や追加ファクターの細部は今後の作業が必要。
- 一部外部ライブラリ（duckdb、psutil、PyYAML など）が必須または任意で必要。validate_config は PyYAML 不在時に YAML 検証をスキップして警告を出す。
- PAPER_FILL_MODE の不正値は Settings で ValueError を発生させるため、環境変数の設定に注意が必要。
- Paper Trading 用 DB と監視 DB を明確に分離しているが、運用上の DB バックアップや権限管理については運用ドキュメント整備が必要。

### Upgrade notes
- 初回リリースのため後方互換性の問題はなし。既存の .env を使用する場合は validate_config を実行して警告・エラーを事前チェックすることを推奨。
- 自動ロードされる .env の挙動を無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

作成者注:
- この CHANGELOG は提示されたコードベースから機能・設計意図を読み取り推測して作成しています。実際の変更履歴（コミットログ）と差異がある可能性があります。必要であればコミット履歴ベースの正確な CHANGELOG 生成を手伝います。