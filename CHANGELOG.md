# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

### Added
- factor_research モジュールのファクター計算ロジックの実装を継続中（モメンタム等の定義・定数は追加済み）。実装未完の関数が一部存在するため、引き続き完成させる予定。

### Changed
- ドキュメントやログメッセージの補足・整理（内部説明の明確化、TODO の明示化）。

### Known issues / TODO
- portfolio.position_sizing: 将来的な拡張として銘柄ごとの単元（lot_size）をマスタで持たせる旨の TODO が残る。
- portfolio.risk_adjustment: 価格が欠損（0.0）の場合のフォールバック戦略が未実装（注記あり）。
- research.factor_research: ファイル途中で実装が途切れている（未完）。

---

## [0.1.0] - 2026-04-23

初回リリース。

### Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用（モック）ブローカークライアントを使用し、Paper Trading 用 DB を分離して利用する（デフォルト: data/paper_trading.db）。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - 停止フラグ（data/stop_requested.flag）および PID 管理（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知で安全にループを抜け、DB 接続をクローズする。

- 設定関連 CLI / ユーティリティ
  - config_setup.py
    - 対話式 .env 作成ウィザード。シークレット入力のマスク、既存値の再利用、.env ファイル書き出し機能を提供。
  - validate_config.py
    - .env と config/*.yaml の静的検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML 未インストール時は警告）等を実行。
    - --strict モードで警告を FAIL 扱いにできる。

- 環境設定 / ローダ
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出済みなら .env → .env.local の順に読み込み、既存 OS 環境変数を保護）。
    - .env パーサは export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスで各種環境変数をプロパティ経由で取得（デフォルト値・バリデーションを付与）。PAPER_FILL_MODE 等の値チェックを実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - 既存ハンドラの二重設定防止処理。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームの優先度設定（Windows の priority class と POSIX の nice 値を吸収）。
    - CPU affinity を設定するユーティリティも提供。権限不足や未対応 OS へのフォールバック処理あり。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限により新規候補を除外するフィルタを実装（unknown セクターは制約対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を想定、未知値はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）に基づくスケールダウン、cost_buffer（手数料・スリッページ見積）を考慮した保守的計算を実装。
    - スケーリング時に残差を lot 単位で配分するロジックを備える。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを出力。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - しきい値（uptime >= 99%、fill_rate >= 90% など）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）に対応。

- モニタリング DB 初期化ユーティリティ呼び出し
  - run_execution/run_monitoring から監視テーブル初期化（init_monitoring_db）を呼び出し、冪等に監視テーブルの存在を保証。

### Changed
- ログ出力の統一
  - 全エントリポイントから setup_logging を呼び出す設計によりログの出力先とフォーマットを統一。

- DB パスの分離方針
  - Paper Trading 実行時は paper_sqlite_path を使用して本番 DB と完全分離する方針を明示。

### Fixed
- .env 読み込みでの既知の落とし穴に対応
  - export プレフィックス、クォート、エスケープ、インラインコメントなどの取り扱いを強化。

### Documentation
- 各モジュールに日本語の docstring・使用例・設計注記を追加。設計上の注釈（参照ドキュメント、PortfolioConstruction.md/StrategyModel.md 等）や TODO を明示。

### Known issues / Caveats
- logging_setup: ログディレクトリ作成失敗時はファイル出力を行わず stdout のみで継続するが、その際にファイル出力が必要な運用では注意が必要。
- process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームでは設定が失敗し警告が出力される（挙動は安全にフォールバック）。
- portfolio.position_sizing:
  - price が欠損（0 または None）の銘柄はスキップされる。将来的に前日終値等のフォールバックを検討する旨の注記あり。
  - 銘柄別の lot_size を想定した拡張は未実装（TODO）。
- research.factor_research: 一部実装が未完（ファイル末尾で処理が途中になっている）。今後のリリースで完成予定。

---

特記事項:
- パッケージバージョンは __init__.py にて 0.1.0 に設定されています。初回リリース後、機能追加やバグ修正を反映したセマンティックバージョニングでの更新を行ってください。