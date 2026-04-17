CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」形式に準拠します。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- パッケージ初期リリース: kabusys バージョン 0.1.0 を追加。
  - パッケージ情報: src/kabusys/__init__.py にバージョンを定義。

- 実行用スクリプト:
  - run_execution.py: 実取引・ペーパートレード双方に対応する ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動制御を実装。
    - 停止制御用のフラグファイル(data/stop_requested.flag)と PID ファイル(data/execution.pid) による起動／停止ハンドリングを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化・記録。

- 設定関連:
  - config.py: 環境変数 / .env 自動読み込み機能（.env/.env.local）、.env パースロジック（export 形式、引用符とエスケープ、インラインコメント処理）を追加。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを実装し、主要設定（J-Quants / kabu API / DB パス / PID / KILL フラグ等）をプロパティとして提供。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実施。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
    - 各設定項目の説明、選択肢、シークレット入力、既存 .env の読み取り、保存テンプレート生成機能を提供。
    - .env に保存する際は保存確認・マスク表示を行う。生成テンプレートは Git へコミットしない旨を明記。

- 設定検証 CLI:
  - validate_config.py: .env および config/*.yaml を起動前に検証するツールを追加。
    - 必須 / 任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パス親ディレクトリ存在チェック、config YAML の存在および（PyYAML インストール時の）パース検証、本番環境時の追加ガードを実施。
    - --strict オプションで警告も失敗扱いにできる。

- 監視・ユーティリティ:
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。
    - Windows (psutil の PRIORITY_CLASS) と POSIX (nice 値) の差分を吸収。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足時は警告を出してスキップ。
  - run_* スクリプト内で起動時にプロセス優先度を "high" に設定する処理を追加。

- ポートフォリオ構築モジュール (純粋関数群):
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア順ソートと上位選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェックで新規候補の除外を実装（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数計算を実装。リスクベース計算、単元株丸め(lot_size)、max_position_pct/max_utilization、aggregate cap（available_cash に応じたスケーリング）、cost_buffer（手数料・スリッページ見積り）に対応。端数処理は残差に基づく lot 単位の再配分を行う。

- リサーチ:
  - research/factor_research.py:
    - DuckDB 接続を受け取って Momentum / Volatility 等のファクターを計算する関数を追加（calc_momentum, calc_volatility の実装）。prices_daily テーブルを参照し、MA200、1m/3m/6m リターン、ATR、出来高指標等を算出。データ不足時は None を返す設計。

- ツール:
  - tools/paper_verification_report.py:
    - ペーパートレード用検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を算出し PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ（--from / --to）対応、しきい値はスクリプト内で定義（稼働率 99%、成功率 90% など）。

### 変更 (Changed)
- 起動時の DB 初期化:
  - run_execution.py / run_monitoring.py 内で init_monitoring_db を呼び、監視テーブルが存在することを冪等的に保証するように変更（監視系テーブルの初期化を確実に）。

- 設定自動読み込みの優先順位:
  - config.py で OS 環境変数 > .env.local > .env の順に読み込む仕様を採用。OS 環境変数は保護され上書きされない。

### 修正 (Fixed)
- .env パーサーの堅牢化:
  - export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント判定ロジックを実装し、一般的な .env 形式のパターンに対応。
- ポーリングループの堅牢化:
  - run_monitoring.py で monitor.check_once() の例外を捕捉しログ出力して次のポーリングへ続行するようにして、監視ループの停止を回避。

### 注意事項 / 既知の制約 (Notes)
- Settings の一部プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと ValueError を送出します。validate_config.py を使って事前検証を推奨します。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ有効。無効値は例外を発生させます。
- apply_sector_cap のエクスポージャー計算は price が欠損（0.0）だと過少評価される可能性があり、将来的にフォールバック価格を導入する旨の TODO コメントあり。
- process_priority の設定は権限不足や未対応 OS の場合は警告を出してスキップします。
- tools/paper_verification_report の日付フィルタは UTC ISO8601 文字列に変換してクエリを行います。DB ファイルが存在しない場合はエラー出力。

### セキュリティ (Security)
- .env を生成するテンプレートに「絶対に Git にコミットしないこと」を明記。
- config_setup の出力ではシークレット値をマスク表示してユーザに注意喚起。

(今後の予定)
- stocks マスタに銘柄別の lot_size を持たせる拡張（position_sizing の TODO）。
- apply_sector_cap の価格フォールバック、より堅牢な価格欠損処理。
- Factor 計算・シグナル生成の追加ファクターや単体テストの整備。

--- 

この CHANGELOG はコードベースから推測して作成しています。追加のコミット履歴やリリースノートが存在する場合はそれに合わせて更新してください。