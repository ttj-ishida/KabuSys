# Changelog

すべての非互換な変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
このファイルはリポジトリのコードから推測して作成しています。

現在のバージョンは 0.1.0 です。

## [0.1.0] - 2026-04-24

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を追加。
  - 実行・監視用エントリポイント
    - run_execution: ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。
      - PID / stop flag 管理（data/execution.pid, data/stop_requested.flag）。
      - スレッドで Engine をデーモン実行し、停止フラグ検知で安全停止。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグによるループ終了処理と例外ハンドリングの実装。
  - 設定関連
    - Settings クラス（src/kabusys/config.py）
      - .env 自動読込（.env, .env.local）・保護付き上書きロジックを実装。
      - 各種設定プロパティ（DB パス、API トークン、Paper Trading 設定、閾値など）を提供。
      - PAPER_FILL_MODE の妥当性チェックなど細かいバリデーションを実装。
    - config_setup: 対話式 .env ウィザード（src/kabusys/config_setup.py）
      - .env の生成・更新を対話形式で支援。シークレットのマスク表示やオプション項目対応。
    - validate_config: 設定検証 CLI（src/kabusys/validate_config.py）
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在チェック、config/*.yaml の存在・パース検査（PyYAML があれば内容検証）。
      - --strict オプションで警告を失敗扱いにするモードを提供。
  - ロギング・プロセス制御ユーティリティ
    - setup_logging: 統一ログ設定（src/kabusys/utils/logging_setup.py）
      - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、エラー時はファイル出力をスキップ。
      - ログローテーションは 30 日分保持。
    - process_priority: プロセス優先度・CPU affinity 設定（src/kabusys/utils/process_priority.py）
      - Windows/Linux/macOS を抽象化して優先度設定（high/normal/low）や CPU affinity 設定を提供。psutil 依存でエラーは警告でスキップ。
  - データ層統合
    - DuckDB を分析 DB に使用する統合（Settings.duckdb_path、各種接続箇所）。
    - 監視用 SQLite（monitoring.db）初期化ユーティリティ init_monitoring_db の呼び出しを実装（監視テーブルの冪等初期化）。
  - ポートフォリオ構築ライブラリ（src/kabusys/portfolio/）
    - portfolio_builder: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中上限適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - position_sizing: 株数計算（calc_position_sizes）
      - risk_based / equal / score の割当方式に対応。
      - 単元株丸め（lot_size）、コストバッファ、aggregate cap（利用可能現金に基づくスケーリング）を実装。
  - 研究 (research)
    - factor_research（部分実装）: DuckDB 接続を用いたファクター計算フレームワークの骨子を追加（モメンタム・ボラティリティ等を想定）。
  - ツール
    - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
      - Paper Trading DB を解析して稼働率、注文成功率、送信率、レイテンシ(P95 等) を算出し PASS/FAIL 判定するレポート生成 CLI を実装。
      - デフォルトの閾値（稼働率 99%, 成立率 90% 等）を定義。
  - パッケージメタ情報
    - パッケージ初期バージョンを __version__ = "0.1.0" として追加（src/kabusys/__init__.py）。

### Changed
- ログ出力のデフォルト動作
  - StreamHandler を stdout に向けるように変更（cron 等からの起動時に stdout/stderr を統一してリダイレクトしやすくするため）。(src/kabusys/utils/logging_setup.py)
- 監視ループのデフォルト DB 使用ポリシー
  - run_monitoring は KABUSYS_ENV に依存せず本番用 sqlite_path を使用する設計（監視データを本番 DB に集約する意図）。(src/kabusys/run_monitoring.py)
- Execution 起動時の DB 分離
  - 本番/ペーパーで SQLite パスを分離（paper_trading 時は paper_sqlite_path を使用）。(src/kabusys/run_execution.py, src/kabusys/config.py)

### Fixed
- 環境変数パーサの強化（src/kabusys/config.py）
  - export KEY=val 形式やクォート文字列内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、空行/コメント行の無視などを実装。
  - 不正な環境変数（例: MONITOR_POLL_INTERVAL が数値でない等）に対するフォールバックと警告出力を追加。
- process_priority / cpu_affinity の例外ハンドリング強化
  - 権限不足や未サポート環境で失敗した場合に警告を出してスキップするように改善。 (src/kabusys/utils/process_priority.py)

### Removed
- （初回リリースのため該当なし）

### Security
- シークレット扱いの設定項目（J-Quants トークン、kabu API パスワード、LINE トークン等）は config_setup の対話画面でマスク表示されるように配慮。環境ファイル .env を Git にコミットしない旨をドキュメントに明記。 (src/kabusys/config_setup.py, src/kabusys/config.py)

---

注: 上記はコードの内容から推測して作成した変更履歴です。実際のコミット履歴や設計ノートに基づく公式 CHANGELOG と差分がある可能性があります。必要であれば、実際のコミットメッセージを反映した詳細な分割リリースノートを作成します。