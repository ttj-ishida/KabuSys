# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このファイルは、ソースツリーの現状から推測して作成した変更履歴です。

## Unreleased
（このスナップショット時点でリリースに向けてまとまっていない変更や今後の予定項目を記載する想定です。現状は主要機能の初期実装が含まれています。）

### Added
- 基本機能の初期実装を追加（自動売買システムのコアモジュール群）。
  - 環境/設定関連
    - Settings クラスによる環境変数管理（`.env` の自動ロード、必須値チェック、各種パス・閾値取得）。
    - .env ファイルの対話式ウィザード (config_setup.py) を追加。初回セットアップや既存 .env の更新を支援し、テンプレートの書き込みを行う。
    - validate_config CLI を追加し、起動前に環境変数や config/*.yaml ファイルの妥当性を検証可能に（--strict オプションで警告を失敗扱いにできる）。
    - .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサーの強化: export 構文、クォート、インラインコメント、エスケープを考慮した堅牢な実装。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じたブローカークライアント（paper_trading 時は MockBrokerClient）を利用し、paper_trading の場合は専用 SQLite（デフォルト: data/paper_trading.db）で完全分離して記録する。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視の初期化ではプロセス優先度を上げる処理を含む。
    - 実行/監視の停止制御として data/stop_requested.flag（停止フラグ）や PID ファイルの扱いを実装。
  - ポートフォリオ構築関連（純粋関数群、DB 非依存）
    - portfolio_builder: 候補選定（スコア降順、シグナルランクによるタイブレーク）、等重み・スコア重みの計算ロジックを追加。
    - position_sizing: 発注株数計算（risk_based / equal / score）、単元株（lot）丸め、aggregate cap によるスケールダウンと端数処理を実装。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバック動作も定義。
  - 研究用モジュール
    - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、ボラティリティ、流動性等の算出）。prices_daily テーブルを用いて P95 等の指標を計算する設計。
  - ユーティリティ
    - utils/process_priority.py: Windows/Linux/macOS 間の差を吸収するプロセス優先度設定ユーティリティ（nice 値・priority クラス設定、CPU affinity 設定用関数も実装）。権限不足時のフォールバック処理あり。
  - ツール
    - tools/paper_verification_report.py: ペーパートレーディング用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定できる。期間指定と DB パス指定オプションをサポート。

### Changed
- デフォルト構成／運用ポリシーの決定
  - 監視（run_monitoring）は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する設計になっている旨を明示（監視データは環境に依存せず一箇所に集める方針）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全分離する実装とした（テストと検証の安全性向上）。
- Settings クラスでの入力検証を強化
  - env 値や LOG_LEVEL、PAPER_FILL_MODE 等に対する妥当性チェック（不正値は例外で通知）を追加。
  - PATH 系設定（DUCKDB_PATH, SQLITE_PATH 等）のデフォルトと expanduser 処理を明示。
- config/ YAML 検証ロジック
  - validate_config は PyYAML 未導入時にパース検証をスキップして警告を出すようにし、存在チェックやパースエラーの報告を行う。

### Fixed
- .env 読み込み時の IO エラーを警告に変換して処理を継続するように改善（テストや CI 環境での柔軟性向上）。
- process_priority の設定失敗時にプロセスが停止しないよう、例外をキャッチして警告ログに留めるようにした。

### Security
- .env を Git にコミットしないように対話ウィザード出力やテンプレートに明示的な注意書きを追加。

---

## [0.1.0] - 2026-04-17
初回公開想定のベース実装。

### Added
- 上記 Unreleased の主要機能をこのバージョンとしてまとめてリリース。
  - 環境設定管理（Settings, .env 自動読み込み、config_setup ウィザード）
  - 設定検証 CLI（validate_config）
  - 実行および監視のエントリポイント（run_execution, run_monitoring）
  - ポートフォリオ構築・リスク調整・ポジションサイズ計算（portfolio モジュール群）
  - ファクター計算（research/factor_research）
  - ペーパートレード検証レポートツール（tools/paper_verification_report）
  - プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority）

### Notes
- バージョン番号はパッケージ内の __version__ を反映（"0.1.0"）。
- このリリースはシステムの骨格と複数の CLI/ツール群を含む初期段階の実装であり、将来的に単体テスト、ドキュメント充実、ログ設定やエラーハンドリングの強化、並列処理や BrokerClient の詳細実装などが予定されます。

---

注: 本 CHANGELOG は提供されたコードの内容から推測して作成しています。実際のリリースノートには、コミット履歴やリリース時の差分を基にした正確な変更点・著者・関連Issue等を追記してください。