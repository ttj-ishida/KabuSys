CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しています。主な追加点・仕様は以下の通りです。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する挙動を実装。
    - engine をバックグラウンドスレッドで実行し、data/stop_requested.flag により安全に停止できる仕組みを実装。
    - 起動時の PID ファイル出力や停止フラグ検出ロジックを追加。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視用 DB（SQLite）は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）でループを終了する安全な制御を実装。

- 設定・環境変数周り
  - config.py
    - Settings クラスを導入し、アプリケーション設定（各種 API トークン、DB パス、監視閾値、環境種別など）を環境変数から取得する API を提供。
    - KABUSYS_ENV の値検証、LOG_LEVEL の検証、paper_trading 用の paper_sqlite_path、PAPER_FILL_MODE のバリデーションなどを実装。
    - 自動 .env ロード機能を実装（プロジェクトルートの検出、.env / .env.local の読み込み）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup.py
    - .env の対話式ウィザードを追加（初期作成・更新支援）。必要項目の説明と保存機能を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。.env や config/*.yaml の存在チェック、必須環境変数チェック、本番環境特有のガードなどを実装。--strict オプションで警告を失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / app_name による制御、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定のユーティリティを追加。
    - set_process_priority(level) で "high"/"normal"/"low" を設定、許可されない環境や権限不足時は警告でフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの並べ替え（select_candidates）と重み計算（等金額・スコア加重）を実装。スコアが全て 0 の場合は警告と等重フォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）を実装。既存保有を考慮して特定セクターが上限を超える場合に候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をサポート。未知のレジームはフォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分方式（"risk_based", "equal", "score"）に対応する株数決定ロジックを実装。
    - 単元株（lot_size）の丸め、max_position_pct や max_utilization による個別・総合上限、cost_buffer を考慮した保守的見積り、合計投下資金が available_cash を超えた際のスケーリングおよび残差配分ロジックを実装。

- 分析 / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。期間指定可（--from / --to / --db）。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出し、基準値（稼働率>=99%、成立率>=90% 等）で PASS/FAIL 判定を行う。

- 研究用モジュール（骨組み）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加。モメンタム / Value / Volatility / Liquidity 等の計算仕様がコメントで定義され、calc_momentum 等の関数実装の開始が見られる（未完の部分あり）。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### Changed
- 監視と実行の運用設計
  - 監視（monitoring）は環境に依存せず本番用の sqlite_path を使用する挙動により、運用上の一貫した監視データ収集を行う設計に変更（設計決定として実装）。
  - 実行（execution）は paper_trading 環境時に DB を完全分離するように変更。これによりペーパートレードが本番データに影響を与えないよう設計。

### Fixed
- 環境変数パーサの堅牢化（config.py）
  - .env ファイルのパースで引用符付き値のバックスラッシュエスケープやインラインコメント処理、export プレフィックス対応などを実装し、より多様な .env 記法に対応。

### Notes / Implementation details
- ロギングはデフォルトで stdout を使用するため、cron / systemd 等からの起動時にログの取り扱いが容易になっています。加えてログファイル（日次ローテート）を併用することで運用ログの保存も可能です。
- process_priority の設定は権限や OS に依存するため、失敗した場合は警告を出して処理を継続する保守的な実装です。
- position_sizing のスケールダウンアルゴリズムは lot_size 単位での再配分を試み、残余キャッシュを使って残差を調整する方針になっています。将来的に銘柄ごとの lot_size を扱う拡張が想定されています（TODO コメントあり）。
- research/factor_research.py は計算ロジックの実装が途中で、追加実装・検証が必要です。

---
この CHANGELOG はコードベースから推測して作成しています。実装意図や履歴に不明点がある場合は、各モジュールのドキュメントやコミット履歴を参照してください。