CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠します。
リリースはセマンティックバージョニングに従います。

[0.1.0] - 2026-04-24
--------------------

Added
- 初回公開: 基本的な自動売買フレームワークを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - プロセス優先度を起動時に "high" に設定。
    - 停止制御はプロジェクト内 data/stop_requested.flag ファイルを監視する方式を採用。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory 経由でブローカークライアントを注入（paper_trading 時は MockBrokerClient を想定）。
    - 実行中の停止は data/stop_requested.flag を参照、PID 管理用の execution.pid を使用。
    - プロセス優先度を起動時に "high" に設定。
  - config.py
    - Settings クラスを追加し、環境変数／.env ファイルからの設定取得を統一。
    - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
    - 環境変数の読み込み順序: OS > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種設定プロパティを追加（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, PID ファイル等）。
    - paper_trading 用の PAPER_FILL_MODE 検証（有効値検査）と PAPER_TRADING_SQLITE_PATH サポート。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。
    - デフォルト値・説明付きで主要な環境変数をガイド表示し .env を生成可能。
    - 生成した .env に対する保存確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス（親ディレクトリ存在チェック）、config/*.yaml の存在と YAML パース検証（PyYAML がインストールされている場合）等を検査。
    - --strict オプションで警告をエラー扱いにできる。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を持つファイルハンドラをルートロガーに設定。
    - ログディレクトリ自動作成、LOG_DIR / LOG_LEVEL 環境変数対応、ファイル作成失敗時はコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX (Linux/macOS/FreeBSD) に対応した優先度設定を実装。
    - CPU affinity を設定する set_cpu_affinity() を追加。
    - アクセス権限不足や未対応環境では警告を出し処理をスキップする安全設計。
  - portfolio モジュール
    - portfolio_builder.py: 候補選定 (select_candidates)、等比率重み (calc_equal_weights)、スコア重み (calc_score_weights) を追加。
    - risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を追加。
    - position_sizing.py: 各銘柄の発注株数計算 calc_position_sizes を追加（risk_based / equal / score の割当方式、lot_size や cost_buffer による調整、aggregate cap のスケーリングロジックを実装）。
    - これらは純粋関数（DB参照なし）として設計され、PortfolioConstruction.md / StrategyModel.md の設計に準拠する想定。
  - tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成スクリプトを追加。
    - 稼働率、注文成立率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。期間フィルタ (--from / --to) をサポート。
    - 基準値（稼働率 99%、fill 90%、send 95%、P95 <= 200ms）を定義。
  - research/factor_research.py
    - DuckDB を用いたファクター計算基盤を追加（モメンタム、MA200乖離、ATR、ボリューム系等を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計（未完パートあり）。
  - パッケージメタ情報
    - __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- .env 解析ロジックの充実（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理、クォート無し時のコメント判定を実装。
  - .env の読み込みで既存環境変数保護（protected set）と override の挙動を明確化。

Security
- .env の取り扱いに関する注意を config_setup.py の出力で明示（.env を絶対にリポジトリにコミットしないことを通知）。

Notes / Implementation details（重要な挙動）
- Monitoring と Execution の停止制御はファイルフラグ（data/stop_requested.flag）を用いる。
- Execution は paper_trading モード時に本番 SQLite を使わず paper_trading 専用 DB を使用することにより、本番 DB との完全分離を目指す。
- setup_logging() はログディレクトリ作成失敗時にファイル出力を諦め、stdout のみで動作を継続するフェールセーフを備える。
- process_priority.set_process_priority() は権限不足（非 root/管理者）や未対応 OS の場合に例外とせず警告でスキップするため、起動が妨げられない設計。
- position_sizing.calc_position_sizes() の aggregate cap スケーリングは lot_size 単位で切り捨て／残差配分を行い、投下資金上限を守る実装。

Acknowledgements
- 本リリースはプロジェクト初期の骨格実装をまとめたものです。各モジュールには将来的な拡張（銘柄別 lot_size、フォールバック価格、追加ファクター等）を想定した TODO コメントが含まれます。

今後の予定（例）
- research モジュールの完遂（ファクター計算の完全実装・テスト）
- ExecutionEngine / Broker クライアントの詳細実装と統合テスト
- 単体テスト・CI の整備と config/ YAML に対する厳密なスキーマ検証

-----