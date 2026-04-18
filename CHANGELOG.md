Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースの内容から推測して作成しています。実際のコミット履歴とは差異がある場合があります。

---
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点の差分はありません）

## [0.1.0] - 2026-04-18

初回リリース（推定）。以下の機能群・改善を実装しています。

### 追加 (Added)
- 基本ライブラリ・エントリポイント
  - パッケージ初期化: kabusys.__version__ = "0.1.0"
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine 起動スクリプト（プロセス優先度設定、PID ファイル管理、停止フラグ監視、スレッド実行）。
      - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db 等）を使用して本番 DB と分離。
      - BrokerClientFactory により実行時に適切なブローカークライアントを生成。
      - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler を組み立てて起動。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB は常に本番 DB を参照する仕様）。
      - 停止フラグファイル（data/stop_requested.flag）検知による安全停止、例外発生時のログ出力とリトライ継続。
- 設定管理 & 初期化ツール
  - kabusys.config:
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込みルール（OS 環境変数の保護、override ロジック）。
    - 高度な .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスにより lazy プロパティで各種設定値を取得（J-Quants / kabu API / DB パス / 監視閾値 等）。
  - kabusys.config_setup:
    - 対話式ウィザードで .env を初期作成・更新。機密項目はマスク表示。
    - デフォルト値、選択肢、説明を表示しユーザー入力をサポート。
  - kabusys.validate_config:
    - 起動前チェック CLI。必須環境変数の存在、KABUSYS_ENV 値、ログレベル、DB パスの親ディレクトリ、config/*.yaml の存在／YAML パース（PyYAML があれば）を検証。
    - --strict モードで警告も失敗扱いにできる。
- ポートフォリオ構築ユーティリティ（pure functions、DB 非依存）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分（全スコアが 0 の場合は等金額にフォールバックし警告）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（売却予定銘柄を除外、"unknown" セクターは制限適用外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") による投下資金乗数（デフォルトフォールバックあり）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく株数算出。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、残差処理（fractional remainder に基づく追加配分）を実装。
    - cost_buffer を用いた手数料/スリッページ考慮。
- 解析・リサーチ
  - kabusys.research.factor_research:
    - ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）設計。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照して計算する方針。モメンタム計算（calc_momentum）の骨組みを実装（注: ファイル末尾は未完の記述あり）。
- ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード検証レポート生成スクリプト（期間指定可）。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を出力。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）。
    - 基準値（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）を定義。
- 監視用 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db が run_* スクリプトから呼ばれて監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - kabusys.utils.logging_setup:
    - 統一ログ設定関数 setup_logging（StreamHandler を stdout に、TimedRotatingFileHandler による日次ローテーション）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - kabusys.utils.process_priority:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows と POSIX（Linux / Darwin / FreeBSD）を吸収する抽象化。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

### 変更 (Changed)
- 監視（run_monitoring）:
  - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視データは本番 DB に記録する方針）。
- .env 読み込み順と上書きルールを明確化:
  - OS 環境変数 > .env.local > .env の優先順位。既存 OS 環境変数は保護され、.env.local での上書きは許可。

### 修正 (Fixed)
- .env パースの堅牢化:
  - 引用符付き値のバックスラッシュエスケープ処理、export プレフィックス対応、インラインコメントの取り扱い、無効行のスキップを実装して、より多様な .env フォーマットに対応。
- ログ設定の堅牢化:
  - ログディレクトリ作成失敗時にファイルハンドラ作成を安全にスキップし、ストリームのみで継続する回復処理を追加。

### セキュリティ (Security)
- config_setup と設定表示で機密値（トークン・パスワード）をマスクして表示するように実装（.env 生成時の視認性対応）。
- Settings._require による必須環境変数未設定時の明示的な例外。

### 注意事項 / 未実装・TODO
- research.factor_research の一部（calc_momentum の続きなど）がファイル末尾で途中（start_da で中断）になっており、実装が完了していない箇所あり。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）は TODO コメントとして残されている。
- 一部モジュール（ExecutionEngine, SystemMonitor, BrokerClientFactory, OrderManager 等）の実装本体はこの差分に含まれていないため、実動作に関する詳細は当該モジュールの実装に依存。

---

更新やバグフィックスが行われたらこの CHANGELOG に追記してください。