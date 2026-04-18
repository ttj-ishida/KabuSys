# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
語釈: 「追加」は新機能、「変更」は既存挙動の変更、「修正」はバグ修正や堅牢化を示します。

なお、以下の変更内容はソースコード（src/ 以下）から推測してまとめたものです。

## [0.1.0] - 2026-04-18

### 追加
- 基本アプリケーション初期リリース
  - パッケージメタ情報（kabusys/__init__.py）にバージョン 0.1.0 を定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading モードをサポートし、paper_trading の場合は専用の SQLite（data/paper_trading.db, 環境変数で上書き可）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド起動と停止フラグ監視を実装。
    - プロセス PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番用 sqlite_path を使用する実装。

- 設定関連 CLI / ウィザード / 検証
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新するツールを追加。
    - J-Quants や kabuAPI、DBパス、ログレベル、Kill Switch 設定など主要項目を支援するプロンプトを提供。
    - 既存 .env の読み込み・値のマスク表示・保存確認を実装。
  - validate_config.py
    - .env および config/*.yaml の事前検証ツールを追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML があれば）などを実装。
    - --strict オプションで警告を FAIL（exit 1）として扱うモードを提供。

- 環境読み込み・設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml を基準に探索）。
    - 複数の .env ファイル読み込みルール（OS 環境 > .env.local > .env）と保護付き上書き機能を実装。
    - 行パーシングは export プレフィックス対応、クォート内バックスラッシュエスケープ対応、インラインコメント処理等をサポート。
    - Settings クラスでアプリケーション設定を集中管理（DB パス、紙トレードパス、閾値、PID/kill flag パス、env/log_level 判定等）。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を統一的に設定するユーティリティを追加。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップ）・既存ハンドラの安全なクリア処理・ログレベル解決ロジックを実装。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定と CPU affinity 設定関数を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、権限不足や未実装環境では警告を出して安全にフォールバック。

- ポートフォリオ構築・サイズ決定・リスク調整（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークに signal_rank）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター上限適用 apply_sector_cap（既存ポジションを基にセクターごとの時価比率を計算して新規候補を除外）。
    - 市場レジームに基づく乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはワーニングと 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - allocation_method に基づく株数計算 calc_position_sizes（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページの見積り）考慮、および残差処理による追加配分ロジックを実装。

- リサーチ（ファクター計算）基盤（初期実装）
  - research/factor_research.py（モジュール化・定数定義）
    - Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB から計算することを想定したモジュールを追加（関数 calc_momentum 等を含むが一部は実装途中）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - 閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）を定義。
    - 日付フィルタ、DB パス指定（--db / 環境変数）をサポート。

- 監視 DB 初期化補助
  - monitoring.monitoring_db.init_monitoring_db が起動時に呼ばれ、監視テーブルの存在を冪等に保証。

### 変更
- なし（初回リリース想定）

### 修正 / 堅牢化
- .env 読み込みの堅牢化
  - クォート処理、バックスラッシュエスケープ、インラインコメントの解釈などを実装し、より現実的な .env 記述に対応。

- ログ出力の安全化
  - ログディレクトリ作成に失敗した場合でもコンソールログが機能するようにフォールバックを用意。

- プロセス優先度設定の失敗耐性
  - 権限不足やプラットフォーム非対応時にワーニングを出して処理を継続する実装。

- Execution/Monitoring の停止フラグ処理
  - data/stop_requested.flag の存在検知で安全にループを抜ける／エンジン停止を行うように実装（Graceful shutdown）。

### 既知の制約 / 注意点
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用」する実装となっているため、意図的に監視 DB を環境別に分離したい場合は設定（SQLITE_PATH）や実装を変更する必要があります。
- position_sizing や risk_adjustment の一部注釈にある通り、価格データ欠損時のフォールバックロジック（前日終値や取得原価など）は未実装で将来の拡張が予定されています。
- research/factor_research.py はファクター計算の骨格を提供するが、完全実装（スキャン開始日などの細部実装）が残っている箇所があります。

---

今後のリリースでは、以下のような項目が想定されます（例示）:
- Strategy 実装（シグナル生成）とそのテスト
- ExecutionEngine の詳細実装とブローカーインターフェースの追加テストカバレッジ
- DuckDB を使ったファクター計算の完全実装と最適化
- CI / テストスイート、ドキュメントの拡充

もし特定ファイルや変更点について、より詳細な説明・分割したリリースノートが必要であれば対象箇所を指定してください。