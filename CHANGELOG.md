CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
リリース日付はコミット内容から推測して設定しています。

[Unreleased]
-------------

（現在の差分なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション骨格を追加（初期リリース）。
  - src/kabusys/__init__.py にバージョンを定義（__version__ = "0.1.0"）。
- 起動スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御に data/stop_requested.flag を使用。
    - 監視は環境設定に関わらず本番用 sqlite_path を使用して DB を初期化。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - Engine を別スレッドで起動し、停止フラグの検知で安全に停止するロジックを実装。
    - 起動時に data/execution.pid を設定する仕組み（pid_file の受け渡し）。
- 設定管理
  - config.py
    - .env 自動ロード機能（.env / .env.local、OS 環境変数を保護して読み込み）。
    - .env のパース機能を実装（export 形式、クォート内エスケープ、インラインコメント考慮）。
    - Settings クラスを提供し、アプリケーションで使用する環境変数アクセスを型付きプロパティでラップ。
    - KABUSYS_ENV, LOG_LEVEL のバリデーション、PAPER_FILL_MODE の検証、各種パス・閾値のプロパティを提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用途）。
- 設定支援 / 検証 CLI
  - config_setup.py
    - 対話式ウィザードにより .env を初期作成・更新する機能を追加。
    - 秘匿値マスク、選択肢提示、既存 .env の読み込み・再利用に対応。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の存在・基本検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の警告/エラー、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML がある場合）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - stdout への StreamHandler（標準出力）と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定するユーティリティを追加。
    - ログディレクトリの解決順・作成処理、ログレベル解決順を実装。ファイル出力は 30 日分保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップし stderr に警告出力。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
    - CPU アフィニティ設定関数 set_cpu_affinity を追加（指定したコア数に固定）。
    - psutil の例外をハンドリングして権限不足等で安全にフォールバックする実装。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（select_candidates）と重み計算（等金額 calc_equal_weights / スコア重み calc_score_weights）を実装。スコアが全て 0 の場合は等重にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を実装。既存保有を考慮して同一セクターの新規候補を除外可能。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method="risk_based" / "equal"/"score" に対応。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的な見積り、残差処理による再配分ロジックを含む。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading SQLite（PAPER_TRADING_SQLITE_PATH または --db）からシステム稼働率、注文成功率、送信率、レイテンシ等を集計して検証レポートを出力する CLI を追加。
    - P95 計算、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を実装。
- Research（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - calc_momentum の実装を開始（但しファイル末尾で未完の箇所が存在）。

Changed
- なし（初回リリースのため新規追加が中心）。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス対応、クォーテーション内のバックスラッシュエスケープ対応、インラインコメントの取り扱いを実装。
- ログ出力先を stdout に統一（cron 等でのリダイレクトを想定）する仕様に明示。

Notes / Known issues
- research/factor_research.calc_momentum はファイル末尾で未完の行が存在する（開発途中）。ファクター計算は概念設計があるものの一部実装が未完。
- risk_adjustment.apply_sector_cap の注記として、price_map に価格が欠損（0.0）だった場合にエクスポージャーが過少評価される可能性がある旨の TODO コメントあり（将来的に前日終値や取得原価でのフォールバックを検討）。
- position_sizing.calc_position_sizes は将来的に銘柄ごとの lot_size をサポートする拡張を想定している（現状は全銘柄共通の lot_size を想定）。
- ログディレクトリ作成やプロセス優先度設定は権限や実行環境に依存し失敗する可能性があるが、例外は警告でフォールバックする実装になっている。

Security
- なし（特筆すべきセキュリティ修正は含まれていません。秘密情報は .env に格納し .env を Git 管理しないことを README 等で明示してください）。

Acknowledgments
- 初期実装に関わった主要コンポーネント: 起動スクリプト（monitoring/execution）、設定管理（.env パーサ）、ログ設定、プロセス優先度ユーティリティ、ポートフォリオ構築ロジック、Paper Trading 検証ツール。

----- 

注: 上記はコードベースから推測して作成した変更履歴です。実際のコミット履歴や設計意図と差異がある場合がありますので、最終的なリリースノートはソース管理の履歴に基づいて調整してください。