# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- パッケージ初期リリース（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。  
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（Paper/Live を透過）。  
    - エンジンはデーモンスレッドで実行され、data/stop_requested.flag による停止フラグ検出で安全に停止可能。PID ファイルを data/execution.pid に出力。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。  
    - 監視用 DB は環境にかかわらず本番 sqlite_path（data/monitoring.db がデフォルト）を使用して初期化。停止フラグ file(data/stop_requested.flag) 検出でループ終了。
- 環境設定・検証 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新する機能を追加。重要なキー（J-Quants、kabu API 等）を対話的に入力可能。生成される .env はコミット禁止の旨を注記。
  - validate_config.py: 起動前に .env や config/*.yaml の設定不備を検出する CLI を追加。--strict を指定すると警告も失敗扱い（exit 1）にできる。PyYAML が無い場合は YAML 検証をスキップして警告を出す。
- 設定管理
  - config.py: .env の自動ロード（プロジェクトルートに基づく）、安全なパースロジック、環境変数の要求チェックを実装。  
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - PAPER_FILL_MODE（paper_trading のモック約定モード）をサポート（instant/partial/never/reject）。不正値はエラー。  
    - KABUSYS_ENV, LOG_LEVEL の妥当性チェック（許容値リスト）や各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）をプロパティで提供。
- ログ・ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力（30 日分保持）。  
    - LOG_DIR 環境変数や引数でログ保存先を変更可能。既存ハンドラの二重設定防止のためクリアしてから再設定。
- プロセス制御ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加（set_process_priority）。  
    - Windows の場合は psutil の優先度定数を使用、Linux/macOS 等では nice 値を設定。権限不足等で設定できない場合は警告を出してスキップ。  
    - set_cpu_affinity によりプロセスを最初の N コアにピン留め可能（利用できない環境では警告）。
- Portfolio モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア比率配分（calc_score_weights）を追加。スコア全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。  
    - apply_sector_cap は既存保有を考慮してセクター上限を超える候補を除外（"unknown" セクターは適用除外）。  
    - calc_regime_multiplier は regime label に応じて資金乗数（bull=1.0, neutral=0.7, bear=0.3）を返す。不明な値は警告を出して 1.0 をフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score）。  
    - リスクベース計算（risk_pct, stop_loss_pct）、単元株（lot_size）丸め、per-stock 上限や総投下資金（available_cash）を考慮したスケーリング（端数処理の再配分）を実装。cost_buffer を考慮して保守的見積り。
  - portfolio/__init__.py で上記関数群を公開。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite から検証レポートを生成する CLI を追加。  
    - 指定期間（--from / --to）または DB 全期間で集計可能。DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。  
    - 指標: 稼働率（uptime）, 注文成功率（fill rate）, 送信率（send rate）, レイテンシ（avg/max/P95）等。P95 計算の実装あり。  
    - デフォルトの合格基準（閾値）: 稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200ms。基準未達は FAIL として報告。
- research モジュール（着手）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨組み。Momentum/V alue/Volatility/Liquidity 等の計算方針と定数を定義。（実装途中・設計コメントを含む）
- パッケージメタ
  - __init__.py にてパッケージ名と初期バージョン (0.1.0) を設定し、主要サブパッケージを __all__ で公開。

### Changed
- （初回リリースのため過去の変更はなし）  

### Fixed
- （初回リリースのため過去の修正はなし）

### Notes / Important details
- validate_config により起動前の環境不備を検出できるため、運用前に必ず実行して警告／エラーを確認することを推奨します。--strict を使うと警告も fail 扱いになります。  
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。  
- run_monitoring は監視データ格納に本番 sqlite_path を使用します（意図的な設計）。一方 run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番データと分離します。  
- ロギングは stdout 出力を優先しており、ログファイル出力に失敗してもコンソールログは継続します（ログディレクトリ作成失敗時に警告）。  
- process_priority / set_cpu_affinity は psutil に依存します。psutil 未インストールや権限不足の場合は機能が制限されますが、プロセスは継続して動作します。  
- research/factor_research.py は計算方針・定数・API を定義済みですが、実装は継続中です（ファイル末尾が未完である可能性があります）。

----- 

今後のリリースでは、strategy 実装、ExecutionEngine の詳細挙動、monitoring/system_monitor の詳細なログ・アラート連携、各種ユニットテスト・CI、DuckDB を用いた分析パイプラインの拡充などを計画しています。