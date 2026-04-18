# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
リリース日付はソースコードから推測可能な最新の状態（本ドキュメント作成時点）を使用しています。

### Unreleased
- （なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御にファイルベースの停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）をサポート。
    - スレッドでエンジン実行、停止フラグ検出時に安全に停止。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、DuckDB も接続。
    - 停止フラグ検知でループ終了。KeyboardInterrupt に対応。

- 設定管理
  - config.py
    - Settings クラスを導入してアプリケーション設定を一元管理（プロパティベース）。
    - 環境変数自動ロード機能を追加：
      - プロジェクトルートを .git または pyproject.toml から探索して `.env` と `.env.local` を自動ロード（OS 環境変数を保護）。
      - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パーサーは `export KEY=val`、クォートあり／なし、インラインコメント処理等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 実行環境判定等）。
    - `PAPER_FILL_MODE` / `KABUSYS_ENV` / `LOG_LEVEL` の入力検証を実施し、不正値は例外を送出。
    - `settings` のインスタンスをモジュールレベルで提供。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - シークレット項目はマスク表示、選択肢・デフォルト提示、既存 .env の読み込みと Enter による再利用をサポート。
    - 最終確認後に .env を書き込み（ファイルには注意喚起ヘッダを付与）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML ファイル存在とパース検証（PyYAML が有れば詳細検証）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番環境向けの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START が危険な設定になっていないかなど）を実装。

- Portfolio / position sizing / risk
  - portfolio/portfolio_builder.py
    - シグナル選定と重み算出ユーティリティを追加。
    - select_candidates: スコア降順（同点時は signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有（売却予定除外）のセクター比率が上限を超える場合、新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピング、未知レジームは警告の上フォールバック）。

  - portfolio/position_sizing.py
    - position sizing（株数決定）ロジックを実装。
    - allocation_method に `risk_based` / `equal` / `score` をサポート。
    - 単元株（lot_size）での丸め、銘柄単位上限（max_position_pct）、総投下上限（max_utilization）に対する aggregate cap スケーリングを実装。
    - cost_buffer（スリッページ・手数料見積）を加味した保守的なコスト計算、スケールダウン後の残差配分ロジックを実装。

  - portfolio/__init__.py で主要 API をエクスポート。

- 研究（Research）
  - research/factor_research.py
    - DuckDB 接続を受け取りファクター計算を行う骨格を追加（Momentum / Value / Volatility / Liquidity 設計方針をコメントで明記）。
    - 定数（窓幅など）と calc_momentum の開始実装（prices_daily を参照）を用意（ファクター計算パイプラインの基盤）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - CLI から期間指定（--from/--to）や DB パス指定（--db）を受け付け、system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計して判定（PASS/FAIL）を出力。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90% など）し、P95 レイテンシの計算を実装。

- 監視・実行ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db（各起動スクリプトから監視テーブル存在保証のため呼び出し）。
  - SystemMonitor / ExecutionEngine などに接続するための DuckDB / SQLite の接続パターンを用意（各スクリプトで接続を確実にクローズ）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定関数 setup_logging を追加。
    - stdout に出力する StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイル（logs/<app_name>.log）を生成。ファイルハンドラはログディレクトリ作成に失敗した場合にフォールバックしてコンソールのみで継続。
    - デフォルトで 30 日分保持、ログレベルは引数 > 環境変数 > デフォルト の順に決定。
    - StreamHandler は stdout を使用（cron 等の出力リダイレクトを想定）。

  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows の優先度クラス / POSIX の nice 値を扱い `set_process_priority("high"|"normal"|"low")` を提供。
    - CPU アフィニティ設定 `set_cpu_affinity(cpu_count)` を提供。権限不足や未対応環境では警告を出してスキップ。

- ログ・運用
  - 起動スクリプト（execution/monitoring）は起動直後に set_process_priority("high") を呼び、優先度を向上させるように変更。
  - 停止フラグファイル検出による安全停止パターンを統一的に採用。

Changed
- （初期リリースのため大きな変更履歴はなし。以降のバージョンで差分を記載予定）

Fixed
- （初期リリースのため特定の「修正」履歴はなし）

Notes / その他
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされるため、配布先で動作が異なる場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して環境変数読み込みを制御してください。
- Paper Trading と Live の DB は意図的に分離されており、paper_trading モードではモックブローカーを想定した専用 DB に記録されます。
- research/factor_research.py や一部の実装（例: calc_momentum の続き）は骨組みが含まれており、将来的な拡張・最適化を想定した設計になっています。

参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/