CHANGELOG
=========

すべての注目すべき変更履歴はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。主にコードベースから推測された機能追加・設計意図・重要な挙動を記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アプリケーション初期リリース（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動ロジックを提供。バックグラウンドスレッドで run_session を実行し、data/execution.pid に PID を管理。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を実装（モック/実ブローカ切替を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせてエンジンを構築。
    - 停止フラグファイル（data/stop_requested.flag）検出で安全にシャットダウン。
    - RiskManager 初期設定に initial_portfolio_value = broker.get_available_cash() を使用する設定を導入。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。既定ポーリング間隔は 60 秒。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（整数値のみ; 0以下や不正値はデフォルトにフォールバック）。
    - 監視では環境にかかわらず production 用の sqlite_path を使用する設計（監視データは本番 DB を参照）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt にも対応。
- 環境設定 / 検証ツール
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサは引用符付き値のエスケープ・インラインコメント処理に対応。
    - 各種環境変数の取得用 Settings クラスを公開（J-Quants / kabuAPI / DB パス / PaperTrading 設定 / 監視閾値 等）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - KABUSYS_ENV, LOG_LEVEL のバリデーションと便利なプロパティ（is_live / is_paper / is_dev）。
  - config_setup.py
    - インタラクティブな .env ウィザードを実装。デフォルト・既存値読み込み、シークレット値のマスク表示、確認・保存まで。
  - validate_config.py
    - 起動前検証 CLI。必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番用追加ガード等を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点は signal_rank）で候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数 (bull/neutral/bear) を返す。未知レジームはフォールバック 1.0。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based","equal","score") に応じて発注株数を計算。lot_size（単元）で丸め、per-stock 上限・aggregate cap（available_cash）を考慮したスケーリングアルゴリズムを実装。
    - cost_buffer による手数料/スリッページ保守見積り、残差に基づくラウンドアップ配分をサポート。
- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで耐障害性を確保。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト(INFO)。
  - utils/process_priority.py
    - プラットフォームに依存しないプロセス優先度設定関数 set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - Windows の優先度クラス、POSIX nice 値を考慮し、失敗時は警告を出す堅牢設計。
    - set_cpu_affinity(cpu_count) により最初の N コアに固定する機能を提供（権限不足などは警告でスキップ）。
- 分析/Research
  - research/factor_research.py
    - ファクター計算の骨格（モメンタム/MA/ATR/流動性等）の実装開始。DuckDB の prices_daily 等テーブルを利用する設計。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI。PAPER_TRADING_SQLITE_PATH を介してペーパートレード DB を読み取り、稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）・リスク却下数を算出し Pass/Fail 判定（閾値をソース内定義）でレポートを出力。

Changed
- ログの標準出力先を stderr ではなく stdout に統一（cron/task runner とのリダイレクトを想定）。
- .env 自動読み込みは OS 環境変数を保護する設計（.env.local は上書き可能だが OS 環境変数は保護される）。
- Monitoring のデフォルト挙動: 環境設定に関わらず監視 DB は production 用 sqlite_path を使用する旨を明記（run_monitoring）。

Fixed
- 各所でのエラー耐性向上:
  - run_monitoring と run_execution は stop flag を検出して安全に終了する。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に、プロセスが致命的に停止しないようフォールバックを実装。
  - process_priority の権限不足や未サポート OS を警告で扱うようにして無停止運用を可能にした。

Notes
- 設定/運用に関する注意点
  - .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダに明記）。
  - 本番運用時は KABUSYS_ENV=live に注意（validate_config が追加の警告を出す）。LINE 通知設定が未設定だとアラートが届かない点に注意。
  - KILL_FLAG_CLEAR_ON_START は本番で 1 に設定すると危険（自動クリアされるため）。
- 監視と execution の DB 分離設計
  - Execution の paper_trading モードは paper_sqlite_path を使用し本番データと切り離す。監視は別途本番監視 DB を参照する（設計上の意図と注意事項）。
- 未完成 / TODO
  - research/factor_research.py はモメンタム計算等の具体実装（SQL 部分）が途中であるため、追加実装および単体テストが必要。
  - position_sizing の price フォールバック（当日価格が欠損する場合の扱い）など将来的な改善項目をコメントで示している。

Authors
- KabuSys 開発チーム（コードベースから推測して記述）

参考
- バージョンは src/kabusys/__init__.py の __version__ に従っています。