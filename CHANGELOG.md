# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-21

初回リリース。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージ名: KabuSys、バージョン __version__ = 0.1.0 を追加。

- 実行スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用（デフォルト: data/paper_trading.db）。
    - ブローカークライアント生成を BrokerClientFactory に委譲。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を構築。
    - エンジンは別スレッドで run_session を実行。data/execution.pid を PID ファイルとして使用。
    - 停止はプロジェクトルート/data/stop_requested.flag によって制御。

  - run_monitoring.py
    - SystemMonitor を定期実行するポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - モニタリングは環境に関わらず本番用 sqlite_path（data/monitoring.db など）を使用。
    - 停止はプロジェクトルート/data/stop_requested.flag によって制御。

- 設定・環境変数管理
  - config.py
    - 環境変数を読み込み・ラップする Settings クラスを追加。
    - .env の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / PID/kill flag /閾値等）。
    - PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH のサポート。
    - KABUSYS_ENV（development / paper_trading / live）・LOG_LEVEL の検証。

  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。複数の設定項目をプロンプトで入力して .env を生成。
    - シークレット入力のマスクや既存 .env の読み込み、保存前の確認などを実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML が存在する場合）等を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name を利用した設定と既存ハンドラのクリア処理を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - psutil ベースで Nice 値/優先度クラスを設定。エラー時は警告でスキップ。

- ポートフォリオ構築・ポジション計算（純粋関数ライブラリ）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を追加。
  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes を追加。risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケールダウン、cost_buffer を考慮。

- 監視・ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計（稼働率、注文成功率、送信率、レイテンシ等）を集計しレポート出力する CLI を追加。
    - P95 計算、期間フィルタ、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定を実装。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB の prices_daily/raw_financials を用いたファクター計算（Momentum / Value / Volatility / Liquidity）用モジュールを追加。calc_momentum 等の関数実装を開始（設計方針、定数、説明を含む）。

- パッケージ初期化
  - __init__.py に __version__ と主要サブパッケージの __all__ を追加。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

### 実装上の注意・運用メモ
- run_monitoring はモニタリング用 DB（Settings.sqlite_path）を環境に関わらず使用する設計。monitoring データは本番 DB として扱う想定。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全に分離する設計。
- process priority / cpu affinity は権限に依存するため失敗時は警告でスキップ。
- .env の自動読み込みはプロジェクトルートが自動検出できる場合のみ実行され、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- ログ出力はデフォルトで logs/<app_name>.log に日次ローテーションで保存。ログディレクトリ作成失敗時はコンソール出力のみで継続。
- PAPER_FILL_MODE の許容値は "instant" / "partial" / "never" / "reject"。不正値は例外となる。
- PID / stop / kill フラグはファイルベースで制御（data/*.pid, data/stop_requested.flag, data/kill.flag）。

今後の予定（例）
- research モジュールのファクター計算関数の完全実装とユニットテスト追加。
- ExecutionEngine / RiskManager 等の詳細実装（現在は呼び出し側の組み立てを確認済み）。
- テスト・CI、ドキュメント（API・運用手順）の整備。

--- 

注: この CHANGELOG は現行コードベースの実装内容から推測して作成しています。細部の動作や将来的な変更により内容が差分する可能性があります。