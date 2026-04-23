CHANGELOG
=========

すべての注目すべき変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]: https://example.com/kabusys/compare/0.1.0...HEAD

## [0.1.0] - 2026-04-23

Added
-----
- パッケージ初期リリース。
- コア設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パースの拡張:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - 非クォート値でのインラインコメント判定ルールの導入。
  - Settings クラスを提供し、各種環境変数をプロパティとして取得可能（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
  - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（有効値チェック、バリデーションエラー発生時は例外）。

- 環境設定ウィザード CLI (kabusys.config_setup)
  - 対話式で .env を作成・更新するウィザードを実装。
  - デフォルト値・選択肢・シークレット入力・既存 .env の読み込みをサポート。
  - 保存時は .env に分かりやすいヘッダ付きで出力。

- 設定検証 CLI (kabusys.validate_config)
  - .env と config/*.yaml の存在・基本的整合性チェックを実行するコマンドを実装。
  - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL 判定、DB パス親ディレクトリチェック等を実施。
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
  - KABUSYS_ENV=live の場合の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START=1 の危険性）を警告。
  - --strict オプションで警告を失敗扱い（exit(1)）にできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト (kabusys.run_execution)
    - ExecutionEngine を組み立てて別スレッドで run_session を実行する起動ロジック。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
    - 起動前に data/stop_requested.flag を検査し、フラグが立っていれば起動を中止。
    - 実行中は stop フラグでエンジンを停止。PID ファイル (data/execution.pid) を扱う。
  - 監視ループ起動スクリプト (kabusys.run_monitoring)
    - SystemMonitor をポーリング実行するループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視用 DB 初期化は環境に依らず本番 sqlite_path を使用（監視は常に実運用 DB を見る設計）。
    - 停止フラグ (data/stop_requested.flag) でループを終了。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db の呼び出しを各起動点で行い、監視テーブルが存在することを冪等的に保証。

- ログ設定ユーティリティ (kabusys.utils.logging_setup)
  - 全起動スクリプトから共通で使用できる setup_logging を実装。
  - stdout への StreamHandler（stdout 使用）と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
  - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - レベル解決順: 引数 > LOG_LEVEL 環境変数 > INFO。

- プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) で Windows / POSIX（Linux, macOS, FreeBSD）の差分を吸収して優先度変更を試行。権限不足等で変更不可な場合は警告を出すのみ。
  - set_cpu_affinity(cpu_count) により最初 N コアへ固定（未サポート環境・権限不足は警告）。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同スコアは signal_rank 昇順）で並べ上位 N を返す。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア正規化重みを計算。全スコアが 0 の場合は等金額へフォールバック（警告）。
  - risk_adjustment:
    - apply_sector_cap: 現在保有・価格情報を元にセクター毎のエクスポージャーを計算し、1 セクター上限超過セクターの新規候補を除外（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier: market レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を返す。未知のレジームは警告のうえ 1.0 フォールバック。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式 ("risk_based", "equal", "score") をサポートし、lot_size（単元株）で丸め、per-stock 上限・aggregate 上限を考慮してスケーリング、cost_buffer（手数料/スリッページ見積り）を加味した保守的見積りを実装。スケーリング時の端数配分は fractional remainder に基づく安定な追加配分アルゴリズムを採用。

- リサーチ / ファクター計算 (kabusys.research.factor_research)
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する形でモメンタム等のファクター計算の基礎実装（モメンタム計算の設計・定数が追加。実装はファイルの後半で継続）。

- Tools
  - paper_verification_report (kabusys.tools.paper_verification_report)
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計して検証レポートを出力する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、しきい値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。

Changed
-------
- 初期リリースのため変更点なし（今後のリリースで記載予定）。

Fixed
-----
- 初期リリースのため修正点なし（今後のリリースで記載予定）。

Notes
-----
- 本リリースでは多数の機能が「安全性重視」で設計されています（例: .env の OS 変数保護、監視は環境にかかわらず本番 DB を参照、優先度設定失敗時は警告のみ等）。
- 将来的に stocks マスタに lot_size を持たせる等の拡張を想定した実装注釈（TODO）が各所に残されています。

Authors
-------
- KabuSys 開発チーム（コードベースから推測して自動生成）

[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0