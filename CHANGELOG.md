# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 全体
  - 初回リリース。パッケージ名: KabuSys（日本株自動売買システム）。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）検出時に安全に停止。
    - 起動時にモニタリングテーブルの存在を保証するため init_monitoring_db を呼び出す。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）でループを終了。
    - 例外時は logger.exception を出して次のポーリングまで継続。

- 設定管理
  - config.py: 環境変数・設定取得モジュールを追加。
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml 基準）。読み込み順は OS 環境 > .env.local > .env。自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパースでシングル/ダブルクォート、バックスラッシュエスケープ、export KEY=... 形式、コメント扱いルール等に対応。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、Paper Trading 用設定、監視閾値、環境判定等）をプロパティとして取得可能。各プロパティは妥当性チェックやデフォルトを備える（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の検証、LOG_LEVEL の検証など）。
    - settings インスタンスをモジュールレベルで用意。

  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 各設定項目の説明・選択肢・デフォルトを提示し、既存 .env を読み込んで Enter で再利用可能。最終確認後に .env を生成・上書きする。
    - 出力時に機密項目はマスク表示。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があれば YAML パースによる検証を実施。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告も失敗とみなすモードを提供。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーへ設定。
    - ログレベル/ログディレクトリは引数 > 環境変数 > デフォルト の優先順で決定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS（サポート済み POSIX）を抽象化して優先度を設定（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（オプション）。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を返す。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄のスコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合にそのセクターの新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム ("bull", "neutral", "bear") に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック（警告出力）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算を実装。
      - risk_based: 許容リスク率、stop_loss_pct に基づく単銘柄目標株数の計算。
      - equal/score: 各銘柄の重みに基づき割当を計算。
      - lot_size（単元株）に合わせて丸め、単銘柄上限（max_position_pct）を考慮。
      - aggregate cap を実装し、利用可能現金を超える場合はスケールダウンして再分配（端数は lot_size 単位で remainder に基づいて追加配分）。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

- リサーチ（ファクター計算）
  - research/factor_research.py: Momentum 等のファクター計算機能を追加（DuckDB 接続経由で prices_daily / raw_financials を参照する設計）。1M/3M/6M リターン、200日移動平均乖離率、ATR、出来高指標等を計算する方針を実装。設計注記・定数を定義（計算期間やスキャンバッファなど）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB パスを指定可能。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、定義済み閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を用いて PASS/FAIL を判定。
    - P95 計算、各種 NULL/データ欠損時の N/A 表示をサポート。

- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db の呼び出しにより、起動時に監視用テーブルの存在を保証（冪等）。

### 変更 (Changed)
- なし（初回リリースのため変更履歴なし）

### 修正 (Fixed)
- なし（初回リリースのため修正履歴なし）

### 既知の制約・注意点 (Note / Known issues)
- config/_find_project_root は .git または pyproject.toml を基準にプロジェクトルートを探すため、配布後や特殊配置時は自動 .env 読み込みがスキップされる可能性がある。自動ロードを無効化する環境変数も提供。
- portfolio/risk_adjustment.apply_sector_cap の価格欠損（price が 0.0）の場合にエクスポージャーを過少見積りする可能性がある旨の TODO 注記あり（将来的に前日終値等によるフォールバックを検討）。
- position_sizing の lot_size は現状グローバル固定（将来は銘柄別 lot_map を想定する注記あり）。
- process_priority や set_cpu_affinity は権限不足や非対応 OS ではスキップされる設計で、該当状況では警告が出力される。
- monitoring はどの環境でも本番 sqlite_path を使用するため、実行時に意図せぬ DB 操作をしないよう注意が必要（設計上の仕様）。

### 開発メモ (For developers)
- run_monitoring/run_execution は起動時に優先度設定 -> DB 初期化 -> コンポーネント組み立て -> メインループの順で処理するため、初期化順が重要。ログ設定は各スクリプトの最初に setup_logging で行うこと。
- validate_config.py は CI/デプロイ前の設定チェックに利用可能（--strict オプションで警告も失敗扱いにできる）。

---

（今後の変更はこのファイルに追記してください）