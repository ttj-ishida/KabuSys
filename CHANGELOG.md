# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
慣例: 追加(Added)、変更(Changed)、修正(Fixed)、非推奨(Deprecated)、削除(Removed)、セキュリティ(Security)。

※ 本ファイルは、提示されたソースコードの内容から推測して作成したリリースノートです。

## [Unreleased]

### Added
- 設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話式で .env ファイルの作成・更新を支援する。シークレット項目はマスク表示。
  - デフォルト項目、選択肢、説明文を用意し .env を自動生成可能。
- 設定検証 CLI を追加（kabusys.validate_config）
  - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの存在チェック、config/*.yaml の存在・パース検証（PyYAML が無い場合はスキップして警告）。
  - --strict オプションで警告を FAIL 扱いにできる。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
  - Paper Trading 用 SQLite DB を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。
  - CLI で期間（--from / --to）と DB パス（--db）を指定可能。
- 実行系・監視系の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時はペーパートレード用 DB を使用（本番 DB と分離）。
    - BrokerClientFactory を介してブローカークライアントを生成、スレッドでセッションを実行し停止フラグで安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグでループ終了。
- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）
  - 候補選定: select_candidates（スコア降順、タイブレークロジック）
  - 重み計算: calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等分にフォールバック）
  - リスク調整: apply_sector_cap（セクター集中制限）, calc_regime_multiplier（市場レジームに応じた乗数、未知レジームは警告してフォールバック）
  - ポジションサイジング: calc_position_sizes（risk_based / equal / score 対応、単元単位切り捨て、aggregate cap のスケーリングと residual 分配）
- ログ設定ユーティリティを追加（kabusys.utils.logging_setup）
  - stdout ストリームハンドラと日次ローテートファイルハンドラをルートロガーに設定。既存ハンドラのクリアと重複防止を行う。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - Windows / POSIX の差分を吸収して優先度設定を提供。失敗時は警告を出してスキップ。
  - CPU affinity を最初の N コアに固定するヘルパを提供。

### Changed
- .env 自動ロードの改善（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml をもとに探索して自動的に .env/.env.local を読み込む。
  - .env.local は .env より優先して読み込み（既存 OS 環境変数は上書きされない保護あり）。
  - 複雑な .env の行解析に対応：export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など。
  - テスト用途などのため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- 設定表現の整備（kabusys.config.Settings）
  - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）や閾値がプロパティで取得可能になりデフォルト値やバリデーションを備える。
  - PAPER_FILL_MODE の妥当性チェックを実装（instant/partial/never/reject）。
  - KABUSYS_ENV/LOG_LEVEL の許容値チェックで不正値は例外を送出。
- run_monitoring の挙動
  - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用して監視情報を記録する旨を明示。
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックとログ出力を実装。
- run_execution の挙動
  - paper_trading モード時は専用の paper_sqlite_path を使用し、本番 DB と完全に分離するよう変更。
  - 起動時に監視テーブルの存在を保証（init_monitoring_db を呼ぶ、冪等）。

### Fixed
- ログの二重出力やハンドラ重複の抑止（logging_setup）:
  - 既存ハンドラを flush/close のうえ削除してから再設定するようにし、複数回起動した際の二重出力を回避。
- プロセス優先度設定でのクロスプラットフォーム例外処理（process_priority）
  - psutil の未実装やアクセス権限の失敗を捕捉して警告を出すように改善。

### Security
- .env ファイルの取り扱いに関する注意書きを config_setup の出力に追加（.env を Git に絶対コミットしない旨）。

---

## [0.1.0] - 2026-04-19

初回リリース想定 — コア機能を実装。

### Added
- コアライブラリの追加
  - 自動売買のためのポートフォリオ構築（選定・重み付け・ポジションサイジング・リスク調整）。
  - 実行エンジン（ExecutionEngine）起動スクリプトと監視（SystemMonitor）起動スクリプト。
  - ブローカー抽象化（BrokerClientFactory）による paper_trading と live の分離（MockBroker 対応）。
  - duckdb / sqlite を利用したデータ管理基盤（デフォルトパスと設定可能）。
  - 設定管理（kabusys.config）と settings インスタンス。
- 開発支援ツール
  - .env 対話式ウィザード（kabusys.config_setup）。
  - 設定検証ツール（kabusys.validate_config）。
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）。
- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）。

### Changed
- 各種デフォルトパスや環境変数のキーを整理、Settings を介して取得するアプローチに統一。

### Fixed
- 起動スクリプト・ユーティリティでの例外処理とフォールバックを強化（ログディレクトリ作成失敗、psutil の権限エラー、DB 欠損時の安全なハンドリングなど）。

### Known issues / TODO
- research.factor_research モジュールは計算ロジック実装中（ソースが途中で切れている）。完全実装・テストが必要。
- 一部の TODO（例: position_sizing の銘柄別 lot_size 対応、price 欠損時のフォールバック価格）は将来対応予定。

---

メンテナンス方針:
- CLI ツール・起動スクリプトは本番安全性（paper_trading と live の完全分離、kill/stop フラグ、PID ファイル）を重視して実装しています。
- 設定は環境変数と .env ファイルを併用する想定で、テストや CI での再現性を考慮した自動ロード無効化オプションを提供しています。

もし特定のファイルや変更点についてさらに詳細な差分説明（行単位や設計意図の深掘り）が必要であれば教えてください。