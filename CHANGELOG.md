CHANGELOG
=========

すべての重要な変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回公開リリースを追加。
- CLI 起動スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。停止フラグ / PID 管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - kabusys.validate_config: .env と config/*.yaml の起動前チェックツール（--strict オプションで警告を FAIL 扱いにできる）。
  - kabusys.config_setup: .env の対話式ウィザード（.env の初期作成 / 更新を支援）。
  - kabusys.tools.paper_verification_report: Paper Trading 用の検証レポート生成ツール（日時フィルタ、閾値を利用した PASS/FAIL 判定）。
- 設定管理:
  - Settings クラスを実装し、環境変数経由で各種設定（DB パス、API トークン、環境種別など）を提供。
  - .env 自動読み込み機構を導入（プロジェクトルート検出: .git または pyproject.toml を基準）。.env.local を優先度高で読み込み、OS 環境変数を保護して上書き制御。
  - .env パーサ強化: export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどに対応。
- データベース・分析:
  - DuckDB/SQLite の接続を扱うユーティリティと起動フローを追加（monitoring と execution で適切な DB を接続）。
  - Paper Trading と本番 DB の分離: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用する挙動を追加。
- ロギング / 運用ユーティリティ:
  - utils.logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を統一的に設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定のユーティリティを追加。Windows / POSIX 差分を吸収し、失敗時は警告してスキップ。
- ポートフォリオ構築（純粋関数群）:
  - portfolio.portfolio_builder: 候補選定（select_candidates）・等配分（calc_equal_weights）・スコア加重（calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier（未知レジームは警告してフォールバック）。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に基づく発注株数算出。損切り・単元株丸め・ポジション上限・投下資金の aggregate スケーリング・cost_buffer（スリッページ/手数料考慮）を実装。
- Paper Trading 検証:
  - tools.paper_verification_report: システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。デフォルト閾値を使った PASS/FAIL 判定を実装。

Changed
- run_monitoring:
  - 監視は KABUSYS_ENV に関わらず本番向け sqlite_path を使用する仕様（監視データは本番 DB を想定）。
  - 起動時にプロセス優先度を "high" に設定するフローを追加。
  - 停止フラグファイル（data/stop_requested.flag）を検出してループを終了する実装。
  - MONITOR_POLL_INTERVAL 環境変数からポーリング間隔を取得。0以下または不正な値はデフォルト 60 秒にフォールバックして警告を出力。
- run_execution:
  - Execution 起動時にプロセス優先度を "high" に設定。
  - Paper trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient を使用して本番 DB と完全分離。
  - ExecutionEngine を別スレッドで起動し、停止フラグ検知でエンジン停止を呼び出す仕組みに変更。
  - monitoring 用テーブルが存在することを保証するため起動時に init_monitoring_db を呼び出す（冪等化）。
- config.validate:
  - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無い場合は警告）など実用的な検証ルールを追加。
  - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険な値に対する警告）を追加。
- 設定ウィザード（config_setup）:
  - ユーザに対する対話式プロンプトを実装。既存 .env の読み込み・マスク表示・デフォルト提示・選択肢検証・保存確認をサポート。
  - .env ファイル生成時のテンプレートと説明を整備。

Fixed
- 環境変数パースや設定読み込みの堅牢性向上:
  - .env のクォート内エスケープやインラインコメントの扱いを改善し、誤ってコメントを値に取り込む等の問題を防止。
  - MONITOR_POLL_INTERVAL の不正値に対して ValueError を起こさずデフォルトへフォールバックしてログに警告を出すようにした。
- process_priority/set_cpu_affinity:
  - 権限不足・未対応プラットフォームでの例外を捕捉して警告ログを出力、例外によるプロセス停止を防止。

Notes / Implementation details
- デフォルト値:
  - ポーリング間隔: 60 秒（MONITOR_POLL_INTERVAL で上書き可）。
  - DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db、Paper Trading DB: data/paper_trading.db。
  - ログ: デフォルト logs/ ディレクトリに日次ローテート（30日分保持）、コンソール出力は stdout を使用。
- Position sizing の重要仕様:
  - 単元株（lot_size）で丸め、aggregate 投資額が available_cash を超える場合はスケールダウンして残差は fractional 残差順に lot 単位で再配分する。
  - price が欠損（0.0 等）の場合はその銘柄をスキップし、将来的なフォールバック価格導入を示唆する TODO コメントあり。
- Paper verification report:
  - 稼働率、注文成功率、送信率、P95 レイテンシなどを評価。デフォルト閾値はコード内定数で定義（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）。

Security
- .env は絶対に Git にコミットしない旨を生成テンプレートに明記。

Acknowledgements / Misc
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" を初期リリースとして採用。

今後の予定（例）
- portfolio・research モジュールの単体テスト増強。
- position_sizing における銘柄別 lot_size / フォールバック価格の実装。
- DuckDB を用いたファクター計算の高速化・最適化（未完の calc_momentum 実装の継続）。

-----