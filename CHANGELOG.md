CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-11
-------------------
初回公開リリース。

Added
- パッケージ初期化
  - kabusys.__version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を利用して本番 DB と分離して動作。
    - 実行時にプロセス優先度を "high" に設定（utils/process_priority を使用）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てるロジックを実装。

  - run_monitoring.py
    - SystemMonitor を定期ポーリングする監視プロセス起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を利用する設計。
    - 停止フラグ検知・例外ハンドリング・接続クローズ処理を実装。

- 設定・環境変数管理
  - config.py
    - Settings クラスを実装し、アプリケーション設定を環境変数から取得するユーティリティを提供。
    - .env 自動ロード機能を追加（プロジェクトルートの判定: .git または pyproject.toml を探索）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須/デフォルト値、型変換、値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を含むプロパティを定義。
    - paper_trading 用の独立 DB パス（PAPER_TRADING_SQLITE_PATH）や PID / Kill フラグ等の設定を提供。

  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。
    - 各項目の説明・選択肢・シークレット入力対応・既存 .env 読み込み・保存ロジックを実装。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML が存在する場合）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を追加。
    - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時のフォールバック（コンソールのみ）に対応。
    - LOG_LEVEL / LOG_DIR の解決優先度を実装。

  - utils/process_priority.py
    - プラットフォーム差異を吸収するプロセス優先度設定関数 set_process_priority と CPU affinity 設定関数 set_cpu_affinity を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、psutil を用いて実装。不許可時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補の選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコアが全て 0 の場合は等配分にフォールバックする挙動。

  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を実装（sell_codes を考慮、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームは警告の上フォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - 価格欠損時のスキップやログ出力を実装。

- 研究・ファクター計算
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加。DuckDB 接続を受け prices_daily / raw_financials を参照してモメンタム・ボラティリティ等を計算する設計。
    - 各種定数（移動平均期間、ATR 日数、スキャンバッファ等）を定義。
    - （モジュール途中までの実装が含まれる）

- モニタリング DB 初期化
  - monitoring/monitoring_db モジュール（参照箇所あり）を用いて、実行時に監視用テーブルの存在保証を行う（init_monitoring_db を run_* で呼び出し）。

- ツールスクリプト
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 99.0%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms。
    - --from, --to, --db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先。

Changed
- ー（初回リリースのため変更履歴はありません）

Fixed
- ー（初回リリースのため修正履歴はありません）

Security
- ー（初回リリースのためセキュリティ修正はありません）

Notes / Usage tips
- .env 自動ロード
  - リポジトリのプロジェクトルート（.git または pyproject.toml）が見つかれば .env / .env.local を自動的に読み込みます。OS 環境変数を上書きしない配慮あり。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 起動スクリプトの振る舞い
  - run_monitoring は監視データ保存に settings.sqlite_path（本番用）を使用します。MONITOR_POLL_INTERVAL によりポーリング間隔を設定可能（整数 >= 1、無効値はデフォルト 60 秒にフォールバック）。
  - run_execution は paper_trading モード時に settings.paper_sqlite_path を使用し、本番 DB と分離します。

- ログ出力
  - デフォルトで stdout にログを出力しつつ、logs/<app_name>.log に日次ローテーションで保存します。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。

- プロセス優先度 / CPU affinity
  - set_process_priority は psutil を用いてプラットフォーム差を吸収して設定しますが、権限不足等で設定できない場合は警告を出してスキップします。

ライセンスおよび貢献
- 本リポジトリのライセンス情報、貢献方法などはプロジェクトルートの README / LICENSE を参照してください。