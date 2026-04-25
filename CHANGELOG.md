# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルは、リポジトリ内のソースコードから機能追加・改善点・修正点を推測してまとめたものです。

## [Unreleased]

### 追加
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルートの data/stop_requested.flag により行う。監視はどの環境でも本番用 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録する。停止フラグ、PID ファイルによる制御をサポート。

- 設定・環境管理
  - config.py: .env の自動読み込み（.env, .env.local）を実装。プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入。環境変数のパース機能（クォート・エスケープ・インラインコメント対応）、設定読み込み時の上書き制御（protected set）を実装。Settings クラスを追加し、各種設定（DB パス、API トークン、監視しきい値、環境種別など）をプロパティ経由で取得可能に。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。デフォルト値・選択肢表示、シークレット入力、.env 書き出し機能を提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML が未インストール時は警告）を実装。--strict モード対応。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク処理）、等重み・スコア重みによる重み計算を実装。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。risk_based / equal / score の複数方式に対応。単元株（lot_size）丸め、ポジション上限（max_position_pct）、投下資金上限（max_utilization）、コストバッファ、aggregate cap によるスケールダウン処理、端数配分ロジックを提供。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバック挙動を明記。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout に対する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力を提供。LOG_LEVEL/LOG_DIR を尊重し、既存ハンドラをクリアして二重設定を防止。ファイルハンドラ作成失敗時はコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定と CPU affinity 設定を実装。権限不足や未対応 OS の場合は警告を出してスキップする。

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出し、PASS/FAIL 判定を行う。閾値や P95 計算ロジックを実装。DB パスを引数または環境変数で指定可能。

- リサーチ（未完/着手）
  - research/factor_research.py: DuckDB 接続を受けてファクター（Momentum, Value, Volatility, Liquidity）を計算するモジュールの骨格を追加。設計方針と定数を整備。関数の一部（calc_momentum 等）の実装が開始されている（ファイル末尾で途中）。

### 変更（設計上の重要点）
- .env 自動読み込みの仕様を明示
  - OS 環境変数の優先度が高く、.env は既存の OS 環境変数を上書きしない（.env.local は上書き可能）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- run_monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する（監視 DB は常に production path を想定）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使って DB を完全分離する（本番 DB と混ざらない設計）。
- ロギングは標準出力（stdout）を使用するため、cron やスケジューラで stdout/stderr をリダイレクトする運用が容易。

### 修正（堅牢性・エラーハンドリング）
- 環境変数パーサでのクォート・バックスラッシュエスケープ対応を実装し、.env の柔軟な表記に対応。
- MONITOR_POLL_INTERVAL の不正値（非数値・0 以下）に対してフォールバック処理と警告ログを追加。
- プロセス優先度設定や CPU affinity 設定でのアクセス権限エラーや未対応例外を捕捉し、警告を出して安全にスキップする実装に改善。
- logging_setup: ログディレクトリ作成失敗時のフォールバック挙動（StreamHandler のみ）を明確化。
- validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告を出すようにした（依存ライブラリがなくても実行可能）。

### ドキュメント（コード内コメント・使用例）
- 各種起動スクリプト、CLI、ユーティリティに使用方法コメントを追加（モジュール頭部 docstring）。config_setup と validate_config の使い方を明示。

### 既知の注意点 / 互換性に関する変更
- Monitoring（run_monitoring）は環境に関係なく sqlite_path を使うため、開発環境で監視 DB を分離したい場合は sqlite_path を環境変数で指定する必要がある。
- .env 自動読み込みが行われるため、テスト環境等で明示的に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
- research/factor_research.py の実装は途中のため、本番利用時は追加実装が必要。

## [0.1.0] - 2026-04-25

初回リリース想定のまとめ。上記 Unreleased の内容を初期リリースとしてまとめた想定リリースノート。

### 追加
- 基本的な自動売買システムの土台を実装:
  - 起動スクリプト: run_execution, run_monitoring
  - 設定管理: config, config_setup（対話式 .env ウィザード）、validate_config（検証 CLI）
  - ポートフォリオ構築: portfolio モジュール（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）
  - 実行関連プレースホルダ: BrokerFactory, ExecutionEngine 等（呼び出し配置）
  - ユーティリティ: logging_setup（統一ログ設定）、process_priority（優先度/CPU affinity）
  - ツール: paper_verification_report（ペーパートレード検証レポート生成）
  - リサーチ: factor_research の骨格（DuckDB を用いるファクター計算）

### 修正 / 改善
- エラーハンドリングの強化（ファイル/ディレクトリ作成、外部ライブラリ未存在、環境変数不正値などに対するフォールバックと警告）。
- ペーパートレードと本番 DB の分離（paper_trading 用 sqlite path を導入）。

### 破壊的変更
- なし（初回リリース想定のため）。ただし、Monitoring の DB 運用に関する挙動（常に sqlite_path を使用）には注意。

---

補足:
- 主な環境変数（デフォルトを含む）:
  - KABUSYS_ENV (development|paper_trading|live) — default: development
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - LOG_DIR — default: logs/
  - MONITOR_POLL_INTERVAL — default: 60
  - KILL_FLAG_CLEAR_ON_START — default: 0
  - PAPER_FILL_MODE — default: instant (値: instant|partial|never|reject)

この CHANGELOG はソースコードの現状から推測して作成しています。実際の変更履歴・リリース計画と異なる場合がありますので、正式なリリース時には適宜調整してください。