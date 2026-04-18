CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠しています。  
日付はリポジトリ内のコードやコメントから推測したものを使用しています。

フォーマット:
- Added: 新機能
- Changed: 既存挙動の変更 / 改良
- Fixed: バグ修正（コードから推測して記載）
- Deprecated / Removed / Security: 該当があれば記載

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーション初期リリース
  - パッケージ情報: kabusys v0.1.0 を定義。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB とデータを分離する挙動を実装。
    - BrokerClientFactory により環境に応じたブローカークライアント（実際のブローカーまたはモック）を生成。
    - スレッドでエンジンを起動し、data/stop_requested.flag による外部停止制御、実行 PID ファイル管理（data/execution.pid）をサポート。
    - RiskManager, OrderManager, Reconciler, OrderRepository など発注系コンポーネントを組み立てる起点を提供。
    - リスク設定のデフォルト（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20）を導入。
  - run_monitoring.py: SystemMonitor をポーリングする監視プロセスの起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番用 sqlite_path を利用する仕様を明確化。
    - data/stop_requested.flag により監視ループを安全に停止可能。
- 環境設定・検証ツール
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* など）をサポートし、テンプレート形式で .env を書き出す。
    - 秘匿項目はマスク表示、オプション項目のスキップ等をサポート。
    - .env ファイル作成時に「Git にコミットしない」旨のヘッダを付与。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース検証（PyYAML がインストールされている場合）などを実施。
    - --strict オプションで警告も失敗扱いにできる。
- 設定読み込み・管理
  - config.py: Settings クラスを導入。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export 形式、クォート、有効なインラインコメント処理を考慮。
    - 各種プロパティを提供（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, cpu/memory/disk thresholds, paper_fill_mode の検証等）。
    - Settings インスタンス settings をモジュールレベルで用意。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログセットアップ関数を提供。
    - stdout 出力用 StreamHandler（stdout 指定）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログレベルやログディレクトリは引数 / 環境変数 / デフォルトの優先順位で決定。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS に合わせて nice 値や Windows の優先度クラスを設定。権限不足や未対応 OS は安全にスキップ。
    - set_cpu_affinity によりカレントプロセスの CPU コア制限が可能（未指定は全コア）。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 select_candidates（スコア降順、signal_rank によるタイブレーク）。
    - 等重み calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合等重みにフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター濃度上限に基づき新規候補を除外する機能を追加（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（既知以外はフォールバックで 1.0）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - risk_based: risk_pct と stop_loss_pct を用いた単銘柄ベースのサイズ計算。
      - equal/score: weight に基づく配分、max_position_pct / max_utilization 等の上限考慮。
      - 単元株(lot_size)丸め、cost_buffer を加味した保守的なコスト見積り、aggregate cap によるスケールダウン（残余キャッシュでの lot 単位再配分）を実装。
- 研究用ファクター計算
  - research/factor_research.py: DuckDB 接続を受け取り定量ファクター（Momentum, Value, Volatility, Liquidity 等）を計算するための基盤を追加（設計と定数が実装済み）。
- Paper Trading 検証レポート
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成ツールを追加。
    - 指標: 稼働率(uptime_pct), 注文成功率(fill_rate), 送信率(send_rate), リスク却下数, レイテンシ（avg/max/P95）。
    - P95 の計算、期間フィルタ（--from / --to）、DB パス解決（引数 > 環境変数 > デフォルト）を実装。
    - 合格基準（しきい値）を定義: 稼働率 >= 99.0%, fill_rate >= 90.0%, send_rate >= 95.0%, P95 <= 200 ms。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を複数箇所から呼び出すことで、監視テーブルが存在しない場合に作成（冪等処理）する仕組みを導入。

Changed
- ログ出力の統一化
  - 全起動スクリプトは setup_logging を呼び出して一貫したログ設定を行うように設計。
- .env の自動読み込み仕様
  - プロジェクトルートの検出ロジックを __file__ を起点に親ディレクトリを探索する方式へ変更し、CWD に依存しないよう改善。
  - OS 環境変数は保護（protected）し、.env.local は .env を上書きする優先順位で読み込む。
- 監視/実行プロセスの停止制御をファイルベース（data/stop_requested.flag）で統一。
- run_monitoring が監視用 DB に常に sqlite_path（本番パス）を使う挙動を明確化（環境に依存しない監視用データ格納）。

Fixed
- ログハンドラ二重登録の防止
  - setup_logging が既存ハンドラを flush/close してから削除 → 複数回初期化されても二重出力にならないように改善。
- .env 読み込み失敗時のフォールトトレランス
  - ファイルオープンに失敗した場合に warnings.warn を出し自動ロードを続行しない安全な挙動を実装。

Security
- .env ファイル作成時の注意文を追加（.env を絶対に Git にコミットしない旨）して、機密情報の誤コミットリスクを軽減。

Notes / Implementation details（コードから推測）
- 環境変数の妥当性チェックや警告は validate_config で手早く検出可能。production (KABUSYS_ENV=live) の場合に追加の警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を出す。
- process_priority.set_process_priority は権限不足や未対応 OS の場合に安全に警告を出してスキップするため、管理者権限がないデプロイ環境でも壊れにくい。
- portfolio/position_sizing の aggregate cap スケールダウンは、切り捨てによる端数分を再配分するアルゴリズムを持ち、lot_size 単位での再配分を行うため、実取引の単元制約に配慮している。
- Paper Trading 用 DB と本番監視 DB を明確に分離することで、テスト/検証環境での誤操作リスクを低減する設計。

既知の制約 / TODO（コード内コメントより推測）
- position_sizing の price が欠損（0.0）だとエクスポージャーが過小見積もられ、セクターキャップ回避につながる可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が存在。
- research/factor_research.py は本体が途中で切れている（コード抜粋の終端）ため、実装の続きを要確認。
- 一部機能（config/*.yaml 生成や詳細な Strategy / Engine 実装）は別スクリプト（scripts/generate_config.py 等）や他モジュールに依存する想定。

--- 

補足:
- 本 CHANGELOG は提供されたソースコードの内容から機能・意図を推測して作成しています。実際のリリースノートと差分がある場合は、差分を反映して更新してください。