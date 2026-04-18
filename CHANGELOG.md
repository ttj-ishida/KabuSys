# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  

注: 本履歴はソースコードの内容から推測して作成しています。実際のリリースノートはプロジェクト運用に合わせて適宜調整してください。

## [Unreleased]

- 特になし（初回公開相当のリリースノートを下の 0.1.0 にまとめています）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基幹機能群を実装。

### Added
- 起動スクリプト / ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite を使用して本番 DB と完全分離。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine をスレッドで起動。停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化、停止フラグ検出、例外安全なループを実装。Monitoring は環境にかかわらず本番 sqlite_path を使用。

- 設定管理
  - config.py: Settings クラスを実装。環境変数をプロパティで安全に取得。.env/.env.local の自動ロード（優先順位: OS 環境 > .env.local > .env）を実装し、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。.env パースは引用符対応・export 形式対応・インラインコメント処理など堅牢化。PAPER_FILL_MODE 等の妥当性チェック、各種パスや閾値（CPU/MEM/DISK）をプロパティで提供。
  - config_setup.py: 対話式ウィザードで .env を生成/更新するツールを実装。シークレット値はマスク表示し、保存前に確認を行う。デフォルト値・選択肢・説明を備えた項目定義を含む。

- 設定検証ツール
  - validate_config.py: 起動前チェック用 CLI を実装。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml ファイルの存在チェック（PyYAML がない場合はスキップ）。KABUSYS_ENV=live の場合の追加ガードや --strict オプション（警告を FAIL 扱い）を提供。

- ポートフォリオ構築・サイズ決定
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順・タイブレークロジックで並べ替え上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバックして警告。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャが上限を超える場合に候補を除外（"unknown" セクターは除外しない設計）。
    - calc_regime_multiplier: マーケットレジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームはフォールバックして警告。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。lot_size（単元株）で丸め、1 銘柄上限・aggregate cap（available_cash）によるスケールダウン、コストバッファの考慮、余剰キャッシュ配分ロジックなどを備える。価格欠損時のスキップやログ出力も実装。

- ロギング・プロセスユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを実装。ログレベル・ログディレクトリ解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみにフォールバック。
  - utils.process_priority:
    - set_process_priority / set_cpu_affinity を実装。psutil を用いて Windows / POSIX の差分を吸収し、権限不足や未対応環境では警告してスキップするよう安全策を導入。

- ツール
  - tools.paper_verification_report.py:
    - Paper Trading 向けの検証レポート生成スクリプトを実装。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値（稼働率 >= 99%、成立率 >= 90% など）に基づいて PASS/FAIL を判定。日付フィルタ、DB パス指定、P95 計算の実装を含む。

- リサーチ（部分実装）
  - research.factor_research.py:
    - モメンタム等のファクター計算モジュールの骨子を実装（Momentum: 1M/3M/6M、MA200 乖離など）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。いくつかの定数と関数枠組みを実装済み（ファイル末端は途中までの実装）。

### Changed
- なし（初回リリース）

### Fixed
- .env 自動ロード時に OS 環境変数を上書きしないよう protected set を導入（既存 OS 環境を保護）。
- monitoring / execution の DB 初期化は冪等（init_monitoring_db）として監視テーブルの存在を保証。

### Security
- config_setup にて生成された .env ファイルを絶対に Git にコミットしない旨を明記（README 相当の注意書きを .env 出力ヘッダに記載）。

---

注記:
- 多くの機能は環境変数で挙動を制御します（例: KABUSYS_ENV, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL 等）。運用前に `python -m kabusys.validate_config` で検証することを推奨します。
- ファイルの一部（research.factor_research.py 等）は採用方針や将来的な拡張に備えて部分的に実装されています。実運用前に追加テストと検証が必要です。