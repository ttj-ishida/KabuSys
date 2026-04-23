# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-23

### Added
- プロジェクト初回リリース — KabuSys 自動売買フレームワークの基礎機能を実装。
- 設定管理
  - 環境変数を読み込む Settings クラスを実装（src/kabusys/config.py）。
  - プロジェクトルート自動検出による .env 自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env のパースはクォート、エスケープ、インラインコメント、`export KEY=val` 形式に対応。
  - 各種設定（DB パス、API トークン、ログレベル、運用環境フラグ等）をプロパティとして提供。
- 設定支援 CLI
  - 対話式の環境設定ウィザードを追加（src/kabusys/config_setup.py）。.env の初期作成・更新を支援。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数や config/*.yaml、パスの存在をチェック。--strict モードにより警告をエラー扱いに可能。
- ログ基盤
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス制御ユーティリティ
  - 優先度（high/normal/low）と CPU affinity 設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。Windows / POSIX の差を吸収し、失敗時は警告でフォールバック。
- 実行用スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず監視用 sqlite_path（本番 DB）を使用する実装。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全に終了。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し MockBrokerClient を利用する想定（本番 DB と分離）。
    - 実行中の PID ファイル保存、停止フラグ検知によるエンジン停止処理を実装。
    - ExecutionEngine をバックグラウンドスレッドで稼働させ、フラグで停止を制御。
- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター集中制限を適用する apply_sector_cap（当日売却予定を除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピングし未知レジームは警告して 1.0 フォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを使った再配分ロジックを実装。
    - 将来的な拡張ポイント（銘柄別 lot_size など）を注記。
- データ分析 / リサーチ
  - ファクター計算モジュールの骨組み（src/kabusys/research/factor_research.py）。DuckDB を用いた価格・財務データからのファクター算出を想定（momentum/volatility/value/liquidity 等）。
- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計。
    - 基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB を指定可能。
- パッケージ情報
  - バージョン定義を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

### Fixed
- 環境変数読み込みと .env パース時の多様なケース（クォート、エスケープ、コメント、export 形式）に対応して堅牢性を向上（src/kabusys/config.py）。
- MONITOR_POLL_INTERVAL が不正な場合に ValueError を回避し、デフォルト値にフォールバックする処理を実装（src/kabusys/run_monitoring.py）。
- ログディレクトリ作成失敗時にプログラムがクラッシュしないよう、ファイルハンドラ作成をスキップしてコンソール出力のみで継続するように改良（src/kabusys/utils/logging_setup.py）。

### Known issues / Notes
- apply_sector_cap のセクター別エクスポージャ計算で price が 0.0（欠損）だと過少見積もりとなる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO として注記（src/kabusys/portfolio/risk_adjustment.py）。
- process_priority の設定は環境によって権限不足（psutil.AccessDenied）や未サポート属性で失敗する可能性があり、その場合はログ警告でスキップする仕様（src/kabusys/utils/process_priority.py）。
- validate_config における YAML 検証は PyYAML がインストールされていない場合にスキップされ、警告を出す（src/kabusys/validate_config.py）。
- 一部モジュール（research ファクター計算など）は骨組みが含まれ、実運用でのチューニング・追加実装が必要。

### Documentation / Usage snippets
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading 環境では専用 DB に記録（PAPER_TRADING_SQLITE_PATH）
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### Security
- 機密情報（API トークン等）は .env に記載して管理する設計。.env は Git にコミットしない旨をドキュメントヘッダーに明記（src/kabusys/config_setup.py）。
- 起動時に必須環境変数が未設定の場合、validate_config で早期検知可能。

---

今後の作業候補（非網羅）:
- ファクター計算の完全実装・テスト（research モジュールの継続実装）。
- 実運用向けの監視アラート送信（LINE 等）・バックテスト機能の追加。
- 銘柄ごとの lot_size マスタ導入・より厳密な価格フォールバックロジックの実装。
- 単体テスト・CI の整備。