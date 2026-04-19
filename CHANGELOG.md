CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
慣例: 重大/新機能は "Added"、後方互換を脅かす変更は "Changed"、バグ修正は "Fixed" に記載します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーションの初期実装を追加（初期バージョン 0.1.0）。
  - パッケージエントリポイントとバージョン設定: src/kabusys/__init__.py
- 実行系起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。スレッドでエンジンを実行し、data/execution.pid を管理。停止フラグ（data/stop_requested.flag）検知で安全に停止可能。
  - paper_trading モード対応: KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して MockBrokerClient を利用できる設計。
- 監視系起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化を行い DuckDB へ接続して記録を行う。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数の読み取り・検証を統一。デフォルト値、検証（KABUSYS_ENV, LOG_LEVEL 等）、Paper Trading 関連の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）を提供。
  - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パースの強化: export 形式、シングル/ダブルクォート、インラインコメント、エスケープ処理等に対応。
- 設定ユーティリティ
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加（src/kabusys/config_setup.py）。シークレットマスキング、選択肢、デフォルト値をサポート。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数チェック、パスの妥当性、YAML パースチェック（PyYAML があれば）や本番環境ガード等を実行。--strict モードで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - logging_setup: ルートロガー設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）を設定し、既存ハンドラの二重登録を防止。ログディレクトリ作成失敗時はコンソールのみで継続。
  - process_priority: プロセス優先度（Windows / POSIX を吸収）と CPU affinity 設定ユーティリティを追加。権限エラーや未対応 OS を考慮してフォールバックする実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）および配分重み（calc_equal_weights, calc_score_weights）を実装。score が全て 0 の際は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに基づく乗数 calc_regime_multiplier を実装。unknown セクターの扱い、レジーム不明時のフォールバックを備える。
  - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）を実装。単元（lot_size）丸め、per-stock 上限・aggregate cap、コストバッファによる保守的見積り、スケールダウンロジックを実装。
  - portfolio パッケージのエクスポート整備（__init__.py）。
- 研究 / 分析基盤
  - research.factor_research: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、MA200 乖離、ATR、出来高等の仕様コメントを含む）。（実装途中のファイルあり）
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を算出し PASS/FAIL 判定を出力。期間フィルタと DB パス指定をサポート。
- DB 統合
  - DuckDB と SQLite の両方を利用する設計。監視・トレードログは SQLite、分析は DuckDB を想定。起動スクリプトは両 DB へ接続し、監視テーブルの初期化処理を呼び出す（init_monitoring_db を利用）。

Changed
- なし（初回リリース）

Fixed
- 環境変数パースの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォート内エスケープ、インラインコメント処理などに対応し、誤解釈を軽減。
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックして警告を出す実装を追加（ロジック安定化）。
- process_priority / set_cpu_affinity: 未対応 OS、権限不足時に警告を出してスキップするよう改善し、起動失敗を防止。

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / Notes
- research.factor_research の一部実装が途中で切れており、完全なファクター計算実装は今後の作業が必要。
- apply_sector_cap 内の価格欠損（price_map に 0.0 等が入る場合）に対するフォールバックが TODO コメントとして残っている。将来的に前日終値などのフォールバック価格を導入すべき。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップするため、ディスク書き込みに問題がある環境ではログがコンソールのみになる点に留意。
- 一部の振る舞い（例: run_monitoring が常に本番 sqlite_path を使う設計）は意図的な仕様（監視データは本番 DB に集約するため）だが、運用時には環境変数とパス設定を十分に確認のこと。

開発者向けメモ
- .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後やテスト環境で自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようと試みます。権限不足で失敗しても起動は継続しますが、期待するパフォーマンスが得られない可能性があります。

（以上）