Keep a Changelog 準拠の CHANGELOG.md（日本語）

全ての重要な変更点を追跡するためにこのファイルを使用します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 以下はリポジトリ内のソースコード（CLI、ユーティリティ、ポートフォリオ構築ロジック、実行/監視ループ等）の内容から推測して作成した変更履歴です。

Unreleased
---------
- Added
  - 今後対応予定の改善点や未実装箇所を記載。
    - portfolio/position_sizing: 将来的な拡張として銘柄ごとの単元（lot_size）を stocks マスタで管理する設計を検討中（TODO）。
    - portfolio/risk_adjustment: price が欠損した場合のフォールバック（前日終値や取得原価等）の実装検討。
    - research/factor_research: モジュールの続き（calc_momentum の実装途中でファイルが途切れている箇所）を完成させ、他ファクター（Value, Volatility, Liquidity）を統合予定。
- Changed
  - ドキュメント化・ログ出力の改善（ログフォーマットやデフォルト設定の見直し予定）。
- Fixed
  - なし（未公開の修正/調整をここに記載予定）。

[0.1.0] - 2026-04-21
-------------------
Added
- 基本アプリケーション構成
  - パッケージメタ情報にバージョンを追加: kabusys.__version__ = "0.1.0"。
- 環境設定管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数の読み込み・検証を担う Settings とグローバル settings インスタンスを導入。
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env パース機能: export 構文、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 各種設定プロパティ（J-Quants / kabuステーション / DB パス / Paper Trading 用 DB / 監視閾値 / ログレベル 等）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- 環境設定ユーティリティ
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）
    - ユーザー対話により .env を作成・更新する CLI を追加。
    - シークレット値マスキング表示、既存 .env 読み込み、確認プロンプト、保存機能を提供。
- 設定検証ツール
  - validate_config CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の基本検証を実行するコマンドを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML の存在/パースチェック（PyYAML 未インストール時は警告）、本番時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性）を実装。
    - --strict オプションで警告も失敗として扱う。
- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成（Paper 用の MockBroker を想定）。
    - OrderRepository、OrderManager、RiskManager（RiskConfig を含む）、Reconciler を組み立て、ExecutionEngine.run_session をデーモンスレッドで起動。
    - data/execution.pid の PID ファイル、data/stop_requested.flag による停止制御をサポート。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を定期ポーリングで実行するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境に関係なく本番 sqlite_path を使用する（監視データは共有）。
    - stop フラグ（data/stop_requested.flag）で安全停止。
- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを各起動処理内で行い、監視用テーブルが存在することを保証（冪等化）。
- ログ設定ユーティリティ
  - setup_logging（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログレベル/ログディレクトリの決定順序（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしコンソール出力のみで継続。
- プロセス優先度 & CPU affinity
  - process_priority ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/Mac 等の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - psutil のアクセス権限や未サポート OS を考慮してフォールバック・警告を出す設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加（src/kabusys/portfolio/）
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順に選出。
      - calc_equal_weights / calc_score_weights: 等金額 / スコア加重の重み計算。スコアが全て0の場合は等分にフォールバック。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限の実装（sell_codes を考慮、"unknown" セクターは上限制御しない）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear マップ。未定義時はフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいた発注株数計算、単元株丸め、per-stock と aggregate の上限（max_position_pct, max_utilization）、コストバッファ考慮のスケーリングロジックを実装。
      - スケールダウン時の端数配分アルゴリズムを実装（lot_size 単位で再配分）。
- リサーチ / ファクター
  - research/factor_research.py（ファクター計算の骨格）
    - モメンタム（1M/3M/6M、MA200乖離）、ATR、出来高等を計算する設計方針と定数を追加。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針。
    - calc_momentum の冒頭（定義・定数）を追加（実装続行予定）。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み込み、以下の指標を集計・出力する CLI を追加:
      - システム稼働率 (uptime)、ポーリングエラー数
      - 注文成功率 (Filled/Created)、送信率 (Sent/Created)
      - リスク却下数 (risk_logs)
      - レイテンシ（avg/max/P95）
    - PASS/FAIL の閾値を導入（稼働率 99% / 成功率 90% / 送信率 95% / P95 latency 200ms）。
    - --from/--to/--db オプションをサポート。
- 実行/監視の共通動作
  - 起動時にプロセス優先度を "high" に設定する呼び出しを追加（実行スクリプト両方で実行）。
  - stop フラグによる安全停止と、KeyboardInterrupt による整然とした終了処理を実装。
  - SQLite / DuckDB 接続の確立とクローズ処理を適切に行う設計。

Changed
- なし（新規初期リリース）。

Fixed
- なし（新規初期リリース）。

Security
- なし特記。ただし .env は絶対に Git にコミットしないように config_setup のヘッダで注意喚起を追加。

Deprecated
- なし。

Removed
- なし。

Notes / Known issues
- research/factor_research.py が途中で切れている（calc_momentum の実装継続が必要）。
- portfolio/position_sizing の注記として、price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的なフォールバック価格の導入が推奨される。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、権限不足時はフォールバック動作（ファイル出力無効化や警告）となる。
- config/*.yaml の内容検証は PyYAML に依存（未インストール時はパースチェックをスキップして警告）。

作者注
- 本 CHANGELOG はリポジトリ内のソースコードの構造・コメント・実装から推測して作成しました。実際のコミット履歴に基づくものではありません。必要であれば、実際のコミット履歴（git log）を元に詳細な履歴を作成できます。