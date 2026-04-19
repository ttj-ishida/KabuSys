# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
リリース日はソースツリーのバージョンに合わせて記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
- 環境設定関連
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサ実装（`export` 形式、クォート内エスケープ、インラインコメント処理に対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを実装し、環境変数経由での設定取得を統一（J-Quants / kabuAPI / DBパス / Paper Trading 設定 等）。
  - `PAPER_FILL_MODE` のバリデーション（許容値: instant|partial|never|reject）。
  - 環境種別（development / paper_trading / live）やログレベルの検証ロジックを導入。
- 設定管理 CLI
  - 対話式ウィザード `config_setup.py` を追加し、.env の初期作成・更新を支援。
  - 設定検証 CLI `validate_config.py` を追加し、必須環境変数、ファイルパス、config/*.yaml の存在・パースなどの事前チェックを実行可能。
  - `validate_config.py` に `--strict` オプションを実装（警告を FAIL 扱いにする）。
- 実行エントリ／デーモン類
  - ExecutionEngine 起動スクリプト `run_execution.py`
    - KABUSYS_ENV が paper_trading の場合は paper 専用 SQLite を使用して本番と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（本番 / モックの切替）。
    - ExecutionEngine の起動・監視ループ、停止フラグ（data/stop_requested.flag）検知、PID ファイル取り扱い。
    - デフォルトでプロセス優先度を "high" に設定。
  - Monitoring 起動スクリプト `run_monitoring.py`
    - SystemMonitor のポーリングループを起動。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知により安全にループ終了。
- ロギング・プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - StreamHandler（stdout） + TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに統一的に設定するユーティリティ。
    - ログディレクトリ作成失敗時のフォールバック処理（コンソール出力のみにする）。
  - `utils/process_priority.py`
    - psutil ベースで Windows/Linux/macOS のプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`
    - シグナル候補選定（score 降順、signal_rank による tie-break）。
    - 等重み・スコア加重の重み計算（スコア合計が 0 の場合は等重みへフォールバック）。
  - `portfolio/risk_adjustment.py`
    - セクター集中上限を適用する関数（既存保有のセクターエクスポージャ算出、ブロック対象セクターの除外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数計算（allocation_method: risk_based / equal / score）。
    - 単元株丸め、各銘柄上限・aggregate cap、cost_buffer による保守見積り、スケールダウンと残余配分ロジックを実装。
- リサーチ（実装途中）
  - `research/factor_research.py` を追加。DuckDB 接続を用いたモメンタム・ボラティリティ等のファクター計算を目的としており、設計・定数類と calc_momentum の雛形（未完）を含む。
- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を SQLite の paper_trading DB から集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）。
    - 判定閾値を定数で定義（稼働率 99%、成功率 90% など）。
- その他
  - パッケージのメタ情報 `__init__.py` にバージョン（0.1.0）とエクスポートモジュール一覧を追加。
  - モジュール間で DuckDB / SQLite を併用する設計（分析用に DuckDB、履歴/監視用に SQLite）。

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

注記:
- 一部モジュール（例: research/factor_research.py）の関数実装は途中で終わっている箇所があり、今後の追加実装が必要です。
- 実運用時は .env に機密値（API トークン等）を設定し、.env を決して VCS にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。