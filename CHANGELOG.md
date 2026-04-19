CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース (0.1.0) — 日本株自動売買システム "KabuSys" の基礎機能を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI の実装。スレッドでエンジンを起動し、data/execution.pid を使用して PID 管理、data/stop_requested.flag による安全停止をサポート。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。
- 環境設定 / 検証ツール
  - config_setup.py: .env を対話式に作成・更新するウィザードを実装。シークレット入力のマスク、デフォルト提示、選択肢の検証、保存確認等を行う。
  - validate_config.py: .env と config/*.yaml の静的検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML が存在する場合）、本番環境向けのガードチェック（LINE 設定や Kill Switch 設定の注意喚起）を提供。--strict オプションで警告を FAIL 扱いにできる。
  - config.py: 環境変数読み込みロジック（.env 自動ロード）を実装。.env のパースは export プレフィックスやクォート・エスケープ対応、インラインコメント処理を含む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。Settings クラス経由で各種設定値を取得できる（検証付き）。
- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバック（1.0）し、その旨をログ出力する。
  - position_sizing.py: 各銘柄の発注株数決定ロジックを実装。allocation_method("risk_based" / "equal" / "score") に対応。リスクベース計算、単元株丸め(lot_size)、per-position 上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮。価格欠損時のスキップやログ出力あり。
  - portfolio パッケージは主要関数を __all__ で公開。
- 実行周りコンポーネント初期化
  - Execution 側で BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てを行う。RiskManager は初期ポートフォリオ値を broker.get_available_cash() で取得して初期化する。
- 監視・レポート
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して PASS/FAIL 判定（デフォルト閾値を定義）を出力。date 範囲指定 (--from / --to) と DB パス指定 (--db / env) に対応。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを実装。console (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する挙動を採用。
  - utils/process_priority.py: プラットフォーム差分(WINDOWS / POSIX) を吸収してプロセス優先度設定 (high/normal/low) と CPU affinity 設定を提供。アクセス権限不足や未対応 OS の場合は警告ログを出力してスキップする。
- パッケージ情報
  - __init__.py: バージョン情報 __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の注意
- run_monitoring の監視 DB 接続は Settings.sqlite_path（本番の sqlite_path）を使用するように設計されています。環境に応じた監視 DB の分離が必要な場合は設定や実装の見直しが必要です。
- config.py の .env 自動ロードはプロジェクトルート判定に .git または pyproject.toml を使用します。配布済パッケージ等でこれらが存在しない場合は自動ロードがスキップされます。
- position_sizing.calc_position_sizes は lot_size を共通単位として扱います。将来的に銘柄毎の単元をサポートする設計拡張を予定（TODO コメントあり）。
- logging_setup はログディレクトリ作成失敗時に stderr に警告を出します（ハンドラ未設定状態での出力回避のため）。また StreamHandler は stdout を使う設計（cron等で stdout/stderr のリダイレクトを想定）。
- paper_verification_report の閾値（稼働率、成功率、送信率、P95 レイテンシ）はソース内の定数で設定されており、必要に応じて調整してください。

Compatibility / Breaking Changes
- 初回リリースのため既存互換性問題はありません。

Security
- 環境変数に秘匿情報を保持する設計です。.env の Git 管理を厳禁とする旨を config_setup.py ヘッダに明記しています。

以上。￼