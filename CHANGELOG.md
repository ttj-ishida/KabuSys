# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、重要度・カテゴリ別に整理しています。

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能と運用ユーティリティを実装しました。

### Added
- パッケージ基盤
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 実行スクリプト / デーモン化関連
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御にプロジェクトルートの `data/stop_requested.flag` を使用。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用して起動。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は専用の Paper Trading DB（デフォルト `data/paper_trading.db`）を使用し、MockBrokerClient を選択するような設計に対応（BrokerClientFactory を利用）。
    - 実行中は `data/execution.pid` に PID を格納・参照する仕組み（pid_file の引き渡し）。
    - 停止フラグ `data/stop_requested.flag` による安全停止処理を実装。
- 設定・環境変数管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - `.env` / `.env.local` の読み込みポリシー（OS 環境変数を保護する protected オプション）。
    - 複数の設定プロパティを提供（DB パス、API トークン、環境モード、監視閾値、paper_trading の挙動など）。
    - `PAPER_FILL_MODE` のバリデーション、「instant|partial|never|reject」をサポート。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト等で利用）。
  - .env パースと読み込みの堅牢化
    - export PREFIX、クォート文字列（シングル/ダブル引用）、エスケープ、インラインコメントの扱いに対応するパーサを実装。
- 設定支援 / 検証 CLI
  - config_setup: 対話式ウィザードで `.env` を作成・更新する CLI を追加（src/kabusys/config_setup.py）。
    - シークレット項目は表示マスク、既存値の再利用、選択肢サポート、保存前の確認などを実装。
  - validate_config: 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、`KABUSYS_ENV=live` 時の追加ガードなど。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ログディレクトリは引数 > LOG_DIR 環境変数 > デフォルト `logs/` の順に解決。
    - ファイルハンドラ作成に失敗した場合はコンソール出力のみでフォールバック。
    - 日次ローテーション、30日分保持。
  - process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - psutil を利用。権限エラーや未サポート環境では警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコアゼロ時は等金額配分へフォールバックし警告を出力。
  - portfolio.risk_adjustment: セクター集中制限の適用関数とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - unknown セクターは上限除外、レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - portfolio.position_sizing: 発注株数決定ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based", "equal", "score" を実装。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap のスケーリング、cost_buffer を考慮した安全なスケールダウンロジックを提供。
  - portfolio パッケージの __init__ を実装して主要関数をエクスポート。
- 解析 / リサーチ
  - research.factor_research: ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム、移動平均乖離、ATR、流動性等の計算方針と定数を定義。DuckDB 接続を受け取る設計。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status, trade_logs, risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ指標（P95 など）を取得して PASS/FAIL 判定を出力。
    - CLI 引数で期間指定（--from, --to）と DB パス指定（--db）。環境変数 `PAPER_TRADING_SQLITE_PATH` にも対応。
    - デフォルトの閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）。
- Monitoring DB 初期化
  - monitoring_db 初期化用呼び出しを実行スクリプトに組み込み（init_monitoring_db を呼び出して監視テーブルの存在を保証）。

### Changed
- ログ出力ポリシー
  - すべての起動スクリプトから共通の `setup_logging(app_name=...)` を呼び出す設計に統一。
- DB パスの扱い
  - run_monitoring は環境にかかわらず本番 `sqlite_path` を使用する明確化（監視用の分離を避けるため）。
  - run_execution は `KABUSYS_ENV=paper_trading` 時に paper_trading 用 SQLite を使用（分離運用）。
- .env ロード順序
  - OS 環境変数 > .env.local > .env の順でロードする仕様を明文化。OS 環境変数を保護する protected セットを導入。

### Fixed
- 環境変数パースの堅牢化
  - MONITOR_POLL_INTERVAL（run_monitoring）に不正な値が設定された場合にデフォルトへフォールバックするバリデーションを追加。0 以下や非整数で time.sleep に渡すことで発生する例外の回避。
- logging_setup のディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗してもアプリがクラッシュしないようハンドリングを追加し、コンソール出力のみで継続。

### Security
- .env の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト・CI での誤動作防止）。
- config_setup で生成される `.env` に対して「絶対に Git にコミットしないこと」を明示するヘッダを追加。

### Documentation
- 各モジュールに docstring を充実させ、利用方法・引数・戻り値・注意点（例: cost_buffer の用途、regime の扱いなど）を記載。
- config_setup と validate_config に使用方法（CLI）の説明を追加。
- tools.paper_verification_report に使い方の例と環境変数の説明を追加。

### Notes / Known limitations
- research.factor_research モジュールは骨格（設計と定数定義）を含むが、実装の一部（全ての計算処理）は未完了の箇所が存在します（今後の実装予定）。
- position_sizing の価格フォールバック（price が 0.0 の場合の扱い）は注記として残しており、将来的に前日終値や取得原価などのフォールバックを検討中。
- process_priority / set_cpu_affinity は環境（権限・OS）に依存し、失敗時は警告を出してスキップします。

---

今後の予定（短期）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出）。
- ExecutionEngine / BrokerClient 周りの統合テストと paper_trading の挙動確認。
- monitoring 関連のアラート送信（LINE 統合）の実装および運用テスト。

もしログや設定の動作確認、もしくは特定モジュールの動作説明（例: position_sizing のスケーリングロジックの詳細など）が必要であればお知らせください。さらに詳細なリリースノートやアップグレード手順も作成します。