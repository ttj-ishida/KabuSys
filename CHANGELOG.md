# Keep a Changelog — 変更履歴

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。日付はリリース日です。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初期リリース — KabuSys v0.1.0

### Added
- 基本的なアプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト
    - 環境に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御。
  - run_monitoring.py: SystemMonitor のポーリング起動スクリプト
    - 環境に関わらず監視用に本番 sqlite_path を使用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグ検知で安全にループ終了。

- 設定管理・セットアップ・検証
  - config.py: Settings クラスによる環境変数ラッパー
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）
    - .env と .env.local の読み込み順序と OS 環境変数保護の実装
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、しきい値など）とバリデーション
  - config_setup.py: 対話式ウィザードによる .env の作成 / 更新
    - シークレット入力のマスク、デフォルト表示、保存前確認などのフローを提供
    - .env を生成する際のテンプレート出力（Git にコミットしない旨の注記）
  - validate_config.py: 起動前検証 CLI
    - 必須環境変数・KABUSYS_ENV の妥当性・DB パスや config/*.yaml の存在と YAML パース検証（PyYAML 利用）、
      本番環境向けの追加ガードを実装
    - --strict モードで警告を失敗扱いにできる

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレーク（signal_rank）で上位 N を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価ベース算出、当日売却予定銘柄を除外可能）
      - "unknown" セクターはセクター上限の対象外
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定
      - 単元株（lot_size）丸め、1銘柄上限 / 集計上限（available_cash）によるスケーリング、
        cost_buffer を考慮した保守的コスト算出、端数処理の再配分ロジックを実装

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代）を設定
    - LOG_DIR/ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみ出力
    - stdout を使用（stderr ではなく）: cron 等からのリダイレクトを考慮
  - utils/process_priority.py
    - Windows と POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定（psutil 利用）
    - CPU affinity 設定ユーティリティ（指定コア数で固定）
    - 権限不足や未対応 OS ではログ警告を出して安全にフォールバック

- 監視関連
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db を起動スクリプトで呼び出し、冪等にテーブルを保証）

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（data/paper_trading.db）を解析して検証レポートを生成
    - 指標: 稼働率(uptime)、注文成立率(fill rate)、送信率(send rate)、API レイテンシ（平均 / 最大 / P95）
    - デフォルト閾値を定義し、PASS/FAIL 判定を出力
    - コマンドライン引数で期間指定および DB パス指定が可能

- リサーチ（骨格）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュール（Momentum/Value/Volatility/Liquidity）
    - calc_momentum 等の実装方針を含む（prices_daily / raw_financials を参照する設計）

- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 に設定

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Notes / Implementation details
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途を想定）。
- PAPER_FILL_MODE の値検証、LOG_LEVEL / KABUSYS_ENV の妥当性チェックなど、設定値のバリデーションを積極的に行う設計。
- run_monitoring は KABUSYS_ENV に関係なく monitoring 用 DB として Settings.sqlite_path（本番想定パス）を使用する。
- run_execution は paper_trading 環境では paper 用 DB に完全分離して記録することを意図している。
- logging_setup はファイル出力失敗時にもプロセスが停止しないようなフォールバックを行う。

---

（将来のリリースではモジュールごとの詳細な変更やバグフィックス、性能改善、テストカバレッジの追加等を追記してください。）