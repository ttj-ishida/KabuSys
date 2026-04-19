# Changelog

すべての重要な変更点を Keep a Changelog の形式に従って記載します。

全般ルール: Semantic Versioning を意識したバージョニングを採用しています。

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。KabuSys のコアユーティリティ・起動スクリプト・ポートフォリオ構築ロジック・各種ツールを追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - エンジンは別スレッドで実行し、プロセス間停止フラグ（data/stop_requested.flag）を検知して安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py: .env 自動ロードと Settings クラスを追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により .env 自動読み込みを実施（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
    - .env のパースは export 形式、クォート、エスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings により各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）を型付きで取得／検証。
    - 環境（KABUSYS_ENV）やログレベル等の妥当性チェックを実装。
- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を初期作成／更新するツールを追加。
    - 秘匿項目のマスク表示、選択肢・デフォルト提示、保存前の確認を実装。
  - validate_config: 起動前検証ツールを追加。
    - 必須環境変数未設定の検出、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML が利用可能な場合はパース検証）などを実施。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - コンソール（stdout）出力用 StreamHandler と 日次ローテートされたファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログディレクトリ／レベルを指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: プロセス優先度設定および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX に対応し、psutil を使って優先度（high/normal/low）と CPU affinity を設定。権限不足時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights: 等金額配分の重み。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等重にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるフィルタ（当日売却予定を除外可能）。"unknown" セクターは上限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート。未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based/equal/score）に従う株数決定、単元株丸め、per-position 上限・aggregate cap（available_cash）処理、cost_buffer を考慮したスケーリングと端数処理を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。
    - DB（PAPER_TRADING_SQLITE_PATH）から system_status / trade_logs / risk_logs を参照し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定を出力。
    - --from/--to/--db の CLI オプションを提供。
- リサーチ（ファクター計算）スケルトン
  - research/factor_research.py にモメンタム等のファクター計算ロジックのルーチンを追加。DuckDB を用いて prices_daily/raw_financials から計算する方針（いくつかの定数と関数スケルトンを含む）。

### Changed
- なし（初回リリースのため変更履歴は追加のみ）

### Fixed
- なし（初回リリースのため修正履歴はなし）

### Known issues / 注意事項
- .env 自動ロードはプロジェクトルート検出に依存するため、配布パッケージや特殊な配置では自動ロードがスキップされる可能性があります（その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して明示制御可能）。
- process_priority / cpu_affinity の設定はプラットフォーム依存かつ権限に依存するため、権限不足時は警告が出力され設定がスキップされます。
- portfolio.position_sizing の価格欠損（price が None または 0）の場合、一部挙動が保守的になっています。将来的に前日終値等のフォールバック実装を検討。
- research/factor_research.py は一部実装が続き（スケルトン）であり、完全なファクター計算は今後の実装で拡張予定。

---

（以降のリリースでは Unreleased セクションを用いて追加変更を記載してください）