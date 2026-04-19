# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  
このプロジェクトのバージョニングは SemVer を想定します。

## [Unreleased]

### Added
- ドキュメント化されていない内部ユーティリティや実行スクリプトの追加（詳細は 0.1.0 にて初回リリース）。
- 開発・運用時の設定・検証を支援する CLI ツール群の基礎を追加:
  - 対話式 .env 作成ウィザード（kabusys.config_setup.run_wizard）
  - 設定検証 CLI（kabusys.validate_config） — 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml、ライブ環境向けの追加ガードを検査。`--strict` オプションで警告をエラー扱いに可能
- Paper Trading の検証用レポート生成ツール（kabusys.tools.paper_verification_report）を追加 — 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・P95）などを算出して PASS/FAIL 判定を出力
- ポートフォリオ構築用純関数群を追加（kabusys.portfolio）:
  - 候補選定: select_candidates（スコア降順、タイブレークロジックを含む）
  - 重み計算: calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等分配にフォールバック）
  - セクター集中対策: apply_sector_cap（既存ポジションのセクター比率に基づく候補除外）
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear のマッピングと未知レジームでのフォールバック）
  - 口数決定・リスク制限: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り）
- 実行用スクリプトを追加:
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離
    - BrokerClientFactory 経由でブローカークライアントを作成
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。デーモンスレッドで実行し停止フラグを監視して安全に停止
    - デフォルトのリスク設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入
- 監視用スクリプトを追加:
  - SystemMonitor をポーリングする run_monitoring スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）
    - 監視は環境にかかわらず本番 sqlite_path を使用（設計上の挙動）
    - プロセス優先度を起動時に "high" に設定し、停止フラグファイルを検知して正常終了
    - duckdb と sqlite の接続確立と監視 DB の初期化を実施
- 設定管理 / 自動 .env ロード機能（src/kabusys/config.py）:
  - プロジェクトルート検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み（OS 環境変数を保護）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化
  - .env パーサーの強化: export 構文対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの扱いルール、オーバーライド／保護キー機能
  - Settings クラスで各種プロパティを提供（DB パス、paper_trading 用パス、ログレベル検証、閾値設定、環境判定ユーティリティ等）
- ログ／プロセスユーティリティを追加（src/kabusys/utils）:
  - setup_logging: stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成のフォールバックロジックやログレベル解決順を実装、ログファイルはデフォルト logs/<app_name>.log（30 日分保持）
  - process_priority: Windows/Linux の差分を吸収してプロセス優先度（nice / Windows priority class）と CPU affinity 設定を提供。権限不足時は警告してスキップ
- DuckDB を用いたリサーチ用ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py） — Momentum / MA200 / ATR / ボリューム系などの計算方針と定数が定義され、一部実装が着手されている

### Changed
- N/A（初回リリースに相当するため既存機能の変更はなし）

### Fixed
- N/A（初回リリース）

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされてしまう可能性がある旨の TODO コメントあり。将来的に前日終値・取得原価等のフォールバック導入を検討。
- research/factor_research.py:
  - ファイル末尾で実装が途中で切れている（calc_momentum の実装途中で終端している）。追加実装が必要。
- run_monitoring の挙動:
  - 監視は常に本番 sqlite_path を参照する仕様になっていることに注意（paper_trading 環境でも別 DB を使いたい場合は追加対応が必要）。
- 一部外部ライブラリ（PyYAML など）が存在しない場合は検証や機能の一部がスキップされる設計（validate_config で明示）。運用時は必要な依存をインストールすること。

---

## [0.1.0] - 2026-04-19

初回公開リリース。上記「Added」項目に記載した機能群を含む。

- 基本機能:
  - 実行スクリプト（run_execution, run_monitoring）、設定管理（config, config_setup）、設定検証（validate_config）
  - ロギング・プロセス制御ユーティリティ（utils.logging_setup, utils.process_priority）
  - ポートフォリオ構築・リスク調整・ポジションサイズ決定の純関数群（kabusys.portfolio）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - DuckDB ベースのファクター計算モジュールの骨格（kabusys.research.factor_research）

- 既知の設計上の注意:
  - run_monitoring は監視 DB として常に sqlite_path（本番 DB）を使用する仕様
  - paper_trading 環境は run_execution で専用 SQLite（デフォルト data/paper_trading.db）に分離される
  - 一部モジュールに実装 TODO / 未完の箇所あり（将来的な拡張を予定）

---

（今後のリリースでは、未実装部分の完成、テストカバレッジの追加、互換性に関する変更点、既知の問題の修正等を個別のエントリとして記載します。）