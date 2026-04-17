# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般
- 初版リリース。パッケージバージョン: 0.1.0
- リリース日: 2026-04-17

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ骨格
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境・設定管理
  - Settings クラス（src/kabusys/config.py）
    - .env 自動読み込み（プロジェクトルートの .env / .env.local を優先順で読み込む。OS 環境変数は保護され上書きされない）。
    - 各種環境変数の取得ラッパー（J-Quants, kabuステーション, DB パス, Paper Trading 設定、監視閾値等）。
    - env 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション）。
  - .env ファイルパーサ（src/kabusys/config.py）
    - export KEY=val 形式とクォート（シングル/ダブル）、バックスラッシュエスケープ、行内コメント処理に対応。
- 環境設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式で .env を新規作成 / 更新するウィザード。
  - 入力補助（デフォルト値、選択肢、シークレットマスク、キャンセル処理）。
  - .env の既存値読み込み / 保存ロジックを提供。
- 設定検証 CLI（src/kabusys/validate_config.py）
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリチェック、config/*.yaml の存在チェック＆ YAML パース（PyYAML がある場合）。
  - KABUSYS_ENV=live 時の追加ガード（LINE 設定の確認、KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict オプションで警告を失敗扱いにできる。
- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine の起動フローを提供。
  - 環境に応じた DB 接続分離: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（default: data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動、別スレッドでの実行制御、停止フラグ監視（data/stop_requested.flag）。
  - PID ファイル管理（data/execution.pid）。
- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番 sqlite_path を使用（監視 DB は本番 DB を指す設定）。
  - 起動時にプロセス優先度を "high" に設定。
  - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
  - CPU affinity を最初の N コアに固定するユーティリティ。
  - 権限不足や未対応 OS では警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio_builder.py
    - select_candidates: スコア降順で候補選定。タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等配分、スコア加重配分（全スコアが 0 の場合は等配分へフォールバック & WARNING）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）。既存ポジションや売却予定銘柄を考慮したフィルタリング。
    - calc_regime_multiplier: 市場レジームに応じたレバレッジ乗数（bull/neutral/bear）。未知レジームは警告後 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数計算、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り。
    - aggregate スケーリング時の端数処理ロジック（残差に基づく追加配分）を実装。
- リサーチ（ファクター計算, DuckDB ベース）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算するためのクエリ設計（DuckDB）。
    - DuckDB 接続を想定（prices_daily, raw_financials テーブル参照）。営業日ベースのウィンドウ設計。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等の検証レポートを生成。
    - P95 計算、閾値による PASS/FAIL 判定（デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - コマンドライン引数で日付範囲と DB パスを指定可能。
- 監視 DB 初期化フック（init_monitoring_db が監視関連開始前に呼ばれる）
  - run_monitoring.py / run_execution.py で監視テーブルの冪等な初期化を保証。

### Changed
- なし（初版のため過去からの変更なし）

### Fixed
- .env パースの堅牢化
  - クォートやバックスラッシュエスケープ、行内コメント取り扱いの改善により .env の多様な記述に耐性を追加。
- run_monitoring の MONITOR_POLL_INTERVAL 解析
  - 非正の値や整数以外の値を与えた場合に警告を出しデフォルト 60 秒へフォールバックするように変更（ValueError 回避）。

### Security
- 重要な秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings.require 経由で必須化し、未設定時に起動前に検出するように設計。config_setup はシークレットをマスクして表示。

### Notes / Migration
- 環境変数自動読み込み
  - デフォルトではプロジェクトルートの .env / .env.local を自動で読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OS 環境変数は上書きされないよう保護されています（.env.local の override は OS で未設定のキーにのみ適用）。
- Paper Trading と Live の DB 分離
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番の monitoring.db は使用しません。運用時は環境を正しく設定してください。
- 起動スクリプト
  - 監視: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を調整可能（デフォルト 60）。
  - 実行エンジン: python -m kabusys.run_execution
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行う。
- CLI
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### Known limitations / TODO
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄毎の lot_map へ拡張予定）。
- apply_sector_cap の価格欠損時の挙動（price が 0.0 の場合にエクスポージャーが過少評価される可能性）について注記と TODO を残している。
- research/factor_research の一部クエリは大量データでの最適化やNULL取り扱いの検討余地あり。

---

「Keep a Changelog」形式に準拠して変更点を記載しました。追加してほしい詳細（たとえば各モジュールの公開 API サンプルや実行例、具体的な設定テンプレートなど）があれば教えてください。