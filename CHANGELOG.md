# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

現在のリリース履歴:

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基盤的な機能を実装しました。主な追加点と設計上の注意点は以下の通りです。

### Added
- 基本メタ情報
  - パッケージメタとしてバージョンを定義（__version__ = "0.1.0"）。

- 設定管理
  - Settings クラス（kabusys.config）を実装し、環境変数経由の設定取得を統一。
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - .env 読み込みルール:
    - 優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - 複数の意図したパースルール（export プレフィックス、クォートの扱い、インラインコメント判定等）に対応
  - 必須環境変数取得ヘルパー _require を提供（未設定時に明示的エラーを送出）。

- 設定ユーティリティ / CLI
  - 環境設定ウィザード（kabusys.config_setup）を追加。
    - 対話式で .env の初期作成・更新を支援。シークレットはマスク表示、デフォルト値・選択肢対応。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース（PyYAML がある場合）などをチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
    - live 環境向けのガードチェック（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング
  - 統一ロギングセットアップユーティリティ（kabusys.utils.logging_setup）を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR / 引数で挙動を制御可能。

- プロセス優先度 / CPU 制御
  - set_process_priority / set_cpu_affinity（kabusys.utils.process_priority）を実装。
    - Windows / POSIX（Linux/Mac/FreeBSD）の差異を吸収して優先度を設定。失敗時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。

- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離（MockBroker 客体想定）。
    - BrokerClientFactory 経由でブローカクライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。stop フラグファイル検出で安全停止。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値は broker.get_available_cash() を使用して作成。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは環境に依存しない設計）。
    - stop フラグファイル検知でループを終了。例外捕捉して次回ポーリングへ継続。

- データベース接続
  - sqlite3 と DuckDB の接続を利用（duckdb は分析用途に使用）。
  - 監視テーブル初期化ヘルパー init_monitoring_db を呼び出して冪等に監視用テーブルを保証。

- ポートフォリオ構築（純関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio_builder: select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
    - risk_adjustment: apply_sector_cap（既存保有を考慮したセクター集中回避。unknown セクターは上限対象外）、calc_regime_multiplier（regime に基づく投下資金乗数: bull=1.0, neutral=0.7, bear=0.3、未知は警告して 1.0）。
    - position_sizing: calc_position_sizes（allocation_method に応じて株数を算出）。
      - risk_based / equal / score に対応。
      - リスクベースでは stop_loss_pct, risk_pct を使用してベースシェア算出。
      - 1 銘柄上限（max_position_pct）・lot_size（単元）を考慮。
      - aggregate cap: 投資合計が available_cash を超える場合はスケーリングして lot_size 単位で端数調整（remainders により再配分）。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
      - 価格欠損時はスキップ（ログ出力）。

- 研究用ファクター計算基盤
  - kabusys.research.factor_research を追加（モメンタム、MA200乖離、ATR、ボリューム指標等を DuckDB の prices_daily 等から計算する方針）。
  - 設計では DuckDB 接続を受け、外部 API にはアクセスせずメモリ/SQL ベースで結果を返す（関数は (date, code) キーの辞書リストを返す想定）。
  - （実装途中の箇所あり：ファイル末尾が切れているが、方針と主要定数は定義済み）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - SQLite の paper_trading DB からシステム稼働率（system_status）、注文ログ（trade_logs）、リスクログ（risk_logs）を集計。
    - 指標: 稼働率 (uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ等を計算。
    - デフォルト閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）で PASS/FAIL を判定。
    - --from/--to/--db オプション対応。P95 は簡易実装（ソートして上位 95% 指数を取得）。

### Changed
- （初回リリースのため、過去の変更はありません）

### Fixed
- （初回リリースのため、過去の修正はありません）

### Removed
- （初回リリースのため、削除事項はありません）

### Security
- 環境変数のシークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存される想定だが、.env は絶対に Git にコミットしない旨を config_setup の出力で明示。

---

注意事項 / 既知の制約
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML など）に依存します。不足時は警告や機能縮退（例: YAML 検証スキップ、CPU affinity / priority 未設定）を行う設計です。
- price が欠損（0.0）だと position sizing / sector exposure の計算結果が過少見積りとなる可能性があり、将来的にフォールバック価格（前日終値等）を導入する予定です（TODO コメントあり）。
- factor_research モジュールは方針・定数は定義済みですが、ファイル末端が中断しているため完全実装は未確認です（実行前に確認ください）。
- monitor は環境にかかわらず production sqlite_path を参照するため、paper_trading と監視データを分離したい場合は適切なパス設定等で対応してください。

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- ブローカ・モックの詳細実装と paper_trading のさらに厳密な分離
- 銘柄別 lot_size の導入（stocks マスタに lot_size を持たせる拡張）

--- 

（この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートに反映する際は必要に応じて修正してください。）