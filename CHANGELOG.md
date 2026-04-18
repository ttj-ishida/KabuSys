# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
慣例として重要な追加・変更点を日本語で要約しています（コードベースから推測して作成）。

## [0.1.0] - 2026-04-18

### Added
- 基本的な自動売買フレームワークを追加。
  - パッケージ名: `kabusys`。バージョンは `__version__ = "0.1.0"`。
- 起動スクリプト（CLI）を追加:
  - run_execution: ExecutionEngine を起動するスクリプト（python -m kabusys.run_execution）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient（BrokerClientFactory 経由）で発注をシミュレーション。
    - プロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を使用）。
    - PID / 停止フラグにより外部から安全に停止可能（data/execution.pid / data/stop_requested.flag）。
    - ExecutionEngine の起動・停止ループをスレッドで実行し、停止フラグ検出で安全停止。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（python -m kabusys.run_monitoring）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - monitoring は環境に関係なく本番の `sqlite_path` を使用する設計。
    - 停止フラグ（data/stop_requested.flag）の検出でループを終了。
- 設定管理:
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定（API トークン、DB パス、監視閾値、実行環境など）を参照する統一 API を提供。
  - 自動 .env 読み込み機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` をロード（OS 環境変数を保護）。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサは `export KEY=val` 形式、クォートやエスケープ、インラインコメントなどに対応。
- 環境設定支援ツール:
  - `config_setup.py` に対話式ウィザードを実装。`.env` の初期作成・更新を支援（python -m kabusys.config_setup）。
  - 主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を対話的に生成。
  - .env 書き込み時にテンプレートヘッダと注意書きを付与（.env を Git にコミットしない旨の注意）。
- 設定検証 CLI:
  - `validate_config.py` を追加。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検査（PyYAML が利用可能な場合）などをチェック。
  - `--strict` オプションで警告も失敗扱いにできる。
- ロギング関連ユーティリティ:
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーに stdout への StreamHandler（stdout を利用）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を設定。既存ハンドラはクリアして重複を防止。
    - ログレベルとログディレクトリは引数 > 環境変数 > デフォルトで解決。
    - ファイル書き込み不可時はコンソールのみで継続。
- プロセス優先度 / CPU アフィニティユーティリティ:
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority`。
    - CPU アフィニティを最初の N コアに固定する `set_cpu_affinity`。
    - 権限がない場合は警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）:
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates: BUY シグナルのスコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア正規化配分。スコアが全て 0 の場合は等配分にフォールバック（警告）。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap: セクター集中上限チェック（既存保有と当日売却予定を考慮）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知のレジームは警告のうえ 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes: weight/candidates/open_prices などから銘柄ごとの発注株数を算出。`allocation_method` は `"risk_based" | "equal" | "score"` をサポート。
    - lot_size（単元株）対応、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケールダウンと余りの lot 単位での再配分ロジックを実装。
- Paper Trading 検証ツール:
  - `kabusys.tools.paper_verification_report` を追加。paper_trading の SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計して PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99% 等）。
  - P95 計算や日付フィルタ（ISO8601 UTC 形式）に対応。コマンドライン引数 `--from` / `--to` / `--db` をサポート。
- 研究用モジュール（部分実装）:
  - `kabusys.research.factor_research` を追加（モメンタム・ATR 等に基づくファクター群の計算を意図）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モメンタム計算関数の骨組みあり（途中の実装あり）。

### Changed
- ログ出力の標準出力先を stdout に統一（cron や Task Scheduler でのリダイレクト運用を考慮）。
- .env 読み込みの優先順位を明確化: OS 環境 > .env.local > .env。既存の OS 環境変数は保護される。
- run_execution / run_monitoring の DB 初期化で監視テーブルの作成（init_monitoring_db）を冪等に実行するように変更。

### Fixed
- 環境変数パースの改善:
  - シングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントの処理を追加。
  - `export KEY=val` 形式に対応。
- ポジションサイズ算出における端数処理と aggregate スケールダウンの再配分ロジックを実装し、資金超過時により再現性のある配分を行うように修正（lot_size 単位での調整、残差ソートによる安定化）。

### Security
- .env の自動生成テンプレートに「.env を絶対に Git にコミットしない」旨の注意を追加。
- 必須 API トークン（J-Quants / kabu）の読み取りは Settings を通じて行い、未設定時は ValueError を投げて起動前に検出される設計。

## 未分類・補足（実装上の注意）
- monitoring は常に本番用の sqlite_path を使用する設計になっているため、paper_trading 環境であっても監視データが本番 DB に記録される点に注意（コード内で明示的にそう記載されている）。
- process priority / CPU affinity の設定はプラットフォーム依存・権限依存のため、失敗した場合は警告を出して安全にスキップする実装。
- DuckDB / PyYAML / psutil 等の外部ライブラリ利用を前提としている箇所があるため、実行環境に依存した追加インストールが必要。
- research モジュールは途中実装（ソースが途中で切れている箇所あり）。今後の拡張で完全なファクター計算が期待される。

---

今後のリリースでは、Engine / Broker の詳細実装（API 統合）、テストカバレッジ、エラーハンドリングの強化、monitoring/alerting（LINE連携）などの項目が想定されます。必要であれば、この CHANGELOG をプロジェクトの実際のコミット履歴やリリース計画に合わせて分割・更新します。