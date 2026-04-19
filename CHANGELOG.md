# Changelog

すべての重要な変更点は「Keep a Changelog」形式で記録しています。  
このファイルはソースコードの現状（コードベースから推測）に基づき作成されています。

フォーマット:
- Added: 新機能
- Changed: 仕様変更（後方互換性がある程度保たれる変更）
- Fixed: バグ修正（動作不良の修正）
- Deprecated / Removed / Security: 該当する場合に記載

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション設定管理
  - Settings クラスを実装し、環境変数・.env ファイルから設定を取得する機能を追加（src/kabusys/config.py）。
  - プロジェクトルートの自動検出（.git または pyproject.toml 基準）と .env/.env.local の自動読み込み機能を追加。
  - .env パーサは export 形式、クォート付き値、インラインコメント等に対応。

- 実行/監視用の起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用（完全分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager/RiskManager/Reconciler の組み立て、実行スレッド管理、停止フラグ監視に対応。
    - PID ファイル管理・停止フラグ検出により安全に停止する仕組みを実装。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。無効値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する仕様。

- 設定関連 CLI / ユーティリティ
  - 対話式の .env 作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
    - 必須/任意項目の定義、既存 .env 読み込み、マスク表示、保存確認を備える。
  - 起動前設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数検査、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML があれば実施）。
    - --strict オプションで警告を FAIL 扱い（exit(1)）にできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加（src/kabusys/portfolio/risk_adjustment.py）。
  - 株数決定・丸め・投下資金スケーリング（calc_position_sizes）を追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。lot_size（単元）対応、cost_buffer による保守的コスト見積り、aggregate cap スケーリングロジックを実装。

- ロギング・プロセスユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/）をルートロガーへ設定。
    - 既存ハンドラのクリア、ログレベル・ログディレクトリ解決ルールを実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみ継続。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS 等）差分を吸収し、psutil を使って nice/priority を設定。アクセス権限や未対応 OS 時のフォールバックも実装。

- Paper Trading 検証ツール
  - ペーパートレード結果の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、P95 レイテンシなどの指標を出力。
    - デフォルト閾値を定義し、PASS / FAIL 判定を実施。--from/--to/--db オプションをサポート。

- 研究用ファクターモジュール（開発中）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum 等の計算方針を実装する骨組みを追加（DuckDB を利用して prices_daily 等を参照する想定）。
    - 実装は作業中の箇所あり（未完部分あり）。

- パッケージメタ
  - パッケージバージョンを定義: __version__ = "0.1.0"（src/kabusys/__init__.py）。

### Changed
- ログ設定の再構成:
  - setup_logging() が既存ハンドラを安全にフラッシュ/クローズしてから削除するように変更。多重ハンドラ登録の防止。

### Fixed
- 安全な動作回避/フォールバックの強化:
  - MONITOR_POLL_INTERVAL の不正値（0以下や文字列）を検出して警告を出しデフォルト値にフォールバックするように変更（監視の安定化）。
  - ログディレクトリ作成・ファイルハンドラ生成の失敗時にコンソール出力のみで継続するフォールバックを追加。
  - set_process_priority / set_cpu_affinity が権限不足や未対応環境で例外を上げないよう警告ログに差し替えるハンドリングを実装。

### Notes / Implementation details
- run_monitoring はプロジェクトルートの data/stop_requested.flag を参照して安全にループ終了する実装。run_execution も同様に停止フラグを監視してエンジン停止を試みる。
- paper_trading 用 DB はデフォルトで data/paper_trading.db（PAPER_TRADING_SQLITE_PATH による上書き可）。本番監視 DB（monitoring）は環境にかかわらず Settings.sqlite_path を使用する設計。
- ポートフォリオ・ポジションサイズ計算は現状単元株（lot_size）が全銘柄共通となっているが、将来的な拡張点（銘柄別 lot_size）の TODO を含む。
- validate_config は PyYAML が未インストールの場合も graceful に警告して YAML の検証をスキップする。
- research/factor_research.py はファクター設計（Momentum/Value/Volatility/Liquidity）に関する仕様コメントを含むが、実装が未完の箇所がある（要完了）。

---

将来的なリリースでは以下を想定:
- research/factor_research の完全実装（DuckDB クエリ + 正規化ユーティリティ統合）
- ExecutionEngine, Broker ラッパー類のテスト追加とエラーハンドリングの強化
- 単体テスト、CI/CD 設定、ドキュメント（使用例）の充実

もし特定ファイルや変更点について詳細な説明や、実際に CHANGELOG を特定のバージョン管理履歴に合わせて調整したい場合は、追加情報（変更日・コミットメッセージ等）を教えてください。