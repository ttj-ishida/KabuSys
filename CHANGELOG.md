# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。  
安定版リリースはセマンティックバージョニングに従います。

最新: Unreleased
===============

Unreleased
---------

- 現在差分はありません。

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリースを公開。
- 実行スクリプト / デーモン管理
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレーディング用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - 停止制御用フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱いを実装。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番の sqlite_path を参照して監視 DB を初期化・利用。
    - 停止フラグ検出、例外ハンドリング、リソースクローズ処理を備える。
- 設定管理
  - config.py: 環境変数 / .env(.local) の自動読み込み機能を追加（プロジェクトルート検出ロジックを含む）。
    - .env のパースはクォート、バックスラッシュエスケープ、コメント処理に対応。
    - 必須キー取得のユーティリティ、各種設定プロパティ（DB パス、Paper Trading 設定、監視閾値、PID/kill flag パス、ログレベル、環境判定など）を提供。
  - config_setup.py: インタラクティブな .env 作成ウィザードを追加（対話式に初期設定ファイル生成・更新）。
    - シークレット入力のマスク表示、既存 .env の読み込み、保存前の確認、.env 出力テンプレートを提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース検証（PyYAML 未インストール時は警告）などをチェック。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限の適用（既存ポジションのセクターエクスポージャ計算、上限超過セクターの候補除外）
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に基づく投下資金乗数を返す（未知レジームは警告して 1.0 でフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based","equal","score") に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的コスト見積り、残差に基づく追加配分アルゴリズムを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。既存ハンドラの二重設定を防止。
    - LOG_LEVEL / LOG_DIR の解決順、ファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS を吸収し、psutil を用いて優先度設定（high/normal/low）や CPU affinity を設定。権限不足時は警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - DB パスはコマンドライン --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト data/paper_trading.db）。
- リサーチ（未完）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（Momentum、Value、Volatility、Liquidity の仕様と定数を定義）。モメンタム計算関数の枠組みを実装中（ファイル末尾は途中）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし

Notes / 運用メモ
- .env の自動読み込みはデフォルトで有効。テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本リリースでは監視機能は監視 DB（SQLITE_PATH）を参照します。監視・実行プロセスが同一ホストでデータを共有する設計に注意してください（paper_trading モードは発注 DB を分離します）。
- research/factor_research.py は開発中のため、完全なファクター計算は今後のリリースで提供予定です。

--- 

（今後のリリースではバージョンごとに変更点を追加してください）