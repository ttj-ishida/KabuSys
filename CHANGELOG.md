# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。以下は、現行コードベースから推測して作成した変更履歴です。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [Unreleased]
- ドキュメント・ログ出力文言の調整や軽微なリファクタリング（実装ファイルから推測）。
- テスト・ローカル開発向けの環境可搬性改善（.env パーサの堅牢化や自動ロードの無効化フラグなど）。

---

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - __init__.py にて __version__ を定義。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) のサポート。
    - スレッド駆動でエンジンを実行し、停止フラグ検知で安全停止。
    - RiskManager の初期設定値をコード内で定義（max_position_pct や max_utilization 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用する仕様（監視データは一貫した DB に保存）。
    - 停止フラグ（data/stop_requested.flag）でループ終了。

- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を提供。
    - J-Quants / kabu API 等の必須項目やデフォルト値、説明付きプロンプトを実装。
    - .env の読み書きロジック（既存値の読み取り、シークレット表示マスク、確認プロンプト）。
  - validate_config.py
    - .env と config/*.yaml の設定を起動前に検証する CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML 有無に依存）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- 設定管理
  - config.py
    - 自動 .env ロード機構（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - 詳細な .env パース実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応）。
    - Settings クラスによりアプリケーション設定をカプセル化（DB パス、API トークン、paper_trading 用パス、監視閾値、KABUSYS_ENV 判定など）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を追加。
    - スコアが全て 0 の場合のフォールバックロジック（等金額配分）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（既存保有時価を計算し、上限超過セクターの候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングと未知レジームでのフォールバック）。
  - portfolio/position_sizing.py
    - position size 計算ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ（cost_buffer）を考慮したスケーリングと余剰分配アルゴリズムを実装。
    - 価格欠損時のスキップやログ出力。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を利用した定量ファクター計算モジュールを追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20 等）等の関数を実装（prices_daily テーブル参照、データ不足時は None を返す仕様）。
    - 計算範囲のバッファやウィンドウサイズ等を定数化。

- ユーティリティ
  - utils/process_priority.py
    - Windows/Linux/macOS 間の差分を吸収するプロセス優先度設定ユーティリティを実装。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。権限不足や未実装 API の場合は警告を出してスキップ。
    - 実行スクリプトは起動時にプロセス優先度を "high" に設定するよう利用。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視用テーブルの存在を保証（冪等）。

- 実行・検証補助ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計し PASS/FAIL を判定する。
    - CLI 引数で期間指定（--from, --to）および DB パス指定（--db）が可能。
    - P95 計算、データ欠損時の扱い（N/A）を実装。

Changed
- 主要コンポーネントが DuckDB と SQLite を併用する設計に統一
  - DuckDB は主に価格・ファクター計算・分析用（data/kabusys.duckdb）。
  - SQLite は監視および注文トレース等の簡易永続化に使用。

Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート内エスケープ、行内コメントの取り扱い改善により .env の柔軟な記述をサポート。

Notes / Usage
- 監視ループ:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（正の整数、デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで行える。
- 実行エンジン:
  - paper_trading モードでは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
  - Engine の PID 管理および停止フラグ検知を実装。
- 設定:
  - 自動 .env ロードは通常有効。テスト等で自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
  - 設定検証は python -m kabusys.validate_config、ウィザードは python -m kabusys.config_setup を参照。

Security
- 現時点でセキュリティ関連の変更は明示されていないが、シークレット値はウィザードでマスク表示され、.env は Git にコミットしない旨を注意喚起している。

---

今後の予定（推測）
- 銘柄別 lot_size をマスター化して position_sizing を拡張する（コメントに TODO）。
- 不足価格データ時のフォールバック（前日終値や取得原価）実装。
- YAML ベースの config ファイル検証の強化（PyYAML 依存を明確化）や、監視アラート（LINE 通知）の統合強化。