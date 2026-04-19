# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般的な注記:
- 日付はコミット/リリース日に合わせて記載してください（ここではコード内容から推測した例示日を使用しています）。
- 各エントリは関係するファイル名を併記しています。参照しやすいように実装箇所を明記しています。

## [Unreleased]

### Added
- 監視プロセスの起動スクリプトを追加 / 改良（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能に。デフォルトは 60 秒。
  - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
  - Monitoring は環境変数にかかわらず本番用 sqlite_path を使用する仕様（意図的な分離）。
  - duckdb 接続を併用して分析用 DB にデータを渡す実装。

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、専用の paper_trading DB（data/paper_trading.db）に出力する分離を実装。
  - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - stop/kill 用のフラグファイルと pid ファイルを利用した安全な起動/停止制御を実装。
  - 実行エンジンを別スレッドで稼働させ、停止フラグ検知で安全に停止する処理を実装。

- 環境設定と検証ツール
  - 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）。
    - 入力支援、デフォルト/選択肢、シークレットマスキング、保存機能を提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数・DB パス・YAML ファイル等を検査。`--strict` オプションで警告を FAIL 扱いにできる。

- 環境変数読み込みの改善（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml 基準）による .env 自動ロードを実装。
  - .env のパース機能を強化（export プレフィックス、クォート内エスケープ、インラインコメント処理をサポート）。
  - Settings クラスで多数の設定プロパティを提供（DBパス、paper_trading 用パス、しきい値、PID / Kill flag 関連、PAPER_FILL_MODE など）。

- ロギング・プロセス管理ユーティリティ（src/kabusys/utils）
  - 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を自動設定。
    - LOG_DIR 環境変数や引数でログ出力先を設定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分吸収、権限不足時のフォールバック警告、cpu_affinity 設定機能を提供。

- ポートフォリオ関連純粋関数群（src/kabusys/portfolio/*）
  - 候補選定、重み計算（等金額／スコア加重）、セクター上限適用、レジーム乗数、ポジションサイズ計算（リスクベース／等分配）を実装。
  - position sizing では単元株（lot_size）丸め、aggregate cap によるスケールダウンと余剰配分のアルゴリズムを実装。
  - score が全て 0 の場合は等金額配分にフォールバックする警告を出力。

- Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - SQLite の paper_trading DB を読み、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL 判定を出力する CLI を追加。
  - デフォルト閾値を定義（稼働率 99%、Fill rate 90%、Send rate 95%、P95 レイテンシ 200 ms）。

- DuckDB を分析用に併用する実装を追加（各所で duckdb 接続を受け取る設計を採用）。

### Changed
- Settings API の整理（src/kabusys/config.py）
  - 各種閾値、パス、フラグが Settings プロパティとして明示的に取得可能に（テスト・運用での利用が容易に）。
  - KABUSYS_ENV の有効値チェックを厳格化。

- ロギング設定の挙動を明確化（src/kabusys/utils/logging_setup.py）
  - 既存ハンドラをクリアしてから再設定することでログの二重出力を防止。
  - stdout を標準出力に利用する方針（スケジューラ等でのリダイレクトを想定）。

- 実行フローの安全性向上
  - run_monitoring / run_execution 起動時にプロセス優先度を最初に設定するように変更（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
  - DB 初期化（監視テーブルの存在保証）を冪等に行う処理を追加。

### Fixed
- .env 読み込み時のエスケープ/コメント処理の不具合を修正（src/kabusys/config.py）。
  - クォート内でのバックスラッシュエスケープ対応、コメントの誤認識を改善。

- position_sizing: aggregate cap スケールダウン時の丸め・余剰配分ロジックを改善（src/kabusys/portfolio/position_sizing.py）。
  - lot_size 単位の丸め処理と残余キャッシュを用いた再配分ルールを追加し、合計コストが available_cash を超える場合の挙動を安定化。

- process_priority: 権限不足や未対応 OS での例外ハンドリングを強化（src/kabusys/utils/process_priority.py）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

## [0.1.0] - 2026-04-19

初回公開（推定）: KabuSys の基本機能群を実装した最初の安定的なリリース相当。

### Added
- コアライブラリと CLI
  - プロジェクトのバージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 実行スクリプト: run_execution.py、run_monitoring.py（起動・停止制御、DB接続、ログ設定、優先度設定）。
  - 環境設定: Settings クラスによる環境変数アクセス、.env 自動読み込み。
  - 設定ユーティリティ: config_setup.py（対話的 .env 作成）、validate_config.py（起動前チェック）。
  - ロギングユーティリティ: logging_setup.py（stdout + 日次ローテートログ）。
  - プロセス制御ユーティリティ: process_priority.py（優先度・CPU affinity）。
  - ポートフォリオ構築モジュール: portfolio_builder, risk_adjustment, position_sizing（候補選定〜発注株数算出までの純粋関数）。
  - 分析/ツール: research/factor_research（ファクター計算開始点）、tools/paper_verification_report（ペーパートレード検証レポート）。
  - DuckDB/SQLite を併用したデータ保存・分析フローを導入。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

注:
- 上記は提示いただいたソースコードの内容から推測して作成した変更履歴の例です。実際のコミット履歴やリリースノートはバージョン管理履歴（Git のコミットログ）やリリース担当者の記録に基づいて作成してください。必要ならば、実際の Git 履歴からより正確な CHANGELOG を生成する補助もできます。