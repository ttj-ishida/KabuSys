# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回公開リリース

### 追加
- 全体
  - プロジェクト初期版を追加。パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - DuckDB / SQLite を利用したデータ処理基盤を実装。設定は環境変数で指定可能（Settings クラス）。
- 実行・監視関連
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全分離する仕組みをサポート。
    - ExecutionEngine の組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）を行い、別スレッドでセッションを実行。停止フラグ（data/stop_requested.flag）検知で安全に停止する。
    - 起動時にプロセス優先度を "high" にセットし、実行中は PID ファイルを扱う（data/execution.pid）。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正値・0 以下はデフォルトにフォールバックして警告を出力。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用して記録する（監視 DB の初期化も行う）。
    - 停止フラグを検知してループを終了。check_once() 実行中の例外はログに記録して次回ポーリングに影響を与えない。
- 設定・運用ツール
  - 環境設定管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml ベース）。読み込み順は OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パース機能はクォート・エスケープ・コメント（インライン含む）の取り扱いに対応。既存 OS の環境変数を保護するためのオプションも提供。
    - Settings クラスによりアプリケーション設定を一元化（DB パス、API トークン、Paper Trading 関連、監視閾値、ログレベル、環境判定ユーティリティ等）。
    - PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を作成・更新。秘密値はマスク表示。生成テンプレートを .env に書き出す機能を提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV の値、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML が利用可能な場合）を検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch の自動クリア設定など）を実装。
    - --strict オプションで警告を FAIL として扱うモードを提供。
- 監査・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を行う。
    - CLI オプションで期間指定（--from / --to）と DB パス指定（--db）。PAPER_TRADING_SQLITE_PATH 環境変数を使用可能。
    - 基準値（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）に基づく判定を実行。
    - テーブルが存在しない場合の安全なフォールバック（OperationalError を捕捉して N/A 扱い）。
- ポートフォリオ・ポジション関連（純粋関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークで候補抽出。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を基にセクター別エクスポージャを計算し、max_sector_pct 超過セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: market regime に応じた投下倍率（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告の上 1.0 にフォールバック。
  - 株数算出・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method により target shares を算出（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、ポートフォリオ全体投資上限（max_utilization）を考慮。
    - aggregate cap オーバー時はスケールダウンして再割当（小数端数は lot 単位で残差配分）。手数料・スリッページを想定した cost_buffer をサポート。
    - 価格欠損時のスキップやデバッグログを実装。
- リサーチ（factor 計算）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials から Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対 ATR）、流動性指標等を計算する機能を実装（営業日ベースでのウィンドウ計算）。
    - 欠損データに対する安全な None 返却や結果のログ出力を行う設計。
- ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX の差分を吸収して set_process_priority(level) を提供。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアにピン留め（未指定は無処理）。エラー時は警告で続行。
  - パッケージ内での utils / tools / portfolio のエクスポート定義を整備。

### 変更
- なし（初回リリースのため新規追加中心）

### 修正
- 例外処理と入力検証を強化
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバックとログ出力を追加（監視ループの安定性向上）。
  - process_priority の権限不足や未実装 API 呼び出し時に警告のみを出して起動を継続するように変更。
  - Paper レポートでテーブル欠損時に OperationalError を捕捉して安全に N/A 扱いするようにした。

### 注意・既知の問題
- position_sizing では価格が欠損（0.0）だとエクスポージャが過少見積もられ、セクター上限判定が外れる可能性がある（TODO コメントあり）。将来的に前日終値や取得原価でのフォールバックを検討。
- .env の自動読み込みはプロジェクトルート検出に依存する。配布後にルートが見つからない場合は自動ロードをスキップする。

### セキュリティ
- .env ファイルは生成ツールで作成されるが、.env を Git にコミットしない旨をテンプレートに明示。

----------

今後のリリースでは、Engine / Broker 実装の追加・テスト強化、各種エッジケースへの対処（価格フォールバック、マルチロット対応、銘柄別 lot_size の導入等）、およびドキュメント整備を予定しています。