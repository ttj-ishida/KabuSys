# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。日付はリポジトリ内の現在のコード状態から推測して記載しています。

## [Unreleased]
- 開発中の変更点や未リリースの改善点をここに記載してください。

---

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。監視・実行・設定管理・ポートフォリオ構築・各種ユーティリティ・検証ツールを含みます。

### Added
- 全体
  - パッケージ初期バージョンを追加（`__version__ = "0.1.0"`）。
  - モジュール構成を整備：execution, monitoring, portfolio, research, utils, tools など。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するランチャーを追加。
    - KABUSYS_ENV が `paper_trading` の場合、実運用 DB と完全に分離されたペーパートレーディング用 SQLite（`data/paper_trading.db`、`PAPER_TRADING_SQLITE_PATH` で上書き可）を使用するロジックを実装。
    - BrokerClientFactory を用いて環境に応じたブローカークライアント（MockBrokerClient を含む）を作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。data/execution.pid、data/stop_requested.flag による起動・停止制御を備える。
    - RiskManager の既定設定値（max_position_pct 等）を実装し、初期ポートフォリオ値を broker.get_available_cash() で取得して投入。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するランチャーを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）、値検証とフォールバック実装。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用する設計（監視データの一元管理）。

- 設定管理
  - config.py
    - 環境変数ラッパー `Settings` クラスを追加。多数の設定プロパティを提供（J-Quants, kabuAPI, DB パス, 各種閾値, 環境判定ロジック等）。
    - `.env` 自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env の行パーサは `export` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - `paper_fill_mode` の検証（有効値: instant/partial/never/reject）や `KABUSYS_ENV` / `LOG_LEVEL` の検証を行い、不正な値は例外を送出。

  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。既存値の読み込み、シークレットマスク表示、選択肢・デフォルトの提示、保存確認機能を提供。
    - 書き出しはテンプレート化されたコメント付き `.env` を生成（Git コミット禁止の注意書きあり）。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース確認（PyYAML 未インストール時は警告）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）用の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築（pure function）
  - portfolio.portfolio_builder
    - 候補選定（score 降順、同点時 tie-breaker）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額へフォールバック）を実装。

  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が閾値を超える場合、同一セクターの新規候補を除外）。
    - レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知は 1.0 にフォールバック）。

  - portfolio.position_sizing
    - position size 計算を実装。`risk_based`, `equal`, `score` の各配分方式に対応。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash でスケールダウン）、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジックなどを実装。

- ユーティリティ
  - utils.logging_setup
    - グローバルなログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、既存ハンドラのクリア・再設定やログディレクトリ作成失敗時のフォールバックに対応。
    - ログレベル・ログディレクトリの解決順序や 30 日保持などを実装。

  - utils.process_priority
    - Windows / POSIX（Linux/Mac 等）の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。psutil を利用、権限不足時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足や未対応環境は警告でスキップ）。

- 監視・モニタリング
  - run_monitoring および SystemMonitor / monitoring_db（参照）により、定期ポーリングで system_status 等のテーブルを更新する仕組みを用意（DB 初期化用 init_monitoring_db が呼ばれる）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成ツールを追加。SQLite（PAPER_TRADING_SQLITE_PATH / --db）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、PASS/FAIL 判定（閾値はソース内定義）で出力。
    - CLI オプションで期間指定（--from/--to）や DB 指定が可能。
    - P95 算出、SQL の日付フィルタ生成、データ欠損時の graceful handling を実装。

- 研究（研究用ファクタ計算）
  - research.factor_research（モメンタム等の計算を開始）
    - DuckDB を用いたファクター計算モジュールを追加（モメンタム等を計画）。（注：ファイル末尾が途中で切れているため実装の続きが必要）

### Changed
- （初回リリースのため過去変更はなし）

### Fixed
- （初回リリースのため修正項目はなし）

### Notes / Important behavior
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、配布後やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
- run_monitoring は説明コメントの通り、監視データベースは KABUSYS_ENV に依存せず本番用 sqlite_path を参照する。運用時は意図に注意してください。
- run_execution は paper_trading を明示的に分離する設計。ただし broker の実装によっては追加の差分が存在します（BrokerClientFactory に依存）。
- utils.logging_setup はログディレクトリ作成に失敗した場合でも stdout ログは確実に出力されるよう設計されています。
- 設定検証ツール（validate_config）は PyYAML 未導入時に YAML の中身チェックをスキップしますが、存在チェックは行います。

---

今後の予定（参考）
- research.factor_research の未完了部分の実装完了。
- テストケースの追加（ユニット/統合）。
- strategy / execution の詳細な実装とドキュメント整備。
- モニタリングとアラート送信（LINE 連携）等の統合テストと運用ドキュメント作成。