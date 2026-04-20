Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

注: ここに記載した変更点は、提供されたコードベースの内容から推測してまとめたものです。

[Unreleased]
------------

- （現在のスニペット基づく推測のため未リリースの作業や TODO を記載）
  - research/factor_research.py の実装が途中で切れている箇所が存在します（ファイル末尾が不完全）。
  - 将来的に個別銘柄ごとの lot_size をサポートするための拡張（stocks マスタ等）が TODO コメントとして残されています。
  - position_sizing の price フォールバック（前日終値や取得原価）に関する注記あり。現状 price が欠損すると見積りが不正確になる可能性があります。

[0.1.0] - 2026-04-20
--------------------

Added
- 基本モジュール群を初版として追加
  - portfolio: 銘柄選定・配分・リスク調整・ポジションサイズ決定の純粋関数群を提供
    - portfolio_builder.py
      - select_candidates: スコア降順で候補を選択
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全0時は等配分へフォールバック）
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（sell 対象は除外可能、unknown セクターは上限不適用）
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは警告とフォールバック）
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") による株数算出、単元株丸め、aggregate cap によるスケールダウンや残差の lot 単位での配分
      - cost_buffer/lot_size 等のパラメータで手数料・スリッページや単元を考慮可能

- 実行 / 監視用エントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するためのスクリプト
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでの実行管理、停止フラグ検知（data/stop_requested.flag）を実装
    - 実行 PID を data/execution.pid に書き出す想定（pid_file 引数）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の設計
    - 停止フラグ（data/stop_requested.flag）を検知して安全に終了

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの .env / .env.local を読み込み、.env.local は上書き）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）
    - .env の行パーサ実装: export プレフィックス、クォート、エスケープ、行内コメントの扱い等を考慮した堅牢な解析
    - Settings クラスで環境変数をラップし型変換・検証を提供（PAPER_FILL_MODE の検証、KABUSYS_ENV の有効値検証、パスの Path 化 等）
  - config_setup.py
    - 対話式ウィザードで .env を生成／更新する CLI を提供（secret 項目のマスク表示等）
    - .env の既存読み込み、項目ごとの説明・選択肢表示、保存確認および .env 出力ロジックを実装
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML があればパースチェック、KABUSYS_ENV=live 時の追加ガード）
    - --strict オプションで警告も失敗扱いにできる

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定するユーティリティ
    - LOG_LEVEL / LOG_DIR の環境変数経由での解決、既存ハンドラのクリア、ディレクトリ作成失敗時のフォールバック対応
  - utils/process_priority.py
    - psutil を利用したプロセス優先度設定（Windows と POSIX の差分吸収）
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供
    - 権限不足や未サポート環境では警告を出して安全にスキップ

- 監視・モニタリング DB 初期化ユーティリティの呼び出し（init_monitoring_db）
  - run_execution/run_monitoring で監視用テーブルが存在することを保証する初期化処理を実行（冪等）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から集計して検証レポートを生成する CLI
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を算出
    - P95 計算ロジック、閾値定義（稼働率 99%、fill 90%、send 95%、P95 200ms）、Pass/Fail 出力を実装

- 研究用モジュール（未完含む）
  - research/factor_research.py（DuckDB を用いたファクター計算の設計）
    - Momentum / Value / Volatility / Liquidity 等の計算方針・定数を定義
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照する想定で設計
    - （ファイル一部未完）

Changed
- 初期リリースのため該当なし（ベース機能追加が中心）

Fixed
- 初期リリースのため該当なし

Notes / Known issues
- research/factor_research.py が途中で切れているため、ファクター計算の一部実装が未完です。
- position_sizing の価格欠損時の扱いに注意（現行では price が無い場合に当該銘柄をスキップし、セクターエクスポージャー計算も過少見積りになる可能性あり）。
- set_process_priority / set_cpu_affinity は実行環境の権限や OS に依存するため、権限不足時には警告ログが出力され正常にスキップされます。
- monitor は明示的に本番 sqlite_path を参照する設計であり、paper_trading 環境でも監視 DB が本番用に向かないか注意が必要（コードコメントに明示）。

References
- バージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

===============================================================================
今後の提案（開発向けメモ）
- research/factor_research.py の実装完了（DuckDB SQL 実装の追加、ユニットテスト）
- position_sizing の銘柄別 lot_size サポート・price フォールバック実装
- 監視および実行の統合テスト（paper_trading と live の DB 分離、stop/kill フラグの動作確認）
- ログ出力先に関する権限エラーの自動回復策（例: 権限不足時にデフォルトディレクトリに退避）