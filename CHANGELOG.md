# CHANGELOG

すべての注記は Keep a Changelog 準拠です。  
この CHANGELOG はコードベースから推測して作成しています（自動生成・人手補完の余地あり）。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。KabuSys のコアユーティリティ・起動スクリプト・ポートフォリオ構築・検証ツール群を追加。
- 設定管理
  - Settings クラスによる環境変数ベースの設定取得を追加。J-Quants / kabuステーション / LINE / DB パス /監視閾値などをプロパティで提供。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を利用）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パース機能を実装。export プレフィックス、シングル／ダブルクォート内のエスケープ、行内コメント処理などに対応。
  - PAPER_TRADING 用に本番 DB と分離する `PAPER_TRADING_SQLITE_PATH` / `paper_sqlite_path` をサポート。Paper Trading 時は専用 DB を使用。
  - `PAPER_FILL_MODE`（instant/partial/never/reject）の検証を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し paper_trading 用 DB に記録して本番 DB と分離。
    - プロセス優先度を起動時に設定（`set_process_priority("high")`）。
    - 停止処理: プロジェクトルートの `data/stop_requested.flag` を監視し、検知時にエンジンを安全に停止。
    - PID ファイル書き出し・参照用の `data/execution.pid` をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- ロギング
  - 統一ロギングセットアップ関数 `setup_logging` を追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリは `LOG_DIR` 環境変数または `logs/`。
  - ハンドラ二重設定防止のため既存ハンドラをクリアする実装。
  - ログディレクトリ作成失敗時は警告を出しファイル出力をスキップするフォールバックを実装。
- プロセス制御ユーティリティ
  - `set_process_priority(level)`（high/normal/low）を追加。Windows（priority class）と POSIX 系（nice 値）を吸収して動作。権限不足や未対応 OS は警告してスキップ。
  - `set_cpu_affinity(cpu_count)` を追加。指定 core 数への固定を試行し、失敗時は警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定（score 降順、同点時 signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分へフォールバック）。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
  - position_sizing: 発注株数計算 calc_position_sizes を実装。allocation_method による分岐（risk_based / equal / score）、単元株丸め（lot_size）、1銘柄上限・総投下上限（aggregate cap）のスケーリングロジック、および手数料・スリッページを考慮した cost_buffer。
- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。シークレット項目はマスク表示、デフォルト値や選択肢をサポート。
  - validate_config.py: 起動前に .env および config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証、`KABUSYS_ENV=live` 時の追加警告（LINE 通知設定や Kill Switch 設定）を行う。
- テスト／検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL を判定。CLI 引数で期間（--from/--to）・DB パス（--db）を指定可能。P95 算出、各種 SQL クエリを実装。
- 研究用モジュール（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加。DuckDB を使った価格・財務データ参照でモメンタム/価値/ボラ/流動性等を算出する設計（実装の一部が含まれる／未完の可能性あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 設定読み込み・パースに関する堅牢性向上
  - .env 解析ロジックの改善（引用符内のエスケープ、インラインコメントの扱い、export プレフィックス対応）。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック実装（0 以下や非整数値を検知してデフォルト 60 秒を使用）。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成を安全にスキップするようにして起動の失敗を防止。
  - process_priority: 未対応 OS や権限不足時に警告して継続するようにして起動堅牢性を向上。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

-----

注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして利用する場合は、実際のコミット履歴やリリース時の意図に合わせて適宜修正してください。