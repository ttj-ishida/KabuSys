CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はセクションごと（Added/Changed/Fixed/Removed/Deprecated/Security）に整理しています。
- 各リリースには日付を付与しています。

[Unreleased]
------------

なし

0.1.0 - 2026-04-19
------------------

初回リリース。以下の主要機能・ユーティリティ・CLI を実装しました。

Added
- 起動スクリプト/ランナー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止用フラグファイル data/stop_requested.flag を検知して安全に終了。
    - Monitoring は実行環境に依らず本番 sqlite_path を使用する仕様。
    - プロセス起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、ペーパートレード専用 DB (data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可) に完全分離して記録。
    - 停止フラグ (data/stop_requested.flag) の検知により実行中エンジンを停止可能。
    - PID ファイル管理 (data/execution.pid) をサポート。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動読み込みを実装（プロジェクトルートを自動判定）。優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - 環境変数の堅牢なパース実装（クォート / エスケープ / コメント処理など）。
    - Settings クラスを提供し、各種設定（DB パス、PID/kill フラグパス、しきい値、環境判定等）をプロパティで取得可能。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- 設定ユーティリティ / CLI
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。
    - デフォルト値、選択肢、シークレット入力の扱いを提供。
    - 生成・保存時に注意（.env を Git にコミットしないこと）をドキュメント化。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数の存在、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース（PyYAML 利用）等を検証。
    - --strict フラグで警告を FAIL 扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収（nice 値 / Windows priority class）。
    - CPU affinity 設定 (set_cpu_affinity) を実装。権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ (純関数群)
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限 (max_sector_pct) に基づき新規候補を除外するロジックを追加。既存保有のセクター時価を計算し、"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes を実装。allocation_method に応じて発注株数を算出（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash に合わせたスケーリング）、保守的コストバッファ (cost_buffer) を考慮。
    - スケールダウン時に残差を lot_size 単位で再配分するロジックを実装。
- 分析 / 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照し、稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）などを出力。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。期間指定 --from / --to と DB パス --db をサポート。
- リサーチ / ファクター計算
  - research/factor_research.py（ファイル追加）
    - DuckDB 接続を受け取り prices_daily / raw_financials を利用してモメンタム・バリュー・ボラティリティ・流動性等のファクターを計算する設計。関数 calc_momentum の実装開始（モメンタム関連定数とインタフェースを定義）。（注: 本リリースでは一部実装が継続中）
- パッケージ基礎
  - kabusys.__version__ を "0.1.0" に設定。
  - パッケージエクスポート（__all__）を整備（data/strategy/execution/monitoring 等を想定）。

Changed
- 環境変数の取り扱い
  - .env の自動読み込み戦略を導入（プロジェクトルート検出により CWD 非依存で動作）。
  - .env 読み込み時の既存 OS 環境変数の保護処理を実装。
- ログ出力
  - stdout を使用する方針（cron 等とのリダイレクト運用を考慮）。既存ハンドラをクリアしてから再設定することで二重ログ出力を防止。

Fixed
- なし（初回リリースのためバグフィックス履歴はなし）。

Removed
- なし。

Deprecated
- なし。

Security
- 秘密トークンは Settings 経由で要求され、config_setup ウィザードでは画面表示時にマスクして扱う等の配慮を実装。ただし .env 自体は平文で保存される点に注意。

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる可能性あり。将来的に前日終値や取得原価へのフォールバックを検討（コード内に TODO）。
- research/factor_research.py:
  - ファイルは追加されモメンタム計算の枠組みが始まっているが、calc_momentum の実装の途中でファイルが切れている（本リリースでは継続実装が必要）。
- process_priority / set_cpu_affinity:
  - 権限不足 (psutil.AccessDenied) や未対応 OS の場合は警告を出してスキップする設計。運用環境では適切な権限確認が必要。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイルログを無効化してコンソールのみで継続。運用時は LOG_DIR の書き込み権限を確認してください。
- validate_config の YAML 検証は PyYAML 未インストール時はスキップされる（警告）。
- run_execution/run_monitoring の停止は stop flag ファイルの存在確認に依存する。外部運用ツールによる flag 管理方法を運用ドキュメントで定義推奨。

Usage highlights
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動:
  - python -m kabusys.run_monitoring  (MONITOR_POLL_INTERVAL 環境変数で間隔調整)
- 実行エンジン起動:
  - python -m kabusys.run_execution  (KABUSYS_ENV=paper_trading でペーパートレード)
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス / コントリビューション
- 初回リリース。今後のバグ修正・機能追加はセクションを追記して管理します。

お問い合わせ
- 実運用前に validate_config を必ず実行し、必須環境変数や本番用フラグ（KABUSYS_ENV=live）に伴う注意点（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を確認してください。