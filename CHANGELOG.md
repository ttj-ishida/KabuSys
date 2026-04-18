CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and the versioning is
based on Semantic Versioning.

Unreleased
----------

- なし（現状のスナップショットは v0.1.0 を基準に作成されています）

0.1.0 - 2026-04-18
-----------------

Added
- 基本パッケージ初期リリース。
  - パッケージバージョン: 0.1.0

- 起動スクリプト / 実行環境関連
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) の検知で安全にループ停止。
    - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用して監視データを記録。
    - check_once() 内の例外は捕捉してログに記録、次ポーリングに継続。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して MockBrokerClient を利用可能。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - 停止フラグ検知で Engine.stop() を呼び出して安全に停止。
    - 実行用 PID ファイル（data/execution.pid）サポート。

- 設定管理
  - config.py
    - .env 自動読み込み実装（プロジェクトルートの .env/.env.local を読み込む。OS 環境変数は保護、.env.local は override を許可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - .env の各行パースで export KEY=val、クォート値、バックスラッシュエスケープ、行内コメント等を考慮した堅牢な実装。
    - Settings クラスで環境変数へアクセスする整形済みプロパティ群を提供（DBパス、PIDファイル、閾値、環境判定フラグ等）。
    - PAPER_FILL_MODE のバリデーションと有効値チェック。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値チェック）。

  - config_setup.py
    - 対話式ウィザードで .env を作成 / 更新する CLI を追加。
    - シークレット項目はマスク表示、既存値を Enter で再利用可能。
    - 出力はテンプレ化された .env フォーマットで保存し、保存前に確認を求める。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
    - --strict モードで警告も失敗扱いにできる。
    - live 環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）を実装。

- ログ / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保存）を設定するユーティリティを追加。
    - すでにハンドラが存在する場合はクリアしてから再設定（重複防止）。
    - LOG_DIR / LOG_LEVEL の環境変数と引数での上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py
    - Windows / POSIX を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能。プラットフォームごとの実装を内部で吸収。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（必要に応じて最初の N コアに固定）。
    - 権限不足などの失敗時は警告ログを出してスキップ（安全なフォールバック）。

- 監視・モニタリング
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルを冪等に初期化（存在確認用）。
  - SystemMonitor を使って system_status 等の監視データを記録（run_monitoring/run_execution から初期化呼び出し）。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア加重配分を返す。全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックして Warning を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外の対象外）。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告を出す。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数計算を実装。
      - "risk_based": 許容リスク率・損切り率に基づくポジションサイズ計算。
      - "equal"/"score": ウェイトに基づく金額配分から株数決定。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）を考慮。
    - cost_buffer（手数料・スリッページ見積）を導入して保守的にコスト見積り。
    - aggregate cap を超過する場合はスケールダウンし、余りキャッシュで残差順に lot 単位で再配分するロジックを実装。
    - 価格未取得銘柄はスキップして安全な挙動を確保。

  - portfolio/__init__.py
    - 上記関数群をパッケージ公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- リサーチ / ファクター計算（研究用）
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB を受け取って prices_daily / raw_financials を参照する設計。
    - Momentum、Value、Volatility、Liquidity といった複数のファクター群を想定している実装骨子を追加。
    - calc_momentum の雛形・定数を追加（1M/3M/6M リターン、MA200 乖離、データ不足ハンドリングなど）。
    - （注）ファイル末尾で calc_momentum 実装が途中で切れている箇所があり、完全実装は今後の作業予定。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - PAPER_TRADING_SQLITE_PATH（環境変数）または --db オプションで DB 指定可能。
    - システム安定性（稼働率）、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - PASS/FAIL 判定基準の閾値を定義（例: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 レイテンシ <= 200 ms）。
    - 日付範囲指定 (--from / --to) に対応。データ欠落時は N/A を表示。

Other
- __init__.py にパッケージ version を設定（__version__ = "0.1.0"）。

Notes / Development
- .env の自動ロードはプロジェクトルートの検出に依存しており、.git または pyproject.toml を基準に探索する。配布後にプロジェクトルートが特定できない場合は自動ロードをスキップする仕様。
- run_monitoring は monitoring 用 DB を常に本番 sqlite_path に接続する設計で、環境に依らず監視データの記録先を一定にしています。一方、run_execution は paper_trading 環境を明確に分離して paper_sqlite_path を使用します。
- process_priority / cpu_affinity の設定は権限不足や未対応 OS の場合に安全にフォールバックするよう実装されています。
- research/factor_research.py は計算ロジック（SQL や集計）が中心で、DuckDB テーブル設計に依存するため、本番運用前に prices_daily/raw_financials のデータ品質確認が必要です。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Security
- なし

今後の予定（提案）
- research/factor_research.py の完全実装（Value / Volatility / Liquidity ファクター、Zスコア正規化）。
- ExecutionEngine / BrokerClient のテストカバレッジ拡充とモックの整備。
- 単体テスト・CI 設定の追加（設定検証・静的解析・主要コンポーネントの動作確認）。
- レポートやモニタリングのアラート経路（LINE 通知）実装の確認とテスト。