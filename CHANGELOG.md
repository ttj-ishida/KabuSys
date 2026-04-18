# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
日付はリポジトリ内の参照（2026年）に合わせて記載しています。

## [Unreleased]

- ドキュメント化・コード整備:
  - factor_research モジュールが途中で切れている箇所を検出。今後のリリースで実装継続予定（ファイル末尾が不完全）。
- 注意事項:
  - 一部のファイル・関数には TODO コメントや将来の拡張案が残っています（例: position_sizing の lot_size 銘柄別対応、risk_adjustment の価格フォールバック）。

## [0.1.0] - 2026-04-18

### Added
- 基本機能・モジュールを初期実装
  - 実行用エントリポイント
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプト。
      - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB (data/paper_trading.db) を使用し、MockBrokerClient（BrokerClientFactory 経由）により本番 DB と分離して動作する設計。
      - エンジンはバックグラウンドスレッドで run_session を実行し、data/stop_requested.flag の検出で安全に停止する仕組み。
      - 起動時にプロセス優先度を "high" に設定するフローを組み込み。
      - Execution 用 PID ファイル管理 (data/execution.pid)。
      - RiskManager 用の既定パラメータ (max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20) を設定し、initial_portfolio_value をブローカーから取得する実装。
  - 監視用エントリポイント
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動用スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化・記録する設計。
      - 停止フラグ (data/stop_requested.flag) による安全停止、KeyboardInterrupt のハンドリング、例外ログの捕捉を実装。
  - 設定管理
    - config.py
      - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env / .env.local の読み込み順と保護（OS 環境変数を上書きしない）を実装。
      - 複雑な .env パース対応（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
      - Settings クラスで各種設定値をプロパティとして提供（J-Quants / kabu API トークン、DB パス、paper trading 関連、監視閾値、環境 KABUSYS_ENV のバリデーションなど）。
      - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH の取り扱いを実装。
  - 設定支援 CLI
    - config_setup.py
      - 対話式ウィザードで .env を初期作成／更新するツール。
      - 秘匿値のマスク表示、選択肢提示、既存値の読み込み、生成テンプレートの書き出しを提供。
      - デフォルトや説明文を含む整形された .env 出力。
    - validate_config.py
      - 起動前チェックツール。必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML があればパース検証）を実行。
      - --strict モードで警告を失敗扱いにできる。
      - 本番環境向けガード（LINE 設定未指定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を実装。
  - ロギング／プロセス制御ユーティリティ
    - utils/logging_setup.py
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定するユーティリティ。
      - LOG_LEVEL / LOG_DIR の解決順、ログディレクトリ作成のフォールバックを実装。
    - utils/process_priority.py
      - psutil を用いたプロセス優先度設定（Windows / POSIX に対応）と CPU affinity 設定ユーティリティ。
      - アクセス権限や未対応 OS に対する安全なフォールバック（警告出力）を実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナル選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の際は等配分へフォールバックして警告。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap を実装（当日売却予定銘柄を除外できる）。
      - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
    - portfolio/position_sizing.py
      - allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出ロジックを実装。
      - 単元株（lot_size）丸め、1銘柄上限・集計キャップ（available_cash）スケーリング、cost_buffer による保守的見積りを実装。
      - aggregate cap のスケーリングで残余キャッシュを考慮し fractional 残差に基づく追加配分ロジックを用意。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - PAPER_TRADING_SQLITE_PATH（または --db）を指定してレポートを生成する CLI。
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等を算出して PASS/FAIL 判定を行う。
      - P95 計算、日付フィルタ、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 ≤ 200ms）を実装。
  - research/factor_research.py（部分実装）
    - DuckDB を用いたファクター計算の枠組みを導入（モメンタム・MA200・ATR 等を想定）。設計ドキュメント参照の旨を記載。

### Changed
- なし（初回リリース）

### Fixed
- いくつかの堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値を警告してデフォルトにフォールバックする実装（run_monitoring）。
  - ログディレクトリ作成やファイルハンドラ生成で失敗した場合にコンソール出力にフォールバックする実装（logging_setup）。
  - .env 読み込みでファイルオープン失敗時に警告を出して継続する実装（config.py）。

### Deprecated
- なし

### Removed
- なし

### Security
- 既定では秘匿情報は .env に保持し .env を Git に絶対にコミットしない旨を config_setup のテンプレートに明記。
- config_setup では秘匿項目を対話中にマスク表示する等、秘匿情報取り扱いに配慮。

---

注記:
- 本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴や CHANGELOG の運用方針に応じて適宜更新してください。