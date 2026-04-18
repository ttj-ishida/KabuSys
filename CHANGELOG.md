CHANGELOG
=========
すべての notable な変更をここに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

Unreleased
----------
- ドキュメント/リファクタ: 内部 API の整理とモジュール分割を行いました（ポートフォリオ構築、実行エンジン、監視、設定、ユーティリティ等）。  
- 監視/実行の起動スクリプトに小さな堅牢化を追加しました（停止フラグ検知や例外ログの明確化など）。

0.1.0 - 2026-04-18
-----------------
Added
- 初回リリース: KabuSys 自動売買フレームワークの基礎実装を追加。
  - 実行/監視エントリポイント
    - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV が paper_trading の場合は専用のペーパートレード DB を使用し MockBrokerClient を用いる等、実行環境に応じた分離を実現。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止用フラグファイル（data/stop_requested.flag）を検知して安全に終了。
  - 設定管理
    - config.py: .env 自動読み込み機能、.env/.env.local の優先度、引用符付き値や export KEY=val 形式のパース対応、Settings クラス経由の型チェック、環境ごとのフラグ（is_live / is_paper / is_dev）などを実装。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションをサポート。
  - ユーティリティ
    - utils/logging_setup.py: ルートロガーの統一設定ユーティリティ。stdout へ StreamHandler、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールだけで稼働。
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。プラットフォーム差分や権限不足を安全に扱う。
  - ポートフォリオ構築（純粋関数群、DB 非依存）
    - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコアが全て 0 の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市況レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート）を実装。
    - portfolio/position_sizing.py: position size（発注株数）計算ロジックを実装。allocation_method に "risk_based"/"equal"/"score" をサポートし、単元株（lot_size）やコストバッファ、aggregate cap（利用可能現金超過時のスケーリング）など安全弁を備える。
  - リサーチ
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、移動平均、ATR、流動性等の計算を想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH で DB 指定可能。
  - モジュール初期化情報
    - __init__.py にパッケージバージョン __version__="0.1.0" を設定。

Changed
- 起動時の DB 接続ポリシーを明示
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視テーブルは一貫した DB に保つ設計）。
  - 実行（execution）は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する。
- .env 読み込みの挙動
  - OS 環境変数は保護（protected）され、.env.local は .env の上書きとして扱う。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Fixed
- 例外安全性の向上
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げたときに全体が止まらないよう logger.exception で捕捉して次のポーリングへ待機する処理を実装。
  - ログ設定でログディレクトリ作成に失敗した場合にファイルハンドラ作成失敗をハンドルし、コンソールのみで継続するようにした。
- 入力検証とフォールバック
  - MONITOR_POLL_INTERVAL が不正（数値以外や 0 以下）な場合に警告を出してデフォルト（60 秒）へフォールバックするように改善。

Notes
- 設計指針として、DB 参照を行う部分（ExecutionEngine / Monitoring 等）と純粋関数群（portfolio/*）を明確に分離しています。これによりユニットテストが容易になります。  
- 今後の予定: factor_research の完成、ExecutionEngine / BrokerClient の詳細な実装・テスト、StrategyModel に基づくシグナル生成モジュールの追加、CI/CD 用の起動スクリプト整備。

参考（主要な環境変数）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading の fill 動作（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリア抑止用フラグ

--- 
この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして利用する際は必要に応じて手元の変更履歴（コミットログ等）で補完してください。