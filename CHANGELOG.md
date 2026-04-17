CHANGELOG
=========

すべての重要な変更はここに記載します。  
このファイルは "Keep a Changelog" の形式に従っています。

Unreleased
----------

なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys の基礎的なモジュール群を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite DB (data/paper_trading.db, 環境変数で上書き可能) に記録する。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止はプロジェクト配下 data/stop_requested.flag による。
  - 設定関連
    - config.py: .env の自動読み込み（.env, .env.local）と Settings クラスによる環境変数アクセスを追加。プロジェクトルート探索は .git / pyproject.toml を基準に行う（CWD 非依存）。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加（シークレット入力サポート、既存値の再利用、ファイル出力）。
    - validate_config.py: 起動前チェック用 CLI を追加（必須環境変数、パス、config/*.yaml の存在とパース検証、KABUSYS_ENV に関する注意喚起等）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - portfolio/position_sizing.py: 発注株数計算ロジックを追加（risk_based / equal / score、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り）。
    - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap) と市場レジームによる投下資金乗数 (calc_regime_multiplier) を追加。
  - リサーチ
    - research/factor_research.py: DuckDB を使ったファクター計算モジュールを追加（モメンタム：1M/3M/6M リターン、MA200乖離。ボラティリティ：ATR20、出来高指標等）。DuckDB 接続を受け取り SQL+Python で計算する設計。
  - ユーティリティ
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加（Windows / POSIX に対応、失敗時は警告でスキップ）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間指定、DB パス指定 (--db / 環境変数) に対応。稼働率、注文成功率、送信率、P95 レイテンシ等の指標算出と閾値判定を行う。

Changed
- 設定読み込みの挙動を明確化
  - OS 環境変数を保護するため、.env 自動読み込み時に既存 OS 環境変数を上書きしない（.env.local は override=True で上書きだが、OS 環境変数は保護される）。
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途）。
- DB の扱い
  - 監視 (run_monitoring) は KABUSYS_ENV にかかわらず監視用 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化する設計。
  - 実行 (run_execution) は paper_trading モードで paper_sqlite_path を使用し、本番 DB と確実に分離するよう変更。
- 実行開始前のプロセス優先度設定を起動直後に行うように統一（run_monitoring / run_execution）。
- run_monitoring のポーリング間隔設定を MONITOR_POLL_INTERVAL 環境変数で上書き可能にし、不正値時はデフォルト (60 秒) にフォールバックして警告を出すようにした。
- config_setup.py のウィザードで既存 .env を読み込み、Enter で現在値再利用が可能になった（秘密値は表示をマスク）。

Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの判定ロジック改善、無効行の排除等により現実的な .env フォーマットに耐性を持たせた。
- validate_config.py
  - PyYAML がインストールされていない環境でも動作するように YAML パースをオプショナルにし、未インストール時は警告を出すようにした（config/*.yaml の内容検証をスキップ）。
- process_priority.set_cpu_affinity / set_process_priority
  - 利用可能コア数より大きい cpu_count が渡された場合の扱いや、未対応 OS でのフォールバック動作を明確化。設定失敗時は警告ログを出力して続行する。

Notes / Behavior changes (重要な注意)
- run_monitoring は「環境にかかわらず」Settings.sqlite_path を使い監視 DB を初期化します。開発時に本番の監視 DB を誤って操作しないよう、Settings の環境変数（SQLITE_PATH）設定に注意してください。
- run_execution は paper_trading モードで専用 DB を使用しますが、Settings.paper_sqlite_path を明示的に設定しない場合はデフォルト data/paper_trading.db を使用します。
- calc_score_weights は全スコアが 0.0 の場合に等金額配分へフォールバックし、WARNING をログ出力します。
- calc_position_sizes は単元株（lot_size）丸め、投下資金超過時のスケーリング（端数処理を含む）などのロジックを実装しており、手数料・スリッページ推定を cost_buffer で与えて保守的に見積もることが可能です。

Security
- .env を絶対に Git にコミットしない旨を config_setup.py の出力ヘッダに明記。

Removed / Deprecated
- なし

Acknowledgements
- 本リリースは内部実装に基づく推測により作成された CHANGELOG です。実際のリリースノートは実装者の判断で更新してください。