# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
重要: ここに記載した変更点は、提示されたコードベースの内容から推測してまとめたものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

### Added
- 起動スクリプトを追加／整備
  - run_execution.py: ExecutionEngine を起動するためのエントリポイントを実装。プロセス優先度設定、停止フラグ検出、専用 PID ファイルの出力、スレッドでのセッション実行と安全な停止処理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグの検知でループ終了。

- 環境設定・管理
  - config.py: Settings クラスを実装し、.env 自動読み込み（.env / .env.local）・環境変数の取得とバリデーションを行うように。PAPER_FILL_MODE の妥当性チェックや各種パス／閾値のプロパティを提供。
  - config_setup.py: 対話式ウィザードで .env ファイルを初期作成／更新する CLI を実装。
  - validate_config.py: 起動前の設定検証 CLI を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML があれば）などをチェック。`--strict` オプションをサポート。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーへ設定するユーティリティを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定機能を実装。Windows/Linux/macOS でのフォールバックと失敗時の警告を実施。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）と等額・スコア加重の重み計算を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method（risk_based / equal / score）に対応、単元株（lot）丸め、max position 制約、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り等をサポート。
  - portfolio/__init__.py: 上記関数群をパブリック API としてエクスポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite (data/paper_trading.db 等) を集計し、稼働率／注文成功率／送信率／レイテンシ（P95）等の指標を算出して PASS/FAIL を判定する CLI ツールを実装。日付範囲フィルタとカスタム DB パスをサポート。

- Research（着手）
  - research/factor_research.py: ファクター計算モジュールの骨格を実装（Momentum 等の計算方針、定数定義、calc_momentum の実装開始）。DuckDB 接続を受け取り prices_daily 等を参照する設計。

### Changed
- データベースの扱いに関する方針明記
  - 監視（monitoring）は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（run_monitoring）。
  - 実行（execution）は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離（run_execution）。

### Fixed / Robustness
- .env 読み込みの堅牢化
  - export 構文、クォート内のバックスラッシュエスケープ、行末コメントの扱いなどに対応したパーサを実装し、.env の解析を堅牢化（config._parse_env_line）。
  - .env 読み込み失敗時は警告で処理を継続（ファイルアクセス例外に対する警告出力）。

- ロギング設定の失敗時挙動
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合は適切に警告を出し、コンソール出力のみで継続するように実装（utils.logging_setup）。

- プロセス優先度 / CPU アフィニティの安全な扱い
  - 権限不足や非対応プラットフォームでは警告を出して処理をスキップするようにし、起動失敗を防止（utils.process_priority）。

- ポジションサイズの丸め・スケーリングロジック
  - 単元株（lot_size）での丸め、合計投資額が利用可能現金を超過した場合のスケーリング、端数（fractional remainder）を用いた残余配分ロジックを実装し、より一貫した発注量配分を実現。

### Documentation / UX
- 各 CLI スクリプトに使用方法の docstring / ヘルプを追加し、ユーザビリティを向上（config_setup, validate_config, tools.paper_verification_report など）。

## [0.1.0] - 2026-04-23

初期リリース相当のまとめ（提示されたコードベースの状態をバージョン 0.1.0 として記述）。

### Added
- プロジェクト基本情報
  - パッケージバージョンを __version__ = "0.1.0" として設定（kabusys/__init__.py）。

- 基本コンポーネント
  - 環境設定 (config.py)、対話式設定ウィザード (config_setup.py)、設定検証 CLI (validate_config.py)。
  - 実行エンジン起動スクリプト (run_execution.py)、監視起動スクリプト (run_monitoring.py)。
  - ロギング設定ユーティリティ (utils.logging_setup.py)、プロセス優先度ユーティリティ (utils.process_priority.py)。
  - ポートフォリオ構築・リスク調整・ポジションサイジングの純関数群（portfolio/）。
  - Paper Trading 検証レポートツール (tools/paper_verification_report.py)。
  - 研究用ファクター計算モジュール（research/factor_research.py の骨格）。

### Changed
- 初期公開版として、上記機能群を統合。

### Fixed
- 起動時・運用時に想定される環境依存問題（ログディレクトリ作成失敗、プロセス優先度設定の失敗、.env 読み込みエラー等）について、例外捕捉と警告出力で起動継続可能な実装とした。

---

今後の提案 / TODO（コードから推測）
- research/factor_research.py の calc_momentum 等ファクター計算の完全実装。
- 各モジュールのユニットテスト追加（特に金融ロジックとポジションサイジングの境界ケース）。
- 単体での CLI テストや E2E のデモ手順ドキュメント化。
- 銘柄ごとの単元株数（lot）を stocks マスタで保持し、銘柄別 lot_size をサポートする拡張。
- position_sizing の price 欠損時のフォールバックロジック（前日終値や取得原価など）。
- monitoring / execution の監視・アラート（LINE 通知等）実装の確認・強化。

---
注: 上記は提示されたソースコードから見える実装内容を基にした CHANGELOG です。実際の commit 単位の差分や既存の履歴が必要な場合は、バージョン管理履歴（git log 等）を参照して正確なエントリを作成してください。