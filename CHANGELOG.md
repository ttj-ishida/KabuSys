# Changelog

すべての重要な変更は「Keep a Changelog」フォーマットで記録しています。  
このファイルはコードベース（src/ 以下）の内容から推測して作成した変更履歴です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Deprecated: 削除または非推奨事項
- Known issues / Notes: 既知の制限や注意点

---

## [0.1.0] - 2026-04-23 (初回リリース)
最初の公開リリース。KabuSys のコア機能（設定管理、起動スクリプト、ポートフォリオ構築、リスク調整、発注ロジック補助、モニタリング基盤、ユーティリティ、ツール類）をまとめて提供。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB と SQLite を併用する分析 / 監視データ基盤を導入（デフォルトファイルパス: data/kabusys.duckdb, data/monitoring.db）。
  - 日次ローテーションログとコンソール出力を統一する共通ロギングユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout を主要出力に使用、ファイルは logs/<app_name>.log に日次ローテーション（30日保持）。
    - LOG_DIR 環境変数や引数でログディレクトリを変更可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- 設定管理
  - .env 自動ロード機能を実装（プロジェクトルートの .env, .env.local を順に読み込み）。
  - Settings クラスによる環境変数ラッパーを提供（型変換・検証付き）。主要設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - PAPER_FILL_MODE（paper trading 用の fill_mode 検証）
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - 監視関連（PID ファイルパス、Kill Flag パス、しきい値など）
  - 環境自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の対話式ウィザード（kabusys.config_setup）を実装。既存 .env の読み込み・更新、秘密項目はマスク表示。
  - 設定検証 CLI（kabusys.validate_config）を実装:
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML 未インストール時はスキップ）。
    - --strict オプションで警告も失敗扱いにする。
- 起動スクリプト / 実行制御
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。
    - stop_flag（data/stop_requested.flag）による安全停止、KeyboardInterrupt での終了処理、例外ハンドリング時のログ出力を実装。
  - Execution エンジン起動スクリプト（kabusys.run_execution）を追加:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper_trading 環境では MockBrokerClient を想定）。
    - PID ファイル管理、stop_flag による安全停止、別スレッドでエンジンを実行する仕組みをサポート。
    - 起動時にプロセス優先度を "high" に設定するフローを導入。
- プロセス優先度 / CPU 設定
  - クロスプラットフォーム対応のプロセス優先度設定ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX(nice) に対応。psutil を利用。権限不足や未対応 OS の場合は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を実装。
- ポートフォリオ構築（pure functions）
  - 構成モジュール群を追加（kabusys.portfolio）:
    - portfolio_builder: select_candidates（スコア降順＋tie-break）、calc_equal_weights、calc_score_weights（全スコア0 の場合等金額配分にフォールバック／警告）。
    - risk_adjustment: apply_sector_cap（既存ポジションのセクター暴露を計算し上限超過セクターの候補除外）、calc_regime_multiplier（regime -> multiplier mapping、未知レジームで警告してフォールバック）。
    - position_sizing: calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）、lot_size 単位丸め、aggregate cap による縮尺、残差配分アルゴリズム（fractional remainders に基づき lot 単位で再配分）、cost_buffer を用いた保守的コスト見積り。
  - 設計方針: すべて純粋関数で DB や外部 I/O に依存しない（メモリ内計算）。
- モニタリング / 検証ツール
  - init_monitoring_db による監視テーブルの冪等初期化を追加（監視スキーマの整備）。
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加:
    - 指標: 稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - デフォルトしきい値を設定して PASS / FAIL を判定（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from/--to）、DB パスオーバーライド（--db）に対応。
- リサーチ
  - research/factor_research (ファクター計算モジュール) を追加。Momentum/Value/Volatility/Liquidity の計算方針を実装する設計（DuckDB 接続を受ける想定）。一部関数（calc_momentum）を実装し始めている。

### Changed
- 設定読み込みの優先度を明確化:
  - OS 環境変数 > .env.local > .env の順で読み込む（.env.local は override=True）。
  - ただし OS 環境変数は protected として上書きされない。
- logging_setup の挙動:
  - 既存ハンドラがある場合は一度 flush/close してから再設定（多重ハンドラ防止）。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを改善。
- process_priority の例外耐性強化:
  - 権限不足や未実装 API に対して警告ログを出し安全にスキップするように変更。
- init_monitoring_db を起動時に呼ぶことで監視用テーブルが必ず存在するようにし、起動時の欠落によるエラーを軽減。

### Removed / Deprecated
- なし（初回リリース）。

### Known issues / Notes
- research/factor_research の一部実装が途中で切れている（calc_momentum の実装途中）。本モジュールはまだ完成しておらず、使用時は注意が必要。
- position_sizing の TODO:
  - 銘柄ごとの lot_size を将来的に stocks マスタで持たせる拡張の計画あり。
  - price が欠損（0.0）だった場合のフォールバック価格の扱いに改善余地あり（risk_adjustment 内の注記参照）。
- monitoring はコード上「環境にかかわらず本番 sqlite_path を使用する」と明示されているため、テスト環境で監視 DB を分離したい場合は運用上の調整が必要。
- 一部の外部パッケージ（psutil, duckdb, PyYAML）の存在を前提としているため、環境に応じた依存関係のインストールが必要。PyYAML 未インストール時は config YAML の検証をスキップする仕様。

---

開発・運用に関して不明な点があれば、該当モジュールのソース内ドキュメント（docstring / コメント）を参照してください。必要であれば、この CHANGELOG をベースにより詳細なリリースノートを作成します。