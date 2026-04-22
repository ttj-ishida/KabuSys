# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」仕様に準拠します。

## [0.1.0] - 2026-04-22

初回リリース。

### 追加 (Added)
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージエントリポイントでバージョンを定義: `__version__ = "0.1.0"`。

- 実行系 / 監視用起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 向けの起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - BrokerClientFactory によるブローカークライアント生成を導入（Mock を含む抽象化）。
    - Engine をデーモンスレッドで起動し、プロジェクトルートの data/stop_requested.flag による外部停止制御に対応。
    - 実行中 PID を data/execution.pid に記録する仕組み（pid_file のパス管理）。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループ終了。
    - 監視処理は常に本番の sqlite_path を使用（環境に依存せず監視 DB を統一）。

- 設定管理・CLI
  - config.py
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env, .env.local の読み込み順、OS 環境変数の保護（既存キーの保護）を実装。
    - `.env` のパースで export プレフィックス、クォート内エスケープ、インラインコメントを考慮する堅牢な実装。
    - Settings クラスを提供し、環境変数をプロパティとして型付きに取得（各種検証付き: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - paper_trading 用の PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の設定をサポート。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - デフォルト値、選択肢、シークレット入力の扱い、既存 .env の読み込みを提供。
    - .env ファイルの安全なテンプレート生成（コメント付き）を行う `_write_env`。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML の存在とパース検証、live 環境時の追加ガード（LINE 設定や Kill Switch の注意喚起）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコアが全て 0 の場合のフォールバック（等金額配分）と警告出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック警告）。

  - portfolio/position_sizing.py
    - 複数の配分方式をサポートする calc_position_sizes（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金でスケールダウン）、手数料/スリッページ見積り（cost_buffer）を考慮したスケーリングロジック。
    - スケールダウン時の端数（fractional remainder）を考慮して lot_size 単位で追加配分するアルゴリズムを実装。

  - portfolio/__init__.py で上記関数群を公開。

- ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーション共通のログ設定ユーティリティ。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30 日保持）をルートロガーに設定。
    - LOG_DIR 指定・自動作成、LOG_LEVEL 解決順をサポート。ファイル出力に失敗した場合はコンソールのみで継続。

  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応するフォールバック実装。権限不足や未対応 OS の場合は警告出力。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite データを集計し、稼働率・注文成功率・送信率・レイテンシ等の検証レポートを生成する CLI。
    - P95 レイテンシ計算、期間フィルタ（--from/--to）、DB パスの引数/環境変数解決を実装。
    - 合格基準（閾値）を定義し PASS/FAIL 判定を出力。

- 研究用ファクター計算基盤（未完の関数を含む）
  - research/factor_research.py を追加。DuckDB 接続を受けてモメンタム等のファクターを計算する設計を導入（計算範囲定義・定数群を実装）。

- 初期データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出し、監視テーブルの存在を保証（冪等処理）。

### 変更 (Changed)
- （初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- .env パーサーの強化
  - export プレフィックス、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメント処理などをサポートし、より堅牢な .env 読み込みを実現。

- 起動スクリプトの堅牢化
  - run_monitoring のポーリング例外を catch してループ継続（単一チェック失敗時にプロセスが停止しない）。
  - run_execution は停止フラグを起動前に確認し、既に停止フラグがある場合はエンジンを起動しない安全挙動を追加。

### その他 / 注意点 (Notes)
- 未実装 / TODO:
  - portfolio.risk_adjustment.apply_sector_cap では価格が欠損（0.0）な場合のフォールバック価格（前日終値など）未実装。将来的に拡張予定。
  - position_sizing の将来的拡張として銘柄毎の lot_size を支援する設計検討中（現状は全銘柄共通の単元数を想定）。
  - research/factor_research.py はファイルの末尾が不完全（実装途中）であり、完全な因子計算関数群の実装が必要。

- 実行環境注意:
  - .env 自動ロードはプロジェクトルートが検出できた場合のみ行われ、必要に応じて環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - ログディレクトリの作成に失敗した場合、ファイルロギングは無効化され標準出力のみでログが出力される。
  - process_priority / cpu_affinity の設定は権限が必要な場合があり、失敗時は警告を出してスキップする仕様。

### 既知の破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

（将来のリリースでは、ここに Unreleased セクションを追加し、変更内容を時系列で記録してください。）