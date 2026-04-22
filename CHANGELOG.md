CHANGELOG
=========

このプロジェクトは "Keep a Changelog" の方針に準拠して変更履歴を管理します。  
以下は、提供されたコードベースの内容から推測して作成した初回リリースと直近の変更の要約です。

Unreleased
----------
（作業中 / 将来の変更点をここに記載します）

v0.1.0
------
初回リリース（機能追加・基盤実装）

Added
- 基本パッケージ初期実装
  - パッケージバージョンを設定: __version__ = "0.1.0"
  - モジュールエクスポートの整理（portfolio, execution, monitoring 等）
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを実装
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を利用し、MockBrokerClient を使用して本番 DB と切り離し。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウン。
    - PID ファイル管理（data/execution.pid）およびデーモンスレッド実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検出でループを終了、例外発生時はログ出力して次サイクルへ。
    - Monitoring は環境に依らず production の sqlite_path（監視 DB）を使用する設計。
- 設定管理
  - config.py: .env 自動読み込み（.env → .env.local の順、OS 環境変数は保護）、環境変数の取得ユーティリティ（Settings クラス）。
    - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等の設定をサポート。
    - env 値検証（KABUSYS_ENV / LOG_LEVEL 等）。
- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新するツールを追加。
    - シークレットマスク表示、選択肢・デフォルト対応、保存の確認。
  - validate_config.py: 設定検証 CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML 確認）。
    - --strict オプションで警告を fail 扱いに可能。
- ロギング・プロセス周りユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティ
    - stdout 出力の StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして安全に動作。
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足や未対応 OS は警告ログでスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選択（同点タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 重み算出（スコア合計が 0 の場合は等分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear を定義、未知レジームは警告とともに 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割付方式を実装。単元株丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した安全マージン。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定（閾値はソース内定義）。
    - 日付フィルタのサポート、DB パスは引数/環境変数/デフォルトで解決。
- データ処理・リサーチ
  - research/factor_research.py: ファクター計算の枠組み（モメンタム等）を追加（DuckDB 接続想定）。一部実装が続く（ファイル末尾で途切れた形）。

Changed
- .env パーサーの強化（config.py）
  - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、コメント解釈をサポートし堅牢性を向上。
  - OS 環境変数を保護する protected オプションを導入し、自動ロード時に上書きを防止。
- ロギング設定
  - stdout を利用することでスケジュール系ジョブやリダイレクト環境での視認性を改善。
  - ログファイルは日次ローテーション・30 日保持をデフォルトに設定。
- プロセス起動時の初期化順序
  - 起動スクリプトはまずプロセス優先度を設定してからリソースや DB を初期化する流れに統一（高優先度を要求する処理向けに安定化）。

Fixed
- 環境変数に不正な MONITOR_POLL_INTERVAL を与えた場合にクラッシュしないようフォールバック処理を実装（run_monitoring.py）。
- DB 初期化の冪等化（init_monitoring_db を呼ぶことで監視テーブルが存在することを保証）。
- Paper Trading と本番 DB の完全分離を明確化（run_execution.py で PAPER_TRADING_SQLITE_PATH を優先）。

Security
- .env ファイル生成ウィザードでシークレット項目をマスク表示するなど、平文表示を抑制する配慮を追加。

Notes / Known limitations
- research/factor_research.py はファイル末尾で未完の実装が確認される（calc_momentum の途中）。追加実装が必要。
- 一部の機能（例: BrokerClientFactory, ExecutionEngine, SystemMonitor, init_monitoring_db 等）はここに含まれるスクリプトから参照されるが、実装詳細は本差分に含まれていない（別モジュールに委譲）。実際の挙動はそれらの実装に依存する。
- process_priority の設定は権限（Linux の nice 値、Windows の優先度変更権限）に依存し、失敗時はログでスキップされる挙動。

今後の予定（推測）
- research モジュールのファクター算出処理完了
- 実行エンジン／ブローカー連携のテスト補強（特にペーパートレードの挙動検証）
- config によるさらなるバリデーション強化・サンプル config 生成スクリプトの整備

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリース履歴や日付はリポジトリの git 履歴／リリースノートに合わせて調整してください。