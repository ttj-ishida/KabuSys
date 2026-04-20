CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-20
--------------------

Added
- 基本アプリケーション骨格を追加（初期リリース）。
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として定義。
- 実行用スクリプトを追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた DB 切り替え（paper_trading 時は専用 SQLite を使用）を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ検出（data/stop_requested.flag）を実装。
    - 実行用 PID ファイルへの対応（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境に依らず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt ハンドリング、接続のクローズ処理を実装。
- 環境設定関連の CLI を追加。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。
    - J-Quants / kabu ステーション / DB パス / LOG_LEVEL / Kill Switch 等の項目を対話で生成・更新可能。
    - 秘匿項目はマスク表示し、保存前に確認プロンプトを表示。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等の妥当性検証、DB パスと config/*.yaml の存在・パース検証、KABUSYS_ENV=live 向けの追加ガードチェックを実装。
    - `--strict` オプションで警告を失敗扱いにできる。
- 環境変数読み込みと設定管理を実装。
  - config.py:
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、.env/.env.local の自動読み込みを提供（OS 環境変数の上書きを防ぐ protected 機構を実装）。
    - 複雑な .env 行パース（export プレフィックス、クォート/エスケープ、インラインコメント処理）に対応。
    - Settings クラスを実装し、各種設定プロパティ（DB パス、PID/kill flag パス、各閾値、PAPER_FILL_MODE の検査、env/log_level の妥当性検証など）を提供。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
- ログ・プロセス管理ユーティリティを追加。
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（daily、30日保持）を設定する共通セットアップを追加。
    - LOG_DIR / LOG_LEVEL による上書き、ディレクトリ作成失敗時はファイルハンドラをスキップする耐障害性を実装。
  - utils/process_priority.py:
    - Windows / POSIX を吸収するプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity を最初 N コアに固定するユーティリティを追加。権限不足・未対応環境では警告でスキップ。
- ポートフォリオ構築周りの純粋関数群を追加（DB 参照なしのメモリ計算）。
  - portfolio/portfolio_builder.py:
    - 候補選定（スコア降順、タイブレーク）、等金額・スコア加重配分関数を実装。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率を計算し、上限超のセクターを新規候補から除外するロジックを実装。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップ）を実装。未知レジームは警告のうえフォールバック。
  - portfolio/position_sizing.py:
    - allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - 単元株丸め（lot_size）、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer の考慮、余り分の配分アルゴリズムを実装。
- Paper Trading 向け解析ツールを追加。
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して標準出力レポートを生成する CLI を追加。
    - 日付範囲指定（--from / --to）と DB パス上書き（--db）に対応。
    - PASS/FAIL 判定の閾値（稼働率、成立率、送信率、P95 レイテンシ）を定義。
- 研究モジュール（factor_research.py）骨子を追加。
  - DuckDB を用いて Momentum / Value / Volatility / Liquidity 等のファクター計算を想定した設計注記を実装（関数シグネチャ・定数定義、注意書きあり）。

Changed
- ロギングの出力先は stdout を優先（cron/Task Scheduler でのリダイレクトに配慮）。
- .env の自動ロードは OS 環境変数を保護する仕組みにより、意図しない上書きを避けるように挙動を明確化。

Fixed
- 起動時のファイルハンドラ作成失敗や権限エラーをハンドリングし、アプリケーションがコンソールログのみで継続できるように改善。

Security
- .env を生成する際に注意書きを付与（.env を Git にコミットしないことを明記）。

Notes
- monitoring の DB 初期化（init_monitoring_db）を起動時に保証することで監視テーブルの欠如による起動失敗を防止。
- 実際の市場発注ロジック・ブローカークライアントの実装は抽象化されており（BrokerClientFactory 等）、paper_trading と live の分離が行われているため、本番 DB とペーパートレード用 DB を明確に分離可能。
- 一部モジュール（research/factor_research.py）は計算ロジックの実装途中または呼び出し側との結合が必要な箇所がある（今後の拡張予定）。

Acknowledgements
- 初期実装のため、今後以下の点の追加・拡張を推奨:
  - 単体テスト・統合テストの追加（特に position sizing／risk logic／CLI）。
  - モジュール間のエラーハンドリング・監視アラート（LINE 通知等）の統合。
  - 銘柄別単元数の扱い拡張（lot_size の銘柄別サポート）。
  - factor_research の完全実装および最適化。