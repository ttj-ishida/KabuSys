# Changelog

すべての注記は Keep a Changelog 準拠形式で記載しています。  
比較的初期のリリースの想定（version 0.1.0）に基づき、ソースコードから推測される追加機能・改善点・修正点を日本語でまとめています。

注意: 実際のコミット履歴がないため、内容はコードの実装から推測した変更点です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 実行用エントリポイントを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカークライアント生成、各種コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）組み立て、スレッドでのエンジン実行と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイルの検出で安全に終了。
- 設定管理
  - config.py: Settings クラスを実装し、環境変数から各種設定値を取得する API を提供（DB パス、ログ設定、閾値、ペーパートレード設定など）。.env/.env.local の自動読み込み機能を実装（プロジェクトルート検出に .git / pyproject.toml を利用）。自動読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。複数の設定項目（J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等）を対話的に取得して .env に書き込む機能を提供。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、本番環境向けのガード項目などを検証。--strict オプションで警告をエラー扱いに可能。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力をルートロガーに設定。ログディレクトリ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS を考慮）。CPU affinity 固定機能も提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap と、市場レジームに基づく資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: 複数方式（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株丸め、per-position および aggregate のキャップ、cost_buffer を考慮したスケーリング処理を含む。
  - portfolio/__init__.py: 上記 API を公開。
- Paper Trading 用検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を解析して検証レポートを出力する CLI を実装。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを取得して基準（閾値）と比較し PASS/FAIL を判定。
- 研究 / ファクター計算（開始）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity の設計と定数が実装）。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。モメンタム計算関数 calc_momentum の雛形を含む（実装途中）。
- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を定義。

### Changed
- 監視・実行プロセスの挙動
  - モニタリングは環境（KABUSYS_ENV）に関係なく本番用 sqlite_path を使用する実装に変更（意図的に監視用 DB を共通化）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離する仕様を採用。Paper トレード時は MockBrokerClient を使用する想定（BrokerClientFactory 経由）。
- .env パースの堅牢化
  - config._parse_env_line にてシングル/ダブルクォート内のバックスラッシュエスケープ処理やインラインコメントの扱い、export キーワード対応などを実装。より現実的な .env の記述に対応。

### Fixed
- ログ設定の冗長ハンドラ設定防止
  - setup_logging が既存ハンドラをクリアしてから再設定するようになり、二重出力の問題を回避。
- 環境・ファイル存在チェックの改善
  - validate_config にて DB パスの親ディレクトリ存在チェックや PyYAML 未インストール時のフォールバック挙動（警告出力）を実装。

### Documentation / Scripts
- 対話式ウィザードおよび検証ツールに利用方法ドキュメント（docstring と CLI ヘルプ）を充実。起動方法の例や環境変数の説明を各ファイル冒頭に記載。

### Notes / Implementation details
- 多くのモジュールは「DB 参照なし」かつ「純粋関数」として実装されており、ユニットテストしやすい設計が意図されている（portfolio/*.py など）。
- run_* スクリプトは PID / stop flag / kill flag 等を使ったプロセス制御フローを採用しており、デプロイ時の外部制御（停止ファイル操作）に対応。
- 一部モジュール（research/factor_research.calc_momentum 等）は実装途中の箇所が含まれる（ファイル末尾が未完）。今後の実装拡張が想定される。

## Deprecated
- なし

## Removed
- なし

## Security
- なし

------------------------------------------------------------
作成者注: 実際の CHANGELOG.md を生成する場合は、コミット履歴（git log）を参照して差分を正確に記載してください。本ファイルは提示されたソースコードの内容から機能追加・設計意図を推測してまとめたものです。