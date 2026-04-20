# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。重要な機能追加・変更・修正を日本語で記載しています。

## [Unreleased]

### Added
- プロジェクト初期実装として以下の主要コンポーネントを追加。
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine をデーモンスレッドで起動・監視する起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による外部制御をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立てを導入。
    - RiskManager に対するデフォルト RiskConfig を導入（max_position_pct, max_utilization, rate_limit_per_sec など）。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor を定期的にポーリングするループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様。
    - 外部停止フラグ検出で優雅に終了。
  - 設定管理 (src/kabusys/config.py)
    - .env / .env.local の自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml）。
    - 複雑な .env 行パース（export 形式、クォート内エスケープ、インラインコメント処理 等）を実装。
    - Settings クラスで環境変数をプロパティとして取得する API を提供（DB パス、各種閾値、env 判定、paper_trading 用設定 等）。
  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 起動前に .env と config/*.yaml の基本的な妥当性チェックを行う CLI を実装。
    - --strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、YAML パース検証（PyYAML があれば）、本番環境向けガード等を実装。
  - 設定ウィザード CLI (src/kabusys/config_setup.py)
    - 対話式に .env を作成・更新するウィザードを実装。既存 .env の読み込みとマスク表示（シークレット項目）対応。
  - ロギング共通設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラのクリア、環境変数 / 引数によるログレベル・ログディレクトリ解決をサポート。
  - プロセス優先度ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX を吸収した set_process_priority と set_cpu_affinity を実装（psutil ベース）。
    - アクセス権限エラー時は警告を出してフォールバックする安全策を実装。
  - ポートフォリオ構築ライブラリ (src/kabusys/portfolio/*)
    - 候補選定: select_candidates（スコア降順・タイブレーク）。
    - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等重フォールバック）。
    - セクター集中制限: apply_sector_cap（既存保有エクスポージャーを用いた除外ロジック、unknown セクターは無制限扱い）。
    - レジーム乗数: calc_regime_multiplier（bull/neutral/bear の乗数を定義、未知レジームはフォールバック）.
    - 株数決定: calc_position_sizes（risk_based / equal / score の割当方式、lot_size、aggregate cap、cost_buffer によるスケールダウンを実装）。
  - 研究用ファクタ計算スケルトン (src/kabusys/research/factor_research.py)
    - Momentum 等のファクター計算方針と定数を定義。DuckDB 接続を受け取り prices_daily 等を参照して計算する設計。
  - Paper Trading 検証レポートツール (src/kabusys/tools/paper_verification_report.py)
    - SQLite（Paper Trading DB）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）に基づく PASS/FAIL 判定を実装。
  - パッケージメタ (src/kabusys/__init__.py)
    - バージョンを __version__ = "0.1.0" に設定。

### Changed
- なし（初期リリース相当の追加のみと推定）。

### Fixed
- なし（初期実装段階のためバグ修正履歴は無し）。

### Security
- .env の自動生成ウィザードでシークレット項目はマスク表示し、.env を Git にコミットしない旨の注意書きを出力。

## [0.1.0] - 2026-04-20

初期公開リリース（開発段階）。上記の主要機能をパッケージ化してリリース。

### Added
- 実行制御・監視の起動スクリプト（run_execution, run_monitoring）。
- 環境設定の自動読み込み・パース、Settings API。
- 設定ウィザード（config_setup）と検証ツール（validate_config）。
- ロギング / プロセス優先度ユーティリティ。
- ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群。
- Paper Trading 向け検証レポート生成ツール。
- 研究用ファクタ計算の骨格実装。
- パッケージメタ情報（バージョン 0.1.0）。

### Notes / Known limitations
- factor_research.calc_momentum 等の一部関数は実装継続中（ファイル末尾で未完部分あり）。
- 一部のロジックで外部データ欠損（価格 0.0 など）に対するフォールバックが TODO コメントとして残っています（将来的な改善予定）。
- process_priority の一部挙動は OS 権限に依存し、権限不足時は設定がスキップされる可能性がある。
- .env の自動読み込みはプロジェクトルートが検出できない場合スキップされる（配布後の挙動を考慮）。

---

今後の予定（例）
- research モジュールのファクター実装完了とユニットテスト追加。
- ExecutionEngine / Broker クライアントの統合テストおよび paper_trading/backtest 機能強化。
- ポートフォリオ最適化アルゴリズムの拡張（銘柄別 lot_size 対応、手数料モデルの改善）。
- 監視・アラート機能の強化（LINE 通知統合のテストとリトライ等）。