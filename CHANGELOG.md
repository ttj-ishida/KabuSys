# Changelog

すべての重大な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はソースコードの状態に基づき記載しています。

## [0.1.0] - 2026-04-18

### Added
- コア: パッケージ初期リリース相当の機能群を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を設定。
  - パブリック API エクスポート: portfolio 関連関数をトップレベルで公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。
- 実行スクリプト:
  - `run_execution.py`: ExecutionEngine 起動スクリプトを追加。
    - Paper trading モード時は専用の SQLite（`data/paper_trading.db` デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、EngineConfig を用いて ExecutionEngine を起動。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）に対応。プロセス優先度を「high」に設定する仕組みを導入。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ検知でループを終了。プロセス優先度を「high」に設定。
- 設定管理:
  - `config.py`: 環境変数読み込み・ラッパー Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の読み込み順: OS 環境 > .env.local > .env。自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 多数の設定プロパティ（J-Quants / kabu API / DB パス / PID や閾値パラメータ / 環境判定など）を提供。値検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を実装。
- 設定支援ツール:
  - `config_setup.py`: 対話式 .env ウィザードを追加。
    - 主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話入力で生成・更新できる。
    - 既存 .env 読み込み、マスク表示、保存機能を実装。
- 設定検証:
  - `validate_config.py`: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証、本番時の追加ガードチェックを実装。
    - `--strict` モードで警告を FAIL 扱いにできる。
- ロギング・ユーティリティ:
  - `utils/logging_setup.py`: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（デフォルト logs/、30 日保持）をルートロガーに設定。
    - 環境変数または関数引数でログレベル・ログディレクトリを制御可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス制御ユーティリティ:
  - `utils/process_priority.py`: プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定を追加。
    - Windows / POSIX(nice) を考慮した優先度設定 (`high`/`normal`/`low`)。
    - CPU affinity を最初の N コアに固定する機能を提供（権限不足等は警告でスキップ）。
- ポートフォリオ構築（純粋関数群）:
  - `portfolio/portfolio_builder.py`:
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等分配にフォールバックして警告を出力。
  - `portfolio/risk_adjustment.py`:
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - unknown セクターは上限適用除外、未知レジームは 1.0 にフォールバックして警告。
  - `portfolio/position_sizing.py`:
    - 発注株数計算ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）による aggregate cap まで考慮。
    - aggregate スケーリング時に端数の再配分ロジックを導入（安定な順序で lot 単位を割り当て）。
    - TODO コメントで将来の拡張（銘柄別 lot_size 等）を明記。
- Paper trading 検証ツール:
  - `tools/paper_verification_report.py`:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計し、PASS/FAIL 判定付きレポートを出力する CLI を追加。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）を定義。
    - 日付フィルタ、--db オプションをサポート。
- 解析 / リサーチ:
  - `research/factor_research.py`（ファクター計算モジュール）を追加。
    - Momentum / Value / Volatility / Liquidity の設計方針を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。モメンタム計算周りの定数と関数スケルトンを含む。
    - 注: ファイルは途中まで実装されている（calc_momentum の実装が途中で切れている）。今後の実装継続予定。
- DB 初期化:
  - `monitoring/monitoring_db.init_monitoring_db`（参照）を呼ぶことで監視用テーブルの冪等な初期化が行われることを前提に実装。
- 外部依存:
  - DuckDB（分析用）と sqlite3（状態・監視・paper DB）を併用する設計を導入。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注意事項・既知の制約:
- research/factor_research.py はまだ途中実装（calc_momentum が中断）です。完全実装は今後のリリースで対応予定。
- position_sizing の price フォールバック（price が 0 の場合の扱い）や銘柄別 lot_size は TODO として残っています。
- 設定に関する自動読み込みは .git / pyproject.toml が見つかった場合にのみ動作します。自動ロードが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本リリースでは本番用・ペーパートレード用 DB を分離する設計をとっていますが、運用時は .env に記載するパスや KABUSYS_ENV の設定を十分に確認してください（`validate_config.py` を活用してください）。

今後の予定（参考）:
- research モジュールの完成、シグナル生成パイプラインとの統合。
- 銘柄別 lot_size サポート、価格フォールバックの改善。
- CI / テスト追加、ドキュメント整備の強化。