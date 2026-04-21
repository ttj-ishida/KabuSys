CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
（訳注: 以下は与えられたコードベースから挙げられる機能・修正点を推測してまとめた初版の変更履歴です）

Unreleased
----------

- なし（次回リリースに向けた未反映の変更点はここに記載されます）

0.1.0 - 2026-04-21
-----------------

Added
- 基本機能（初回リリース）
  - KabuSys のパッケージ化とバージョン管理を導入（__version__ = 0.1.0）。
  - 実行エントリポイント:
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。スレッドでエンジンを実行し、停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する設計。
      - BrokerClientFactory により実運用/モック（ペーパートレード）を切り替え可能。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。RiskConfig のデフォルトパラメータを定義（例: max_position_pct, max_utilization, rate_limit_per_sec 等）。
      - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理（data/execution.pid）への対応あり。
    - run_monitoring.py: SystemMonitor をポーリングする監視用スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
      - 監視データは環境に関係なく本番の sqlite_path（デフォルト: data/monitoring.db）を使用して記録。
      - 停止フラグ（data/stop_requested.flag）を検知してループを終了する。
  - 環境・設定管理:
    - config.py: Settings クラスを提供。環境変数の読み取り、型変換、バリデーションを行う。
      - .env の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。OS 環境変数優先の読み込み順（OS > .env.local > .env）をサポート。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env の行解析において export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどを正しく扱う堅牢なパーサを実装。
      - 各種設定項目をプロパティ化（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 実行環境 判定等）。PAPER_FILL_MODE の値検証（instant/partial/never/reject）や KABUSYS_ENV の検証を含む。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット項目のマスク表示、既存 .env の読み込み、確認プロンプト、書き込みをサポート。
    - validate_config.py: 起動前に .env と config/*.yaml の基本チェックを行う検証 CLI を追加。--strict オプションで警告も失敗扱いにできる。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML がインストールされている場合）や本番環境向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を実行。

  - ログ周り:
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
      - コンソール出力（stdout）用 StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log）をルートロガーに設定。
      - ログディレクトリ自動生成、失敗時はファイル出力をスキップしてコンソールのみで継続。
      - 既存ハンドラの二重登録防止（既存ハンドラを削除してから設定）。
      - ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト の優先順位で決定。
  - プロセス制御ユーティリティ:
    - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice / Windows priority class）を設定する機能を追加。AccessDenied 等の例外は警告してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
  - ポートフォリオ構築ロジック（純粋関数群 — DB 参照なし）:
    - portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択（同点時のタイブレーク処理あり）。
      - calc_equal_weights / calc_score_weights: 等金額・スコア重み付けを実装。全銘柄のスコアが 0 の場合は等金額にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合に新規候補を除外するロジックを実装（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear のマッピング、未知のレジームは警告して 1.0 にフォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。単元株（lot_size）で丸め、per-stock 上限や aggregate cap（available_cash を超えた場合のスケーリング）を実装。スケーリング後の端数配分ロジック（残差順に lot_size を追加）や cost_buffer による保守的見積り対応あり。

  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用 SQLite を解析して検証レポート（稼働率、注文成功率、送信率、リスク却下数、API レイテンシなど）を生成するスクリプトを追加。日付フィルタ、DB パスオーバーライド (--db) に対応。P95 計算や閾値による PASS/FAIL 判定を実装。
  - 研究モジュール（部分実装）
    - research/factor_research.py: DuckDB 接続を受け取ってファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を追加。モメンタム計算（mom_1m/3m/6m, MA200 乖離等）を実装するための下地を整備（実装は継続中／途中までの状態）。

Changed
- なし（初回リリースにおける新規追加内容を中心に記載）

Fixed
- なし（既知のバグ修正はこのリリース時点では特に記載なし）

Security
- なし

Notes / Defaults / 環境変数（主要）
- デフォルト値の例:
  - KABUSYS_ENV: development
  - LOG_LEVEL: INFO
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - MONITOR_POLL_INTERVAL: 60
  - KILL_FLAG_CLEAR_ON_START: 0
- 重要: .env は絶対にリポジトリにコミットしないこと（config_setup.py のヘッダ注記）。

今後の予定（参考）
- research/factor_research のファクター計算の完成・テスト追加
- ExecutionEngine / RiskManager の単体テスト・統合テスト強化
- ロギング設定のさらなるオプション化（ファイルローテーション設定等）
- 単体モジュールに対するドキュメントとサンプル設定の充実

---------------
本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートに反映する際は、コミット履歴やリリース担当者の確認に基づいて調整してください。