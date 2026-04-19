# Changelog

すべての重要な変更点をこのファイルに記載します。
フォーマットは「Keep a Changelog」準拠です。  

※ 本CHANGELOGは提供されたソースコードから推測して作成しています。

## [Unreleased]

（現時点で未リリースの差分はありません）

---

## [0.1.0] - 2026-04-19

初回リリース。以下の主要コンポーネントとユーティリティを実装しています。

### Added
- 基本バージョン情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 `data/stop_requested.flag` ファイルで検知して終了。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用して DB 接続。
    - duckdb と sqlite3 の接続確立と初期化処理を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、Paper Trading 用 DB（`data/paper_trading.db` など）に完全分離して記録。
    - 停止フラグ、PID ファイル (`data/execution.pid`) の扱いと、スレッドでの実行制御を実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderManager / RiskManager / Reconciler 等を組み立てて ExecutionEngine を起動。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート判定: .git / pyproject.toml を探索）。
    - `.env` と `.env.local` の読み込み順序を実装（OS 環境変数を保護する仕組みあり）。
    - `.env` 行のパースでクォートやエスケープ、インラインコメントに対応。
    - 各種設定値をプロパティとして提供（DB パス、PID/kill フラグ、閾値、環境判定など）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト用）。
  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - 入力項目一覧（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を定義。
    - 既存 `.env` の読み込み/参照、秘密値のマスク表示、保存確認、書き込みロジックを実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無い場合はスキップ）、本番環境向けのガード（LINE 設定や Kill Switch の設定確認）を実装。
    - `--strict` オプションで警告を FAIL 扱いするモードを提供。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル順位付け（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て0の場合は等分配へフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有を基にセクターごとのエクスポージャーを計算し、上限（デフォルト 30%）を超えるセクターの新規候補を除外。
    - レジームに応じた資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマップと未知レジームのフォールバック挙動）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）、stop-loss ベースのリスク計算、per-position および aggregate のキャップ、コストバッファ、スケールダウンと残差調整（lot 単位での再配分）を実装。

- 監視／レポートツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを実装。
    - CLI 引数で期間指定（--from/--to）と DB パス更新（--db）をサポート。
    - 指標：
      - システム稼働率（uptime）、総ポーリング数、エラー数
      - 注文成功率（fill rate）、送信率（send rate）
      - リスク却下数
      - API レイテンシ（平均／最大／P95）
    - Pass/Fail 基準を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200ms など）して判定を出力。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対する統一ログ設定機能を追加。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（ログディレクトリ、ファイル名: <app_name>.log）を設定。ログファイルは 30 日分保持。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）、ログディレクトリ解決順（引数 > 環境変数 LOG_DIR > logs/）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度設定（set_process_priority）を実装。Windows / POSIX（Linux/Mac/FreeBSD）を吸収し、psutil を用いて nice / priority を設定。許可エラー時は警告を出して安全にスキップ。
    - CPU affinity 設定（set_cpu_affinity）を実装。利用可能コア数の制約や権限エラーに対するフォールバック付き。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算の設計を実装（Momentum, Value, Volatility, Liquidity 等を想定、DuckDB を利用）。
    - モメンタム (calc_momentum) の実装を開始。ターゲット日を基準に 1M/3M/6M リターンや 200 日移動平均乖離率を算出する設計になっている（関数は未完の箇所あり）。全関数は prices_daily / raw_financials テーブル参照を前提。
    - 設計方針として「外部 API を使わない」「純粋関数／DB 参照のみ」での実装を明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- 機密情報（J-Quants リフレッシュトークンや kabu API パスワード等）は .env に保存する想定。`.env` を Git にコミットしない旨を README / ウィザード出力で明記。

---

注記:
- 一部モジュール（研究用ファクター計算など）は未完の箇所や TODO コメントが残っています（例: factor_research.calc_momentum の末尾が未完）。
- 実行時の挙動や外部依存（psutil, duckdb, PyYAML 等）の有無によりファイル入出力/検証が異なるため、運用環境では依存関係の確認と環境変数の設定（validate_config の実行）を推奨します。