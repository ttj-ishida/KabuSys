# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- バージョンはパッケージの __version__ に合わせています（0.1.0）。
- リリース日: 2026-04-23（このコードスナップショットを基に推測）。

## [Unreleased]
（次のリリースでマージ予定の変更をここに記載）

## [0.1.0] - 2026-04-23

### Added
- 基本機能の初期実装を追加（初期公開リリース）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading 環境では MockBrokerClient を利用し、paper_trading 用の専用 SQLite（data/paper_trading.db）にデータを記録する仕組みを提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（デフォルト 60 秒）。停止はプロジェクトルートの data/stop_requested.flag ファイル検知で行う。
- 設定管理・初期化
  - config.py: 環境変数/.env 読み込みロジックを追加。.env と .env.local の読み込み順をサポートし、OS 環境変数（既存値）を保護する機構を実装。クォート & エスケープを考慮した .env パーサを実装。
  - config_setup.py: 対話式ウィザードで .env ファイルを作成/更新する CLI を追加。secret 項目はマスク表示し、保存前に確認を促す。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、パスの存在チェック、YAML パース（PyYAML が無ければ警告）などを行い、--strict で警告も失敗扱いにできる。
- ロギング・プロセス管理
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout 出力と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップするフォールバックを実装。
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定ユーティリティを追加。CPU affinity 設定関数も提供。権限不足時は安全にスキップする。
- ポートフォリオ構築ライブラリ（純関数）
  - portfolio/portfolio_builder.py: シグナル選定・重み計算（候補選定、等金額・スコア加重）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用ロジックと市場レジームに応じた資金乗数（regime multiplier）を実装。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数決定ロジックを実装（risk_based／equal／score の配分方式、単元株丸め、aggregate cap スケーリング、手数料バッファ考慮）。
  - portfolio/__init__.py: 上記関数群を外部公開するパッケージ初期化。
- 監視・監査・ユーティリティ
  - monitoring 初期化呼び出しを run_execution/run_monitoring に統合（init_monitoring_db を起動時に呼ぶことで監視テーブルの存在を保証）。
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、PASS/FAIL 判定を行う。期間フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。
- research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）の骨組みを追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### Changed
- 監視 DB の使用方針: run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用するように設計（監視は環境ごとに分離せず一元管理を想定）。
- 実行エンジンの DB 接続: paper_trading 環境では paper_sqlite_path を使用することで本番 DB と分離（paper trading は完全に別 DB に記録）。
- ログ設定のデフォルトや解決順を明確化:
  - ログレベルは (1) 引数、(2) 環境変数 LOG_LEVEL、(3) デフォルト INFO の順で解決。
  - ログディレクトリは引数 > 環境変数 LOG_DIR > デフォルト logs/。
- .env ロードの保護: OS 環境変数は protected として .env の上書きを防ぐ。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

### Fixed
- 複数の起動シーケンス改善:
  - 各起動スクリプトで最初にプロセス優先度を設定することで起動直後の安定性を向上。
  - run_execution のスレッド制御を改善し、stop flag 検知時に engine.stop() を呼んで安全にシャットダウンするようにした。
- logging_setup: 既に root にハンドラが存在する場合、一度 flush/close してからハンドラを再設定することで二重ログ出力を防止。

### Security
- .env ファイルに関して警告を明示:
  - config_setup にて .env を Git にコミットしないよう明記。
  - validate_config の live 確認で、LINE トークン未設定等のリスクを警告。

### Known issues / Notes
- research/factor_research.py の calc_momentum 関数はファイルの末尾が途中で切れている部分があり（start_da で途切れ）、一部実装が未完了の可能性があります。ファクター計算の完全実装は今後の完善を予定。
- position_sizing の価格欠損時（price==0.0）によりエクスポージャーの過少見積りが起きる点は TODO コメントで認識済。将来的に前日終値やコストベースのフォールバックを実装予定。
- process_priority/set_cpu_affinity は権限不足や未対応 OS の場合は安全にスキップする実装だが、期待通りに効果が出ない環境があるかもしれません。

---

（注）上記は与えられたコードベースの内容から推測して作成した CHANGELOG です。実際のコミット履歴や過去バージョンとの比較に基づく変更記録ではありません。必要であれば、より詳細なセクション分け（example: Breaking Changes, Migration notes）や各モジュールごとの変更差分推測を追加で作成します。