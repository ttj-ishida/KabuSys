# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/kabusys）から推測して作成しています。実際のコミット履歴ではなく、ソースコードの内容に基づく機能一覧・変更点の要約です。

## [Unreleased]
- なし（初回リリース相当のスナップショットから生成）

## [0.1.0] - 2026-04-23
初回公開（コードベースの機能スナップショット）。

### Added
- コアパッケージ
  - kabusys パッケージを追加。バージョン 0.1.0。
- 設定管理
  - 環境変数／.env を扱う Settings クラスを実装（src/kabusys/config.py）。
  - 自動 .env 読み込み機能（プロジェクトルート検出: .git / pyproject.toml）を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースロジックの強化:
    - export KEY=val 形式対応
    - シングル・ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの取り扱い（適切に無視）
- 環境設定ウィザード
  - 対話式 CLI による .env の初期作成／更新ウィザードを提供（src/kabusys/config_setup.py）。
  - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）をサポート。
- 設定検証ツール
  - 起動前に .env および config/*.yaml の不足や誤りを検出する CLI を実装（src/kabusys/validate_config.py）。
  - --strict オプションで警告もエラー扱いにする機能。
  - PyYAML がない環境でも graceful にスキップする設計。
- 実行／監視ランナー
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離する実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合せて Engine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に記録する仕様）。
    - stop フラグ検出によるループ終了、例外発生時も次ポーリングまで待機して継続する堅牢化。
- ロギング関連
  - 統一的なロギング初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout に出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログをファイルに保存（デフォルト logs/<app_name>.log）。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続するフォールバック処理。
    - 引数/環境変数からログレベル・ログディレクトリを解決。
- プロセス制御ユーティリティ
  - プロセス優先度設定・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 差分を吸収。権限不足や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築モジュール
  - 候補選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を提供。
    - score がすべて 0 の場合は等金額配分へフォールバック。
  - セクター集中とレジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に候補を除外。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を提供。未知の値はフォールバック（1.0）し警告を出力。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式をサポート。
    - 単元株数（lot_size）の丸め、1 銘柄上限・aggregate 上限（利用可能現金）・コストバッファを考慮したスケーリングロジックを実装。
- リサーチ
  - ファクター計算モジュールの骨格（src/kabusys/research/factor_research.py）を追加（Momentum / Value / Volatility / Liquidity の設計方針と定数を含む）。DuckDB を用いた prices_daily/raw_financials 参照を想定。
- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（fill_rate）、送信率、レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を出力。
    - CLI で期間（--from/--to）や DB パス（--db）を指定可能。
    - デフォルト閾値: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
- DuckDB 統合
  - analytics 用の DuckDB パス (DUCKDB_PATH) を Settings で取り扱い、run スクリプトや各コンポーネントで接続を利用。

### Changed
- なし（初期リリースのため、既存機能の変更点は該当しません）

### Fixed
- なし（初期リリースのため、バグ修正履歴は該当しません）

### Security
- .env ファイルを生成する際の注意を README 等で明示する想定（.env を Git にコミットしないことを強調）。
- Secrets（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）は Settings 経由で必須/任意を明示。

### Notes / Migration
- 環境変数の主なキー:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 任意・デフォルトあり: KABUSYS_ENV (development|paper_trading|live)、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABU_API_BASE_URL、LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID
  - 動作制御: KABUSYS_DISABLE_AUTO_ENV_LOAD、KILL_FLAG_CLEAR_ON_START、MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH
- PAPER_TRADING:
  - paper_trading 環境では発注は仮想化（MockBrokerClient を使用）され、SQLite は data/paper_trading.db（デフォルト）に記録されるため本番データと分離されます。
- MONITORING:
  - run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合にデフォルト（60秒）へフォールバックして警告を出します。
  - 監視処理は監視用 DB テーブルの初期化を idempotent に行うため、既存 DB があっても問題なく起動できます。
- ロギング:
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存（30 日保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみとなります。
- プロセス優先度設定:
  - 起動時に set_process_priority("high") を呼び出す箇所があるため、実行環境において権限不足で警告が出る場合があります（動作自体は継続します）。

### Breaking Changes
- なし（初回リリース）

---

この CHANGELOG はソースコードの構造・コメント・実装から推測して作成しています。実際の履歴やリリースノートとして使用する前に、コミットログやリリース管理システムの情報で検証してください。必要であれば、各ファイルの実装行に対応するより細かい項目（例: 関数名・引数の変更、既知の制限・TODO）を追加できます。