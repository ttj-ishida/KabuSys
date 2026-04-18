CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-18
-----------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
- 実行・監視用エントリポイントを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、モックブローカー経由でペーパートレードを行う設計。
  - run_monitoring.py: SystemMonitor を起動するポーリングループスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 両スクリプトとも停止フラグ（data/stop_requested.flag）と pid ファイルの取り扱いを実装。
- 環境設定関連 CLI を追加:
  - config_setup.py: 対話式ウィザードで .env の初期作成／更新を支援。必須項目やデフォルト値を提示し、シークレット項目はマスク表示。保存前に確認プロンプトを実装。
  - validate_config.py: .env と config/*.yaml の検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、YAML パース（PyYAML が未インストールの場合は警告）等を行う。--strict オプションで警告を失敗扱いにできる。
- 環境変数ローダーと設定管理:
  - config.py: プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local）。自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の設定プロパティを実装。
  - .env のパースは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント処理など複数ケースに対応。
- ロギング基盤:
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ自動作成（失敗時はファイル出力をスキップ）と 30 日分のローテーション保持を実装。LOG_DIR / LOG_LEVEL からの解決をサポート。
- プロセス優先度・CPU 固定ユーティリティ:
  - utils/process_priority.py: Windows / POSIX（Linux/Mac等）に対応した set_process_priority と set_cpu_affinity を追加。アクセス権限や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全ゼロ時は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装（regime: bull/neutral/bear を考慮）。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method（risk_based / equal / score）に対応し、lot_size（単元株）、cost_buffer（手数料/スリッページ見積り）や aggregate cap によるスケーリング処理を実装。
  - package-level エクスポートを追加（kabusys.portfolio.*）。
- 解析・検証ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを SQLite のテーブルから集計し PASS/FAIL 判定を行う。期間フィルタ (--from / --to / --db) をサポート。
- 研究用ファクターモジュールの追加（research/factor_research.py）。DuckDB 接続を受け prices_daily/raw_financials テーブルに基づいてファクター（Momentum, Value, Volatility, Liquidity）を計算する設計。純粋関数で結果を返す方針を採用。

Changed
- 監視・実行起動の挙動:
  - run_execution: Paper trading 時に専用 DB を用いるように明示（settings.is_paper 判定）。
  - run_monitoring: ポーリングループ実行前にプロセス優先度を High に設定、予期せぬ例外はループ内でキャッチして次回ポーリングへ継続する耐障害性を追加。
- .env 読み込みの既定動作を OS 環境変数優先（.env を上書きしない）/ .env.local は上書き可能 に調整。
- ログ出力を stdout に統一して StreamHandler を標準装備（cron 等からの起動を想定）。

Fixed
- 環境変数解析の堅牢化:
  - _parse_env_line で export プレフィックスやクォートされた値、バックスラッシュエスケープ、インラインコメントの取り扱いを改善。無効行の除外処理を明確化。
- DB 初期化の冪等性:
  - run_execution / run_monitoring 起動時に monitoring 用テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（存在しない場合に作成）。
- Paper Trading 用の DB 分離:
  - 誤って本番監視 DB にペーパートレードデータを書き込まないよう paper_sqlite_path を優先するロジックを run_execution に導入。

Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で切れている（ソースが途中まで）。完全なファクター計算の実装は今後の作業予定。
- position_sizing の価格欠損処理に TODO コメントあり（価格が 0 の場合のフォールバック価格を将来的にサポート予定）。
- process_priority の優先度設定は権限に依存する（一般ユーザーだと変更に失敗する場合がある）。失敗時は警告でスキップする挙動。
- logging_setup のファイルハンドラ作成はディレクトリ作成に依存する。作成に失敗した場合はコンソール出力のみで継続。

開発者向け補足
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。
- Paper Trading の挙動を制御する主要環境変数:
  - PAPER_FILL_MODE: instant|partial|never|reject（デフォルト instant）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス（デフォルト data/paper_trading.db）
- 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒）。不正値はデフォルト 60 秒にフォールバックします。

--- 

（この CHANGELOG はソースコードから推測して作成しています。実際の変更・リリースノートはリポジトリの履歴やリリース管理情報に基づいて調整してください。）