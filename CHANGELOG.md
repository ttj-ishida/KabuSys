# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
リリース日はソースコードの作成時点（本ファイル作成時点）を使用しています。

※本 CHANGELOG はソースコード内容から推測して作成したもので、実際のコミット履歴とは異なる場合があります。

## [0.1.0] - 2026-04-23

初版リリース。KabuSys の基本的な実行／監視基盤、設定管理、ポートフォリオ構築・ポジション算出ロジック、ユーティリティ、及び検証ツールを含みます。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する仕組みを追加。
    - BrokerClient を BrokerClientFactory で生成（環境に応じた実装を選択可能、paper_trading では MockBrokerClient を利用する想定）。
    - ストップフラグ（data/stop_requested.flag）検出時に安全に終了するロジックを実装。
    - 実行中の PID を file（data/execution.pid）に記録するための pid_file パスを利用。
    - プロセス優先度を起動直後に "high" に設定する処理を追加（utils.process_priority を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視データは環境にかかわらず本番 sqlite_path を使用する（監視用 DB 初期化を保証）。
    - 停止フラグ検出、例外発生時のログ出力や安全な DB 切断処理を実装。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml）を実装。
    - .env の簡易パーサを実装（export プレフィックス、クォート文字列、エスケープ、インラインコメント対応）。
    - Settings クラスを追加し、環境変数のラップと型変換、バリデーション（KABUSYS_ENV, LOG_LEVEL 等）を提供。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）をサポート。
    - 各種閾値設定（CPU/MEM/DISK 等）や PID / Kill flag のパスを設定可能に。

  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。
    - 秘密値はマスク表示、選択肢／デフォルトの提示、.env の書き出し機能を提供。
    - 生成時に .env を上書き/新規作成する `_write_env` を実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の存在・基本的妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML が未インストールの場合は YAML 検証をスキップ（警告表示）。
    - `--strict` オプションにより警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio モジュールを追加（ポートフォリオ構築に必要な純関数を提供）。
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の重み計算。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジックを実装（既存保有のセクター暴露に基づき候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金の乗数（bull/neutral/bear）を提供。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）による丸め、1銘柄上限、aggregate cap（available_cash によるスケーリング）、手数料・スリッページのバッファを考慮したスケーリングを備える。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を root ロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、失敗時はコンソール出力のみでフォールバック。
  - utils/process_priority.py
    - プロセス優先度（Windows: priority class, POSIX: nice 値）と CPU affinity 設定関数を追加（psutil 必須）。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出す箇所を run_execution/run_monitoring に追加して、テーブル存在を保証（冪等）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）を集計して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）等を算出し、閾値に基づいて PASS/FAIL を判定。
    - P95 計算、日付フィルタ、各種フォーマット関数を実装。

- 研究用ファクター計算（部分実装）
  - research/factor_research.py を追加（モメンタム、ボラティリティ、バリュー等の計算を行う設計）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針で設計。

### 変更 (Changed)
- 既存ライブラリ設計
  - さまざまなモジュールが「DB 参照なし・純粋関数」設計を採用（ポートフォリオ関連）。ユニットテストしやすい API に。

- 起動時の優先度設定
  - 実行スクリプトで起動直後に set_process_priority("high") を呼び出すよう設定（遅延起動や子スレッド前に優先度を上げるため）。

### 修正 (Fixed)
- 環境変数読み込みの堅牢化
  - .env パーサを強化（export 対応、クォートとエスケープ、インラインコメント処理）し、環境読み込みの誤判定を低減。
- ログ設定の耐障害性
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてコンソール出力のみで継続するよう改善。

### 注意点 / 互換性 (Notes)
- 監視（run_monitoring）は「監視 DB」として Settings.sqlite_path を使用するように実装されています。環境（development / paper_trading / live）にかかわらず同一パスを参照するため、監視データの保存先を変更したい場合は環境変数 SQLITE_PATH を設定してください。
- Execution エンジンは paper_trading モードで専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。paper_trading と本番 DB は分離されます。
- process_priority や CPU affinity の設定は psutil に依存し、権限不足や未対応 OS では警告を出してスキップします。
- config_setup による .env 作成後は validate_config で検証することを推奨します（validate_config は PyYAML の有無に応じて YAML 検証を行います）。
- tools/paper_verification_report のレポートは DB スキーマ（system_status / trade_logs / risk_logs 等）に依存します。スキーマが存在しない場合は該当指標は N/A / 0 になります。

---

今後の予定（例）
- research/factor_research の完全実装と単体テスト追加
- ExecutionEngine / SystemMonitor 周りの統合テスト整備
- 各モジュールのドキュメント化（API ドキュメント、設計ノート）
- config のより細かい型チェックと例外メッセージの改善

（以上）