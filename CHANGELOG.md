CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。
日付はリポジトリ内のコードから推測して付与しています。内容はソースコードのコメント・実装から推測した要点をまとめたものです。

Unreleased
----------
- 進行中 / 注意事項
  - research.factor_research.calc_momentum がソース中で途中で切れており（未完）、ファクター計算モジュールはまだ開発途上です。今後のリリースで実装完了およびテスト追加予定。
  - position_sizing, risk_adjustment 内に将来的な拡張（銘柄別 lot_size 管理、価格フォールバック等）の TODO コメントあり。これらは将来の改善対象。

0.1.0 - 2026-04-19
------------------
Added
- 実行用スクリプト
  - run_execution.py を追加。ExecutionEngine を起動し、以下を実現:
    - プロセス優先度を高に設定（set_process_priority）。
    - Paper Trading 用に本番 DB と分離された paper_trading 用 SQLite を使用可能（KABUSYS_ENV=paper_trading 時）。
    - BrokerClientFactory からブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/stop_requested.flag）で安全に停止、PID ファイル管理用のパスをサポート。
    - データ分析用に DuckDB を接続。

- 監視用スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループを実装:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計（監視データは paper_trading と分離しない挙動を意図）。
    - 停止フラグファイル検出によるループ終了、例外発生時にログ出力しつつ次ポーリングへ継続。

- 設定管理
  - config.py を導入。.env 自動ロード（.env / .env.local の優先読み込み）機能、プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を実装。
  - 強力な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、環境変数を型付きで取得。以下を含む:
    - J-Quants / kabu API 設定、LINE 通知設定
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - KABUSYS_ENV / LOG_LEVEL 等の検証メソッドと is_live / is_paper / is_dev プロパティ
    - 各種監視閾値（CPU/MEM/DISK）とファイルパス設定

- 設定ユーティリティ
  - config_setup.py を追加。対話式ウィザードで .env の初期作成・更新を支援:
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch など）。
    - 既存 .env 読み込み、シークレットマスク表示、保存前確認、.env ファイル生成ロジックを実装。
  - validate_config.py を追加。起動前の設定チェック CLI:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML があれば検証）、
      KABUSYS_ENV=live のガード（LINE 未設定警告や KILL_FLAG_CLEAR_ON_START の注意喚起）等を実行。
    - --strict オプションで警告を失敗として扱うモードを提供。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。全起動スクリプト共通のログ設定:
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - 既存ハンドラのクリア、ログディレクトリ作成のフォールバック（失敗したらコンソールのみ）等を実装。
  - utils/process_priority.py を追加。OS 抽象化したプロセス優先度設定 / CPU affinity 設定:
    - Windows / POSIX の差分を吸収し、set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン留めする機能。
    - 権限不足・未対応 OS に対する警告フォールバックを実装。

- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全スコア 0 の場合に等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター上限除外 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を追加。
    - apply_sector_cap は既存保有のセクター別時価を使って新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をマッピングし、未知レジームは警告とともに 1.0 でフォールバック。
  - portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score）。
    - lot_size（例: 100）単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。
    - スケールダウン時は端数の分配アルゴリズムを用い、再現性を保つためコードを二次キーに使用。

- 研究・ツール
  - research/factor_research.py を追加（ファクター計算の骨格実装）。Momentum / Value / Volatility / Liquidity 等の計算方針をコメントで明記し、DuckDB 経由の処理設計を採用。ただし calc_momentum は途中で未完。
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポート生成 CLI:
    - system_status / trade_logs / risk_logs から稼働率・成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定（閾値はソース内定数で定義）を出力。
    - P95 計算、日付フィルタ（--from / --to）、DB パスの切替（環境変数または --db）に対応。

- パッケージメタ
  - パッケージ初期化 __version__ = "0.1.0"、主要モジュールの __all__ を定義。

Changed
- 設計上の振る舞い（注意喚起）
  - 監視（run_monitoring）は KABUSYS_ENV に関係なく Settings.sqlite_path（監視用 production sqlite）を使用する実装となっているため、paper_trading 環境でも監視 DB は別扱いにならない点に注意（設計選択）。

Fixed
- 環境変数読み込みの堅牢化
  - .env の自動ロード実装で OS 環境変数を保護する protected セットを導入。.env.local は .env の上書きが可能だが OS 環境変数は上書きされない。

Known issues / Notes
- research.factor_research.calc_momentum が未完（コード切断）であるため、ファクター計算は現状で完全ではありません。今後のリリースで完成予定。
- position_sizing の価格欠損時の挙動や、risk_adjustment の price フォールバックについて TODO コメントあり。実運用前に追加のフォールバック・テストを推奨。
- 一部の機能は外部ライブラリ（psutil, PyYAML, duckdb）に依存しており、環境に応じたインストールが必要です。ログディレクトリ作成等で権限不足があるとファイルログ出力が無効化される可能性があります（フォールバックは有）。

その他
- 今後の改善候補:
  - research モジュールの単体テスト追加と calc_momentum の完成
  - 銘柄別 lot_size 管理（stocks マスタの導入）
  - .env 読み込みのユニットテスト強化
  - monitoring / execution のより詳細な監視メトリクス（例: DuckDB 側のログ連携）

ライセンスやセキュリティに関する修正・影響は本変更ログに含まれていません。必要に応じて追記してください。