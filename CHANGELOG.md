CHANGELOG
=========

すべての重要な変更点をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリースを追加。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定し、KABUSYS_ENV によって paper_trading 用の専用 SQLite DB を使用可能。BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立て、ExecutionEngine のデーモンスレッド実行・停止制御、停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）処理を実装。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。停止フラグ検出時にループを終了。
- 設定管理:
  - config.py: .env 自動読み込み（プロジェクトルート検出）機能と Settings クラスを実装。J-Quants / kabu API / LINE / DB / 監視閾値 / 実行環境（development/paper_trading/live）などのプロパティを提供し、値検証を行うユーティリティを実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 等）を対話的に入力・保存可能。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数やパス、config/*.yaml の存在・パース検証、KABUSYS_ENV に対する本番環境ガードなどを実行。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた資金乗数 calc_regime_multiplier を実装。unknown セクターの扱い、ログ出力、フォールバック挙動を定義。
  - portfolio/position_sizing.py: position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファによる保守的見積り、スケーリングと残差処理を実装。
  - portfolio/__init__.py にて上記 API を公開。
- ログ／プロセスユーティリティ:
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log、30 日分保持）を組み合わせ、既存ハンドラのクリアやログレベル・ログディレクトリ解決を行う。
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority と、CPU affinity を設定する set_cpu_affinity を実装。権限不足や未対応 OS の場合は警告を出してスキップ。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に基づく PASS/FAIL を出力。P95 の計算や日付フィルタ処理、DB パスの CLI オプション（--db）/環境変数（PAPER_TRADING_SQLITE_PATH）対応を実装。
- 研究モジュール（ファクター計算）:
  - research/factor_research.py: ファクター計算モジュールの骨子を追加。モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR ベースのボラティリティ、流動性指標などの設計方針と定数を定義。DuckDB 接続を利用する設計。モメンタム計算関数 calc_momentum の実装を開始（関数シグネチャとドキュメントあり、計算範囲バッファ等を定義）。
- パッケージ情報:
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を追加。

Changed
- n/a（初回リリースのため既存変更はありません）

Fixed
- n/a（初回リリースのため修正はありません）

Notes / Usage highlights
- 起動スクリプトは起動直後にプロセス優先度を "high" に設定するよう設計されている（権限がない場合は警告を出して継続）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（デフォルト data/paper_trading.db）を使用して本番 DB と分離する設計。
- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（正の整数のみ、無効値はデフォルト 60 秒にフォールバック）。
- ログは標準出力（stdout）とファイル（logs/<app>.log）に出力。ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続。
- .env 自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に基づき行われ、OS 環境変数を保護する挙動（.env.local の override 等）を持つ。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Known limitations / TODO
- research/factor_research.py はモメンタム等の計算ロジックの骨子を含むが、完全実装・テストが必要（ファイル末尾に未完の箇所あり）。
- position_sizing の lot_size は現状全銘柄共通の仮定。将来的に銘柄別単元対応（マスタ参照）へ拡張予定（コメントに TODOあり）。
- apply_sector_cap は price_map の欠損（0.0）によりエクスポージャーを過少見積もる可能性があり、フォールバック価格導入の検討がコメントに残されている。

セマンティクス・バージョニング
- 初回リリース (0.1.0)。今後の互換性方針や API 変更はメジャー/マイナー/パッチのルールに従って管理してください。