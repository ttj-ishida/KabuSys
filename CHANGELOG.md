# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

フォーマット:  
- Added: 新機能  
- Changed: 既存機能の変更  
- Fixed: バグ修正  
- Removed / Deprecated / Security: 該当あれば記載

## [0.1.0] - 2026-04-18

初回リリース。KabuSys の基本的な実行・監視・設定・ポートフォリオ構築・ツール群を追加。

### Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag によるフラグ検出で行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 Mock クライアントと専用 SQLite（デフォルト: data/paper_trading.db）を使用する。停止フラグ・PID ファイル管理・スレッドでのエンジン実行をサポート。

- 設定管理
  - config.py: 環境変数/.env 読み込みロジックを実装。プロジェクトルートを .git または pyproject.toml で自動検出し、.env/.env.local を安全にロード（OS 環境変数を保護）。.env のパースはクォート、export プレフィックス、インラインコメント等に対応。Settings クラスで各種設定（DB パス、API トークン、監視閾値、環境判定等）を型安全に取得可能。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。秘密項目はマスク表示、デフォルト値・選択肢サポート。

- 設定検証
  - validate_config.py: .env と config/*.yaml の起動前検証用 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）などを実行。--strict モードで警告を FAIL 扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ自動作成とファイルハンドラのフォールバック処理を実装。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows と POSIX 系の差分吸収、失敗時の安全なフォールバックを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates) と重み計算 (calc_equal_weights, calc_score_weights) を追加。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を追加。未知レジームのフォールバックやログ出力を実装。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）の実装。単元株丸め、1 銘柄上限・合計投下キャップ、スケールダウンロジック（残差処理を含む）を実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（P95 等）を集計し PASS/FAIL 判定を行う。デフォルト DB は data/paper_trading.db。閾値はスクリプト内定義（稼働率 99% 等）。

- データアクセス / 分析基盤
  - DuckDB 接続を利用する設計を導入（duckdb_conn を各エンジン・ツールで受け渡し）。

- パッケージ定義
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- 監視起動のデフォルト動作
  - run_monitoring は Monitoring 用に「環境に依存せず」Settings.sqlite_path（本番用監視 DB パス）を使用して監視テーブルを初期化する仕様。監視は本番監視対象を想定して常に本番 DB を参照する設計。

- ロギングのデフォルト
  - logging_setup は stdout へ出力するようにデフォルト設定（stderr ではなく stdout を使用）し、ログファイルは logs/<app_name>.log に日次ローテートで保存。

### Fixed
- ポーリング間隔の妥当性チェック
  - MONITOR_POLL_INTERVAL の値が 0 以下や不正文字列の場合、デフォルト 60 秒にフォールバックするように修正（run_monitoring._get_poll_interval）。0 を time.sleep に渡すと ValueError になる問題を避けるためのガード。

- .env パースの堅牢化
  - config._parse_env_line でクォート付き値のバックスラッシュエスケープや export プレフィックス、インラインコメント処理に対応。不正行を無視することで読み込みエラーを低減。

### Notes / Known issues / TODO
- research/factor_research.py はファクター計算モジュールの実装を開始しています（モメンタム計算の実装途中でファイル末尾が途切れています）。完全実装は次のリリースで継続予定。
- portfolio/position_sizing.py や risk_adjustment.py 内に将来の拡張（銘柄別 lot_size、価格フォールバック等）に関する TODO コメントが残っています。
- monitoring_db や SystemMonitor、ExecutionEngine、BrokerClientFactory などの内部実装は本変更ログの対象外（本差分で参照されているがここに含まれる実装の変更点は記載していません）。本リリースではそれらの組み合わせ動作を想定しているため、実稼働前に validate_config と paper_verification_report で動作確認を推奨します。

---

将来のリリースでは、research モジュールの完成、テスト整備、監視アラート（LINE 通知等）の追加、細かなパラメータ調整やパフォーマンス最適化を予定しています。