# Changelog

すべての変更は Keep a Changelog の形式に従います。  
タグ付けと日付はコード内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース（コードベースの主要機能を実装）。

### Added
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数（.env）から設定を読み込み、各種プロパティ（DBパス、APIトークン、環境種別、ログレベルなど）を提供。
    - 自動 `.env` ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードの無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パースの強化（export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理など）。
    - Paper Trading 用 DB パス、PAPER_FILL_MODE の検証ロジック、各種監視閾値プロパティを提供。

- 環境セットアップ / 検証 CLI
  - 対話式ウィザード `config_setup` を実装（src/kabusys/config_setup.py）。
    - .env の作成・更新を支援。機密値はマスク表示。保存前の確認プロンプトあり。
    - デフォルト値や選択肢、説明文を含む項目定義を実装。
  - 設定検証ツール `validate_config` を実装（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML があれば検証）をチェック。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行 / 監視用スクリプト
  - ExecutionEngine 起動スクリプト `run_execution` を追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper DB（`PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。スレッドで実行し停止監視ループを持つ。
    - RiskManager のデフォルト構成値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。初期ポートフォリオ値に broker.get_available_cash() を使用。

  - SystemMonitor 起動スクリプト `run_monitoring` を追加（src/kabusys/run_monitoring.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用ポーリングループを実行。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、1秒未満や不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用（監視テーブルの初期化を保証する init_monitoring_db 呼び出しあり）。
    - 停止フラグ（data/stop_requested.flag）検知で優雅に終了。

- 監視関連ユーティリティ
  - init_monitoring_db（監視テーブルの初期化呼び出し）を各起動処理で利用（monitoring 側の初期化を冪等に保証）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - SQLite（paper_trading.db）から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを算出。
    - CLI 引数で期間（--from / --to）と DB パス（--db）を指定可能。
    - 判定閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms 等）に基づく PASS/FAIL を出力。

- ポートフォリオ構築関連（純粋関数群）
  - select_candidates、calc_equal_weights、calc_score_weights を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順ソート、等金額配分、スコアに基づく重み正規化（全スコアが0の場合は等配分にフォールバック）。
  - セクター集中制限とレジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有に基づくセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する投下資金乗数を提供（未知レジームは警告して 1.0 でフォールバック）。
  - 株数決定ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた株数算出 ("risk_based" / "equal" / "score")。
    - lot_size（単元株）丸め、1銘柄上限（max_position_pct）、全体投下上限（max_utilization）、cost_buffer を考慮した集約スケールダウンロジックを実装。
    - 利用可能現金を超えた場合のスケールダウンと残差処理（lot 単位での繰り上げ配分）の実装。

- 研究用ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う設計。
    - DuckDB 接続を受け取り SQL による処理を行う（外部 API にはアクセスしない）。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - psutil の機能差や権限不足に対して警告を出して安全にフォールバック。

- パッケージ構成
  - portfolio パッケージの __init__ を用意して主要関数をエクスポート。
  - tools パッケージと __init__ を追加。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- .env ファイルに関する注意喚起を config_setup のヘッダやコメントに追加（.env を Git にコミットしない旨）。

### Notes / Implementation details（重要な挙動）
- .env の自動ロード順は OS 環境変数 > .env.local > .env。OS 環境変数は上書きされない保護機構を持つ。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でループ間隔を変更可能。1秒未満や不正値はデフォルト 60 秒にフォールバックする実装。
- run_execution は paper_trading モード時に本番とデータを分離する設計（paper_trading 用 DB を使用）。
- position_sizing のスケーリングロジックは lot_size 単位で切り捨て→残余キャッシュで残差の大きい銘柄順に lot 単位を追加配分するため再現性を確保。
- factor_research の関数は DuckDB の prices_daily テーブルに依存。データ不足時は None を返すなど安全に動作するよう設計されている。

---

今後のリリース案（候補）
- ExecutionEngine / Broker 実装の詳細（実注文フロー、MockBroker の実装、テストカバレッジなど）の追加。
- monitor / execution のサービス化（systemd 単位ファイル等）やログ設定の環境変数反映。
- portfolio モジュールの単体テスト追加、stocks マスタに基づく銘柄別 lot_size サポート。
- factor_research による追加ファクター、Zスコア正規化連携、DuckDB クエリ最適化。

（以上）