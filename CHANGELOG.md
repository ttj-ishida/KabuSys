# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-21

初期リリース。

### 追加
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 起動スクリプト（CLI）を追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用することで本番 DB と完全分離。
    - ブローカークライアントは BrokerClientFactory を通じて作成。
    - 実行中の停止フラグ（data/stop_requested.flag）を監視し、安全に停止する仕組みを実装。
    - 実行時に高優先度でプロセス優先度を設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視（monitoring）関連は環境に依らず本番 sqlite_path を使用する仕様。
    - 停止フラグを検知してループを終了、例外はログ出力して次回ポーリングまで待機。

- 環境・設定管理
  - config.py
    - .env 自動読み込み機構（プロジェクトルートの検出に .git / pyproject.toml を利用）。
    - .env のパースは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントを考慮。
    - 環境変数のラップを Settings クラスとして提供（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 用設定など）。
    - 自動ロードを無効にするフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI。
    - 秘密値（トークン/パスワード）をマスクして入力できる仕組み。
    - デフォルト値、選択肢、説明を含んだプロンプトを提供。
    - 生成時に .env ファイルへの注意書き（コミット禁止など）を出力。

  - validate_config.py
    - .env および config/*.yaml の設定検証 CLI。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML がある場合のみ）、本番環境向けの追加ガード（LINE 通知設定、Kill Switch の自動クリア設定）を実施。
    - --strict モードで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/<app>.log）を設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_LEVEL / LOG_DIR 環境変数または引数で制御可能。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定。
    - psutil の例外（AccessDenied 等）をハンドルしてフォールバックする設計。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順）select_candidates
    - 等金額・スコア加重の重み算出 calc_equal_weights / calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（売却予定銘柄を除外して既存ポジションのセクター比率を評価）
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知値は 1.0 にフォールバック）
  - portfolio/position_sizing.py
    - position size 計算 calc_position_sizes（risk_based / equal / score の割当方式をサポート）
    - lot_size（単元株）丸め、per-stock 上限、aggregate cap（available_cash に収まるようスケール）を実装
    - cost_buffer による手数料 / スリッページ見積りを反映

- リサーチ / ファクター計算
  - research/factor_research.py (骨組み・設計の追加)
    - Momentum / Value / Volatility / Liquidity といったファクターを計算する設計を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。
    - calc_momentum のインターフェースと定数を定義（計算ロジックの主要部分を実装予定）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計してレポート出力。
    - PASS/FAIL 判定基準（稼働率 99% 以上、注文成功率 90% 以上、送信率 95% 以上、P95 レイテンシ <= 200 ms）を実装。
    - --from / --to / --db オプションをサポート。デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- その他
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを複数箇所で導入し、監視テーブルが存在することを保証（冪等）。
  - stop/kill フラグファイル（data/stop_requested.flag, data/kill.flag 等）による外部制御を起動スクリプトでサポート。

### 変更
- 該当なし（初期リリースのため既存変更はなし）。

### 修正
- 該当なし（初期リリースのため既存修正はなし）。

### 既知の問題 / 注意点
- research/factor_research.calc_momentum の実装が途中で終了している箇所があり（ソース末尾が未完）、完全なファクター計算は現時点で未完です。今後のリリースで実装を完了予定。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に 0.0（欠損）を用いるとエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格（前日終値・取得原価など）の導入が検討されています（TODO）。
- position_sizing の将来的拡張点:
  - 現在は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map の導入を予定。
- .env ファイル: 自動生成された .env は絶対に Git にコミットしないでください（config_setup.py のヘッダに注意書きあり）。
- ログディレクトリ作成に失敗した場合はファイルロギングが無効化され、コンソールのみでログが出力されます。運用環境では logs/ ディレクトリの書き込み権限を事前に確認してください。
- process priority / cpu affinity の設定は OS 権限に依存します。権限不足の場合は警告が出力され、処理は継続します。
- validate_config.py は PyYAML がインストールされていない環境では config/*.yaml の中身検証をスキップします（警告を出力）。

### 互換性 / 移行ノート
- 起動方法
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 環境変数の主なデフォルト
  - KABUSYS_ENV: development
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - MONITOR_POLL_INTERVAL: 60（秒、run_monitoring 用）

- Paper Trading と Live（本番）は DB を分離する設計になっています。paper_trading を使う場合は KABUSYS_ENV を paper_trading に設定してください（または config_setup で選択）。

---

今後の予定:
- research/factor_research のファクター計算ロジックを完成させる。
- strategy / execution 周りの統合テストとドキュメントの拡充。
- 銘柄別 lot_size 管理や価格フォールバックの実装。