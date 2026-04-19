# Changelog

すべての注目すべき変更点をこのファイルに記載します。
このドキュメントは「Keep a Changelog」準拠のフォーマットを採用しています。

フォーマットの意味:
- Added: 新規に追加された機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の変更

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-19

初回リリース。以下の主要コンポーネントと CLI / ユーティリティ群を実装しました。

### Added
- 基本設定・環境変数管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得する仕組みを追加。
  - .env の自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml で自動検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env のパースは quoted / unquoted / export 形式やインラインコメントに対応する堅牢な実装を提供（ファイル: src/kabusys/config.py）。

- 環境設定ウィザード CLI
  - 対話式ウィザードで .env を初期作成・更新するツールを追加（python -m kabusys.config_setup）。
  - シークレット項目はマスク表示、選択肢／デフォルト提示、既存値の再利用機能を備える（ファイル: src/kabusys/config_setup.py）。

- 設定検証ツール
  - 起動前に必須環境変数やパス、config/*.yaml の存在・パース（PyYAML が存在する場合）を検証する CLI を実装（python -m kabusys.validate_config）。
  - KABUSYS_ENV の値チェック、KILL/LINE など本番環境向けの追加ガードを実装（ファイル: src/kabusys/validate_config.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプト（run_execution）を追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper トレード用 SQLite を利用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立ててセッションをスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理、execution.pid 管理（ファイル: src/kabusys/run_execution.py）。
  - 監視（モニタリング）ループ起動スクリプト（run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視は環境に関わらず本番用 sqlite_path を使用する仕様、stop flag による終了検知（ファイル: src/kabusys/run_monitoring.py）。

- ロギングの共通ユーティリティ
  - setup_logging を提供（StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテート、ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続）。（ファイル: src/kabusys/utils/logging_setup.py）

- プロセス優先度・CPU affinity ユーティリティ
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX の違いを吸収し、権限不足や未対応環境時は警告を出してスキップする（ファイル: src/kabusys/utils/process_priority.py）。

- ポートフォリオ構築モジュール
  - 候補選定と重み計算: select_candidates, calc_equal_weights, calc_score_weights を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順での選定、同点時の tie-break（signal_rank）に対応。スコア合計が 0 の場合は等重配分へフォールバックし警告出力。
  - セクター上限・レジーム乗数: apply_sector_cap, calc_regime_multiplier を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター集中上限チェック（売却予定銘柄の除外対応）。unknown セクターは上限適用除外。レジームに応じた乗数（bull/neutral/bear）を定義、未定義レジームは警告の上フォールバック。
  - ポジションサイズ計算: calc_position_sizes を実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）で丸め、per-stock 上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積、残差処理による追加配分ロジックを実装。

- Paper Trading 検証レポートツール
  - paper_verification_report CLI を追加。Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを集計し、閾値に基づいて PASS/FAIL を判定してレポート出力（ファイル: src/kabusys/tools/paper_verification_report.py）。
  - P95 計算ユーティリティや期間フィルタ、欠損テーブル時のフォールバックに対応。

- 研究用ファクター計算（骨格）
  - factor_research モジュールを追加（DuckDB 接続を受ける設計）。モメンタム・MA・ATR 等を計算する方針で実装開始（実装はファイル末尾で途切れているため一部未完の状態です）（ファイル: src/kabusys/research/factor_research.py）。

- パッケージメタ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定（ファイル: src/kabusys/__init__.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 設定ウィザードおよび表示時にシークレット項目をマスク表示することで、対話中の秘匿情報取り扱いに配慮（config_setup）。

---

注記:
- 各 CLI / スクリプトは外部ライブラリ（psutil, duckdb, PyYAML など）への依存を持ちます。validate_config は PyYAML のインストール有無で YAML 検証をスキップします。
- 実装の一部（例: research/factor_research が途中で切れている箇所など）は継続開発の余地があります。将来的なリリースで機能追加／修正が見込まれます。