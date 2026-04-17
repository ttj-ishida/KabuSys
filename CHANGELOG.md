# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠しています。  
バージョン番号はパッケージ内の __version__ に基づきます。

## [0.1.0] - 2026-04-17

Added
- 初期リリース: KabuSys の基本機能群を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、Paper Trading 用の別 SQLite DB（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と完全分離する。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag により安全に停止できる。
    - 起動時にプロセス優先度を "high" に設定 (utils.process_priority)。
    - 各種コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てと起動処理を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 監視は環境に依らず本番 sqlite_path を使用する（監視データの一貫性保持）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了、check_once() の例外をログに残して次回ポーリングへ継続。
- 設定管理
  - config.py: 環境変数 / .env 読み込みユーティリティと Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）により .env 自動読み込みを行う（.env → .env.local、OS環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - .env パーサは export プレフィックス、クォート値（バックスラッシュエスケープ対応）、インラインコメント処理など多くのケースをサポート。
    - 各種設定プロパティを提供（DB パス、LINE 設定、監視閾値、PAPER_FILL_MODE の検証など）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを提供。
    - 主要設定項目の対話入力、既存 .env の読み込み、保存テンプレートの生成をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番環境 (KABUSYS_ENV=live) 向けガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等重・スコア加重 (calc_equal_weights / calc_score_weights) を追加。スコアが全て 0 の場合は等重にフォールバックして警告を出力。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を追加。未知レジームはフォールバックで 1.0。
  - portfolio.position_sizing: 株数計算ロジックを追加。
    - risk_based / equal / score の割付方式に対応。
    - 単元株（lot_size）で丸め、max_position_pct や max_utilization に基づく上限、aggregate cap によるスケールダウン・端数処理を実装。
    - cost_buffer を考慮した保守的見積り。
- ユーティリティ
  - utils.process_priority: プラットフォーム差を吸収したプロセス優先度設定（Windows/Linux/Mac 対応）および CPU affinity 設定ユーティリティを追加。権限不足や未サポート環境では警告ログを出して安全にフォールバック。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB を用いたファクター計算モジュールを追加（momentum, volatility 等）。
    - MOMENTUM（1M/3M/6M リターン、MA200乖離）、ATR、20日平均売買代金、出来高変化率等を計算。
    - DuckDB の prices_daily テーブルのみを参照し、関数は純粋関数（副作用なし）として設計。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（デフォルト閾値をファイル先頭で定義）。
    - P95 計算や日付フィルタ（--from/--to）、DB パス上書き (--db) をサポート。

Changed
- .env 読み込みの挙動設計
  - OS 環境変数 > .env.local > .env の優先順位を明確化し、OS 環境変数は protected として上書きできないようにした。
- 設定検証（validate_config）
  - config/*.yaml の存在確認と（PyYAML があれば）パース検証を追加。見つからないファイルは警告。パースに失敗した場合はエラーとして報告。
- run_monitoring/run_execution
  - 起動時にプロセス優先度を最優先で設定するように変更（set_process_priority("high") を最初に呼び出す）。
  - run_monitoring は monitor の DB 初期化（init_monitoring_db）を確実に実行し、ループ内での例外を捕捉して次回ポーリングへ継続するように安全性を高めた。
  - run_execution は paper_trading モードで専用 DB を使用し、停止フラグ検知時の起動抑止や実行中の停止処理を強化。

Fixed
- MONITOR_POLL_INTERVAL の不正値ハンドリングを追加
  - 環境変数から取得した値が不正（数値化失敗、0 以下など）の場合にデフォルト（60秒）へフォールバックし、警告ログを出力するようにした。
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどを正しく処理するように改善。
- DB 初期化の冪等性確保
  - init_monitoring_db を起動フローに組み込み、監視用テーブルが存在することを保証（何度でも安全に呼べる）。

Security
- .env の扱いに関する注意点をドキュメント化（config_setup による生成時のヘッダ）。
  - .env を絶対にリポジトリにコミットしない旨を明記。

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- position_sizing の lot_size や price フォールバックは現状グローバル固定や price=0 の場合の簡易スキップにとどまる。将来的に銘柄別 lot_size や価格フォールバック（前日終値等）の導入を検討。
- process_priority や cpu_affinity の操作は権限に依存するため、権限不足時は警告ログを出して設定をスキップする挙動となる。
- research.factor_research は DuckDB の prices_daily / raw_financials に依存。データ不足銘柄は None を返す仕様。

---

今後のリリースでは、戦略実装部（signal generation / ExecutionEngine の細部）、バックテスト・分析機能、銘柄マスタ連携等の強化を予定しています。