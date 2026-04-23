# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。重要な変更点を日本語で要約しています。日付はソースコードから推測される最新の状態（このドキュメント作成日）を使用しています。

全般的な注記:
- 本リポジトリは日本株向け自動売買システム KabuSys の一部機能を含みます（設定管理、起動スクリプト、ポートフォリオ構築、発注ロジック補助、監視、ユーティリティ、解析ツールなど）。
- .env の自動ロードや実行時の挙動に関する設計が取り入れられており、本番/ペーパーの分離やログ/プロセス管理に配慮されています。

## [0.1.0] - 2026-04-23

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite/DuckDB 接続確立、BrokerClient の作成、OrderManager/RiskManager/Reconciler の組み立て、スレッドでのセッション実行と停止フラグ監視を実装。KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用する設計を採用。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を利用する仕様（監視 DB の初期化も行う）。停止フラグファイルによりループ終了を行う。

- 設定・環境変数関連
  - config.py: 設定読み込み/管理モジュール。
    - プロジェクトルート自動検出（.git / pyproject.toml を手掛かり）に基づく .env 自動ロード（.env, .env.local、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理などに対応。
    - Settings クラスを提供し、各種設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/kill フラグ、閾値、PAPER_FILL_MODE 等）の取得と妥当性検証を行う。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジックを導入。

  - config_setup.py: 対話式ウィザードで .env を作成 / 更新する CLI を実装。シークレット項目のマスク表示、選択肢/デフォルト提示、保存前の確認、.env 出力テンプレートを提供（.env を Git に含めない旨の注意を同梱）。

  - validate_config.py: 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定など）。--strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選択（同点時は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき、新規候補を除外するロジック（"unknown" セクターは除外対象外）。sell_codes パラメータで当日売却予定の銘柄を除外して計算可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した発注株数計算、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（手数料/スリッページ見積り）考慮、残余キャッシュによる lot 単位での再配分ロジックを実装。設計に TODO コメント（銘柄別 lot_size、価格フォールバックなど）あり。

- 監視・検証ツール
  - monitoring.monitoring_db の初期化呼び出しを各スクリプトで行う（監視テーブルの存在保証・冪等化）。
  - tools/paper_verification_report.py: Paper Trading 用の SQLite DB（デフォルト data/paper_trading.db）から稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定付きレポートを標準出力に出力する CLI を実装。日付フィルタ（--from/--to）と --db オプションをサポート。P95 は簡易的なパーセンタイル計算を実装。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。既存ハンドラの二重登録を防止するために一度クリアして再設定する。LOG_DIR / LOG_LEVEL 解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class、POSIX の nice、エラー時に警告を出してスキップ）。CPU affinity を最初 N コアに固定するユーティリティを提供。権限不足時の安全なフォールバックあり。

- パッケージ初期化
  - kabusys.__init__.py に __version__ = "0.1.0" を追加。

- 研究用モジュール（着手）
  - research/factor_research.py: ファクター計算モジュールの骨格（モメンタム・ボラティリティ等の指標計算設計、DuckDB 接続経由で prices_daily/raw_financials を参照）を追加。関数 calc_momentum の実装開始（ファイル末尾で途中まで記述）。

### Changed
- 実行時ポリシーの明示化
  - 監視（run_monitoring）は監視 DB に対して常に本番 sqlite_path を使用する挙動を明示（環境変数 KABUSYS_ENV に依存しない）。
  - 実行（run_execution）は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB を使用することで本番 DB と完全分離する仕様を採用。

- .env ロードの挙動
  - OS 環境変数を保護（protected set）し、.env/.env.local の読み込み順序や上書きルールを明確化（.env.local は override=True）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加。

### Fixed
- .env パーサの堅牢性向上
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォートなしの行でのインラインコメントの扱いなどを実装。空行・コメント行の無視や無効行のスキップ処理を整備。

- ログ設定の安全化
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール出力は継続するように安全にフォールバックする実装に変更。

- プロセス優先度設定の例外ハンドリング
  - 権限不足や未サポート環境での例外をキャッチして警告を出し、処理を中断しないように改善。

### Notes / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の扱いや、銘柄別 lot_size サポートについては TODO コメントあり。将来的に stocks マスタに lot_size を持たせる設計への拡張が想定されている。
- risk_adjustment.apply_sector_cap:
  - price の欠損によるエクスポージャー過少見積りに関する注記あり。前日終値や取得原価などのフォールバック価格を検討する予定。
- research/factor_research.py:
  - ファイル末尾で calc_momentum の実装が途中で終わっている（未完）。ファクター計算ロジックは今後の実装継続が必要。

### Security
- config_setup にて .env を生成するテンプレートに「.env を絶対に Git にコミットしないこと」を明記。シークレット項目は対話中にマスク表示。

---

今後のリリースでは、以下を予定または検討中です:
- research/factor_research の完全実装（ファクター計算・正規化・出力整形）。
- Engine / Broker 周りの統合テストと MockBroker の追加実装およびドキュメント整備。
- ランタイムメトリクスのダッシュボード出力や通知（LINE）連携の強化。
- 単体/統合テストの追加と CI の導入。

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴（コミットログ等）とは差異がある場合があります。必要であればコミット履歴を元に正式な CHANGELOG を生成します。