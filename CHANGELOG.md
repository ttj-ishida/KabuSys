CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

Added
- 監視・実行の起動スクリプトを追加
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを開始するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止はプロジェクト直下 data/stop_requested.flag により検知。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用（本番 DB と分離）。
    - BrokerClientFactory によりブローカークライアントを切り替え。
    - ExecutionEngine を別スレッドで実行し、停止フラグを監視して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。

Added
- 設定管理・自動読み込み機構を追加
  - src/kabusys/config.py
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local の優先順位（OS 環境変数を保護）。
    - Settings クラスに各種設定プロパティ（DB パス、API トークン、監視閾値、環境判定フラグ等）を実装。
    - PAPER_FILL_MODE（ペーパートレードの約定動作）や PAPER_TRADING_SQLITE_PATH 等のデフォルト・検証を実装。

Added
- 設定支援ツール・検証ツールを追加
  - src/kabusys/config_setup.py
    - 対話式の .env 作成・更新ウィザード。デフォルト値の提示、シークレットのマスク表示、保存確認などを提供。
  - src/kabusys/validate_config.py
    - 起動前設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在／パース確認、live 環境向けの追加警告等を実装。
    - --strict オプションで警告をエラー扱いにできる。

Added
- ログ・プロセス管理ユーティリティを追加
  - src/kabusys/utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定する共通関数 setup_logging を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）を Windows / POSIX に対応して設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限やプラットフォームでフォールバックして安全に動作）。

Added
- ポートフォリオ構築関連モジュールを追加（純粋関数）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックし WARNING を出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄の除外や "unknown" セクターの扱いなど）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知値はフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - 複数の配分方式（risk_based, equal, score）に対応した発注株数計算 calc_position_sizes を実装。
    - 単元株丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュの再配分ロジックを実装。

Added
- Paper Trading 検証レポートツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - SQLite（paper_trading DB）からデータを集計して検証レポートを標準出力に出力する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - デフォルトの合格基準（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200ms）を設定。
    - --from / --to / --db オプションで期間・DB を指定可能。

Added
- 研究・ファクター計算 (DuckDB 利用) の基盤を追加
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity に関する計算方針と定数を定義。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照しファクターを計算する想定（calc_momentum の実装開始）。

Added
- パッケージ初期情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- ドキュメント的な注記・設計方針を多数のモジュールに追記
  - 各モジュールに用途、入力・出力、補足（例: フォールバック動作、TODO）を明記して可読性・保守性を向上。

Fixed
- 環境変数パースの堅牢化（config._parse_env_line）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメント扱いの改善を実装。
  - .env 自動読み込み時に OS 環境変数を保護する protected 機能を実装。

0.1.0 — 2026-04-18
------------------
Added
- 最初の公開リリースとして上記の機能群を同梱:
  - 起動スクリプト（run_monitoring, run_execution）
  - 設定管理・対話ウィザード・検証ツール
  - ロギング・プロセス管理ユーティリティ
  - ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・リスク調整）
  - Paper Trading 検証レポート生成ツール
  - 研究用ファクター計算モジュールの土台
  - パッケージメタ情報（__version__）

Notes
- 一部モジュール（研究用ファクター計算など）は今後の追加実装・テスト整備が想定されます。
- .env と機密値の取り扱いについては .env を絶対にバージョン管理に含めない旨を README / config_setup のヘッダで明記しています。
- 実運用（KABUSYS_ENV=live）時の注意点（LINE 通知設定や Kill Switch の挙動）については validate_config で警告を出す仕組みを備えています。

Security
- 今回のリリースで特定のセキュリティ修正は行っていません。API トークンやパスワードなど機密情報は .env にて管理し、ファイルの取扱いに注意してください。