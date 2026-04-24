CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
概要はコードベースから推測して作成しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: 追加 (Added)、変更 (Changed)、修正 (Fixed)、削除 (Removed) などのカテゴリで記載

Unreleased
----------

- 現在の開発ブランチに未リリースの変更はありません。

[0.1.0] - 2026-04-24
-------------------

Added
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 DB（data/paper_trading.db など）を使用し、MockBrokerClient を使う仕組みを組み込んでいる。停止用フラグファイル (data/stop_requested.flag) の検出、PID ファイル経由での管理、スレッド実行と安全な停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を使用する仕様。
- 設定管理と初期化ツール
  - config.py: .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）、高度な .env パーサ（export 付き行、クォート、エスケープ、インラインコメント処理対応）、Settings クラスによる環境変数アクセスを追加。各種設定プロパティ（DB パス、PID / Kill flag、閾値、環境判定など）を提供。
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新する CLI。既存値の読み込み、シークレットマスク表示、保存前の確認を実装。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パースチェック、--strict オプションで警告を FAIL 扱いにできる機能を追加。
- ログとプロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定するユーティリティを追加。LOG_DIR / LOG_LEVEL の解決順と、ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: psutil を使ったクロスプラットフォームなプロセス優先度設定 (high/normal/low) と CPU affinity 固定関数を追加。Windows / POSIX (Linux, macOS, FreeBSD) を考慮した実装で、権限不足時は警告を出してスキップする安全設計。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル候補選択 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア合計が 0 の場合は警告を出して等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限適用関数 (apply_sector_cap) と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターの扱い、ログ出力、既存ポジションや当日売却予定銘柄の除外対応を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。リスクベース計算、単元株（lot_size）丸め、per-position 上限・aggregate cap、資金スケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した安全な配分ロジックを備える。
  - portfolio/__init__.py: 上記 API をエクスポート。
- リサーチ / ツール
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールを追加（モメンタム、MA、ATR、流動性等を想定）。（注: ファイル末尾はスナップショットのため未完部分あり）
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。期間指定（--from / --to）、DB 指定 (--db) に対応し、稼働率、注文成功率、送信率、レイテンシ（P95 など）に基づいて PASS/FAIL を判定する。デフォルト閾値をコード内で定義（例: 稼働率 >= 99% 、P95 <= 200 ms など）。
- DB 初期化 / 監視連携
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを run_monitoring / run_execution の起動時に行い、監視用テーブルの存在を保証（冪等）。各スクリプトで sqlite3 と duckdb の接続を確立して利用。

Changed
- ログ出力の方針統一
  - すべての起動スクリプトから utils.setup_logging() を呼び出すことで、ログの出力先・回転ポリシー・レベルが統一されるように設計。
- .env 自動読み込みの挙動
  - OS 環境変数優先のまま .env/.env.local を読み込み、.env.local は .env を上書き。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 実行フローの安全性強化
  - run_execution/run_monitoring でプロセス優先度設定を起動直後に行い、監視ループ・エンジン実行時に停止フラグを監視して安全にシャットダウンする設計に統一。

Fixed
- .env パーサの堅牢化
  - export PREFIX 形式、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなどのケースを正しくパースするよう修正（空行・コメント行無視等）。
- ログディレクトリ作成失敗時のフォールバック
  - ファイルハンドラ作成に失敗してもコンソールへの出力は継続されるように改善。警告は stderr / ロガーで通知。

Security
- 秘密情報の取り扱い
  - config_setup の対話式表示でシークレット（API トークンやパスワード）をマスクして画面表示。README / .env では機密情報を Git にコミットしないよう注意書きを付与。

Notes / Implementation details（重要な挙動）
- run_monitoring は KABUSYS_ENV にかかわらず monitoring 用に指定された sqlite_path（Settings.sqlite_path）を使用する。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を整数秒で上書き可能（1 未満や不正値はデフォルト 60 秒にフォールバックし、警告を出力）。
- run_execution は paper_trading 環境時に settings.paper_sqlite_path を使用して本番 DB と完全に分離する。リスク管理の初期値に broker.get_available_cash() を参照している点に注意。
- position_sizing のスケーリング処理は lot_size 単位で端数処理を行い、残余キャッシュを用いて fractional 残差の大きい順に追加配分する再現性のあるアルゴリズムを採用。
- process_priority と set_cpu_affinity は権限・プラットフォームに依存する動作があり、失敗時は警告を出して続行する（例: 権限不足での nice 設定失敗など）。
- validate_config は PyYAML が未インストールの場合、YAML の内容チェックをスキップする（警告を出す）。

BREAKING CHANGES
- なし（初回リリース）

参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ に従い 0.1.0 を初期リリースとしています。