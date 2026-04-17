# CHANGELOG

すべての注目できる変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース — 基本機能の実装を含む安定した初期版。

### 追加 (Added)
- パッケージ基礎
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージエクスポート: data, strategy, execution, monitoring モジュール群を公開。

- 設定周り
  - Settings クラスを実装し、環境変数経由で各種設定（J-Quants / kabu API / DB パス / 監視設定 等）を取得可能に。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env 読み込み/パースの堅牢化（export プレフィックス、クォート・エスケープ、インラインコメントの処理対応）。
  - 環境設定ウィザード CLI（kabusys.config_setup）を実装し、対話式で .env を生成・更新可能に。
  - 設定検証 CLI（kabusys.validate_config）を実装。必須環境変数チェック、パス/ファイル存在チェック、YAML のパース確認、--strict モードをサポート。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用して paper_trading 用 DB（data/paper_trading.db）と分離して実行。
    - ExecutionEngine の起動、依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる実装。
    - 停止フラグ（data/stop_requested.flag）検出時の安全な停止処理を実装。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する仕様。
    - stop flag によるループ終了、例外発生時のログと継続性を考慮。

- データベース / 分析
  - DuckDB および SQLite 接続を扱う流れを各スクリプトに組み込み。
  - 監視用 DB 初期化（init_monitoring_db）を起動時に呼び出し、テーブル存在を保証（冪等）。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 銘柄選定: select_candidates（スコア降順、signal_rank によるタイブレーク）を実装。
  - 重み計算: calc_equal_weights（等金額配分）、calc_score_weights（スコア加重、全スコアが 0 の場合は等配分にフォールバック）を実装。
  - セクター集中制限: apply_sector_cap（既存保有と当日売却予定を考慮したセクター上限チェック）を実装。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear に応じた乗数）を実装。
  - ポジションサイズ計算: calc_position_sizes を実装（allocation_method: risk_based / equal / score、lot サイズ丸め、aggregate cap スケーリング、cost_buffer 対応）。

- ユーティリティ
  - process_priority と CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する API を提供。
    - 権限不足や未対応プラットフォームでは警告を出し安全にスキップ。

- 研究モジュール
  - ファクター計算（kabusys.research.factor_research）を実装。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR、avg turnover、volume ratio）等を DuckDB 上の prices_daily テーブルから計算する関数群を追加。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL を判定。
    - 日付範囲指定および DB パス指定オプションをサポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- .env パースにおけるクォート・エスケープやインラインコメントの解釈を改善し、意図しない切り取りや不正な値設定を防止。
- 環境変数の自動ロード時に OS 側の既存環境変数を保護する仕組み（protected set）を導入。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注意:
- 本 CHANGELOG はソースコードの機能実装から推測して作成しています。実際のコミット履歴やチケット管理とは差異がある場合があります。