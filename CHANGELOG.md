CHANGELOG
=========

すべての重要な変更点をこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠します。
リリース日はコード内の参照日や現状を踏まえ推定しています。

[Unreleased]
------------

- 特になし（初回リリース）

[0.1.0] - 2026-04-23
-------------------

Added
- 基本アプリケーション骨格を追加
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。
- 起動スクリプト / 実行環境
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を利用する。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag の存在を監視して安全に停止する仕組み。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用して動作（監視データは一元管理）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定・環境管理
  - config.py: 環境変数の読み込み・管理を追加
    - プロジェクトルート自動検出 (.git / pyproject.toml) に基づく .env 自動読み込み（.env, .env.local、OS 環境変数を保護）。
    - 複数の設定プロパティを提供（DB パス、KABUSYS_ENV, LOG_LEVEL, Paper Trading 関連等）。
    - PAPER_FILL_MODE のバリデーションや paper_sqlite_path、閾値設定（CPU/MEM/DISK）等。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（python -m kabusys.config_setup）。
  - validate_config.py: 起動前設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）。
    - --strict オプションで警告もエラー扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップし警告を出すフォールバックあり。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを追加。
    - set_process_priority/set_cpu_affinity を提供。権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定
    - calc_equal_weights, calc_score_weights: 重み計算（score が全て 0 の場合は等配分へフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用するフィルタ
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき株数計算、単元株（lot_size）丸め、aggregate cap によるスケール調整、cost_buffer による保守的コスト推定を実装
  - portfolio/__init__.py で便利関数群をエクスポート
- Research / 分析ツール
  - research/factor_research.py: DuckDB を用いたファクター計算基盤を追加（モメンタム・ATR 等の指針、関数雛形）。
    - design note と定数、calc_momentum の骨格を実装（以降の実装で prices_daily テーブル参照）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を計算し PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。--db / 環境変数で上書き可能。
- その他ユーティリティ
  - tools パッケージ初期化、utils パッケージ初期化ファイル追加。
- DB 初期化補助
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトで呼び出して監視テーブルの存在を保証（冪等）。

Changed
- n/a（初回リリース）

Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line: export 形式、クォート内のエスケープ、行末コメントの扱い等に対応して .env のパースを堅牢化。
- ログ設定時のフェールセーフ
  - logging_setup.setup_logging: ログディレクトリ作成に失敗した場合もコンソールログを継続するよう改善（stderr 出力で警告）。
- ポジションサイズ計算の安定性
  - position_sizing.calc_position_sizes: price がない/ゼロの場合のスキップ処理や aggregate scale-down の端数処理（lot 単位）を実装し安全性を向上。
- Process Priority のクロスプラットフォーム対応強化
  - process_priority.set_process_priority: Windows/POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。

Security
- n/a

Notes / 互換性 / マイグレーション
- 環境変数の自動読み込み
  - デフォルトでプロジェクトルートを検出して .env/.env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB の分離
  - paper_trading モードでは paper_sqlite_path を使い、発注等のデータは本番用 monitoring.db とは分離されます。
- ログファイルと権限
  - ログディレクトリ作成に失敗するとファイル出力は無効化されコンソール出力のみになります。権限のない環境での運用時は注意してください。
- 既知の制限
  - research/factor_research.calc_momentum はファイル上で実装の途中（骨格が見られる）で、完全実装が必要です。DuckDB 側テーブル（prices_daily, raw_financials）に依存するため、環境構築後に実運用での検証が必要です。
  - 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 対応）があります。将来的な拡張予定。

使い方（抜粋）
- 起動スクリプト
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
- 設定ツール
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- レポート
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

貢献 / 開発メモ
- このリリースはコードベースの初期公開と見なされます。今後は以下を優先的に改善予定:
  - research モジュールの完全実装と DuckDB クエリ最適化
  - ExecutionEngine 周りの統合テスト（paper/live 切替含む）
  - 単体テスト・CI の整備
  - 銘柄別単元設定などの position_sizing 拡張

---