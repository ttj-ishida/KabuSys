# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- セマンティックバージョニングを採用しています（パッケージ版 __version__ は 0.1.0）。
- 日付はリリース日を示します。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎機能を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは専用の Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 起動前に data/stop_requested.flag を検査し、停止フラグがある場合は起動を中止。
    - 実行中は stop flag を監視し検出時に Engine.stop() を呼び出して安全に停止。
    - エンジン用 PID ファイル（data/execution.pid 等）をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 停止制御は data/stop_requested.flag による検出。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する設計。

- 設定管理
  - config.py: 環境変数と .env ファイルの読み込み・ラッパーを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env/.env.local を読み込む（必要に応じて自動ロードを無効化可能：KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントに対応。
    - OS 環境変数を保護するための上書き制御（protected keys）。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、閾値、ログレベル、KABUSYS_ENV 判定用ユーティリティ等）をプロパティとして取得可能。
    - PAPER_FILL_MODE（paper trading の fill モード）や PAPER_TRADING_SQLITE_PATH 等の設定をサポートし、値検証を実施。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 主要な環境変数の入力を対話形式で行い、.env ファイルを生成（既存値の読み込み / シークレットマスク表示 / 保存確認）。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML があればパース検証を実施。
    - 本番（KABUSYS_ENV=live）向けの追加警告（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定等）。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定するユーティリティを追加。
    - ログディレクトリ作成失敗時にはファイルハンドラをスキップしてコンソールのみで継続するフェイルセーフを実装。
    - LOG_LEVEL / LOG_DIR の解決順を明示。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）を追加。権限不足等の例外は警告を出してスキップ。
    - set_cpu_affinity によりプロセスの CPU affinity を固定するユーティリティを追加。

- ポートフォリオ構築（純関数群）
  - kabusys.portfolio 以下を追加:
    - portfolio_builder.py
      - select_candidates: スコア降順（同点時は signal_rank 昇順）で候補抽出。
      - calc_equal_weights / calc_score_weights: 等配分およびスコア重みの重み計算。スコア全てが 0 の場合に等配分へフォールバック（警告）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中を抑えるフィルタ（既存保有のセクター時価を計算し、max_sector_pct を超えているセクターの新規候補を除外）。"unknown" セクターは除外対象外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知値は 1.0 にフォールバックして警告出力。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数算出。lot_size 単位で丸め、max_position_pct、max_utilization、cost_buffer（手数料/スリッページの想定）を考慮した aggregate cap のスケーリングロジックを実装。残差分を基に lot 単位で追加配分するロジックも実装。

- 解析/研究系ツール
  - research/factor_research.py: ファクター計算モジュールの初期実装（Momentum, MA200 dev, ATR, liquidity 等を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（純粋関数）。（注: 実装途中の箇所あり）

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db、--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
    - P95 計算ユーティリティ（_p95）を実装。
    - しきい値はソース内で定義（稼働率 >= 99.0%、fill >= 90%、send >=95%、P95 <= 200ms など）。

### Changed
- ログ出力は標準エラーではなく標準出力（stdout）へ出す方針を採用（cron/task scheduler より使いやすくするため）。
- .env 読み込みの優先順位を明確化（OS 環境 > .env.local > .env）。OS 環境変数は保護（上書き禁止）。

### Fixed
- .env パーサ: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの取り扱いなどに対応し、より頑健にパースするよう改善。
- ログディレクトリ作成やファイルハンドラ作成失敗時に、システムがクラッシュせずコンソール出力にフォールバックするように修正（起動環境が限定的な場合でも可用性を維持）。
- プロセス優先度設定において、OS 毎の定数未定義や権限不足で例外が発生するケースをキャッチして警告を出すように変更。

### Security
- シークレット（J-Quants リフレッシュトークン、kabu API パスワード、LINE トークン等）は .env に平文で保持する想定だが、config_setup のウィザードではシークレット入力をマスク表示して扱いやすさを向上。運用上の注意喚起（.env を Git にコミットしないこと）を明記。

### Notes / Known issues
- research/factor_research.py の一部は実装途中（ファイル末尾付近で切れている）。今後のリリースで完全実装予定。
- ExecutionEngine / SystemMonitor の内部実装（詳細な注文処理や監視ロジック）は別モジュールに分かれており、このリリースでは起動・組み立て周りの統合とユーティリティを中心に提供。
- 一部の機能（PID ファイルやファイル書き込み）に対して権限が必要な場合がある（コンテナ・systemd などの実行環境で注意）。

---

今後の予定:
- factor_research の完成、テストケース追加、Strategy の本体実装、より詳細な監視アラート（LINE 通知等）の統合、安全性向上（テスト用モックの整備）を行う予定です。