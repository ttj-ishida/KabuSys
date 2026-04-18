# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期リリース。
- 起動スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、本番 DB と完全分離された Paper Trading 用 SQLite (デフォルト: data/paper_trading.db) に記録する。
  - run_monitoring: システム監視ポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` でオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する点に注意。
- 環境設定関連 CLI
  - config_setup: 対話式ウィザードで `.env` を作成・更新する CLI を追加（python -m kabusys.config_setup）。
  - validate_config: `.env` および config/*.yaml の起動前検証 CLI を追加（python -m kabusys.validate_config）。`--strict` オプションで警告を失敗扱いにできる。
- ユーティリティ
  - logging_setup: stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を組み合わせた統一ログ設定ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続する（フォールバック）。
  - process_priority: Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティを追加（`set_process_priority`, `set_cpu_affinity`）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナルから候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 投下株数の算出ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、コストバッファ考慮を実装。
- 解析・検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL を判定可能（python -m kabusys.tools.paper_verification_report）。
- 設定読み込み機能
  - config: `.env` 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。`.env` と `.env.local` の読み込み順を制御し、OS 環境変数を保護する仕組みを導入。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パース機能でシングル/ダブルクォートとバックスラッシュエスケープ、行内コメントの取り扱いに対応。
- 設定オプション・環境変数
  - 新たに参照/利用される環境変数を導入/明記:
    - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。
    - PAPER_FILL_MODE: Paper Trading のモック約定モード（"instant" / "partial" / "never" / "reject"、デフォルト "instant"）。
    - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite のパス（デフォルト data/paper_trading.db）。
    - KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアするか（"0"/"1"）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読込を無効化するフラグ。

### Changed
- DB/分析基盤
  - DuckDB 統合: 複数コンポーネント（実行エンジン、監視等）で DuckDB 接続を受け取り分析用データベース（デフォルト data/kabusys.duckdb）を利用する設計に。
- ログ設定
  - デフォルトで logs/ に日次ローテーションのログファイルを保存（30 日保持）。ログディレクトリが作成できない場合はファイル出力をスキップする安全動作を実装。
- run_execution / run_monitoring
  - 起動直後にプロセス優先度を "high" に設定するよう変更（set_process_priority の呼び出しを追加）。
  - 停止制御にプロジェクト直下の data/stop_requested.flag といったフラグファイルを利用する共通方式を採用。
  - run_execution: Paper Trading 時は専用 SQLite を使用し、monitoring テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値（0 / 負 / 非数）に対して警告を出しデフォルトにフォールバックする実装に変更。
- validate_config
  - 設定ファイル（config/*.yaml）の存在チェックと（PyYAML が存在する場合の）パース検証を追加。PyYAML 未インストール時は警告を出して YAML 検証をスキップする。
  - 起動前に主要環境変数の存在/プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無の警告等を行うよう改善。
- portfolio モジュール
  - スコア重み付けで全スコアが 0 の場合に等配分へフォールバックする動作を追加（警告ログあり）。
  - セクター適用時に "unknown" セクターはセクター上限適用対象外とする扱いを明確化。
  - position_sizing: lot_size による丸め、cost_buffer による保守的見積、および aggregate cap 超過時のスケーリングと端数配分ロジックを実装。

### Fixed
- 環境変数パーサーでのクォート/エスケープ処理やインラインコメントの誤処理を改善し、より堅牢に `.env` を読み込めるよう修正。
- process_priority / set_cpu_affinity:
  - 非対応 OS や権限不足時に例外を落とさず警告ログにフォールバックするようにし、起動失敗のリスクを低減。
- logging_setup:
  - ルートロガーに既存ハンドラがある場合、二重出力を防ぐために一度ハンドラを flush/close してから置き換える実装に修正。
- tools.paper_verification_report:
  - データ不足（テーブル未存在やレコードなし）時に例外を上げずレポート内で N/A 表示にフォールバックするよう改善。

### Security
- シークレット入力の取り扱い
  - config_setup の対話式ウィザードでシークレット項目（J-Quants トークンや API パスワード）をマスク表示するように実装。`.env` ファイル生成時に注意書きを追加（.env を絶対に Git にコミットしない旨）。

### Notes / Migration
- run_monitoring は監視データとして Settings.sqlite_path（data/monitoring.db 等）を使用します。開発・紙取引環境でも本番用パスが参照される点に注意してください（意図的設計）。
- Paper Trading と本番の DB は完全に分離されます。Paper Trading を使う場合は KABUSYS_ENV を `paper_trading` に設定してください（paper 用 DB は PAPER_TRADING_SQLITE_PATH で上書き可能）。
- `.env` 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。
- ログディレクトリ作成に失敗するとファイル出力は行われず stdout のみになります。ログ保存先を変更する場合は LOG_DIR 環境変数または setup_logging の引数で指定してください。

---

今後の予定:
- research.factor_research の完成（ファクター計算ロジックの追加完了とテスト）
- execution / monitoring の細かな E2E テスト追加、運用監視・アラート拡張

（本リリースはソースコードから推測して作成した変更履歴です。実際のコミット履歴と差異がある可能性があります。）