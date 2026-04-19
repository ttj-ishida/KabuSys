Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトでは「Keep a Changelog」仕様に概ね準拠します。

フォーマット
-----------
- 変更はバージョン別にまとめ、カテゴリ（Added/Changed/Fixed/…）で分類します。
- 日付はリリース日を示します。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------

Added
- 基本機能・モジュールの追加（初期リリース）。
  - kabusys パッケージ本体（__version__ = "0.1.0"）。
- 実行エントリスクリプトの追加。
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、発注は MockBrokerClient 経由で行うよう分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を監視し、フラグ検出でエンジンを停止。
    - 実行用 PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に依存せず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグ検出でループを終了、例外発生時はログ出力して次ポーリングへ継続。
- 設定・環境管理
  - config.py
    - 環境変数・.env の自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env のパース機能を実装（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理など）。
    - 環境変数の取得ヘルパー（必須チェック _require()）、Settings クラスを提供。
    - 多数の設定プロパティ（DB パス、PID/kill flag、Paper Trading 関連、閾値設定、環境種別検証など）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
- 設定ユーティリティ CLI
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - デフォルト値、選択肢、シークレット入力（マスク表示）対応。
    - .env の読み書きロジックを提供（既存値の読み込み・上書き）。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数の有無チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック。
    - config/*.yaml ファイルの存在確認および PyYAML があればパース検証。
    - KABUSYS_ENV=live に対する追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を FAIL 扱いにするオプション。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定するユーティリティ。
    - ログレベル/ログディレクトリの解決順序、既存ハンドラのクリア、ファイル出力失敗時のフェールオーバー等を実装。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収したプロセス優先度設定（"high"/"normal"/"low"）および CPU affinity 固定機能。
    - psutil を用い、権限不足や未対応環境では警告を出してスキップする安全な実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコアが全てゼロの際は等配分にフォールバックする挙動。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップとフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes（risk_based / equal / score の allocation_method に対応）。
    - lot_size（単元株）丸め、1銘柄上限・aggregate cap、cost_buffer による保守的推定、スケーリング/再配分ロジック。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成するツール。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）を集計し Pass/Fail 判定を出力。
    - P95 計算、日付フィルタ (--from/--to)、DB パス解決（引数・環境変数・デフォルト）を実装。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタム等のファクターを計算する設計を追加（モジュールと定数群、calc_momentum の骨組みを実装中）。
- DB/分析エンジン連携
  - duckdb を分析用 DB として利用する接続コードを各所で採用（Execution / Monitoring / research ツール）。
  - monitoring DB 初期化 init_monitoring_db の呼び出しにより監視テーブルの作成を保証（冪等性を想定）。
- その他ユーティリティ・設計上の注意点をドキュメント化
  - .env パーサの詳細（クォート・エスケープ、コメントルール）。
  - デフォルト値、環境変数名一覧、設定の検証と警告メッセージ。

Changed
- N/A（初回リリースのため変更履歴はありません）

Fixed
- N/A（初回リリースのため修正履歴はありません）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の重要な挙動
- .env 自動ロード:
  - デフォルトでプロジェクトルートの .env と .env.local を自動的に読み込みますが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能です。
  - .env.local は .env の上書き（ただし OS 環境変数は保護）として読み込まれます。
- Paper Trading 分離:
  - paper_trading 環境では本番用 DB を汚さないよう SQLite パスを分離しているため、実運用とテストが明確に分離されます。
- プロセス制御:
  - 起動スクリプトは最初にプロセス優先度を上げる処理を実行しますが、権限不足等で設定できない場合は警告に留めて継続します。
- ログ設定:
  - デフォルトで stdout 出力と日次ローテートファイル出力を行います。ログディレクトリが作成できない場合はコンソールのみで継続します。
- Graceful shutdown:
  - run_execution と run_monitoring は共に外部の停止フラグ（data/stop_requested.flag）を監視し、検出時に正常終了処理を行います。

今後の予定（例）
- research/factor_research.py の完全実装（各ファクター計算の SQL 実装・テスト追加）。
- strategy / execution の詳細ロジック（ExecutionEngine, BrokerClient の実装・テスト拡充）。
- 単体テストと CI の整備、型チェックの強化。

お問い合わせ
------------
不明点や誤記を見つけた場合は issue を立ててください。