# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

### Added
- ドキュメント化および対話式セットアップ:
  - .env を対話形式で作成・更新する config_setup ウィザードを追加（python -m kabusys.config_setup）。
  - 設定検証用 CLI を追加（python -m kabusys.validate_config）。必須環境変数や config/*.yaml の存在・パース検証、環境依存の安全ガードをチェック。
- 実行/監視用エントリスクリプト:
  - 実行エンジン起動スクリプト run_execution を追加。KABUSYS_ENV=paper_trading の場合に専用のペーパートレード DB を使用し、MockBrokerClient を利用する分離をサポート。ExecutionEngine をスレッドで起動・監視し、停止フラグを検知して安全に停止するフローを実装。
  - 監視ループ起動スクリプト run_monitoring を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を利用する設計。
- ポートフォリオ構築ライブラリ:
  - 銘柄候補選定・重み計算: select_candidates、calc_equal_weights、calc_score_weights を実装。
  - リスク調整: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた資金乗数）を実装。
  - ポジションサイズ算出: calc_position_sizes を実装（risk_based / equal / score の配分方法をサポート、単元株（lot_size）で丸め、aggregate cap によるスケーリングロジックを実装）。
- ツール:
  - ペーパートレード検証レポート生成スクリプト tools.paper_verification_report を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。日付レンジ指定や DB パス指定をサポート。
- 設定管理:
  - Settings クラスを実装し、環境変数から各種設定（J-Quants、kabu API、DB パス、監視閾値、paper_trading 用パス等）を取得できるようにした。PAPER_FILL_MODE のバリデーションや KABUSYS_ENV の妥当性チェック等を含む。
  - .env 自動読み込み: プロジェクトルートを探索して .env/.env.local を自動読み込み（OS 環境変数を保護）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースは export プレフィックス、クォート文字とエスケープ、インラインコメント等に耐性をもたせた実装。
- ロギング/プロセス制御ユーティリティ:
  - 統一的なログ設定ユーティリティ utils.logging_setup を実装。stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定、既存ハンドラの二重設定を防止、ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - プロセス優先度・CPU affinity 設定ユーティリティ utils.process_priority を追加。Windows / POSIX（Linux/Mac 等）差分を吸収して優先度設定を行い、失敗時は警告ログでスキップする安全実装を採用。
- データベース連携:
  - DuckDB（分析用）と SQLite（監視/注文履歴用）双方の接続を扱う実装を追加。起動時に monitoring 用テーブルが存在することを保証する init_monitoring_db を呼び出す箇所を追加（冪等）。

### Changed
- ログ出力:
  - すべての起動スクリプトで共通の logging_setup を使用するように統一。
  - コンソール出力は stdout を使用するよう明示（cron 等でのリダイレクト対策）。
- .env の読み込み順序と上書きルール:
  - OS 環境変数を保護しつつ、.env（未設定のキーのみ） → .env.local（上書き可）という優先順を適用。
- 実行系の DB 分離:
  - paper_trading モードでは paper_trading 用 SQLite を使用するように変更（本番データと完全に分離）。
- エラーハンドリング/堅牢性:
  - run_monitoring のポーリングループで monitor.check_once() の例外をキャッチしてログ出力し、ループを継続する堅牢化を追加。
  - run_execution/run_monitoring ともに stop フラグ（data/stop_requested.flag）および PID ファイルを用いた安全停止の取り扱いを実装。

### Fixed
- ログハンドラの二重設定問題を解消（既存ハンドラを一旦 flush/close してからクリアして再設定）。
- .env パーサの不正な値解釈（クォート、エスケープ、コメント）に起因する誤動作を改善。

### Deprecated
- なし

### Removed
- なし

### Security
- .env 書き出しヘッダに「.env を絶対に Git にコミットしない」旨の注意を明記（config_setup の出力）。

---

## [0.1.0] - 2026-04-23

初回リリース。上の Unreleased に記載の機能群をまとめてリリース。

### Added
- 基本機能の一式を初回追加:
  - 環境設定読み込み・対話式ウィザード（config_setup）、設定検証（validate_config）。
  - 実行エンジン run_execution、監視 run_monitoring の起動スクリプト。
  - ポートフォリオ構築ライブラリ（portfolio モジュール: 銘柄選定、重み計算、リスク調整、ポジションサイズ算出）。
  - ユーティリティ（logging_setup、process_priority）。
  - ペーパートレード検証レポート生成ツール（tools.paper_verification_report）。
  - Settings クラス、.env 自動読み込みロジック。
  - DuckDB / SQLite を利用するデータアクセス基盤の初期実装。

### Changed
- なし（初回リリースのため）

### Fixed
- なし（初回リリースのため）

### Security
- .env の取り扱いに関する注意喚起を追加。

---

注記
- research/factor_research.py はモメンタム等のファクター計算を目的としたモジュールとして追加されていますが、ファイル末尾で実装が途中に見える箇所（未完）があります。今後のリリースで残りのファクター計算ロジックを完成させる予定です。
- position_sizing や apply_sector_cap 内に将来の拡張（銘柄別 lot_size のサポートや価格フォールバックの改善）を示す TODO コメントがあります。今後の改善項目として管理してください。

もし特定のコミットやさらに細かい変更履歴（各ファイルごとの行単位差分に基づく項目）が必要であれば、差分（git log や git diff）をいただければそれに基づいてより正確な CHANGELOG を生成します。