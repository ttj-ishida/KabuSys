# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

- 変更履歴は主にソースコードから推測して記載しています。実際のコミット単位の履歴ではありません。

## [Unreleased]

- ドキュメント化・テストケース追加など運用上の細かな改善予定。
- factor_research モジュールの残り実装（モメンタム計算の続きなど）を完了予定。
- 監視・実行のより詳細なメトリクス収集やアラート強化を検討中。

---

## [0.1.0] - 2026-04-19

Added
- 基本アプリケーション構成を追加
  - パッケージ初期バージョン (src/kabusys/__init__.py: __version__ = "0.1.0") を導入。
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の DB を使用し MockBroker を利用する分離をサポート。停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 環境設定管理を追加
  - config.py: .env 自動読み込み機能（プロジェクトルート検出ロジック付き）、環境変数パーサ、Settings クラスを実装。環境 (KABUSYS_ENV)、各種パス、しきい値や Paper Trading の挙動 (PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH) 等の取得・検証を提供。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加（secret マスク、デフォルト・選択肢対応、保存機能）。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数確認、KABUSYS_ENV/LOG_LEVEL 検査、DB パスや config/*.yaml の存在チェック、live 環境向けの追加ガードなどを実装。--strict オプションで警告を失敗扱いに可能。
- 監視・検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定（PASS/FAIL）して出力。日付フィルタ・DB パスオーバーライド対応。
- ポートフォリオ構築ライブラリを追加
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分・スコア重み (calc_equal_weights, calc_score_weights) を実装。スコア全てが 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap と市場レジームに応じた投資倍率 calc_regime_multiplier を実装。未知レジーム時はフォールバック挙動を提供。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method="risk_based"/"equal"/"score" をサポート、単元株(lot_size)丸め、per-stock 上限・aggregate cap スケーリング、cost_buffer を使った保守的見積り等を含む。
  - portfolio/__init__.py: 上記関数群の公開 API を定義。
- 実行関連コンポーネントでの設定例を追加
  - run_execution から組み立てるコンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を利用する構成で起動可能に（RiskManager にデフォルト設定を渡す実装あり。初期ポートフォリオ値は broker.get_available_cash() から取得）。
- ロギング・プロセス管理ユーティリティを追加
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリアなどを実装。ファイル出力ができない場合はコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（Windows の優先度クラス / POSIX の nice 値）や CPU affinity の設定ユーティリティを追加。対応 OS を抽象化し、権限不足などは警告でスキップ。
- 監視 DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を run_execution/run_monitoring 起動時に呼び出して監視テーブルの存在を保証（冪等）。
- DB アクセス
  - duckdb および sqlite3 を利用する設計を導入（DuckDB は分析・リサーチ、SQLite は監視・発注ログ等）。
- 研究モジュール（部分実装）
  - research/factor_research.py を追加。モメンタム・移動平均乖離・ATR 等ファクターの計算方針と定数を定義し、calc_momentum の骨組みを開始（ファイル末尾で実装が途中の状態）。

Changed
- N/A（初版のため既存からの変更なし）

Fixed
- N/A（初版のためバグ修正履歴なし）

Security
- 環境変数の取り扱いについて .env は絶対に Git にコミットしない旨をドキュメントに明示（config_setup の出力コメント）。

Notes / 実装上の重要ポイント
- .env の自動ロードはデフォルトで有効。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない読み込みが行われる。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- .env パーサは export KEY=val、クォート値（シングル・ダブル）およびインラインエスケープやコメント処理に対応。
- PAPER_TRADING は本番 DB と分離（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。Paper Trading の fill モードは PAPER_FILL_MODE で制御され、有効値を検証して不正値はエラー。
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。0 以下の値はデフォルトにフォールバックしてログ警告を出す実装。
- process priority 設定とログ設定は起動スクリプト群の最初で実行して安定した動作を目指す。
- position_sizing の aggregate cap スケーリングは lot_size 単位で丸め、余剰資金により大きい残差から追加割当てするアルゴリズムを採用（再現性のため tie-breaker に code を利用）。

Acknowledgements
- 初版は運用を想定した実用的な CLI、監視・実行フロー、ポートフォリオ構築ロジックを含みます。今後はテスト、ドキュメント、factor_research 等の完成度向上を予定しています。