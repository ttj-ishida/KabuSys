# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
続けて翻訳・要約はコードベースの内容から推測して作成しています。

## [Unreleased]

### Added
- 監視ループの起動スクリプトを追加 / 改良
  - run_monitoring.py を導入。SystemMonitor のポーリングループを起動するエントリポイントを提供。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値時はデフォルトにフォールバックし警告を出力。
  - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了する仕組みを実装。
  - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する旨を明記。

- 実行エンジン起動スクリプトの整備
  - run_execution.py を追加。ExecutionEngine の起動フロー（プロセス優先度設定、DB 接続、ブローカー生成、コンポーネント組み立て、スレッド実行、停止フラグ監視）を実装。
  - `KABUSYS_ENV=paper_trading` 時は専用の paper_trading DB（`data/paper_trading.db`）を使用し、本番 DB から完全分離。
  - ExecutionEngine 用の PID ファイル出力や停止フラグ監視、スレッドデーモン化を実装。
  - BrokerClientFactory によるブローカークライアント選択を採用。

- 設定管理・ウィザード・検証ツールを追加
  - config.py: .env 自動ロード機構を実装（`.env` / `.env.local`、OS 環境変数優先、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env パーサを強化（`export KEY=val` 形式のサポート、クォート内のバックスラッシュエスケープ処理、インラインコメント処理など）。
  - Settings クラスに各種プロパティを追加（`paper_fill_mode` バリデーション、`paper_sqlite_path`、監視閾値、KABUSYS_ENV / LOG_LEVEL の検証等）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。秘密項目はマスク表示、デフォルト・選択肢に対応。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV / LOG_LEVEL、DB パス、config/*.yaml の存在とパース検証、live 時の追加ガードなどを実行。`--strict` オプションで警告を FAIL 扱い可能。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。ルートロガーへ stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity を設定する関数も提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築・ポジション決定ロジック
  - portfolio モジュールを追加。銘柄選定（select_candidates）、重み算出（calc_equal_weights / calc_score_weights）、セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）、ポジションサイズ計算（calc_position_sizes）等を純粋関数として実装。
  - calc_position_sizes は risk_based / equal / score の割当方式に対応。単元株（lot_size）丸め、1銘柄上限・総投下キャップ・コストバッファを考慮したスケーリングロジックを導入。

- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py を追加。paper_trading 用 SQLite DB から稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを集計し PASS/FAIL 判定を行う。日付フィルタ・P95 計算等に対応。

- 一部リサーチ用モジュール（factor_research.py）の骨組みを追加（モメンタム等のファクター算出を意図した設計、DuckDB 接続前提）。

### Changed
- ログ設定を統一
  - 個々の起動スクリプトから setup_logging を呼び出すことで、ログ出力先・回転ポリシー・ログレベルの一貫性を確保。

- .env 読み込み順序と保護ポリシーを明確化
  - OS 環境変数 > .env.local（上書き） > .env（未設定のみ）という優先度を採用。既存 OS 環境変数は保護される。

- Execution / Monitoring 起動時にプロセス優先度を最初に設定するように変更（起動直後に優先度を上げることで安定化を図る）。

- monitoring 用 DB 初期化呼び出し（init_monitoring_db）を起動フローで冪等に実行し、監視テーブルの存在を保証。

### Fixed
- ログハンドラの二重登録を防止
  - setup_logging は既存ハンドラを flush/close してから削除し再設定するように修正。

- .env パースの不整合を是正
  - クォートあり値中のバックスラッシュエスケープや、クォートなしでのインラインコメント扱い（直前がスペース/タブの場合のみコメントと解釈）を改善し、実際の環境値読み込みミスを低減。

- process_priority の未対応 OS / 権限エラーをハンドル
  - psutil の属性欠如や AccessDenied 時に例外を落とさず警告ログを出力してスキップするよう改善。

- config/ YAML 検証
  - PyYAML 未インストール時にパース検証をスキップし、警告出力するように変更（起動時にクラッシュしないように）。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys の基礎機能群をまとめて公開。
  - 実行（ExecutionEngine）・監視（SystemMonitor）・モニタリング DB 初期化等のエントリポイント。
  - 設定管理（.env 自動読み込み、Settings クラス）。
  - 対話式 .env 作成ウィザード（config_setup）。
  - 起動前設定検証ツール（validate_config）。
  - ロギング設定ユーティリティ（stdout + 日次ローテーション）。
  - プロセス優先度 / CPU affinity ユーティリティ。
  - ポートフォリオ構築ライブラリ（選定・重み付け・セクター制限・ポジションサイズ決定）。
  - Paper Trading 向け検証レポート生成スクリプト。
  - リサーチ用ファクター計算モジュールの骨子（DuckDB ベース設計）。
  - パッケージメタ情報: バージョン __version__ = "0.1.0"

### Changed
- （初回リリースのため基礎実装を収録）

### Fixed
- （初回リリース時点で発見された軽微な不具合修正は上位の Unreleased に反映）

---

注記:
- 本 CHANGELOG は、提供されたコードベースの実装内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに従って更新してください。
- 重要な動作に関する設定（特に KABUSYS_ENV=live の本番設定や Kill Switch の取り扱い）は注意して運用してください（validate_config / config_setup のメッセージを参照）。