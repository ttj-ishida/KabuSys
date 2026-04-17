CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」フォーマットに従います。セマンティックバージョニングを採用しています。

[Unreleased]
------------

- なし（現時点のスナップショットは v0.1.0 の初回公開相当です）。

[0.1.0] - 2026-04-17
-------------------

### Added
- 初期リリース: KabuSys コア機能群を追加。
  - 環境・設定管理
    - Settings クラス: 環境変数から各種設定（J-Quants / kabuAPI / DB パス / ログ等）を取得・検証。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込み（OS 環境変数が優先、.env.local は上書き）。
    - 強力な .env パーサ: export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - 設定補助 CLI
    - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加（秘密値のマスク表示、項目定義付き）。
    - validate_config: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL 検証、DB パスや YAML のパース確認、"live" 環境向けのガードチェック、--strict モードをサポート。
  - 実行コンポーネント起動スクリプト
    - run_execution: ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を設定、paper_trading 環境では MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。停止フラグ／PID ファイル管理、エンジンスレッドの安全な停止処理を搭載。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB 初期化・duckdb 接続・停止フラグ検出・例外ハンドリングを実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio_builder: シグナル選定（select_candidates）と配分計算（calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 複数の割当手法（risk_based / equal / score）に対応した株数計算（calc_position_sizes）。単元（lot_size）丸め、1銘柄上限・投下資金上限・コストバッファ考慮、スケーリングと端数分配ロジックを実装。
  - リサーチ／ファクター計算
    - factor_research: DuckDB の prices_daily / raw_financials を利用してモメンタム・ボラティリティ・流動性等のファクターを計算する関数を追加（mom_1m/3m/6m、MA200乖離、ATR20、20日平均売買代金等）。不足データ時の None ハンドリング、P95 計算などを実装。
  - ツール
    - tools/paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。期間指定オプションと DB パス指定をサポート。
  - ユーティリティ
    - utils/process_priority: クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice）および CPU affinity 固定のヘルパーを追加。権限不足や未サポート環境では警告を出して安全にフォールバック。

### Changed
- パッケージメタ情報を追加: __version__ = "0.1.0"。

### Fixed / Robustness
- 無効な MONITOR_POLL_INTERVAL 値（非数、0 以下等）を検出してデフォルト（60 秒）にフォールバックし、警告ログを出力するようにした。
- .env 自動ロードでは OS 環境変数を保護（protected）して .env/.env.local による不意の上書きを防止。
- DB 初期化呼び出しを冪等化（init_monitoring_db を起動時に呼ぶ）して、監視テーブル不在による起動失敗を防止。
- run_execution / run_monitoring の起動フローでプロセス優先度設定を最初に行い、以降の処理が高優先度で実行されるようにした。
- run_execution の paper_trading モードで本番 DB と完全に分離する挙動を明示（PAPER_TRADING_SQLITE_PATH）。
- position_sizing の aggregate cap スケーリングでの端数処理を安定化（lot_size 単位での残差配分、再現性のためソート安定化）。
- process_priority の未対応 OS や権限不足時に例外を握りつぶして警告を出す安全な実装に修正。

### Notes / Implementation details
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視情報は環境を問わず一元化する方針）。
- paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能（デフォルト data/paper_trading.db）。
- calc_regime_multiplier は未知のレジームに対して 1.0 でフォールバックし、その旨を警告ログに出力する。
- factor_research の窓サイズ・スキャン範囲等はコメントに定数化してあり、将来のパラメタ調整が容易。
- validate_config は PyYAML 未インストール時、YAML の内容検証をスキップして警告を表示する。

Security
--------
- 現在のコードベースでは秘密情報（トークンやパスワード）は .env に保存する想定。.env は絶対にバージョン管理に含めないよう README とウィザード内コメントで注意喚起。

参考
----
- セマンティックバージョニングに従い、今後の互換性のある変更は MINOR、互換性を壊す変更は MAJOR にてリリース予定です。