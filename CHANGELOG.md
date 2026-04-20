CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」フォーマットに従って記録します。ここに記載した変更点は、提供されたソースコードを読み取り・推測して作成したものです。

Unreleased
----------

Added
- 環境設定ウィザード CLI を追加（kabusys.config_setup）。
  - .env の対話的生成・更新をサポート。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）に対応。
  - 既存 .env の読み込みと Enter による既存値再利用、シークレット表示のマスク機能を提供。
  - 書き込みテンプレート（コメント付き）を生成。

- 設定検証 CLI を追加（kabusys.validate_config）。
  - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証（PyYAML が存在しない場合は警告）などを行う。
  - --strict オプションで警告を FAIL 扱いにできる。

- 実行コンポーネント起動スクリプトを追加/改善。
  - run_execution: ExecutionEngine 起動スクリプトを提供。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離する（PAPER_TRADING_SQLITE_PATH）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する設計。

- Paper Trading 検証レポート作成ツールを追加（kabusys.tools.paper_verification_report）。
  - system_status / trade_logs / risk_logs などを集計して稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を算出し、閾値に基づき PASS/FAIL を判定。
  - --from / --to / --db オプションをサポート。

- ポートフォリオ構築系モジュールを追加（kabusys.portfolio）:
  - portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア重み（calc_score_weights: 全スコアが 0 の場合は等分配にフォールバック）。
  - risk_adjustment: セクター上限の適用（apply_sector_cap）、マーケットレジームに応じた乗数（calc_regime_multiplier: bull/neutral/bear とフォールバック）。
  - position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の allocation_method をサポート、単元株（lot_size）丸め、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer による保守的コスト見積り、残差を用いた追加配分ロジックを実装。

- ユーティリティ群を追加/改善（kabusys.utils）:
  - logging_setup: stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ロギング設定を提供。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。LOG_DIR / LOG_LEVEL を考慮。
  - process_priority: Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定機能を提供。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N)。

Changed
- .env 読み込みロジックを改善（kabusys.config）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動ロードに変更。
  - .env ファイルのパースを強化し、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無での挙動差）などに対応。
  - 読み込みの優先順位は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- Settings クラスの妥当性検証を強化（kabusys.config）。
  - KABUSYS_ENV / LOG_LEVEL の許容値を明示的チェックし、不正値時は ValueError を発生させる。
  - PAPER_FILL_MODE における有効値チェック（instant/partial/never/reject）。
  - デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）を Path 型で返すように統一。

- 起動スクリプト（run_execution, run_monitoring）でプロセス優先度を最初に設定するように変更（set_process_priority("high")）して運用安定性を向上。

Fixed
- calc_score_weights: 全銘柄のスコアが 0.0 の場合にゼロ除算や不正な重みになるのを防ぎ、等金額配分へフォールバックするように修正。

- position_sizing のスケーリング実装で、単位（lot_size）丸めや aggregate cap 適用後の残差処理を実装し、投下額が available_cash を超える場合に安全にスケールダウンするよう改良。

- logging_setup: 既存ハンドラが二重登録される問題を防ぐため、設定前に既存ハンドラを flush/close してから削除するように修正。

- process_priority: サポート外 OS や権限不足時に例外で落ちないよう処理を捕捉して警告ログでフォールバックするように修正。

Security
- .env ファイル生成テンプレート（config_setup）に注意書きを追加し、.env を誤ってリポジトリにコミットしないよう促す。

0.1.0 - 初期リリース (推定)
--------------------------

Added
- パッケージ基礎構成と以下主要機能を実装:
  - 実行/監視起動スクリプト: run_execution, run_monitoring
  - 設定管理と自動 .env ロード: kabusys.config, Settings クラス
  - 設定ウィザードおよび検証ツール: kabusys.config_setup, kabusys.validate_config
  - ロギング・プロセス優先度ユーティリティ: kabusys.utils.logging_setup, kabusys.utils.process_priority
  - ポートフォリオ構築・サイズ決定・リスク調整: kabusys.portfolio.*
  - Paper Trading 検証レポートツール: kabusys.tools.paper_verification_report
  - 研究用ファクタモジュール（骨格）: kabusys.research.factor_research（モメンタム等の計算関数を設置、実装継続）

Changed
- パッケージメタ情報: __version__ = "0.1.0"

Known issues / Notes
- kabusys.research.factor_research の実装は途中（ファイル末尾が途中で切れているため、モメンタム計算関数の続き実装が必要）。
- 一部の機能は外部依存（psutil, duckdb, PyYAML 等）に依存。環境により機能差分が発生する旨をドキュメント化すべき。
- run_monitoring/run_execution は停止フラグ (data/stop_requested.flag) や PID ファイルを用いた運用を前提としている。デプロイ手順にこれらの運用フローを明記することを推奨。

参考: 主な CLI / エントリポイント（推定）
- 起動:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- 設定:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
- ツール:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（以上はソースコードの内容から推測して作成した CHANGELOG です。必要があれば実際のコミット履歴・リリース日・作者情報等を反映して更新してください。）