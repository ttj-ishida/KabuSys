CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
安定版リリースはセマンティックバージョニングを使用します。

0.1.0 — 2026-04-23
------------------

Added
- 基本アプリケーション構成を実装（初期リリース）。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
- 環境設定管理
  - .env ファイルと環境変数を扱う Settings クラスを実装。
  - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env の堅牢なパーサ実装（export 書式、シングル/ダブルクォート、インラインコメント対応）。
  - 必須環境変数検査ロジック（J-Quants / kabu API など）を提供。
  - 各種設定プロパティ: DB パス、PID/kill フラグ、監視閾値、PAPER_FILL_MODE 等。
  - 環境値検証で無効な値は例外を投げる（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を初期作成・更新可能。
  - 保存前の確認表示とシークレット（マスク）表示に対応。
- 設定検証 CLI
  - `kabusys.validate_config`：.env と config/*.yaml の存在・基礎チェックを行う CLI。
  - --strict オプションで警告を失敗扱いにできる。
  - PyYAML 非インストール時のフォールバック（YAML 検証スキップ）と適切な警告。
- 実行系ランタイム
  - `run_execution.py`：ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化（モック / 実ブローカー切替）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てロジック。
    - デフォルト RiskConfig 値を設定（max_position_pct 等）し、初期 available_cash を broker.get_available_cash() から取得。
    - エンジンはデーモンスレッドで実行し、 stop フラグ検知で安全停止。
    - 起動前に停止フラグを検査して起動を回避する動作。
- 監視系ランタイム
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを一元管理。
    - stop フラグファイル検知でループを終了、例外発生時もロギングして次ポーリングへ。
- ロギング / オペレーションユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし stdout のみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR の利用、既存ハンドラのクリーンアップ対応。
  - `kabusys.utils.process_priority`：
    - psutil を利用したプロセス優先度設定（Windows / POSIX を吸収）。
    - CPU affinity 設定関数（最初の N コアに固定）を提供。権限不足等の例外は警告でスキップ。
    - 起動スクリプトは最初にプロセス優先度を "high" に設定。
- データベース / 分析
  - DuckDB を分析用に統合（duckdb 接続を複数スクリプトで利用）。
  - 監視 DB 初期化（init_monitoring_db を起動時に呼び出し、テーブル存在を保証）。
- ポートフォリオ構築モジュール（純粋関数群）
  - `portfolio.portfolio_builder`:
    - 候補選定 select_candidates（スコア降順・同点タイブレーク）。
    - 重み計算 calc_equal_weights, calc_score_weights（スコア全て 0 のとき等金額にフォールバック）。
  - `portfolio.risk_adjustment`:
    - apply_sector_cap：セクター集中上限チェック（売却予定銘柄を除外するオプション、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）。
  - `portfolio.position_sizing`:
    - calc_position_sizes：allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - 単元株丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリングと残差調整）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もるロジックを提供。
- Paper Trading 検証ツール
  - `tools.paper_verification_report`：
    - Paper Trading 用 SQLite から集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（平均/最大/P95）等を算出してレポート出力。
    - デフォルト DB は data/paper_trading.db、--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で変更可。
    - P95 計算、期間フィルタ（ISO8601 時刻へ変換）対応。
    - 各指標に基づく PASS/FAIL 判定（閾値はソース内定義）。
- Research（着手）
  - research.factor_research モジュールの骨組み（モメンタム等のファクター計算方針、関数 calc_momentum の開始実装）。（未完：ソースの最後で途中）

Changed
- N/A（初期リリースのため既存変更は無し）

Fixed
- N/A（初期リリースのため既存バグ修正履歴は無し）

Security
- 機密情報取り扱いに注意する警告を .env 生成に含める（.env を絶対に Git にコミットしない旨の注意書き）。

Notes / Implementation details
- run_monitoring は監視用 sqlite を環境に関係なく本番パスで使用する仕様（監視データの一元化）。
- run_execution は paper_trading モード時に DB を分離することでテスト/検証用のデータ分離を確保。
- process priority / cpu affinity 等は権限やプラットフォームに依存するため失敗時は警告を出してスキップする安全設計。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合もサービスは stdout ログで継続する設計。

今後の予定（例）
- research.factor_research の完成（ファクター計算 SQL / DuckDB 実装の続き）。
- ExecutionEngine / SystemMonitor のユニットテスト拡充と依存注入でのモック対応強化。
- 銘柄別単元サイズのサポート（stocks マスタから lot_size を取得する拡張）。
- monitor/engine のより詳細なメトリクス収集とアラート化機能の追加。

---
参考: この CHANGELOG はコード内の実装・コメント・docstring から推測して作成しています。実際のリリースノートとして使う場合は、必要に応じて差分や追加の変更点を手動で追記してください。