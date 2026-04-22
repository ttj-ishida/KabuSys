# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Unreleased: 開発中の変更（現在は空）
- 各リリース: 追加 (Added), 変更 (Changed), 修正 (Fixed), 非推奨 (Deprecated), 削除 (Removed), セキュリティ (Security)

## [Unreleased]

---

## [0.1.0] - 2026-04-11

初回リリース。自動売買システム「KabuSys」のコアユーティリティ、設定管理、起動スクリプト、ポートフォリオ構築ロジック、検証ツールなどを公開。

### Added
- 全体
  - パッケージ初回公開 (パッケージバージョン: 0.1.0)。
  - モジュール構成を整備し、主要機能を分離（config / utils / portfolio / portfolio/* / execution / monitoring / tools / research 等）。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定（J-Quants / kabu API / DB パス / ログレベル / 環境種別 等）を取得。
    - env の妥当性検査（development / paper_trading / live）とログレベル検証。
    - Paper Trading 用の各種設定（paper_sqlite_path、paper_fill_mode 等）。
  - 自動 .env ロード機能を実装（.env / .env.local をプロジェクトルートから読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話形式で .env の作成・更新を支援。機密項目はマスク表示。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数・ファイル存在・YAML パース等の事前検証を実行（--strict オプションあり）。
- 起動スクリプト / 実行系
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用 SQLite（data/paper_trading.db など）と MockBrokerClient を利用し、本番 DB と分離して動作。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
    - リスク管理（RiskManager）、OrderManager、Reconciler 等の組み立てと実行ループを実装。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境に関係なく監視は本番 sqlite_path を使用し、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 停止フラグ検知、例外発生時のログ出力やリソース後片付けを実装。
- ロギング / プロセス制御
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の環境変数連携。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収して set_process_priority(level) と set_cpu_affinity(n) を提供。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・配分（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコアが全て 0 の場合は等配分にフォールバック（警告ログ）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有に基づくセクター集中制限を実装（unknown セクターは除外しない挙動）。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバック 1.0。
  - 銘柄ごとの株数決定（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - lot_size（単元株）対応、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング実装。
    - aggregate cap 超過時のスケールダウンと残差処理を実装（ロット単位で再配分）。
  - portfolio パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- Research
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 等の計算設計方針を記載。DuckDB 接続を想定。
- Tools
  - Paper Trading 向け検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定。
    - 日付フィルタ、DB パス引数、閾値の定義を含む。
- DB 初期化 / 監視
  - 監視用 DB 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring で呼ぶことでテーブルの存在を保証。
- パッケージ情報
  - __version__ = "0.1.0" を設定（src/kabusys/__init__.py）。

### Changed
- 環境変数読み込み
  - .env パーサーを強化し、export 構文、クォート文字列中のバックスラッシュエスケープ、行内コメントの扱いなどに対応（src/kabusys/config.py）。
  - .env の読み込み順序を OS 環境 > .env.local (override) > .env として、OS 環境変数を保護する仕組みを導入。
- ログ出力
  - StreamHandler を stdout に向けることで外部のリダイレクト/pipeline と整合するようにした（src/kabusys/utils/logging_setup.py）。
- 起動スクリプト
  - run_execution/run_monitoring 起動時に最初にプロセス優先度を high に設定するようにした（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）。
- Paper Trading 分離
  - paper_trading 環境では専用 SQLite を使用するように分離（settings.is_paper による分岐）。これにより paper_trading と本番データベースは完全分離。

### Fixed
- .env パースの堅牢性向上（引用文字列のエスケープ処理、コメント処理の改善）により、特殊文字を含む値の読み込み問題を軽減（src/kabusys/config.py）。
- ログディレクトリ作成失敗時のハンドリングを改善し、起動継続できるように（src/kabusys/utils/logging_setup.py）。
- プロセス優先度設定で発生し得る権限エラーを捕捉し、警告に留めて処理を継続するように（src/kabusys/utils/process_priority.py）。

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- 機密情報の取り扱い
  - 設定ウィザードは機密項目（トークンやパスワード）をマスク表示し、.env を生成する際に注意を促すメッセージを明示。

---

注:
- この CHANGELOG はコードベースの内容から機能と変更点を推測して作成しています。実際のリリースノート作成時にはコミット履歴や PR 説明を参照して微修正してください。