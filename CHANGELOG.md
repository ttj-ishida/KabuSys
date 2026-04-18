# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース日付は YYYY-MM-DD 形式です。
- 重要な変更（機能追加、修正、破壊的変更など）をカテゴリ別に記載します。

## [Unreleased]
（現時点のスナップショットは 0.1.0 として初回リリース済みの想定のため、未リリース項目はありません）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 停止はプロジェクトの `data/stop_requested.flag` を検知して行う。  
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用して監視テーブルを初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 用の専用 SQLite（`data/paper_trading.db`）に記録して本番 DB と分離。  
    - 停止フラグ検知で安全にエンジンを停止する仕組み（`data/stop_requested.flag`）。  
    - 実行時に PID ファイルを管理。

- 設定管理・ウィザード・検証
  - config.py: 環境変数/ .env 管理モジュールを追加。  
    - 自動 .env ロード（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）を提供（無効化可能なフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意）。  
    - 複雑な .env 行パーサ実装（export プレフィックス対応、クォート内エスケープ対応、インラインコメント処理など）。  
    - 各種設定プロパティ（DB パス、API トークン、監視しきい値、環境判定ヘルパー等）を提供。
  - config_setup.py: 対話式 .env ウィザードを追加。  
    - 初期 .env の作成/更新を支援する CLI。複数の設定項目（実行環境、API トークン、DB パス、ログレベル、Kill Switch 設定等）を対話的に入力可能。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パースチェック（PyYAML 有無に応じて）など。  
    - `--strict` オプションで警告を失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - コンソール stdout 用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力をルートロガーに設定。  
    - ログディレクトリ自動作成、既存ハンドラの安全なクローズ・クリア、環境変数/引数経由でのログレベル/ディレクトリ解決をサポート。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX を吸収する実装（psutil 利用）。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。権限不足や未対応環境は警告でフォールバック。

- Execution（発注系）骨組み
  - run_execution から組み立てられる各コンポーネント（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager）への接続を想定した初期化コードを追加。  
  - RiskManager のデフォルトパラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を設定し、初期資金に broker.get_available_cash() を使用。

- ポートフォリオ構築モジュール（純関数群）
  - portfolio/portfolio_builder.py: 候補選定・重み計算を追加。  
    - select_candidates: スコア降順で候補抽出（タイブレークに signal_rank）。  
    - calc_equal_weights: 等金額配分。  
    - calc_score_weights: スコア加重（全スコアが 0 の場合は等分配にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py: セクター集中制限・レジーム乗数を追加。  
    - apply_sector_cap: セクター別既存保有率が上限を超える場合に当該セクターの新規候補を除外。unknown セクターは除外対象外。  
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数（1.0/0.7/0.3）。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数算出ロジックを追加。  
    - risk_based と equal/score の両方式をサポート。  
    - lot_size（単元）で丸め、単銘柄上限や aggregate cap（available_cash）でスケーリングし、残余キャッシュ分を端数処理で優先配分するロジックを実装。  
    - cost_buffer による保守的なコスト見積りを考慮。入力価格欠損時のログ出力を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 結果の検証レポート生成スクリプトを追加。  
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等。  
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。  
    - 日付フィルタ（--from/--to）および DB パス指定（--db, 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。  
    - P95 計算、各種フォーマット関数、データ欠如時の耐性（OperationalError 捕捉）を実装。

- リサーチモジュール（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム、MA、ATR、出来高等を想定）。  
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルから計算する設計方針を明記。  
    - 定数（窓長等）と関数 calc_momentum の雛形を含む（詳細実装は継続）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記（実装に関する補足・設計上の判断）
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされ、テスト目的等で `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。  
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとする（権限不足時は警告でフォールバック）。  
- Paper Trading モードでは DB を明確に分離しており、本番データベースへの書き込み混入を防止する設計。  
- position_sizing 等の数値ロジックは将来的な拡張（銘柄別 lot_size 管理、価格フォールバックなど）を考慮した TODO コメントを含む。

もしリリースノートにもっと詳細な変更（コミット単位の差分や既存コードからの移行手順など）を含めたい場合は、該当する差分（コミットログや以前のバージョンのソース）を提供してください。