# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

最新のリリースや機能追加・修正等は以下を参照してください。

## [Unreleased]

（このファイルはコードベースから推測して作成されています。実際の履歴とは差異がある場合があります。）

### Added
- 実行スクリプトを追加 / 改良
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient（paper_trading 用 DB へ記録）を使用し、本番 DB と分離して動作。
- 設定管理・支援ツール
  - config.py: 環境変数の読み込みロジックを導入。プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。クォートやエスケープ、`export KEY=val` 形式、コメント処理を考慮した堅牢なパーサを実装。PAPER_FILL_MODE の検証や各種設定プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, PID/kill flag パスや監視閾値など）を提供する Settings クラスを追加。
  - config_setup.py: .env を対話的に作成・更新するウィザードを追加（秘密値のマスク表示、デフォルト・選択肢対応、保存時のテンプレート出力）。
  - validate_config.py: 起動前に .env / config/*.yaml の設定不備を検出する CLI を追加（--strict オプションで警告を失敗扱いに可能）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、PyYAML があれば YAML のパース検証、また本番（live）用の安全チェックを実施。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成するスクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）の集計と PASS/FAIL 判定を行う。コマンドライン引数で期間指定および DB パス指定をサポート。
- ポートフォリオ構築ユーティリティ
  - portfolio/portfolio_builder.py: シグナルの候補選定（select_candidates）と重み付け（calc_equal_weights, calc_score_weights。スコアが全て 0 の場合は等分配にフォールバック）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた資金乗数 calc_regime_multiplier を追加（既知レジーム以外は 1.0 にフォールバック）。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。単元株丸め、1 銘柄上限や aggregate cap（利用可能現金超過時にスケールダウン）、cost_buffer を用いた保守的コスト見積り、lot_size による配分の切り上げロジックなどを実装。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーへ設定する。ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR の解決順序をサポート。ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。psutil を利用し、権限不足などを安全にハンドリング。
- その他
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - research/factor_research.py: DuckDB 接続を利用したファクター計算（モメンタム等）のモジュールを追加（関数の骨組み・定数を含む）。calc_momentum の実装開始（ファイルは途中までの実装）。

### Changed
- ログの標準出力先を stdout に設定（utils/logging_setup）。cron 等から起動してログを一括リダイレクトする運用を想定。
- .env 自動ロードの挙動を明確化: OS 環境変数を保護する（.env.local は上書き可能だが OS 環境変数は protected）。
- run_monitoring.py: ポーリングループで停止フラグファイル（data/stop_requested.flag）をチェックする実装を採用。例外発生時にもログを残してループ継続する堅牢化。

### Fixed
- .env パーサの改善により、引用符付き値内のバックスラッシュエスケープやインラインコメントの誤解析を修正（export プレフィックス対応含む）。
- 設定検証ツールで YAML が未インストールの場合にパースチェックをスキップし、適切に警告を出すように変更。

### Documentation
- config_setup.py と validate_config.py に CLI ヘルプと実行手順を記載。config_setup は .env サンプルテンプレートの出力を実装。
- tools/paper_verification_report.py にコマンドラインオプションと出力フォーマット（指標・判定）を記載。

### Internal
- 各モジュールは DB 接続（sqlite3 / duckdb）を受け渡す設計に統一。monitoring 用テーブルの初期化関数 init_monitoring_db を呼び出すことで冪等に監視テーブルを確保する実装。
- run_execution のリスク管理初期化で broker.get_available_cash() を用いて initial_portfolio_value を設定する連携を実装。

---

## [0.1.0] - 2026-04-18

初回公開リリース（コードベースから推測）。上記の追加機能群（実行/監視スクリプト、設定管理・検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、Paper Trading 検証ツール、研究用ファクター計算スケルトン等）を含む。

- See "Added" セクション参照。

---

注意:
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成したものです。実際のコミット履歴やリリースノートと差異がある可能性があります。リリース時には git のコミットログやタグを基に正式な CHANGELOG を生成することを推奨します。