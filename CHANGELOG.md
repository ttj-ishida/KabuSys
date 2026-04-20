CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠します。  
日付はコードベースから推測して付与しています。

Unreleased
----------

- ドキュメント・テスト・細かな調整（今後整理予定）

[0.1.0] - 2026-04-20
--------------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
  - 起動スクリプト / デーモン
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite を使用し、MockBrokerClient を利用可能。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ file による安全停止、例外発生時のログ出力を実装。
  - 設定・環境
    - config.py: Settings クラスを実装し、.env/.env.local の自動読み込み（優先順: OS 環境 > .env.local > .env）や各種環境変数の検証・デフォルト解決を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（--env-file オプション対応）。
    - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict フラグで警告を FAIL 扱いにできる。
  - ポートフォリオ構築関連（純粋関数群、DB 参照なし）
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等金額配分へフォールバックする警告あり。
    - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap と市場レジームに応じた資金乗数 calc_regime_multiplier を実装。
    - portfolio/position_sizing.py: position sizing ロジックを実装。risk_based / equal / score の配分方式、単元（lot_size）丸め、aggregate cap によるスケーリングと残余配分ロジック、コストバッファ考慮を含む。
  - 研究・分析
    - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モメンタム計算関数（calc_momentum）の実装開始（部分的）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ (--from/--to)、DB パス (--db) 指定可。稼働率 / 注文成功率 / 送信率 / レイテンシ（avg/max/P95）を計算し PASS/FAIL 判定を出力。複数閾値を定義（例: 稼働率 >= 99% 等）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR による制御、ディレクトリ作成失敗時はファイル出力をスキップするフォールバックを実装。
    - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。Windows / POSIX の差分吸収、権限不足や未対応環境時は警告でスキップ。
  - モジュール公開
    - kabusys.__init__ にて __version__ = "0.1.0" を設定。portfolio パッケージのエクスポート整理。

Changed
- .env 読み込みの挙動を明確化:
  - _find_project_root() によりパッケージ内からプロジェクトルートを探索（.git または pyproject.toml）。
  - _parse_env_line() が export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - OS 環境変数はデフォルトで保護され、.env.local は .env より優先して上書き可能。
- DB 周り:
  - init_monitoring_db() を呼び出して監視テーブルの存在を保証（冪等）。Monitoring は environment にかかわらず本番 sqlite_path を使用する方針を明文化。
  - Execution は paper_trading 環境時に専用 paper_sqlite_path を使用して本番 DB と分離。
- run_execution の実行フロー:
  - BrokerClientFactory 経由でブローカークライアントを取得。OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドでデーモン起動。停止フラグ監視により安全に停止可能。

Fixed / Robustness
- 環境変数パースの堅牢化:
  - _parse_env_line() においてクォート内のエスケープ処理やコメント扱いの改善を実装し、誤った .env 設定による破壊的挙動を低減。
- 環境検証強化:
  - validate_config にて必須環境変数の有無チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェックと（PyYAML が利用可能な場合の）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
- ログ出力の安全化:
  - logging_setup: ログディレクトリ作成失敗時は明示的に警告を出し、コンソール出力のみで継続する。
- process_priority: 権限不足や未対応プラットフォームでは警告ログを出して処理を継続。

Known limitations / Notes
- research/factor_research.py の calc_momentum 等ファクター計算ロジックは骨格が含まれるが、コードスニペットでは途中まで（未完）です。今後の実装完了が必要。
- position_sizing や risk_adjustment は現状共通 lot_size を想定（銘柄別単元対応は将来の拡張予定）。また price の欠損時のフォールバックについて TODO コメントあり。
- run_monitoring は MONITOR_POLL_INTERVAL が不正（0以下や非数）の場合にデフォルトへフォールバックする仕様。異常値入力時には警告が出力される。
- 一部の外部ライブラリ（psutil, duckdb, PyYAML）が存在しない環境では該当機能が制限される可能性がある（警告でフォールバック）。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

License
- プロジェクトルートのライセンス表記に従うこと。