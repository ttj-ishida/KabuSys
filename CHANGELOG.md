# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
タグ付け・リリース管理に応じてエントリを分割してください。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-21

初回公開リリース。自動売買システム KabuSys の基盤機能一式を追加しました。

### Added
- 全体
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として追加。
  - プロジェクトルートの自動検出と .env 自動読み込みを実装（`kabusys.config`）。
    - .git または pyproject.toml を基準にプロジェクトルートを探索するため、CWD に依存しない設計。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` と `.env.local` の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
  - 高度な .env パーサ実装（`kabusys.config._parse_env_line`）：
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ、行内コメント処理などに対応。

- CLI / ツール
  - 対話式環境設定ウィザード（`kabusys.config_setup`）
    - `.env` の初期作成・更新を支援。シークレットマスクや選択肢サポート。
  - 設定検証ツール（`kabusys.validate_config`）
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 未導入時はスキップ）。
    - `--strict` オプションで警告も失敗扱いにできる。
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）
    - 稼働率、注文成功率、送信率、遅延（P95 等）を集計して PASS/FAIL 判定を行う。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数（デフォルト: `data/paper_trading.db`）。
    - レポートに使用する閾値（稼働率/成功率/レイテンシ等）を定義。

- 実行・監視ランチャー
  - ExecutionEngine 起動スクリプト（`kabusys.run_execution`）
    - `KABUSYS_ENV=paper_trading` 時は専用の paper-trading SQLite（`data/paper_trading.db`）と MockBrokerClient を使用し、本番 DB と分離。
    - プロセス優先度変更（High）や PID ファイル管理、停止フラグ監視を実装。
  - SystemMonitor ポーリングループ起動スクリプト（`kabusys.run_monitoring`）
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - Monitoring は常に本番の sqlite_path を使用する（環境に依存せず監視テーブルを保持）。
    - stop フラグ検知による graceful shutdown 実装。

- ロギング / プロセス制御
  - ログ設定ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）
    - コンソール（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの優先順位をドキュメント化。
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - Windows/Linux/macOS を吸収する API（nice / psutil）経由で優先度設定。CPU affinity の設定機能も提供。
    - 許容レベル: "high" / "normal" / "low"。

- ポートフォリオ構築（純粋関数群、DB非依存）
  - 候補選定・重み計算（`kabusys.portfolio.portfolio_builder`）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合は等金額にフォールバック。
  - セクター集中制限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap（既存ポジション比率に応じた除外ロジック）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" による乗数。未知レジームはワーニングを出して 1.0 にフォールバック）
  - ポジションサイジング（`kabusys.portfolio.position_sizing`）
    - risk_based / equal / score の配分メソッドをサポート。
    - lot_size（単元株）丸め、単銘柄上限・合計キャッシュ上限（aggregate cap）を考慮したスケーリング、cost_buffer を用いた保守的コスト見積り、残余キャッシュ配分のための端数ロジックを実装。

- リサーチ
  - ファクター計算モジュール（`kabusys.research.factor_research`）の骨格を追加（モメンタム、MA200、ATR 等の定義・定数）。（一部未実装）

### Changed
- 既存ライブラリの扱いを明確化
  - validate_config は PyYAML が未インストール時に YAML 検証をスキップし、警告を出すようにした。
  - logging_setup はログディレクトリが作成できない場合にファイルハンドラ作成をスキップするフォールバックを追加。

### Fixed
- .env パーサの堅牢化
  - 引用符やエスケープ、行頭の export キーワード、行内コメント処理の不備に対応し、より正確に .env の各行を解釈するよう修正。

### Security
- .env ファイルに関する注意をドキュメント化（config_setup に警告行を追加）。`.env` は Git にコミットしないことを明示。

### Documentation / Notes
- config_setup による .env 生成での注意点やデフォルト値を明記。
- validate_config により起動前に設定不備を検出できるため、運用時はまずこのツールを実行することを推奨。
- run_execution は paper_trading モードと live モードで DB とブローカークライアントが明確に分離されているため、誤って本番に発注するリスクを低減。
- 環境変数に関する主要キー（必須/任意）や有効値:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - KABUSYS_ENV: development / paper_trading / live
  - PAPER_FILL_MODE: instant / partial / never / reject
  - KILL_FLAG_CLEAR_ON_START: 0 / 1
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - DB 関連: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

---

今後の予定（例）
- factor_research の完全実装（DuckDB クエリと Z-score 正規化）。
- 戦略生成・シグナル処理モジュールの追加・結合テスト。
- 単体テストの整備と CI パイプラインの導入。

---

参照
- この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は、コミットログや PR の情報を併用して調整してください。