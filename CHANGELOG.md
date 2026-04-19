# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

- リリース日付はコミット時点のコード内容から推定しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-19
初期リリース。KabuSys のコアユーティリティ・実行/監視エントリポイント・ポートフォリオ構築ロジック・設定ツール・レポート/リサーチ補助等を実装しました。

### 追加 (Added)
- 実行／監視プロセス起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV によって paper_trading モード時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを行い、別スレッドでエンジンを実行する。停止は data/stop_requested.flag により制御。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor ポーリングループ用スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず（paper/live/dev）本番 sqlite_path を利用して監視 DB を初期化・使用する。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理・自動読み込み
  - config.py
    - Settings クラスを追加し、環境変数経由の設定を統一的に取得。
    - .env/.env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種設定プロパティ（J-Quants、kabu API、LINE、DUCKDB/SQLite パス、ペーパートレード関連、監視しきい値、環境/ログレベル判定等）を実装。入力値検証（有効値チェック、必須チェック）を含む。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - is_live / is_paper / is_dev ヘルパー。
  - config_setup.py
    - 対話式 .env 作成ウィザードを実装。既存 .env 読み込み・シークレットマスク表示・選択肢・デフォルト提示をサポート。
    - 最終確認後に .env を書き出す。

- 設定検証 CLI
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在確認と（PyYAML 有効時の）パース検証を実装。
    - KABUSYS_ENV=live の場合に追加のガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。
    - --strict モードで警告を失敗扱い（exit(1)）にできる。

- ポートフォリオ構築ユーティリティ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークにより上位 N を選択。
    - calc_equal_weights: 等分配重。
    - calc_score_weights: スコア比例配分（スコア合計が 0 の場合は等分配にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中リスク制限。既存ポジションを基にセクターごとのエクスポージャーを計算し、上限超過セクターの候補銘柄を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知の値は 1.0 でフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じて発注株数を算出（"risk_based", "equal", "score" をサポート）。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的コスト見積り、スケールダウン後の端数配分ロジック等を実装。
    - 価格欠損時のスキップ・ログ出力を考慮。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を提供。root ロガーを初期化し、StreamHandler（stdout）＋TimedRotatingFileHandler（日次、30日保持）を設定。既存ハンドラは一度クリアしてから再設定する。
    - LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を用いる（stderr ではない：cron 等の出力リダイレクトを想定）。
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows と POSIX を抽象化）。
    - psutil を使って優先度 / nice 値を設定。アクセス拒否や未対応プラットフォームの場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン可能（未指定時は何もしない）。不正値エラーチェックあり。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または --db 指定）から集計して検証レポートを標準出力に生成する CLI。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、リスク却下数、API レイテンシ（avg/max/P95）などを集約。
    - P95 計算実装、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - DB テーブルが存在しない場合に個別に例外を捕捉してデフォルト値でレポートを生成。

- リサーチ支援モジュール（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受け取り prices_daily / raw_financials を基に Momentum/Value/Volatility/Liquidity 系ファクターを計算する設計を導入。
    - 各種定数（期間等）と calc_momentum の骨組みを実装（ファイル末尾にて未完の実装の痕跡あり）。DuckDB を用いた計算フローを想定。
    - 現状一部関数は未完（後続実装が必要）。

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 実装上の留意点（ドキュメント的メモ）
- 環境変数自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後や特殊配置では自動ロードがスキップされる場合があります。
- run_monitoring は監視 DB を環境にかかわらず sqlite_path（本番 DB）へ接続します。ペーパートレードの監視を分離したい場合は設定やコードの変更が必要です。
- process_priority や CPU affinity の設定は OS 権限に依存し、失敗時は警告によりフォールバックします。
- portfolio 関連関数は純粋関数設計で副作用を持ちませんが、価格データの欠損時は期待通りの配分にならない可能性があります（ログに注記あり）。将来的には価格フォールバックの実装を検討してください。
- research/factor_research.py は骨格が実装されていますが未完の箇所があり、リリース後の追加実装が必要です。

### セキュリティ (Security)
- （このリリースではセキュリティ修正は含まれていません）

---

（以降のリリースでは本ファイルを更新してください。）