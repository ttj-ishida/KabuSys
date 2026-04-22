CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
（内容はコードベースから推測して作成しています。）

Unreleased
----------

- （なし）

0.1.0 - 2026-04-22
------------------

Added
- 全体
  - 初回公開相当の機能群を実装。
  - パッケージメタ情報としてバージョンを __version__ = "0.1.0" に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。PID ファイルを利用。
  - 監視（モニタリング）ループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視データは常に本番 DB 想定）。
    - 停止フラグ検知でループ終了。例外はログに記録して次ポーリングへ継続。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - 各種環境変数ラッパー（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定など）。
    - Paper Trading 関連設定（paper_fill_mode、paper_sqlite_path）、kill_flag 関連設定、環境検証（env/log_level の検証）を含む。
    - 自動 .env ロード機能を実装（プロジェクトルートの特定: .git または pyproject.toml を基準）。OS 環境変数は保護して上書きを制御可能。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

  - 対話式 .env 作成ウィザードを実装（src/kabusys/config_setup.py）。
    - 既存 .env 読み込み、値のマスク表示、選択肢／デフォルト提示、入力キャンセル対応、最終確認のうえ .env を出力。

  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険な値等に警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・同点時タイブレーク）
    - calc_equal_weights, calc_score_weights（スコア合計ゼロ時は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮し、セクター上限を越える候補を除外。unknown セクターは上限適用除外）
    - calc_regime_multiplier（regime に応じた投下資金乗数。未知レジームはフォールバックして警告）
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method="risk_based"/"equal"/"score" に対応
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer の考慮、残差に基づく追加配分ロジックを実装

- 研究（research）
  - ファクター計算モジュールの骨格を実装（src/kabusys/research/factor_research.py）。
    - モメンタム、MA200乖離、ATR、出来高系等の計算方針と定数が定義され、calc_momentum 等の関数を開始（実装途中）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを実装（src/kabusys/tools/paper_verification_report.py）。
    - DB から稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）・リスク却下数を集計し PASS/FAIL を判定する CLI。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数（無指定時 data/paper_trading.db）、--from / --to / --db オプション対応。
    - P95 計算実装、閾値定義（稼働率 99%、成立率 90% 等）。

- ロギング・ユーティリティ
  - 統一ログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - 既存ハンドラの二重登録防止（クリアして再設定）、ログレベル/ログディレクトリの解決順をサポート。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度ユーティリティ
  - set_process_priority / set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収して優先度設定。アクセス権限エラー時は警告してスキップ。
    - CPU affinity 固定をサポート（利用可能コア数より多い指定時の扱い、エラー時のフォールバック）。

Changed
- ログ出力は標準エラーではなく標準出力（stdout）に出す設計に統一（cron 等からのリダイレクトを想定）（src/kabusys/utils/logging_setup.py）。

Fixed
- .env パーサーの強化（src/kabusys/config.py）:
  - export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、行内コメントの扱い、クォートなし値での # コメント判定などに対応。
  - プロジェクトルート探索を __file__ から親ディレクトリへ辿って行うようにして、CWD に依存しない自動ロードを実現。
  - 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。

- run_monitoring.py:
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックと警告ログを追加して、time.sleep に渡す不正値による例外を回避。

- run_execution.py:
  - 起動時に停止フラグが既に立っている場合はエンジンを起動せず終了する安全策を追加。

Notes / Implementation details
- 設計思想として、発注系コード（ExecutionEngine 等）と分析系コード（DuckDB を使う research / portfolio）を分離し、ペーパートレード時には本番 DB と分離するよう配慮しています。
- 多くのモジュールは DB 接続（sqlite3 / duckdb）や外部クライアントを引数として受ける設計で、テスト容易性（純関数の採用や外部依存の注入）に配慮しています。
- 一部モジュール（research の calc_momentum など）は実装途中の箇所があるため、今後の追加実装・テストが必要です。

Acknowledgements / TODO
- README やドキュメント（PortfolioConstruction.md 等）の参照をコードコメントに残しています。今後ドキュメント化・自動生成・ユニットテスト整備を推奨します。
- strategy/research のユニットテスト、ExecutionEngine 周りの統合テスト、edge-case（価格欠損時のフォールバック等）のハンドリング強化が今後の課題です。