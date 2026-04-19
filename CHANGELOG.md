Keep a Changelog
================

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし（このリリースが初期公開相当の内容です）

0.1.0 - 2026-04-19
-----------------

Added
- 全体
  - 初期機能セットを追加（バージョン __version__ = 0.1.0）。
  - パッケージ構成: execution, monitoring, portfolio, utils, research, tools 等のモジュールを提供。

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV が paper_trading の場合、ペーパートレード用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して動作する（MockBrokerClient を利用する実装想定）。
    - プロセス優先度を最初に "high" に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag（実行中の停止要求）と data/execution.pid を使用して安全に停止可能。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値は警告を出してデフォルトにフォールバック）。
    - 監視 DB は KABUSYS_ENV に関わらず settings.sqlite_path（本番想定パス）を使用して接続し、監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 例外ハンドリングにより check_once() の例外発生時も監視ループを継続。

- 設定・環境管理
  - config.py
    - 環境変数／.env の自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパース強化: export プレフィックス、クォート内エスケープ、インラインコメント処理などに対応。
    - Settings クラスでアプリ設定をプロパティとして提供（DB パス、PID パス、しきい値、環境判定フラグ等）。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH 等の専用プロパティを追加。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。
    - シークレット値のマスク表示、選択肢サポート、保存前の確認ダイアログを備える。
    - 書き出しテンプレートを提供（.env を Git にコミットしない旨を明記）。

  - validate_config.py
    - 起動前に必須環境変数や設定ファイルの有無・基本整合性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在チェック（PyYAML があればパース検証も実施）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定などを警告）。
    - --strict モードで警告を FAIL 扱いに可能。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化ユーティリティを提供。
    - stdout 出力用 StreamHandler と 日次ローテーションを行う TimedRotatingFileHandler をルートロガーに設定（30日分保持）。
    - LOG_DIR / LOG_LEVEL からの解決、既存ハンドラのクリア機構、ログディレクトリ作成失敗時のフォールバックを実装。

  - utils/process_priority.py
    - psutil を利用したプロセス優先度設定ユーティリティを実装（Windows / POSIX の差分を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構成（Portfolio construction）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャが閾値を超える場合に新規候補を除外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）、未知のレジームは 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes を実装（allocation_method="risk_based" / "equal" / "score" 対応）。
    - lot_size（単元株）で丸め、per-stock 上限および aggregate cap（available_cash でスケール）を考慮。
    - cost_buffer を用いた保守的なコスト見積り、スケール時の端数処理（残余キャッシュで lot 単位を再配分するロジック）を実装。
    - 設計上の TODO コメントとして将来的な銘柄別 lot_size 対応を明記。

  - portfolio.__init__ で主要関数を公開。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを実装。
    - CLI オプション --from / --to / --db をサポート。
    - 指標: システム稼働率／ポーリング数、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - PASS/FAIL 判定基準（デフォルト閾値）を実装:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- research（部分実装）
  - research/factor_research.py
    - モメンタム等のファクター計算の枠組みと定数を追加（momentum 用の関数雛形を含む）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。注: ファイル末尾で実装が途中で切れている（下記 Known issues 参照）。

Changed
- なし（初期追加のため該当なし）。

Fixed
- なし（初期追加のため該当なし）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Known issues / Notes
- run_monitoring は Monitoring 用 DB に settings.sqlite_path（監視 DB）を使用する設計。監視データは環境に関係なく同一 sqlite_path に記録される点に注意。
- run_execution は paper_trading 時に専用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用するよう明確に分離。
- config._find_project_root() によりプロジェクトルートを .git または pyproject.toml で判定するため、配布後にこれらが存在しない環境では .env の自動読み込みをスキップする。
- 一部の処理で将来的な改善点（TODO）がコード内に残っている:
  - position_sizing: 銘柄別 lot_size の導入（現在は共通 lot_size を想定）
  - risk_adjustment: price が欠損（0.0）時のフォールバック価格処理
  - research/factor_research.py はモメンタム計算の実装が途中で切れている（現状は骨格のみ）
- ログディレクトリ作成やプロセス優先度設定は環境・権限に依存するため、失敗時は警告を出してフォールバックする設計（サービスの致命的停止を防ぐ）。

参考（環境変数 / デフォルト）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト: 60。無効値は警告でデフォルトにフォールバック。
- KABUSYS_ENV: 実行環境。valid: development | paper_trading | live。デフォルト: development。
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant|partial|never|reject）。デフォルト: instant。
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）。
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）。
- DUCKDB_PATH: DuckDB（デフォルト: data/kabusys.duckdb）。
- LOG_LEVEL / LOG_DIR: ログ設定に利用。

-- END --