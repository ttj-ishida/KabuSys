CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリース日はソースコード内のコメント・使用例等から推測しています。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-11
-----------------

Added
- 全体
  - 初版の公開。自動売買システム KabuSys の基本ユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を追加。

- 起動スクリプト / 実行制御
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV による挙動分岐: paper_trading の場合は専用の MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db）を使用して実環境とデータを分離。
    - 起動前にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag の検知、PID ファイルの扱い、スレッドで実行されたエンジンの安全な停止処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）の検知と例外ハンドリング（check_once() の例外はログに残してポーリングを継続）。

- 設定管理
  - config.py: 環境変数と .env 自動読み込み機能を追加。
    - .git または pyproject.toml を基準にプロジェクトルートを探索して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応したパーサを実装。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境判定など）をプロパティ経由で取得。値検証（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）を行う。
  - config_setup.py: .env を対話的に作成・更新するウィザードを追加。
    - シークレット値は表示をマスクしつつ既存値の再利用をサポート。
    - ファイルへの書き込みフォーマットとヘッダを整備。

- 設定検証
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実施。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次・30 日保持）を併用。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL / LOG_DIR / 引数から解決。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の優先度定数）と POSIX（nice 値）を吸収し、未対応 OS はスキップ。権限不足や未対応機能は警告ログでフォールバック。
    - set_cpu_affinity で先頭 N コアに固定する機能を実装（引数 None で無効化）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順に並べ上位 N を選択（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限のフィルタリング実装（既存保有のセクター比率が上限を超える場合、新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じた株数計算を実装。
      - risk_based: 許容リスク率、stop_loss、1 銘柄上限などを考慮して基準株数を算出し、単元株（lot_size）で丸め。
      - equal/score: 重みと max_utilization を用いて割当量を算出。
      - aggregate cap の超過時はスケールダウンと端数処理（lot 単位での再配分）を行う。手数料・スリッページ見積り用 cost_buffer を考慮。

- 研究 / ファクター計算
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 系のファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - モメンタム指標（1M/3M/6M リターン、200 日 MA 乖離）などを計算予定（実装はモジュールに基礎的な定数と calc_momentum の骨組みを含む）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH、--db）からシステム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）を出力。
    - P95 計算、期間フィルタ（--from / --to）、閾値による Pass/Fail 判定実装。
    - DB スキーマが存在しない場合に sqlite3.OperationalError をハンドルしてデフォルト値でレポートを作成。

- パッケージメタ
  - __init__.py にてバージョン 0.1.0 を設定。

Security
- （現在なし）

Deprecated
- （現在なし）

Removed
- （現在なし）

Fixed
- （初版のためリリース前の調整やフォールバック処理を含む）
  - .env のパースでのクォート・エスケープ・コメント処理を堅牢化。  
  - ログディレクトリ作成失敗時やプロセス優先度設定失敗時に例外で停止せず警告ログで安全にフォールバックするよう改善。

Notes / 実装上の注意
- run_monitoring は記載の通り監視 DB に本番の sqlite_path を使うため、開発用途で分離したい場合は Settings.paper_sqlite_path 等を利用して運用側で切り替えてください。
- config.py の自動 .env ロードはプロジェクトルートの検出を行うため、配布後やテスト環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 一部モジュール（例えば research/factor_research.calc_momentum）は骨格を含み計算ロジックの詳細実装が続く見込みです。

今後の予定（概要）
- factor_research の各ファクター実装完了とテスト追加。
- ExecutionEngine 周辺コンポーネント（broker, order_manager, reconciler, risk_manager 等）の詳細仕様・ユニットテスト強化。
- CI 設定・パッケージング、ドキュメント拡充（使用例・運用手順の整備）。

--- 

（本 CHANGELOG はソースコードの内容・コメント・使用例から推測して作成しています。実際の変更履歴はリポジトリのコミットログを参照してください。）