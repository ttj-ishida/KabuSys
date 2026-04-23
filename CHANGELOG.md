CHANGELOG
=========

すべての変更は Keep a Changelog の方針に準拠して記載しています。
タグ付けは semantic versioning に従います。

[Unreleased]
------------

- ドキュメント/改善予定
  - research/factor_research.py のモメンタム計算部分は実装途中（ファイル末尾で切れているため、計算ロジックの完成とテストを予定）。
  - いくつかの TODO コメント（価格フォールバック、銘柄ごとの lot_size 管理等）が残っているため、それらの改良を予定。

0.1.0 - 2026-04-23
------------------

Added
- 基本アプリケーション構成を追加（初期リリース）。
  - パッケージ metadata: kabusys.__version__ = "0.1.0"。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、高可用性の停止フラグ連携、別スレッドでエンジン実行、paper_trading 環境での専用 SQLite（data/paper_trading.db）使用に対応。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグ検知で安全に終了。
- 設定関連
  - config.py: Settings クラスを実装。環境変数の読み出し・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。DUCKDB/SQLite パス、PID/kill フラグパス等をプロパティで取得可能。
  - 自動 .env ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。優先順位は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサーの強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
- 環境セットアップ / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。シークレット項目はマスク表示、確認後にファイル書き込み。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パースチェック（PyYAML が無ければスキップ）や本番環境向けのガード警告を実行。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL による上書き対応。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows と POSIX (Linux/Mac/FreeBSD) の差異を吸収し、権限不足や未対応 OS を安全に扱う。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア重み配分（スコア合計が 0 の場合はフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap と市場レジームに基づく calc_regime_multiplier を実装（regime ごとの乗数: bull=1.0, neutral=0.7, bear=0.3、未定義は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py: 発注株数計算を実装。risk_based / equal / score の配分方式をサポート、単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を使った保守的見積り、スケーリングと端数配分のロジックを含む。
  - portfolio/__init__.py で主要関数を公開。
- 実行・監視データベース関連
  - 各起動スクリプトで SQLite 接続と監視テーブル初期化（init_monitoring_db）を行う。monitoring は環境にかかわらず本番 sqlite_path を使用（設計上の意図）。
  - DuckDB を分析用途に接続（duckdb_path）。
- 実行系の主要コンポーネント（参照実装）
  - run_execution.py で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てる流れを実装（RiskManager のデフォルト構成値を含む）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。P95 計算、期間フィルタ、DB パス解決（引数 / 環境変数 / デフォルト）に対応。
- research
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 経由で prices_daily / raw_financials を参照する設計。
- パッケージ構成
  - kabusys/tools, kabusys/portfolio, kabusys/utils, kabusys/research などのモジュールを追加。

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Removed
- (初回リリースのため該当なし)

Security
- (なし)

Notes / Implementation details
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）により外部から安全に終了できる設計。
- run_execution は KABUSYS_ENV=paper_trading の場合、ブローカークライアントを切り替え paper_trading 用 DB に記録することを想定（BrokerClientFactory により実装される）。
- logging_setup は標準出力を stdout に統一しており、cron 等でのログリダイレクト運用を考慮。
- .env パーサーはシンプルな実装ながらエスケープやクォートを考慮しており、実運用での柔軟性を高めている。
- position_sizing の aggregate cap スケーリングと端数配分は、コスト見積り（cost_buffer）を加味して保守的に割り当てるロジックを採用。

今後の改善案（予定）
- research/factor_research の完全実装とユニットテスト追加。
- 銘柄ごとの単元株数管理（stocks マスタへの lot_size の導入）と position_sizing の対応。
- price フォールバック（前日終値や取得原価）による exposure 計算の精度向上。
- config/*.yaml の詳細スキーマ検証と生成スクリプトの充実。
- 実行/監視系の統合テストと CI ワークフローの整備。

-- End of CHANGELOG --