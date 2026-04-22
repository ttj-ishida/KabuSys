# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
本ファイルはコードベースの内容から推測して作成したリリースノートです。

なお、コード内の __version__ は 0.1.0 のため、最初の公開バージョンを [0.1.0] としてまとめています。

## [Unreleased]
- 開発中の機能やドキュメント未完了部分を継続して実装予定。
- 既知の未実装／要改善点は「Known issues」にまとめています。

## [0.1.0] - 2026-04-22
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- 起動スクリプト／デーモン機能
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV に応じてペーパートレード用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor をポーリングで動かす起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は本番 sqlite_path を利用。

- 設定管理とセットアップ
  - config.py: 環境変数読み込みと Settings クラスを実装。プロジェクトルート自動検出（.git または pyproject.toml を基準）や .env / .env.local の読み込みロジックを提供。PAPER_FILL_MODE、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV 等のプロパティを定義。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。よく使われる環境変数の説明・デフォルトを提示。
  - validate_config.py: 起動前に .env および config/*.yaml の検証を行う CLI を追加。必須環境変数チェック、パス存在チェック、YAML のパース検証（PyYAML があれば）や本番向けガードチェックを実装。--strict オプション対応。

- 実行系コンポーネント（骨格）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager などの実行関連コンポーネントを統合する起動フローを実装（run_execution が組み立てを実施）。RiskConfig のデフォルト値（max_position_pct 等）や ExecutionEngine のセッション管理、Reconciler/RiskManager の接続が行われる設計を導入。

- 監視（Monitoring）
  - monitoring_db 初期化の呼び出しと SystemMonitor の一回実行チェックループ実装。監視ループは停止フラグの検知・例外の捕捉・ログ出力により安全に回るよう設計。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をセットアップ。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux（および一部 POSIX）を透過してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity を固定する set_cpu_affinity も提供。psutil を利用し、権限不足等は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。レジーム別（bull/neutral/bear）の投下資金倍率を提供。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。risk_based / equal / score 配分に対応し、単元株（lot_size）丸め、1銘柄上限、全体キャップ（aggregate cap）に応じたスケールダウンと残差配分ロジックを提供。cost_buffer により保守的なコスト見積りを反映。

- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力するスクリプトを追加。閾値（uptime 99%、fill rate 90% 等）に基づく PASS/FAIL 判定を実装。日付フィルタ（--from / --to）および --db オプションをサポート。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity といったファクター計算を行うモジュールの枠組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。パラメータ（窓長等）と P95 等のヘルパー実装がある（ただし一部未完）。

- パッケージメタデータ
  - __init__.py にて パッケージ名とバージョン（0.1.0）を定義。

### Changed
- （初回リリースのため変更履歴は該当なし）

### Fixed
- （初回リリースのため修正項目は該当なし）

### Documentation
- 各モジュールに docstring を付与し、使い方や設計上の注意点（例: .env を絶対に Git 管理しない旨、Paper Trading の DB 分離など）を記載。
- config_setup と validate_config に CLI の利用方法と出力メッセージを用意。

### Security
- .env の対話式ウィザードでシークレット入力をマスク表示（保存前に確認）。.env は Git にコミットしないよう出力ヘッダで明示。

## Known issues / Notes
- research/factor_research.py はファクター計算の骨格があるものの、ファイル末尾で実装が途中で終わっている（ソース末尾に中途半端なトークンが存在）。追加実装が必要。
- portfolio/position_sizing.py の price フォールバック処理（price が 0.0 の場合の扱い）や、stocks マスタからの個別 lot_size 取り込みは TODO コメントとして残している。実運用時は価格欠損対策を検討する必要あり。
- process_priority.set_cpu_affinity はプラットフォームや権限に依存するため、権限不足時は警告でスキップされる。運用環境での挙動確認を推奨。
- logging_setup はログディレクトリ作成に失敗した場合ファイルログを無効化しコンソール出力のみとなるため、ログ永続化が必要な環境では権限・パス設定を確認すること。
- Paper Trading と Live の DB を分離しているが、設定ミスにより本番 DB に接続されないよう .env や KABUSYS_ENV の設定を validate_config で事前に検証することを推奨。

---

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリース日や変更点はリポジトリ運用者の記録に準じて更新してください。