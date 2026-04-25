# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-25
初期リリース。本プロジェクトの基本機能・CLI・ユーティリティ群を実装。

### Added
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値は警告しデフォルトにフォールバック。
    - 監視用 DB（SQLite）と DuckDB に接続して monitoring テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）により安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - ロギング初期化（utils.logging_setup）を共通利用。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を介したブローカークライアント生成（paper 時は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て・実行。
    - ExecutionEngine を別スレッドで実行し、停止フラグで安全停止。PID ファイル管理（data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視テーブルの冪等な初期化を実行（init_monitoring_db）。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化対応。
    - .env パーサを強化（`export ` プレフィックス・引用符対応・エスケープ・インラインコメント処理）。
    - 保護付きキー（既存 OS 環境変数）を上書きしない仕組みを実装。
    - Settings クラスで各種設定プロパティを提供:
      - J-Quants / kabu API トークン/パスワード、KABUSYS_ENV（値検証）、LOG_LEVEL（検証）、DB パス（DuckDB/SQLite）、paper_trading 用パス、PID/KILL フラグパス、監視しきい値（CPU/MEM/DISK）等。
      - PAPER_FILL_MODE のバリデーション（許容値: "instant", "partial", "never", "reject"）。
      - is_live / is_paper / is_dev ヘルパー。

- 設定ユーティリティ・CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目は表示をマスクし、選択肢・デフォルトのサポート、.env の読み書きテンプレート（コメント付き）を提供。
  - validate_config.py
    - 起動前の設定検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAMLがあれば）パース検証、KABUSYS_ENV=live 向けの追加ガードチェック。
    - `--strict` オプションで警告をエラー扱いにする機能を提供。
    - exit コード（エラー/警告）に応じた戻り値。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 計算、日付フィルタ（--from/--to）、DB パスの引数または環境変数サポート（PAPER_TRADING_SQLITE_PATH）。
    - 合格基準（稼働率 99% など）による PASS/FAIL 判定と人間向け出力。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順 + tie-breaker）select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap（既存保有を考慮、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をマップ、未知のレジームは警告の上で 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based" / "equal" / "score") に基づく株数算出 calc_position_sizes。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケールダウン、cost_buffer を用いた保守的見積り。
    - スケールダウン時に余りの配分を再配分するアルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - 既存ハンドラの二重設定防止のためクリア後に再設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows/Linux/macOS 等）でプロセス優先度（nice / Windows priority class）と CPU affinity 設定のユーティリティを追加。
    - アクセス拒否や未サポート環境の際は警告を出して安全にスキップ。

- 研究用（未完/スケルトン）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム / MA / ATR / Liquidity 等の計算方針と定数を定義）。
    - DuckDB 接続を受け取り prices_daily 等を参照して計算する設計。実装途中の関数あり（ファイル末尾が途中で切れている）。

### Changed
- N/A（初期リリースのためなし）

### Fixed
- N/A（初期リリースのためなし）

### Deprecated
- N/A

### Security
- N/A

---

開発者注:
- 一部モジュール（research/factor_research.py 等）は実装途中またはスケルトンの状態です。運用前に未実装箇所の完成と追加のテストを推奨します。
- .env 自動読み込みはデフォルトで有効です。テストや特殊用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。