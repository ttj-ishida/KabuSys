# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

全般的な方針:
- バージョニングは SemVer を意識しています（本リリースは初期リリース相当）。
- コマンドライン / スクリプトについては各モジュールのエントリーポイント（python -m ...）を明記しています。

## [Unreleased]

## [0.1.0] - 2026-04-21
初期リリース。

### Added
- 基本パッケージ構成を追加（kabusys）。
  - バージョン情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行系スクリプトを追加:
  - 実行エンジン起動スクリプト (run_execution.py)
    - 起動時にプロセス優先度を "high" に設定 (utils/process_priority.py)。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。(src/kabusys/run_execution.py)
    - BrokerClientFactory によりブローカークライアントを生成し、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) により安全に停止可能。
    - PID ファイル (data/execution.pid) をサポート。

  - 監視ループ起動スクリプト (run_monitoring.py)
    - SystemMonitor を用いたポーリングループを提供。監視は環境にかかわらず本番の sqlite_path を使用する旨を明示。(src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。

- 設定・環境関連ユーティリティを追加:
  - Settings クラス（src/kabusys/config.py）
    - .env の自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml を基準）
    - 必須値チェック用の _require、各種パス、KABUSYS_ENV のバリデーション、paper_trading 関連設定（paper_sqlite_path、paper_fill_mode 等）を提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。
    - 環境切替フラグ: is_live / is_paper / is_dev。

  - .env 対応の対話式ウィザード (config_setup.py)
    - .env の初期作成・更新を支援する対話式ツールを提供。コマンド: python -m kabusys.config_setup
    - シークレット項目のマスク表示、選択肢、デフォルト値提示などを実装。
    - 出力ファイルに注意喚起コメントを付与（.env を Git にコミットしない旨）。

  - 設定検証 CLI (validate_config.py)
    - .env と config/*.yaml の存在・基礎妥当性検証を行う。コマンド: python -m kabusys.validate_config
    - --strict オプションにより警告を FAIL 扱いで終了可能。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML があれば実施）、本番環境向け追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。

- ポートフォリオ構築ライブラリを追加 (src/kabusys/portfolio)
  - portfolio_builder.py:
    - 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights) の純粋関数群を実装。
  - risk_adjustment.py:
    - セクター集中制限適用(apply_sector_cap)、市場レジームに応じた乗数(calc_regime_multiplier) を実装。
    - 未知レジームやセクター未定義時のフォールバック挙動を定義。
  - position_sizing.py:
    - allocation_method（risk_based / equal / score）に対応した発注株数算出。
    - lot_size（単元）丸め、per-stock 上限・aggregate cap、コストバッファによる保守的見積り、スケーリングロジック（割合スケーリングと端数処理）を実装。

- ログ設定ユーティリティを追加 (src/kabusys/utils/logging_setup.py)
  - StreamHandler（stdout） + TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
  - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
  - ログレベルとログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。

- プロセス優先度・CPU affinity ユーティリティを追加 (src/kabusys/utils/process_priority.py)
  - Windows / POSIX を抽象化して優先度設定(set_process_priority) を提供。psutil の権限不足や未実装 API は警告出力して安全にスキップ。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。

- Paper Trading 検証レポート生成ツールを追加 (src/kabusys/tools/paper_verification_report.py)
  - ペーパートレード用 SQLite（既定 data/paper_trading.db / 環境変数 PAPER_TRADING_SQLITE_PATH）から集計してレポートを標準出力に表示。
  - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ、リスク却下数 等。
  - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
  - コマンド: python -m kabusys.tools.paper_verification_report

- リサーチ / ファクター計算の骨組みを追加 (src/kabusys/research/factor_research.py)
  - Momentum / Value / Volatility / Liquidity 等のファクター計算の設計・定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

- DB 初期化ヘルパを追加（監視目的）: init_monitoring_db 呼び出しを run_monitoring/run_execution に導入（監視テーブルの存在保証、冪等）。

### Changed
- .env 自動ロードの挙動:
  - プロジェクトルートを .git または pyproject.toml により検出するようにして CWD 依存を排除。（src/kabusys/config.py）
  - 環境変数上書き保護の仕組みを導入（既存 OS 環境変数を protected として .env.local による上書きを制御）。

- ロギング出力の標準化:
  - コンソール出力は stdout を使用する方針（cron / Task Scheduler でのリダイレクトを考慮）。(src/kabusys/utils/logging_setup.py)

### Fixed / Robustness improvements
- .env パーサーを堅牢化:
  - export プレフィックス対応、クォートあり/なしの処理、バックスラッシュエスケープ対応、行末のコメント取り扱いルールを実装してパーサを改善。(src/kabusys/config.py)

- 実行スクリプトの安定化:
  - 停止フラグ (data/stop_requested.flag) を監視して安全にループを抜ける実装を追加（実行中の stop/kill 管理の共通化）。(src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
  - run_execution の起動前に停止フラグが立っている場合は起動を中止する早期チェックを追加。

- process_priority / CPU affinity は権限不足時に安全にスキップしてログ警告を出すよう改善。

### Security
- シークレットの扱い:
  - config_setup の対話表示でシークレット項目はマスク表示（画面表示上）。
  - .env ファイル生成時に「.env は絶対に Git にコミットしないこと」をコメントで強調。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config で未設定の場合はエラーとなるため、起動前に .env を設定しておくことを推奨。
- Paper Trading を使用する場合は KABUSYS_ENV を paper_trading に設定し、PAPER_TRADING_SQLITE_PATH を適切に指定してください。ペーパートレードは本番 DB と分離されます。
- monitoring は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します（設計上の注意）。実行系は env に応じて sqlite_path を切り替えます。

---

この変更履歴は、ソースコードの実装・コメント・ドキュメント文字列から推測して作成しています。実際の変更履歴やリリースノートの最終版として使用する際は、開発履歴（コミットログ等）に基づいて整合性を確認してください。