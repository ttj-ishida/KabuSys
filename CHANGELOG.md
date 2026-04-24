CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリのコードから推測して自動生成した変更履歴です。日付・細部は推定を含みますので、リリース時に適宜調整してください。

Unreleased
---------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 基本パッケージ初期リリースを追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動・停止制御を実装。
    - 停止制御はプロジェクトルートの data/stop_requested.flag と data/execution.pid を使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境管理機能を追加。
  - config.py
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env の行パーサーで `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、各種環境変数をプロパティ経由で取得。値検証（有効値・必須チェック・数値変換）を組み込み。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）や監視閾値（CPU/MEMORY/DISK）などを整理。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - デフォルト値・選択肢・説明付きプロンプト、既存 .env の読み込み・保持、保存前の確認、.env ファイルの書き込みロジックを実装。

  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在とパース確認（PyYAML 未インストール時はスキップ）。
    - `--strict` モードで警告を失敗扱いにする機能。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）。

- ロギング・プロセス制御ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout） と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティ `setup_logging()`。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）をサポート。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定 `set_process_priority()`（high/normal/low）。
    - CPU affinity 設定 `set_cpu_affinity()` を提供。
    - psutil の権限不足や未実装 API を考慮した安全なフォールバックと警告出力。

- ポートフォリオ構築関連モジュールを追加（純粋関数群: DB 参照なし）。
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates()`（スコア降順、タイブレークは signal_rank）。
    - 等分配 `calc_equal_weights()`、スコア加重 `calc_score_weights()`（スコア合計が 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap()`（既存ポジションのセクター比率が閾値を超える場合に新規候補を除外。unknown セクターは無視）。
    - レジーム乗数 `calc_regime_multiplier()`（bull/neutral/bear に対応、未知はフォールバックと警告）。
  - portfolio/position_sizing.py
    - ポジションサイズ算出 `calc_position_sizes()`。
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた再配分ロジックを実装。

- Paper Trading 検証ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、レイテンシ指標（P95 など）、リスク却下数を集計してレポート出力。
    - デフォルトの合格基準 (稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms) を定義。
    - 日付フィルタ（--from / --to）、--db オプションをサポート。データ不足やテーブル未存在時のフォールバック処理を実装。

- 研究用ファクター計算モジュール（research/factor_research.py）の骨格を追加。
  - Momentum / Value / Volatility / Liquidity 計算方針、DuckDB 経由で prices_daily / raw_financials を参照する設計を記載（一部実装は途中）。

Changed
- なし（初期リリースとして新規追加が中心）。

Fixed
- なし（初期リリースとして新規追加が中心）。

Notes / 注意点
- .env 自動ロードはプロジェクトルート検出に依存します。配布後や特殊なデプロイ環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用して明示的に環境を設定してください。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用します（設計上の意図）。paper_trading 環境でも監視は本番 DB を参照するため注意が必要です。
- run_execution は paper_trading 環境時に paper_trading 用 DB を使用します。発注ログ等を本番 DB と分離することで検証が行いやすくなっています。
- process_priority / logging の操作は権限や OS に依存するため、実行環境によっては設定が無視される場合があります。ログディレクトリ作成等で権限エラーが発生した場合はコンソールログのみで継続します。

参考: 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（data/kabusys.duckdb）
- SQLITE_PATH（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）
- LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START

今後の提案（開発ロードマップに向けた推奨）
- research/factor_research.py の完全実装とユニットテストの追加。
- config の値取得・検証に関するユニットテストを整備（特に .env パーサーの corner case）。
- run_monitoring / run_execution の統合テスト（stop フラグ・PID ファイル等の動作確認）。
- position_sizing の lot_size を銘柄毎にサポートする拡張（stocks マスタへの lot 情報追加）。

--- 

（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のコミット履歴やリリース方針に基づいて修正・日付調整を行ってください。