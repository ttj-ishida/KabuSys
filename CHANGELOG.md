# Changelog

すべての変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般:
- 本リポジトリはバージョン管理下での初期リリースとして機能する一連のモジュール（設定、起動スクリプト、ポートフォリオ構築、ユーティリティ、検証ツール等）が含まれます。

## [0.1.0] - 2026-04-23

### Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。バージョンは `__version__ = "0.1.0"`。

- 設定管理
  - 環境変数読み込み・管理モジュール (kabusys.config)
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env のパースロジックはコメント、export プレフィックス、クォート、エスケープに対応。
    - Settings クラスを提供し、アプリ全体で使用する設定をプロパティ経由で取得可能（J-Quants トークン、kabuAPI設定、DBパス、監視設定、システム環境フラグ等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）や KABUSYS_ENV の検証を実装。
    - paper_trading 用のデフォルト SQLite パス（data/paper_trading.db）をサポート。

  - .env 対話式ウィザード（kabusys.config_setup）
    - 初期 .env の作成 / 更新を対話的に支援する CLI。
    - J-Quants、kabuAPI、DBパス、ログレベル、Kill Switch 等の項目を用意。
    - シークレット項目はマスク表示。作成後に .env をファイルへ書き出す機能を実装。

  - 設定検証 CLI（kabusys.validate_config）
    - 起動前に環境変数や config/*.yaml の存在と基本妥当性をチェックするコマンド。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DBパスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 起動スクリプト / 実行系
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番用 sqlite_path を参照する実装（監視用 DB を分離せず本番 DB を使用する方針）。
    - プロセス優先度を最初に "high" に設定。停止フラグ file: data/stop_requested.flag を監視して安全停止。
    - SQLite / DuckDB 接続の初期化とクローズ処理を提供。

  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成（paper_trading 時は MockBrokerClient を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動ロジックを実装。
    - RiskManager のデフォルト構成（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定し、初期 available_cash をブローカーから取得して使用。
    - 停止フラグ data/stop_requested.flag による安全停止と pid ファイル管理（data/execution.pid）をサポート。
    - 実行は別スレッドで行い、定期的に停止フラグを確認して Engine.stop() を呼ぶ。

- モニタリング関連
  - 監視 DB 初期化ユーティリティ import（init_monitoring_db を使用する呼び出し側統合）。

- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - 既存ハンドラをクリアして再設定することで二重設定を防止。
    - ログ出力ディレクトリの解決順: 引数 > LOG_DIR 環境変数 > logs/。
    - ログレベルの解決順: 引数 > LOG_LEVEL 環境変数 > INFO。
    - ファイルハンドラの生成失敗時はコンソール出力のみで継続。

  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供（権限不足時は警告でスキップ）。
    - 権限不足や未サポートの OS に対して安全にフォールバック。

- ポートフォリオ構築（pure functions）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: BUY シグナルをスコア降順（タイブレークで signal_rank）にソートして上位 N を選択。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア正規化による重み計算。全銘柄のスコアが 0 の場合は等配分にフォールバックして警告を出す。

  - セクター制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた資金乗数を返す（未定義値は 1.0 にフォールバックし警告）。

  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき各銘柄の発注株数を計算。
    - risk_based: risk_pct、stop_loss_pct で 1 銘柄あたりの基本株数を算出し、単元（lot_size）で丸める。
    - equal/score: 重みと max_utilization に基づき割当を計算。単元丸め、per-stock 上限（max_position_pct）を適用。
    - aggregate cap: 全銘柄投資合計が available_cash を超える場合はスケーリングし、残余キャッシュで fractional remainder に応じて lot 単位で再配分するロジックを実装。
    - cost_buffer を加味して手数料・スリッページを保守的に見積もる。

- 解析・ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを集計してレポートを作成。
    - 指標: システム稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ、リスク却下数 等。
    - パス/フェイル基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプション: --from, --to（YYYY-MM-DD）, --db（DB パス上書き）。
    - DB が空またはテーブル欠如の場合でも例外を吸収して N/A を表示する耐障害的な集計。

- 研究用モジュール（部分実装）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum、Value、Volatility、Liquidity といった定量ファクター算出方針を実装する設計が含まれる。
    - momentum 計算関数 calc_momentum の実装が開始（prices_daily テーブルを想定、各種 horizon の定義や MA200 乖離などを仕様化）。（ファイル末尾で実装途中の箇所があるため、さらなる実装・テストが必要）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注:
- この CHANGELOG はコードベースの内容から推定して作成しています。実際の設計意図や追加のモジュール（例: ExecutionEngine、SystemMonitor、BrokerClientFactory 等）の内部実装詳細は別ファイルに委ねられており、本 CHANGELOG では外部インタフェースや確認できる振る舞いに基づいて記載しています。
- 今後のリリースでは「Changed / Fixed / Security」セクションも活用していく予定です。