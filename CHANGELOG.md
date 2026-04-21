CHANGELOG
=========

すべての注目すべき変更点をこのファイルで記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-04-21
-------------------

Added
- 初回公開: KabuSys v0.1.0 を追加。
- 実行エントリ / ランタイム
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト配下 data/stop_requested.flag によるフラグ検出。
    - Monitoring は環境にかかわらず production 相当の sqlite_path を使用（監視 DB を一元化）。
    - duckdb を併用して分析用 DB に接続。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。
    - 実行中 PID 管理（data/execution.pid）と停止フラグによる安全な停止処理を実装。
    - エンジンは別スレッドで実行され、停止フラグ検知時に engine.stop() を呼び出す。
  - CLI / ユーティリティ
    - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
      - 各設定項目の説明・既存値の再利用・シークレットマスク表示をサポート。
      - .env 生成テンプレートを提供（.env を絶対にコミットしない旨の注記あり）。
    - validate_config.py: 起動前の設定検証ツールを追加。
      - 必須 / 任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML が利用可能ならパースも実行）。
      - --strict モードで警告を FAIL 扱い可能。
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
      - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計し PASS/FAIL 判定を出力。
      - デフォルト DB は data/paper_trading.db。コマンドラインで期間指定可。
- 設定・環境管理
  - config.py: 環境変数管理クラス Settings を追加。
    - .env 自動ロード機構（プロジェクトルート判定: .git または pyproject.toml に基づく）。
    - .env と .env.local の読み込みルール（OS 環境変数を保護、.env.local が上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - 各種プロパティ提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値等）とバリデーション。
    - paper_fill_mode の有効値チェック（instant/partial/never/reject）。
- ロギング・運用ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテート（TimedRotatingFileHandler）を root ロガーへ設定。
    - LOG_DIR 環境変数 / 引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - デフォルト保持日数 30 日。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を吸収して set_process_priority("high"|"normal"|"low") が利用可能。
    - set_cpu_affinity(n) による最初の n コア固定をサポート（権限不足等で失敗した場合は警告ログでスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート・上位選出。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率から新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数（未知レジームは警告とともに 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
    - 単元株 (lot_size) の丸め、1銘柄上限・aggregate cap（available_cash）へのスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した安全な配分ロジックを実装。
    - スケールダウン時の端数配分は残差の大きい順に lot 単位で配分して再現性を確保。
- research/factor_research.py
  - ファクター計算モジュールの骨組み（モメンタム / MA200 / ATR / ボリューム等の計算方針）を追加（DuckDB 接続を受ける設計、prices_daily / raw_financials を参照）。
- パッケージ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

Changed
- 設計上の注意点・既定値を明示
  - 監視ループ・実行エンジン起動時に最初にプロセス優先度を "high" に設定するように仕様化。
  - .env の読み込み順序と保護（OS 環境変数を上書きしない）を明文化。
  - monitor 側は環境に依存せず監視 DB を共通の sqlite_path で扱う方針とした（運用上の一元監視を優先）。

Fixed
- —（初回リリースのため該当なし）

Deprecated
- —（初回リリースのため該当なし）

Removed
- —（初回リリースのため該当なし）

Security
- 環境変数取り扱い上の注意喚起をドキュメント化（.env を Git 管理しない旨を config_setup で明示）。

Notes / 備考
- validate_config は PyYAML が存在しない場合は YAML 検証をスキップして警告を出します。CI 環境等では PyYAML をインストールしておくことを推奨します。
- モジュール間で参照する実装（例: SystemMonitor、ExecutionEngine、BrokerClientFactory、OrderManager 等）は本リリースで呼び出しポイントを用意していますが、具体的な外部連携（実際のブローカ API 呼び出し等）は設定に依存します。paper_trading モードでは MockBrokerClient により本番 DB や実際の注文を分離してテスト可能です。
- research/factor_research.py はファクター計算ロジックの設計に沿った実装が含まれますが、ロジックの完全実装・最適化は今後の改善対象です。

--- 

（変更履歴は今後の開発で更新してください）