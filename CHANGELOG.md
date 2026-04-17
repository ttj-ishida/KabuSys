CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- パッケージ初期リリース。
- 実行用スクリプト・CLI を追加:
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag ファイルで制御。監視 DB は環境にかかわらず本番 sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用して data/paper_trading.db に記録することで本番 DB と完全分離。起動前に停止フラグ確認、PID ファイル出力、デーモンスレッドでのエンジン実行・停止処理を行う。
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加（.env の既存値読み込み、シークレットマスク表示、保存確認など）。
  - kabusys.validate_config: .env および config/*.yaml の基本整合性検証 CLI を追加。--strict モードで警告を FAIL として扱う。PyYAML がない場合は YAML 検証をスキップして警告を出す。
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。期間指定（--from/--to）や DB パス指定（--db）をサポートし、稼働率・注文成功率・送信率・レイテンシ（P95 など）を計算して PASS/FAIL 判定を出力する。
- 設定管理:
  - kabusys.config: 環境変数の自動ロード機構を追加（プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込む）。.env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント等に対応。環境変数の必須チェックを行う _require と Settings クラスを提供。
  - Settings に多数の便利プロパティを追加（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID/KILL flag パス、閾値設定、env/log_level 判定など）。paper_fill_mode のバリデーションを実装。
- ポートフォリオ構築モジュール（純粋関数群）を追加:
  - kabusys.portfolio.portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - kabusys.portfolio.risk_adjustment: apply_sector_cap（既存保有のセクター露出が閾値を超える場合に同セクターの新規候補を除外、"unknown" セクターは上限適用除外）と calc_regime_multiplier（market regime に応じた投下資金乗数）を実装。
  - kabusys.portfolio.position_sizing: calc_position_sizes を実装（allocation_method="risk_based" / "equal" / "score"、単元株（lot_size）丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate スケールダウンと残差配分ロジックを実装）。
  - kabusys.portfolio.__init__ で上記関数を公開。
- 研究用ファクタ計算モジュールを追加:
  - kabusys.research.factor_research: DuckDB 接続を用いたファクター計算関数を実装（calc_momentum, calc_volatility）。モメンタム（1M/3M/6M、MA200 乖離）、ATR 等のボラティリティ / 流動性指標を DuckDB SQL で算出する設計。
- ユーティリティ:
  - kabusys.utils.process_priority: クロスプラットフォームでカレントプロセスの優先度（high/normal/low）および CPU affinity 固定（最初 N コア）を設定するユーティリティを実装。Windows / POSIX 差分を吸収し、権限不足などは警告を出してスキップする堅牢性を持つ。
- その他:
  - パッケージ初期バージョンとして __version__ = "0.1.0" を設定。

Changed
- .env の読み込み順を明確化: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
- run_monitoring/run_execution 起動時にプロセス優先度を最初に "high" に設定するように統一。

Fixed
- 不正な MONITOR_POLL_INTERVAL の値（非整数や 0 以下）を検出し、デフォルトにフォールバックして警告を出す実装を追加（run_monitoring）。
- DuckDB/SQLite の存在やテーブル欠如による例外を拾ってデフォルト値にフォールバックしてレポート出力を継続するよう paper_verification_report にて配慮。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / 使用上の注意
- run_monitoring は KABUSYS_ENV に依らず settings.sqlite_path（本番向けパス）を使用します。ペーパートレード用の監視データを分離したい場合は別途設定を変更してください。
- run_execution は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）を使用します。ペーパートレードと本稼働の DB が混在しないよう設計されています。
- .env 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後や特殊な配置では自動ロードがスキップされる場合があります（その場合は環境変数を明示的に設定してください）。
- position_sizing の lot_size は現状グローバル一律の想定（例: 100）。銘柄別単元対応は将来的な拡張を想定。
- calc_regime_multiplier は未知のレジーム文字列で警告を出し 1.0 にフォールバックします。Bear レジーム時には一般に BUY シグナルが生成されない設計（戦略側の仕様）に注意してください。

参考
- 各 CLI のヘルプは python -m <module> または --help で参照できます（例: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）。