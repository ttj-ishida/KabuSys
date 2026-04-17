CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in
Semantic Versioning.

0.1.0 - 2026-04-17
------------------

Added
- 初期リリースとして以下の主要機能・モジュールを追加しました。
  - 環境設定・読み込み
    - kabusys.config
      - .env ファイル自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）
      - .env 解析の拡張（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの柔軟処理）
      - 環境変数必須チェック関数 _require と Settings クラスを提供
      - 代表的な設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL, 各種しきい値など
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート
  - 設定ウィザード & 検証 CLI
    - kabusys.config_setup
      - 対話式ウィザードで .env を初期作成 / 更新できる CLI（python -m kabusys.config_setup）
      - シークレット項目は表示をマスクして対話（Enter で既存値／デフォルト再利用）
      - .env 書き込みテンプレートには注意書き（Git にコミットしないこと）を含む
    - kabusys.validate_config
      - .env および config/*.yaml の存在・基本整合性チェックを行う CLI（python -m kabusys.validate_config）
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、PyYAML があれば YAML パース検証、KABUSYS_ENV=live 向けの追加ガード
      - --strict モードで警告も FAIL 扱いに可能
  - 実行系 / 監視系起動スクリプト
    - run_execution.py
      - ExecutionEngine の起動スクリプト
      - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離
      - BrokerClientFactory 経由でブローカークライアントを生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を別スレッドで実行
      - data/stop_requested.flag による外部停止フラグ対応、data/execution.pid 書き込み対応
      - RiskManager のデフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト
      - 環境にかかわらず監視は本番 sqlite_path を使用（監視データは運用と共有）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
      - data/stop_requested.flag による停止検知
  - モジュール: portfolio（ポートフォリオ構築）
    - kabusys.portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順＋タイブレークで選抜
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコアが 0 の場合は等配分へフォールバック）
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限（既存保有を元にブロックセクターを作成、unknown セクターは適用除外）
      - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear を定義、未知は 1.0 でフォールバック）
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出
      - 単元丸め（lot_size、デフォルト 100）、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer を考慮した手当てロジック
      - スケールダウン時は fractional remainder を使い残余キャッシュを分配して再調整（再現性確保のため安定ソート）
  - ユーティリティ
    - kabusys.utils.process_priority
      - cross-platform にプロセス優先度を設定（Windows の PRIORITY_CLASS / POSIX の nice 値を吸収）
      - set_cpu_affinity で処理を最初の N コアに固定する機能を提供（未対応 OS や権限不足時は警告を出してスキップ）
  - 研究用 / 分析用
    - kabusys.research.factor_research
      - DuckDB を使ったファクター計算（momentum, volatility 等）
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離の算出（データ不足時は None）
      - calc_volatility: ATR, 相対 ATR, 20日平均売買代金、出来高比率等を計算
  - ツール
    - kabusys.tools.paper_verification_report
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定する基準値を実装（しきい値はファイル先頭で定義）
      - コマンドライン引数 --from / --to / --db に対応

Changed
- なし（初回公開）

Fixed
- .env パーサーの堅牢化
  - export KEY=val を許容、クォート文字内のエスケープ処理を行いインラインコメントを正しく無視する挙動を実装
  - 空行・コメント行の無視や無効行のスキップを明確化
- process_priority:
  - 未対応 OS や権限不足の場合に例外ではなく警告でスキップするようにし、呼び出し元が例外処理を意識しなくてよい設計に修正

Security
- .env テンプレートに「絶対に Git にコミットしないこと」を明示する注記を追加（config_setup の出力）
- config_setup はシークレット項目を対話時にマスク表示

Removed
- なし

Deprecated
- なし

Notes / Known limitations
- position_sizing.calc_position_sizes 内に将来の拡張メモ:
  - 銘柄ごとの lot_size をサポートする設計への拡張（現状は全銘柄共通の lot_size を想定）
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0 等）の場合エクスポージャーが過少評価される可能性あり。将来的に前日終値等でフォールバックすることを検討
- research.factor_research:
  - DuckDB 上のテーブル構成（prices_daily, raw_financials 等）に依存。テーブルが不足すると None を返す/例外が発生する箇所あり
- monitoring:
  - 監視は settings.env にかかわらず本番用 sqlite_path を参照する設計（監視データを環境間で共有しないことを意図する場合は構成を変更してください）

開発メモ
- エントリポイント:
  - 各 CLI は python -m kabusys.<module> で実行可能（例: python -m kabusys.validate_config）
- ロギング:
  - 起動スクリプトは基本 logging.basicConfig(level=logging.INFO) を利用して情報ログ出力
- バージョン:
  - パッケージバージョンは kabusys.__version__ = "0.1.0"

もし CHANGELOG に追記してほしい詳細（例: リリース日を別にする、個別ファイルの差分をもっと細かく記録する等）があれば教えてください。