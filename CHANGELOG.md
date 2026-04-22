# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
主な方針: 明確な機能追加、挙動（既定値）と重要な設計決定、潜在的な破壊的変更を記載します。

## [Unreleased]

（将来の変更はこちらに記載します）

---

## [0.1.0] - 2026-04-11

初回リリース。日本株向け自動売買フレームワーク「KabuSys」の基礎機能を収録。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。停止フラグ（data/stop_requested.flag）検知で安全に終了。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。デーモン化されたスレッドでエンジンを実行し、停止フラグで停止。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite（data/paper_trading.db 等）を使用して本番 DB と完全分離。
    - 起動時に PID ファイルを扱い、既存の停止フラグがある場合は起動を中止。

- 設定管理
  - config.py
    - 環境変数読み込みユーティリティ（.env 自動読み込み機能を提供）。
    - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行う。プロジェクトルート非特定時はスキップ。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境フラグ等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）、Paper Trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）等を実装。

- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期化・更新する CLI を追加。
    - J-Quants や kabu API など必須項目、ログ設定、Kill Switch 設定等を対話的に入力可能。
    - .env の既存値読み込み・マスク表示、保存確認を実装。

  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数、KABUSYS_ENV 値、DB パスの親ディレクトリ存在、config/*.yaml ファイル存在と YAML パース（PyYAML がインストール済みの場合）を検証。
    - --strict オプションで警告も失敗扱い（exit(1)）にできる。
    - live 環境向けの追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険な設定など）を実装。

- ロギングおよびプロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップ関数を追加。
    - ログレベルとログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収する実装。権限不足等は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群、DB非依存）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全銘柄スコアが 0.0 の場合に等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）による候補除外ロジック。既存保有・売却予定の銘柄を考慮。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を提供。未知レジームは警告出力で 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定ロジック、単元株（lot_size）丸め、aggregate cap（available_cash）に対するスケーリングと残差再配分アルゴリズムなどを実装。

- リサーチモジュール（骨格）
  - research/factor_research.py
    - DuckDB 接続を受け取り、モメンタム等ファクターを計算するための設計と一部実装を追加（モジュールの骨格）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポートを生成する CLI。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ指標（平均 / 最大 / P95）を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプションにより期間・DB パスを指定可能。

- DB 初期化ユーティリティ
  - monitoring/monitoring_db.init_monitoring_db を使用して監視テーブルの冪等初期化が行えるようにスクリプトから呼び出し。

- エクスポート
  - portfolio パッケージの __all__ を整備し、主要関数群をパッケージ外から利用可能にした。

### Changed
- 環境変数読み込みロジック
  - .env パースの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォート外のインラインコメントの取り扱い等を実装。
    - 空白やタブを利用した '#' のコメント判定を実装（より .env の一般的な記法に近づけた）。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env（.env.local は .env を上書きする目的で使用）。
  - protected 引数で OS 環境変数の上書きを回避。

- ログ出力先の統一
  - StreamHandler を stdout に向けるように変更（cron/task scheduler から stdout/stderr をまとめてリダイレクトする運用を想定）。

- スクリプトの DB 接続挙動
  - run_monitoring: 監視用は常に本番 sqlite_path を使用（環境に依らない）。
  - run_execution: paper_trading 環境時は paper_sqlite_path を使用して本番 DB とデータ分離。

- 安全性・頑健性
  - process_priority の権限不足や未サポート OS に対しては警告を出力して処理をスキップすることで起動失敗を防止。
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗も StreamHandler のみで継続するようにして可用性を高めた。

### Fixed
- 多くの CLI とユーティリティで例外ケースをハンドリング:
  - run_monitoring と run_execution において DB 接続のクローズを finally ブロックで確実に行うようにした。
  - paper_verification_report の各クエリは OperationalError をキャッチしてテーブル未存在時に安全に N/A を返すようにした。
  - ポートフォリオ関連で価格欠損（price が None や <=0）の場合はスキップして安全に動作するように改善。
  - calc_score_weights が全スコア 0 の場合に 0 除算や不正比率を出さないようフォールバック実装を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_TOKEN 等）は .env に保存される前提だが、config_setup で .env の Git コミットを避ける旨をコメントで明示（ユーザー側運用上の注意）。

---

注記:
- 本 CHANGELOG は提供されたコードベースから挙動を推測して作成しています。実際の変更履歴やリリース日付はリポジトリのコミット履歴に基づいて適宜調整してください。