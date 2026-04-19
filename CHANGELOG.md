# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

Added
- 初期リリースを追加。日本株自動売買システム "KabuSys" の基本コンポーネントを実装。
- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じてブローカークライアントを選択（paper_trading 時は MockBrokerClient を利用）。
    - paper_trading 環境では専用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - 停止フラグ (data/stop_requested.flag) の検出、PID ファイル管理、スレッド実行/停止ロジックを実装。
    - ExecutionEngine の起動前に監視テーブルの存在を保証（init_monitoring_db を呼び出し）。
- 監視用スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検出により安全にループを終了。
    - 監視は環境にかかわらず本番用 sqlite_path を参照する挙動（monitoring DB 用）。
    - check_once() 実行時の例外を捕捉しログに記録して次ポーリングへフォールバック。
- 環境設定・検証ツール
  - config_setup: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 必須 / 任意項目の入力、シークレットマスク表示、保存確認機能を提供。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML 有無で挙動分岐）などをチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
- 環境・設定管理
  - config: .env 自動ロード機能と Settings クラスを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - .env / .env.local の自動読み込み（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export プレフィックス、引用符内のエスケープ、インラインコメントの扱い等に対応。
    - Settings による型付きプロパティを多数提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、しきい値など）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject" のみ許容）。
- ログ・プロセスユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - StreamHandler を stdout に設定（cron 等からのリダイレクトを想定）。
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/<app_name>.log、30 日分保持）。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。
    - 既存ハンドラのクリーンアップを行い二重設定を防止。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を追加。
    - psutil を利用し、権限がない場合は警告を出してスキップ。
- ポートフォリオ構成ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + タイブレーク（signal_rank）で BUY 候補を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装（スコア全 0 のとき等分配へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは免除）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を提供（"bull"/"neutral"/"bear" -> 1.0/0.7/0.3、未知レジームは警告と 1.0 フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に対応した発注株数計算を実装。
      - 単元株丸め（lot_size）、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的コスト見積り、残差に対する lot 単位の追加配分ロジックなど。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading データベース（既定: data/paper_trading.db）から指標を算出しレポートを出力。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、平均/最大/P95 レイテンシなどを算出。
    - デフォルト基準値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）による PASS/FAIL 判定を出力。
- research
  - research.factor_research: DuckDB 接続を受け取りファクター（Momentum, Value, Volatility, Liquidity 等）を計算するモジュールの骨格を追加（prices_daily / raw_financials テーブル前提）。一部実装（モメンタム関係）を導入中。
- パッケージ初期設定
  - src/kabusys/__init__.py: バージョンを "0.1.0" に設定し、主要パッケージを __all__ にエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 注意事項
- run_monitoring は監視用 DB として Settings.sqlite_path（デフォルト data/monitoring.db）の使用を明示的に行います。KABUSYS_ENV による自動切替は行いません（監視ログは本番用に一元化する想定）。
- process_priority / cpu affinity の設定は権限や OS 依存のため失敗する可能性があり、その場合は警告ログを出すだけで続行します。
- .env 自動ロードはプロジェクトルートが検出できない環境ではスキップされます（配布後の環境などで発生）。
- research.factor_research モジュールは設計に基づく実装の追加が続く予定です（モジュール末尾で実装が途切れた状態のファイルがあります）。

今後の予定（例）
- strategy、execution の各コンポーネントのテスト充実。
- factor_research の完全実装とユニットテスト。
- 単体ごとのモニタリング・アラート強化（LINE 通知等の統合）。
- 銘柄毎の lot_size をマスタ管理できる拡張（position_sizing の TODO に記載）。

-------------------------------------------------------------------
（本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートはプロジェクト管理規約に従って調整してください。）