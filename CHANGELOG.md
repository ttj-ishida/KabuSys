# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

目次
- [Unreleased](#unreleased)
- [0.1.0] - 2026-04-24

## Unreleased
（現時点で未リリースの変更はありません）

## 0.1.0 - 2026-04-24

概要: 初期公開リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、実行/監視スクリプト、設定管理、ペーパートレード検証ツール、ポートフォリオ構成ロジック、ログ/プロセス制御ユーティリティおよび一部のリサーチ機能を実装。

### Added
- パッケージ初期バージョンの追加
  - パッケージメタ: `__version__ = "0.1.0"`
- 実行・監視ランチャー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト data ディレクトリ内の `stop_requested.flag` ファイル検知で行う。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB は環境にかかわらず production の `sqlite_path` を使用する設計（監視は本番 DB を参照）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` 時は paper 用専用 SQLite（`data/paper_trading.db` がデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live に応じて Mock/実実装を切替）。
    - エンジンはスレッドで実行し、同様に停止フラグで停止可能。PID ファイルの出力に対応。
- 設定・環境管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env の読み込みは優先順: OS 環境 > .env.local > .env。
    - .env パーサは `export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
    - Settings クラスを提供し、各種環境変数（J-Quants トークン、kabu API、DB パス、ログレベル、各種閾値等）をプロパティとして取得・バリデーション。
    - `PAPER_FILL_MODE` に対する検証（許容値: "instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` の有効値チェック（development / paper_trading / live）と `LOG_LEVEL` の検証。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - シークレット入力のマスク、デフォルト値、選択肢表示、既存 .env の読込・再利用機能あり。
    - 最終確認後に .env を書き出し、書き出しテンプレートを提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な検証を行う CLI を実装。
    - 必須環境変数の未設定検出、プレースホルダ値検出、パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 有無に依存）、本番環境向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を提供。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリ共通の logging セットアップ関数 `setup_logging()` を追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで動作。
    - ログレベル/ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - プロセス優先度設定 API を追加（Windows と POSIX を吸収）。
    - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity()` を提供。
    - psutil 利用、権限不足や未対応 OS 時は警告を出してスキップ。
- Portfolio 構成ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定関数 `select_candidates`、等分配 `calc_equal_weights`、スコア加重 `calc_score_weights` を実装。
    - 同点のタイブレークやスコア全0時のフォールバックを考慮。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用 `apply_sector_cap`、市場レジーム乗数 `calc_regime_multiplier` を実装。
    - レジームに応じた乗数（bull/neutral/bear）と未知レジームのフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 `calc_position_sizes` を実装。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap スケーリング、コストバッファの考慮、残余キャッシュによる端数配分ロジック等を実装。
  - portfolio/__init__.py で上記機能をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（既定: data/paper_trading.db）から指標を集計して検証レポートを生成する CLI を実装。
    - 取得指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルトの合否閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - 日付フィルタ（--from, --to）と DB パス指定（--db）をサポート。
- リサーチ（ファクター計算）骨子
  - research/factor_research.py（ファクター計算ロジックの骨格を追加）
    - モメンタム等のファクター計算方針と定数を定義（1M/3M/6M リターン、MA200 乖離、ATR 等）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。ただしファイル末尾で計算関数の実装が途中の状態（今後実装継続予定）。
- パッケージ構成
  - 各モジュールが所定の名前空間（execution, monitoring, portfolio, utils, research, tools 等）でモジュール化。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Security
- 環境変数やシークレットを .env に保存することを想定し、config_setup のヘッダーで .env を Git にコミットしない旨を明示。

### Deprecated
- なし

### Removed
- なし

### Breaking Changes
- なし（初回リリース）

注記:
- 実際のブローカークライアントの実装や SystemMonitor / ExecutionEngine の詳細は本 CHANGELOG に含められていない箇所があります。リポジトリ内の該当モジュール（execution.*, monitoring.* 等）の実装や設定ファイル（config/*.yaml）を参照してください。
- .env の自動ロードや本番/ペーパートレード用 DB パスの扱いは設計上重要な動作を伴うため、本番運用時は `kabusys.validate_config` による検証を必ず実行してください。