CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 追加
  - research/factor_research.py の実装を継続中（モメンタム等のファクター計算ロジックを実装中、未完了箇所あり）。
- 変更 / TODO
  - portfolio.position_sizing の価格フォールバックや銘柄別単元対応など、将来的な拡張の注記と TODO を追加。

0.1.0 - 2026-04-19
------------------

注意: リポジトリ内ソースを元に推測して作成した初期リリースのまとめです。

- 追加 (主要機能)
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB (data/paper_trading.db) を使い、MockBrokerClient を利用する設計を反映。
    - プロセス優先度を起動直後に high に設定。
    - 停止フラグ (data/stop_requested.flag) および実行 PID 管理 (data/execution.pid) の検出とハンドリングを実装。
    - ExecutionEngine をスレッドで実行し、停止フラグを監視して安全に停止するループを実装。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告の上デフォルトにフォールバック。
    - 監視は環境に依らず本番用 sqlite_path を使用する仕様。
    - stop_requested.flag を検知してループを終了する挙動を実装。
  - 環境設定関連ツール
    - config.py
      - .env 自動ロード機構（プロジェクトルート検出：.git または pyproject.toml）を実装。
      - .env/.env.local の読み込みロジック、保護（OS環境変数を上書きしない）オプションを実装。
      - 複雑な .env 行パース（export 形式・クォート・インラインコメント・エスケープ）に対応。
      - Settings クラスを導入し、J-Quants / kabu API / DB パス /各種閾値 等の環境変数取得をプロパティ化（バリデーション・デフォルト含む）。
      - PAPER_FILL_MODE の有効値チェック、環境種別判定プロパティ（is_live / is_paper / is_dev）を提供。
    - config_setup.py
      - .env を対話式に作成・更新するウィザードを追加（既存 .env の読み込み、秘密項目のマスク表示、保存機能）。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数や config/*.yaml の存在・YAML パース（PyYAML 利用可否に応じて）を検証。
      - --strict オプションで警告も失敗扱いにできる。
  - utils
    - logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を標準で設定するユーティリティを追加。
      - LOG_LEVEL / LOG_DIR の解決順を実装。既存ハンドラの二重設定防止のため一度クリアして再設定する。
      - ログディレクトリ作成失敗時はファイルハンドラをスキップしコンソール出力のみで継続。
    - process_priority.py
      - OS（Windows / POSIX）差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
      - CPU affinity 設定関数を提供。権限不足や未サポート環境を想定した例外ハンドリングを実装。
  - portfolio モジュール（銘柄選定・配分・リスク調整・株数決定）
    - portfolio_builder.py
      - select_candidates: score 降順（同点は signal_rank）で候補選定。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア合計が 0 の場合は等金額にフォールバック（警告ログ）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限を適用し、既存保有比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターは無視）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告の上 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数算出を実装。
      - リスクベース計算、per-position 上限、lot_size（単元）丸め、コストバッファ (cost_buffer) を考慮した aggregate cap（可用現金超過時のスケーリングと残余配分）を実装。
      - 将来的な拡張（銘柄別 lot_size、前日終値フォールバック等）について注記あり。
  - monitoring/DB 関連
    - monitoring_db.init_monitoring_db 呼び出しにより、起動時に監視テーブルの存在を保証（冪等）。
    - DuckDB と SQLite の両方を接続して分析用 / 監視用 DB を分離して使用。
  - tools
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。期間指定や DB 指定オプションをサポート。
      - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定（閾値はソース内定義）。
      - P95 計算・日付フィルタ生成・欠損データに対する安全なフォールバック処理を実装。
  - パッケージメタ情報
    - __init__.py によるバージョン定義 __version__ = "0.1.0" を追加。

- 変更（挙動の明示・安全性向上）
  - run_monitoring / run_execution の両起動スクリプトで起動直後にプロセス優先度を設定するよう統一。
  - logging_setup が既存ハンドラを安全にクリーンアップしてからハンドラを再構成するようにし、二重出力を防止。
  - .env 読み込みの際、OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを回避。

- 修正（バグ修正 / 堅牢性）
  - MONITOR_POLL_INTERVAL のパースで 0 以下や非整数値を検出した場合に警告を出しデフォルト値にフォールバックするように変更（time.sleep に渡せない値による例外回避）。
  - process_priority.set_process_priority / set_cpu_affinity で権限不足や未サポート機能に対して例外をハンドリングし、警告を出して処理を継続するように変更。
  - calc_score_weights で全スコアが 0 のケースを警告して等金額配分にフォールバックするようにし、ゼロ除算を回避。
  - tools/paper_verification_report のクエリ実行でテーブル欠損（OperationalError）を想定したフォールバック処理を追加。

- ドキュメント / 開発支援
  - 各モジュールに docstring と使用例、設計メモ（PortfolioConstruction.md / StrategyModel.md への参照や TODO）を整備。
  - config_setup.py のウィザードにて生成される .env のテンプレート（コメント付き）を用意。

- 既知の制限 / 注意点
  - research/factor_research.py は一部未完（ソース末尾が未完の状態）。本リリースではモジュールの骨子と定数を追加済みだが、完全な実装は今後のリリースで対応予定。
  - position_sizing の価格フォールバック（price が欠損した場合の扱い）は TODO コメントあり。欠損データがあるとエクスポージャーや株数計算が過小評価される可能性あり。
  - .env は機密情報を含むため絶対にリポジトリへコミットしないことを .env テンプレートでも明記。

セキュリティ
------------
- 本バージョンで特にセキュリティ脆弱性は検出されていませんが、外部 API の認証情報 (.env 内) は厳重に管理してください（.env を VCS に含めないこと）。

貢献
----
- 今後の改善案・優先度の高いタスク:
  - factor_research の完成（全ファクター計算ロジック実装）。
  - 銘柄別 lot_size のサポートと価格フォールバックロジックの強化。
  - 単体テストの充実（position_sizing, risk_adjustment, portfolio_builder, paper_verification_report など）。
  - CI による静的解析・型チェック・テスト自動化。

