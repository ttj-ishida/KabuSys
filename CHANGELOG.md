CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

注意: 日付はリリース時に更新してください。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- プロジェクト初回公開（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite DB（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動とデーモンスレッド管理を実装。  
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う仕組みを提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は常に本番用の sqlite_path を使用して監視 DB を初期化（init_monitoring_db 呼び出し）。  
    - 停止フラグ検出で優雅にループを終了する挙動を実装。
- 設定管理・ヘルパ
  - config.py: 環境変数・設定管理クラス Settings を実装。  
    - .env 自動ロード（プロジェクトルートの .env / .env.local、OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - J-Quants / kabu API / LINE / DB パス /監視しきい値等のプロパティを提供。PAPER_FILL_MODE の検証、paper_sqlite_path 等を追加。  
    - env 判定 (development, paper_trading, live) と is_live / is_paper / is_dev ヘルパ。
  - config_setup.py: 対話式 .env 作成ウィザードを実装。  
    - デフォルト、選択肢、シークレット入力、既存値の再利用、保存確認、.env 書き込み機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML 有無に応じてスキップ）、本番用ガード（LINE 設定や Kill Switch 設定の注意喚起）を実施。  
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ (純関数)
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）および等重・スコア重み計算（calc_equal_weights, calc_score_weights）を追加。  
    - スコアが全て 0 の場合のフォールバックと警告を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）とレジーム乗数計算（calc_regime_multiplier）を実装。  
    - セクターマップに存在しない銘柄は "unknown" 扱いで上限を適用しない等の挙動を定義。  
    - 未知レジーム時のフォールバックとログ警告を提供。
  - portfolio/position_sizing.py: 株数算出ロジック（calc_position_sizes）を実装。  
    - risk_based / equal / score の配分方式に対応。lot_size による丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的評価、残余キャッシュに基づく端数割当ロジック等を含む。
  - portfolio パッケージ __init__ で主要関数群をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。  
    - stdout ストリームハンドラと日次ローテーションの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30日保持）をルートロガーに設定。既存ハンドラのクリーンアップを行う。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。環境変数 LOG_LEVEL / LOG_DIR をサポート。
  - utils/process_priority.py: プロセス優先度（nice / Windows priority）と CPU affinity 設定ユーティリティを追加。  
    - cross-platform（Windows / Linux / macOS 等）対応を目指し、権限不足や未対応 OS の場合は警告を出してスキップする安全策を採用。
- ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg, max, P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。  
    - 日付フィルタ（--from / --to）、DB パス上書き (--db) をサポート。P95 計算や DB 存在チェックのフォールバックを実装。
- リサーチ（着手）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム／Value／Volatility／Liquidity を想定）。calc_momentum の実装開始（ファイル末尾で未完の箇所あり）。

Changed
- パッケージ初回構成に伴うエクスポートとバージョン情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Fixed
- 多数の安全フォールバックと入力検証を導入
  - 環境変数読み込みのパーサはクォート/エスケープ/インラインコメントを正しく扱うよう実装し、export プレフィックスにも対応。読み込み時に OS 環境変数を保護する仕組みを導入。  
  - MONITOR_POLL_INTERVAL の不正入力（非正の数、数字でない文字列）に対する警告とデフォルトフォールバックを追加。  
  - PAPER_FILL_MODE の値検証を実装（有効値チェック）。  
  - ログディレクトリ作成失敗やプロセス優先度設定失敗時に安全に動作を続行するための警告出力と例外吸収を導入。

Security
- なし

Notes / Implementation details
- run_monitoring / run_execution は停止フラグファイル（data/stop_requested.flag）を用いて外部から優雅に停止できる設計です。また実行時にプロセス優先度を "high" に設定する呼び出しを行います（成功しない環境では警告を出して継続します）。
- ExecutionEngine は paper_trading モードで本番 DB と完全に分離された専用 SQLite を使用する設計です（PAPER_TRADING_SQLITE_PATH で上書き可能）。
- .env の自動読み込みはプロジェクトルートを .git もしくは pyproject.toml から探索することでカレントワーキングディレクトリに依存しないようにしています。
- research/factor_research.py は未完の箇所があります（ファイル末尾が途中で切れているため今後続きの実装が必要です）。

Acknowledgements
- 初回リリース: 基本的な自動売買プラットフォームのコアユーティリティ群（実行/監視/設定/ロギング/ポートフォリオ構築/検証レポート）を提供します。今後は ExecutionEngine や SystemMonitor 本体、ブローカークライアントの実装、ファクター計算の完成、テストやドキュメントの拡充を予定しています。