# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

すべてのリリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

初期リリース。KabuSys の基本機能群（設定管理、起動スクリプト、ログ設定、プロセス管理、ポートフォリオ構築、ポジションサイズ計算、ペーパートレード検証ツール、監視・実行エンジンの起動補助など）を実装しました。

### Added
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - .env 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml で探索して検出）。
  - .env のパースロジックを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い等）。
  - 読み込み優先度: OS 環境 > .env.local > .env。自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを実装し、環境変数アクセスとバリデーションを提供（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の検証を含む）。
  - `settings` インスタンスをモジュールレベルで公開。

- 設定用ユーティリティ / CLI
  - 対話式 `.env` 作成・更新ウィザード (`kabusys.config_setup`) を実装。既存値の読み込み、選択肢、シークレット項目の取り扱い、保存機能を提供。
  - 起動前チェック CLI (`kabusys.validate_config`) を実装。必須環境変数チェック、KABUSYS_ENV 検証、DB パス・YAML 設定ファイルの存在チェック、--strict モードをサポート。PyYAML 未導入時は YAML チェックをスキップして警告を出す。

- 起動スクリプト
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得（デフォルト 60 秒、無効値は警告出力の上デフォルトにフォールバック）。
    - 起動時にプロセス優先度を "high" にセット。
    - 監視は本番用の sqlite_path を参照（KABUSYS_ENV に依存しない）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全終了。
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite DB（data/paper_trading.db、または環境変数で上書き）を使用し、本番 DB と完全分離。
    - プロセス優先度設定（"high"）および PID ファイル管理。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成し、ExecutionEngine を別スレッドで実行。停止フラグによりエンジンを停止可能。

- ロギング
  - 共通のログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout への StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
    - 既存ハンドラの二重設定を防止するため、再設定時は既存ハンドラを一旦クリア。
    - ログディレクトリは引数 / 環境変数 LOG_DIR / デフォルト "logs/" の順で解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス管理ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows と POSIX（Linux / macOS 等）の差分を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
    - CPU アフィニティを設定する `set_cpu_affinity` を追加（利用可能なコア数より大きい指定は全コア使用にフォールバック）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder` を実装。
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。スコア合計が 0 の場合は等金額配分にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment` を実装。
    - セクター集中制限を適用する apply_sector_cap（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。
    - 市場レジームに応じた乗数を返す calc_regime_multiplier（bull/neutral/bear をサポート、未知はフォールバックで 1.0）。
  - `kabusys.portfolio.position_sizing` を実装。
    - 複数の配分方法に基づく発注株数計算（allocation_method: "risk_based", "equal", "score"）。
    - 単元（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応、残差処理による端数配分の論理を実装。

- 監視 / 実行用 DB 初期化
  - `init_monitoring_db`（監視用テーブルの冪等初期化）を run_monitoring/run_execution から呼び出す仕様で組み込み。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report` を実装。
    - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH または引数 --db）からデータを集計して検証レポートを生成。
    - 指標: 稼働率 (uptime_pct)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg, max, P95）。
    - 判定閾値（稼働率>=99%、成功率>=90%、送信率>=95%、P95<=200ms）に基づき PASS/FAIL を判定。
    - 日付フィルタ (--from / --to) をサポート。

- 研究（ファクター計算）モジュール（初期実装）
  - `kabusys.research.factor_research` を追加。モメンタム・ボラティリティ・流動性等を計算する設計方針と定数を定義。モメンタム計算関数（calc_momentum）を実装途中（設計と一部処理を追加）として含む。

- その他
  - ユーティリティパッケージ構成（__all__ 等）や各モジュールのエクスポートを整備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- run_monitoring は監視データ保存に常に production の sqlite_path を使用する仕様で、環境変数 KABUSYS_ENV に依存しません。これにより監視データは本番 DB に一元化されます。
- run_execution は paper_trading 環境では paper_sqlite_path を使用して発注・ログを本番 DB から分離します。
- .env のパースは実運用でよくあるケース（export プレフィックス、クォート、エスケープ、インラインコメント）に対応するようかなり厳密に実装しています。特殊ケースでの振る舞いは .env の取り扱いに注意してください（特にクォート内のエスケープやコメント解釈）。
- ログは stdout に出力するようにしているため、cron や外部ジョブスケジューラで stdout/stderr を統合している運用に適しています。
- process_priority / set_cpu_affinity は権限が必要な操作を伴う可能性があるため、実行環境の権限に依存して失敗する可能性があります。失敗時は警告を出して処理を継続します。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出ロジックと正常系テスト）
- ExecutionEngine / BrokerClient の追加テストと Paper/Live の統合テスト
- 運用性向上のための監視アラート（LINE 通知等）実装
- 各モジュールのユニットテストとドキュメントの整備

（必要であれば、各変更点の詳細な差分・設計意図・運用上の注意点を別途ドキュメント化します。）