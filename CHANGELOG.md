# Changelog

すべての重要な変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載します。

リリースノートは主にソースコードから推測して作成しています。実装済み機能、CLI、設定、ユーティリティ、既知の制約／注意点を中心にまとめています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル（data/stop_requested.flag）検知で優雅に終了。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 `sqlite_path` を使用して DB 接続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動前に停止フラグを確認し、フラグが立っていれば起動せず終了。
    - 実行はデーモンスレッドで行い、停止フラグ発見時にエンジンを停止する。

- 設定管理
  - config.py
    - .env ファイル自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env 読み込みの優先順: OS 環境変数 > .env.local > .env。
    - 複雑な .env パース対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
    - 環境変数取得用の Settings クラスを提供（各種設定プロパティを提供）。
    - 各種検証を組み込んだプロパティ：`env` / `log_level` の値検査、`paper_fill_mode` の有効値検査等。
    - デフォルトパス・フラグ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH など）を一元管理。

- 設定ウィザード & 検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を提供。
    - 必須・任意項目のプロンプト、シークレット値のマスク表示、保存確認、.env 書き出し。
  - validate_config.py
    - 起動前チェック用 CLI を提供。
    - 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング＆プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でファイル出力（デフォルト logs/、30 日間保持）を設定。
    - 既存ハンドラをクリアして二重設定を回避。ログディレクトリ作成失敗時はフォールバックしてコンソールのみ出力。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定 `set_process_priority(level)`（"high"/"normal"/"low"）を追加。Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収。
    - CPU affinity 設定 `set_cpu_affinity(cpu_count)` を追加（アクセス権限や未サポート環境では警告を出してスキップ）。

- Execution 関連コンポーネント（起動スクリプトから組み立てる主要部品の存在が示唆）
  - BrokerClientFactory（ブローカー選定）
  - ExecutionEngine（エンジン本体）
  - OrderManager / OrderRepository / Reconciler / RiskManager（依存コンポーネント）

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視用テーブルを冪等に保証。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等分配 calc_equal_weights。
    - スコア重み calc_score_weights（全スコアが 0 の場合は等分配にフォールバックし Warning）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）と未知レジームのフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき株数を計算。
    - 単元株（lot_size）丸め、1 銘柄上限や aggregate cap（available_cash）に基づくスケーリング、cost_buffer を用いた保守見積り、残差の公平配分ロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）を読み、期間指定で検証レポートを生成する CLI を提供。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数等を計算。
    - Pass/Fail の閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）し、判定を出力。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム / Value / Volatility / Liquidity の計算方針と定数を定義。DuckDB 接続を受け取り `prices_daily`/`raw_financials` から計算する設計（実装の一部は未完）。

### Changed
- ログ出力の振る舞い
  - ログの StreamHandler は stderr ではなく stdout を使用（cron/タスクスケジューラで stdout/stderr を一本化する運用に配慮）。

- DB の扱い
  - 監視（monitoring）処理は環境に関係なく本番用 sqlite_path を使用する運用方針がスクリプトに明記されている。
  - Execution エンジンは paper_trading 環境時に専用 DB に切り替える（分離）。

### Fixed
(特定のバグ修正履歴はソースから直接判別できないため記載なし)

### Security
- 権限に起因する操作（プロセス優先度変更、CPU affinity、ログディレクトリ作成等）に失敗した場合は警告を出してフォールバックする実装になっており、起動失敗につながらない安全な設計。

### Known issues / Notes / TODO
- portfolio/risk_adjustment.apply_sector_cap にて price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる可能性がある点が注記されている。将来的には前日終値や取得原価をフォールバック価格として使用する拡張が想定されている（TODO コメントあり）。
- research/factor_research.py はファイル末尾が途中で切れている（スニペットでは実装が未完／途中）。完全なファクター計算機能は今後の実装が必要。
- tools パッケージの __init__.py は空。ツール群の整理・公開 API 整備が今後の課題。
- validate_config の YAML 検証は PyYAML 非インストール時にスキップされる（警告を出す）。
- 一部の処理は OS 権限や psutil の機能に依存しており、Unprivileged 環境では効果が限定的。警告は出るが処理は継続する設計。

---

注: 本 CHANGELOG は提示されたソースコードの状態に基づいて推測して作成しています。実際のリリースノートには運用上の決定・外部変更（環境構築手順、DB マイグレーション、依存パッケージバージョン等）を合わせて記載することを推奨します。必要であれば、各ファイルごとのさらに詳細な説明（関数一覧・引数説明・使用例など）を付け加えた拡張版 CHANGELOG を作成します。