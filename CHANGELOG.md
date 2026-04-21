# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」記法に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-21

初回公開リリース。KabuSys のコア機能（起動スクリプト、設定管理、実行エンジン周り、ポートフォリオ構築、ユーティリティ、検証ツール、監視関連）を実装しました。

### 追加 (Added)
- 全体
  - パッケージ初版を公開（バージョン 0.1.0）。
  - パッケージメタ情報: `__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定し、DB 接続、ブローカー生成、OrderManager / RiskManager / Reconciler を組み立ててエンジンをスレッドで実行。停止は data/stop_requested.flag を監視して行う。
  - run_monitoring: SystemMonitor をポーリングで起動するスクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を使用。

- 設定・環境管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。環境変数の取得をラップする `Settings` クラスを提供。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL 等）。
    - Paper Trading 用設定（PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH）。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。.env の新規作成・更新を支援。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数や config/*.yaml、パスの存在等を検証 (--strict で警告をエラー扱いに可能)。

- Execution / Broker
  - BrokerClientFactory を用意（実際の実装は別モジュール）。KABUSYS_ENV が `paper_trading` の場合は MockBroker を用い、paper_trading 用 DB（data/paper_trading.db 等）に記録して本番 DB と分離。

- 監視 / DB
  - monitoring_db 初期化ユーティリティ（`init_monitoring_db`）を利用し、監視テーブルの存在を保証（冪等）。
  - DuckDB を分析用に併用（duckdb_path）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルの上位選抜ロジック（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア全ゼロ時は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用。売却予定銘柄を除外するオプション、"unknown" セクターの扱いなど。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。lot_size（単元株）、max_position_pct、max_utilization、コストバッファ、aggregate cap のスケールダウン処理などを実装。残差処理で lot 単位で補正。

- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。コンソール (stdout) と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみにフォールバック。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/macOS/FreeBSD）を吸収し、権限がない場合は警告してスキップ。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。閾値はファイル内に定義（例: 稼働率 >= 99% 等）。
    - コマンドライン引数で期間指定（--from / --to）と DB パス指定（--db）。環境変数 `PAPER_TRADING_SQLITE_PATH` を参照。

- 研究モジュール（スケルトン）
  - research/factor_research.py: DuckDB を使用したファクター計算モジュールの枠組みを追加（Momentum/Value/Volatility/Liquidity 計算を想定）。関数仕様と定数を実装開始。

### 改善 (Changed)
- .env 読み込みロジックを堅牢化
  - _parse_env_line: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの処理、空行・コメント行の無視などをサポート。
  - 自動ロードの挙動: OS 環境変数を保護しつつ .env / .env.local を優先順でロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

- ログ設定
  - 既存ハンドラを安全に flush/close してから上書きすることで二重登録を防止。

- run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` が不正な場合はデフォルトにフォールバックして警告を出力。

### 修正 (Fixed)
- process_priority のエラー耐性を強化
  - 権限不足やプラットフォーム未対応時に例外を抑えて警告ログを出力するようにして、起動失敗につながらないようにした。

- logging_setup のファイル出力失敗をハンドリング
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合でもコンソール出力のみで継続するようにした。

- paper_verification_report
  - P95 の算出、レイテンシ集計、NULL 値ハンドリングを安定化。

### 注意事項 (Notes)
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず production 想定の sqlite_path（Settings.sqlite_path）を使用します。開発/ペーパートレードで監視を分離したい場合は環境変数を明示的に設定してください。
- 実行エンジン（run_execution）は `KABUSYS_ENV=paper_trading` のとき paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離されます。
- 環境変数の取り扱い:
  - PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"（無効値は例外発生）。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険です（validate_config で警告）。
- .env ファイルは機密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup でも注意喚起あり）。
- Engine / Broker 等の詳細実装（API 接続や戦略本体、ブローカー実装等）はこのリリースで枠組みを提供しています。実際の取引接続やストラテジは別モジュール/別実装を参照してください。

### 既知の問題 (Known issues)
- research/factor_research.py はファクター計算の骨組みを提供していますが、一部関数（詳細な SQL 実装など）が未完または拡張余地があります。
- 一部の TODO がコード内に残っており（例: price フォールバックや lot_size 銘柄別対応など）、将来的な改善候補です。

### セキュリティ (Security)
- 初期設定ウィザードと .env 出力は機密情報を扱います。.env のパーミッション管理や安全な保管方法（Vault 等）の検討を推奨します。

---

今後のリリースでは、戦略ロジック本体、ブローカー実装の追加、より詳細なテストカバレッジ、ファクター計算の完成、運用監視の強化などを予定しています。