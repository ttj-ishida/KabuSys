CHANGELOG
=========

すべての注目すべき変更点はここに記載します。フォーマットは "Keep a Changelog" の形式に準拠しています。

現在のバージョン: 0.1.0 — 2026-04-21
---------------------------------

Added
- 初回公開: KabuSys コードベースの主要コンポーネントを追加しました。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory 経由）を使用し、本番 DB と分離した data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）を利用します。
      - エンジンは別スレッドで実行され、data/execution.pid に PID を出力（pid_file を指定）。
      - 停止は data/stop_requested.flag による検知で安全に行えます。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するエントリポイント。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
      - 監視は環境に関係なく本バイナリで参照される sqlite_path を使用して監視 DB を操作します。
      - 停止は data/stop_requested.flag の検知で終了。
  - 設定関連
    - config.py
      - .env の自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
      - .env/.env.local の読み込み順と OS 環境変数保護（既存の OS 環境変数は上書きされない）。
      - 強力な .env ラインパーサを実装（export 形式、引用符とエスケープ、インラインコメント処理に対応）。
      - Settings クラスを導入し、各種設定値（J-Quants、kabuAPI、DB パス、監視閾値、環境判定など）をプロパティ経由で提供。値検証（有効な列挙値チェックなど）を行う。
      - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などの設定をサポート。
    - config_setup.py
      - 対話式ウィザードで .env の初期作成/更新を支援。秘密項目はマスク表示。生成された .env はコミット禁止を明記。
    - validate_config.py
      - 起動前チェック CLI。必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在および（PyYAML がある場合）パース検証を実行。
      - --strict オプションで警告も失敗扱いにできる。
  - ユーティリティ
    - utils/logging_setup.py
      - 全アプリケーションで統一的に利用できるログ設定ユーティリティを導入。
      - stdout の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を含むファイルハンドラを追加。ログディレクトリは引数、環境変数 LOG_DIR、デフォルト "logs/" の順で解決。ローテーションは 30 日分保持。
      - ハンドラ重複防止のため既存ハンドラをクリアして再設定。
      - ログディレクトリ作成に失敗した場合はファイル出力を無効化して標準出力のみで継続。
    - utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定（psutil 利用）。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
      - アクセス権限不足や未対応プラットフォームは警告を出してスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順＋タイブレークに基づく候補選定。
      - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコアが全て 0 の場合は等分にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中リスク制限（既存保有のセクター比率が上限を超える場合、新規候補を除外）。"unknown" セクターは上限適用除外。
      - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に基づく投下資金乗数。未知のレジームは 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes: 各種配分方式 ("risk_based", "equal", "score") を実装。lot_size（単元）丸め、1銘柄上限・aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer による保守的見積もり、残余キャッシュによる端数配分ロジックを備える。
  - Research
    - research/factor_research.py
      - ファクター計算モジュール（モメンタム、MA、ATR、流動性等）を配置する骨組み。DuckDB 接続を受け prices_daily / raw_financials テーブルに基づく計算方針を明記（実装途中の箇所あり）。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレード DB を解析して検証レポートを生成する CLI。
      - system_status, trade_logs, risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシなどを算出。
      - デフォルトの DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。--from / --to で日付フィルタ可能。
      - 閾値を定義して PASS/FAIL 判定を行う（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms など）。
  - パッケージメタ
    - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- （初回リリースにつき過去バージョンからの変更履歴はなし）

Fixed
- （初回リリースにつき修正履歴はなし）

Notes / 動作上の重要事項
- .env の自動ロードはデフォルトで有効。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env 読み込みは OS 環境変数を保護する設計になっています（既存の OS 環境変数キーは上書きされない）。ただし .env.local は override=True で読み込むため、明示的に上書きされます（ただし OS 環境変数は保護される）。
- run_monitoring の挙動:
  - MONITOR_POLL_INTERVAL は正の整数を期待します。無効な値や 0/負値は無視され、デフォルト 60 秒にフォールバックします（ワーニング出力）。
  - 監視は常に Settings.sqlite_path を使用します（環境に依らず本番監視 DB を参照する意図）。
- run_execution の挙動:
  - paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
- ロギング:
  - デフォルトで logs/<app_name>.log に日次ローテートでログが出力されます。ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- process_priority と CPU affinity の設定は権限や OS に依存します。権限不足時は警告が出て設定がスキップされます。
- Paper Trading レポートはデータ不足やテーブル未存在時に graceful に N/A を表示します。

互換性 / 移行
- 既存の起動方法からの主な差分:
  - 環境変数名・意味は既定の .env フォーマットに従います。新規導入の環境変数:
    - MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START, LOG_DIR（任意）
  - .env は必ず .env.example を参考に作成し、絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- production (live) 環境では validate_config を使って設定を事前に検証することを強く推奨します（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値などをチェック）。

Security
- .env 内のシークレットは対話式ウィザードでマスク表示する設計になっています。なお .env ファイル自体の保護（ファイルシステム権限や CI/CD の機密管理）は別途運用ルールを徹底してください。

今後の予定（例）
- research/factor_research.py の完全実装とユニットテスト整備。
- monitoring および execution の監視・アラート（LINE 通知）実装の拡充。
- 銘柄別 lot_size マスタ対応と position_sizing の拡張テスト。

以上。