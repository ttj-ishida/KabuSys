# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、日本語で記載しています。

注意: 本 CHANGELOG は与えられたコードベースから機能・挙動を推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

Added
- コア機能・起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリング監視ループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出す。
    - 監視は常に Settings による sqlite_path（本番 DB パス）を使用して初期化する（環境に依存しない）。
    - 停止制御: プロジェクトの data/stop_requested.flag を検出するとループを終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し paper_trading 専用 DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による停止制御を実装。
    - ExecutionEngine はスレッドで実行し、停止フラグ検知で engine.stop() を呼ぶ。

- 設定管理・検証・セットアップ
  - config.py
    - 環境変数読み込み・ラッパー `Settings` を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml）により .env 自動読み込みを行う（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパースは export キーワードやシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 多数のプロパティを提供（J-Quants、kabu ステーション、LINE、DB パス、監視閾値、環境判定フラグ等）。
    - Paper Trading の挙動制御 `PAPER_FILL_MODE` を実装（有効値: "instant" | "partial" | "never" | "reject"）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パスや config/*.yaml の存在/パース検証を行う。
    - `--strict` オプションで警告も失敗（exit(1)）として扱う。
    - 本番（live）環境向けのガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - config_setup.py
    - .env を対話的に初期作成・更新するウィザードを追加（`python -m kabusys.config_setup`）。
    - 入力補助（選択肢・デフォルト・シークレットマスク表示）と .env の書き込みを実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティ `setup_logging` を追加。
    - stdout 出力（StreamHandler）と日次ローテーションファイル出力（TimedRotatingFileHandler）を統一的に設定。ファイル出力の失敗時は警告しコンソールのみで継続。
    - ログレベルおよびログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows と POSIX 系（Linux/Mac 等）向けにプロセス優先度設定を抽象化するユーティリティを追加。
    - `set_process_priority("high"|"normal"|"low")` を実装（Windows の優先度定数と POSIX の nice 値を対応）。
    - CPU affinity 設定用 `set_cpu_affinity` を追加（使用コア数を最初の N コアに固定）。
    - 権限不足や未対応環境では警告を出して安全にスキップする。

- Portfolio（ポートフォリオ構築）モジュール
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates`（スコア降順、同点時は signal_rank）を追加。
    - 重み計算 `calc_equal_weights`, `calc_score_weights` を実装。score 全てが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を実装（既存保有を考慮して新規候補をフィルタ）。
    - レジームに応じた乗数 `calc_regime_multiplier` を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装:
      - risk_based（リスクベース）方式と equal/score 方式をサポート。
      - 単元丸め（lot_size）、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積りを実装。
      - スケールダウン時の端数配分ロジックを実装（残余キャッシュで lot_size 単位を再配分）。

- ツール・レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill）、送信率（send）、リスク却下数、API レイテンシ（平均・最大・P95）等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - P95 算出、日付フィルタ（--from / --to）、しきい値（稼働率 99%、fill 90%、send 95%、P95 <= 200ms）を定義。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を想定したファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - 定数・計算対象期間（例: 1M/3M/6M、MA200、ATR20 など）を定義。
    - （注）ファイル末尾に実装途中の箇所が見られます（関数途中で切れているため完全実装は今後の作業）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意（推測）
- .env 自動ロードはプロジェクトルートが特定できる場合のみ行われ、OS 環境変数は .env によって上書きされないよう保護される（保護対象は既存の os.environ）。
- config.py の `Settings` は起動時に未設定の必須環境変数があると例外を送出する実装となっているため、本番環境では .env の事前準備と validate_config による検証を推奨。
- run_monitoring は監視 DB の初期化（init_monitoring_db）を確実に行うが、監視は常に sqlite_path（本番 DB）を使用する点に注意。paper_trading 環境の監視も本番 DB を参照するため、運用ポリシーに応じて実行方法を検討のこと。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存するため、失敗時は警告でスキップされる。コンテナ/クラウド環境では期待どおり動作しない可能性がある。
- research/factor_research.py は未完成箇所があるため、利用前に実装の完了・テストが必要。

今後の提案（推奨される改善 / TODO）
- research/factor_research.py の完全実装と単体テストの追加。
- config のデフォルト値や env パースの境界ケースに対する追加ユニットテスト。
- ロギング周りのテスト（ディレクトリ作成失敗時の挙動など）。
- run_monitoring の監視 DB と paper_trading DB の扱い方を明確化（運用ドキュメントに明記）。
- ExecutionEngine / Broker の統合テストおよび paper_trading のレポート検証ワークフロー構築。

--- 

（この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のリリースノート作成時はコミット履歴・変更差分・設計文書を参照して確定してください。）