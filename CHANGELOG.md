CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
フォーマット: [Unreleased] / 各リリースごとに Added / Changed / Fixed / Security / Notes を分けて記載しています。

[Unreleased]
------------

- （現時点なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本機能の初回公開（初期バージョン 0.1.0）。
- 実行スクリプト / デーモン系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じたブローカークライアント選択（paper_trading では MockBrokerClient を使用）や paper_trading 用 DB の分離機能を実装。実行中の停止フラグ（data/stop_requested.flag）検出、PID ファイル管理、スレッド化によるセッション実行・停止をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する設計。
- 環境設定 / 検証ツール
  - config_setup.py: .env の対話式ウィザードを提供。主要な環境変数（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を安全に初期設定できる。作成・更新時に .env に書き出し、保存前に確認プロンプトを表示。
  - validate_config.py: 起動前チェック CLI を追加。.env と config/*.yaml の基本的な整合性検査、必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、YAML パーサが利用可能な場合は YAML ファイルのパース検証を実施。--strict オプションで警告をエラー扱いにできる。
- 設定管理
  - config.py: 環境変数読み込み・管理モジュールを追加。プロジェクトルート自動検出（.git または pyproject.toml）を基に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり）。.env パースは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント処理に対応。Settings クラスで各種設定（DB パス、PID ファイルパス、閾値、PAPER_FILL_MODE バリデーション等）をプロパティとして提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score に対応）。単元ロット（lot_size）で丸め、aggregate cap（available_cash を超える場合のスケールダウン）や cost_buffer を考慮した計算を行う。
  - portfolio/__init__.py で上記関数群を公開。
- 監視・ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。標準出力（stdout）への StreamHandler と日次ローテーション (TimedRotatingFileHandler) によるファイル出力（デフォルト logs/ ディレクトリ）をルートロガーに設定。既存ハンドラのクリア、ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py: Windows / POSIX の差を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足や未対応 OS の場合は警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを集計し、稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。日付範囲フィルタ（--from / --to）と --db オプションをサポート。
- 研究用モジュール（着手・部分実装）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を前提にモメンタム等のファクター計算を行う設計を追加（関数ヘッダ・定数・一部実装あり、以降の実装継続予定）。
- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として定義。

Changed
- なし（新規リリースのため既存 API 変更は無し）

Fixed
- .env パーサの堅牢化:
  - クォートあり値に対するバックスラッシュエスケープ処理や閉じクォート探索、インラインコメントの無視を実装し、.env の多様な書式に対応。
  - export KEY=val 形式を受け入れるように対応。
- run_monitoring のポーリング間隔設定において、MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックする安全処理を追加。

Security
- .env の取り扱いに関する注意書きを config_setup.py に明記（.env を Git にコミットしないことを明示）。

Notes / Design decisions / Known issues
- 監視系（run_monitoring）は設計として「環境にかかわらず本番 sqlite_path を使用する」という動作になっています。運用上の意図的な設計（監視データは本番 DB に集約）です。誤用が懸念される場合は設定の見直しを検討してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 sqlite（data/paper_trading.db など）を使用し、本番 DB と明確に分離するよう実装されています。
- process_priority.set_process_priority / set_cpu_affinity は権限が必要になる場合があります。AccessDenied 等が発生した場合は警告を出してスキップします。
- logging_setup はログディレクトリ作成に失敗した場合でも標準出力へのログを継続する設計ですが、ファイル出力がない場合は運用上の注意（ログ永続化されない）があります。
- portfolio.position_sizing の算出は単元株（lot_size）を前提にしており、将来的に銘柄別の lot_size を持つ設計へ拡張する余地あり（TODO コメント）。

開発者向け補足
- 設定検証スクリプト: python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）になります。
- 環境設定ウィザード: python -m kabusys.config_setup
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 実行 / 監視デーモン:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

ライセンス・機密情報
- .env ファイルは機密情報を含むため、リポジトリへコミットしないでください（config_setup.py にも注記あり）。

--- End of CHANGELOG ---