# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しており、リポジトリ内のコードを元に変更点を推測して作成しています（明示的なコミット履歴ではなく、コードの内容から導出した要約です）。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期実装
  - パッケージのバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージエクスポート: data, strategy, execution, monitoring モジュールをエクスポート。

- 環境設定・管理
  - .env 自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env パーサーを実装（シングル/ダブルクォート、export 形式、インラインコメントの取り扱いをサポート）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - Settings クラスを実装し、環境変数の取得とバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。
  - 環境設定ウィザード CLI (`kabusys.config_setup`) を実装:
    - 対話形式で .env を作成/更新する機能（シークレットマスク表示、デフォルト値、選択肢サポート）。
    - `.env` ファイルテンプレート出力と保存機能。
    - .env は Git にコミットしないよう注記。

- 設定検証ツール
  - `kabusys.validate_config` CLI を実装:
    - 必須環境変数チェック、KABUSYS_ENV の値検証、LOG_LEVEL 検証、DB パス親ディレクトリチェック、config/*.yaml 存在・パース検証（PyYAML 任意）等を実施。
    - --strict オプションで警告を失敗扱いにできる。

- 実行/監視ランナー
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を実装:
    - プロセス優先度を高く設定して起動（set_process_priority("high")）。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler 組み立て。
    - ExecutionEngine を別スレッドで実行し、data/execution.pid に PID を書き込むなどの PID 管理、data/stop_requested.flag による外部停止をサポート。
    - RiskManager のデフォルト RiskConfig を設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker や initial_portfolio_value = broker.get_available_cash() など）。
  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）を実装:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - stop フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt による終了処理、check_once() の例外キャッチでログ出力して継続。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保存）を設定。
    - ログレベル解決の優先順位（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして警告を出力。
    - stdout を使用する設計（cron/Task Scheduler のリダイレクトを考慮）。
  - `kabusys.utils.process_priority` を実装:
    - Windows と POSIX に対応したプロセス優先度設定（psutil 利用）。
    - CPU affinity を設定するユーティリティ（最初の N コアに固定）。
    - 権限不足や未対応 OS の場合は安全にスキップして警告を出力。

- ポートフォリオ構築関連（純関数群）
  - `kabusys.portfolio.portfolio_builder` を実装:
    - select_candidates: スコア降順・タイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で配分、スコア合計が 0 の場合は等金額配分へフォールバック（警告出力）。
  - `kabusys.portfolio.risk_adjustment` を実装:
    - apply_sector_cap: セクター集中制限。既存ポジションのセクター比率が上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - `kabusys.portfolio.position_sizing` を実装:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数決定ロジック。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate 上限（available_cash）、cost_buffer による保守的見積り、スケーリングと残差配分ロジックを実装。
    - 価格欠損・0 の場合はスキップしてログ出力。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を読み取り、システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を集計してレポートを出力。
    - 既定の合格基準を設定（稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms）。
    - 日付フィルタ (--from, --to)、--db オーバーライドをサポート。
    - データ不足やテーブル未存在時に N/A を扱う実装。

- 研究モジュール（着手）
  - `kabusys.research.factor_research` の初期実装（モメンタム、MA200、ATR、出来高系等の計算方針と定数を定義、DuckDB 接続を利用する設計）。実装は途中（ファイル末尾が切れているが基本設計を含む）。

### 変更 (Changed)
- なし（初回リリースとして新規実装が中心のため、互換性破壊に関する注記はありません）。

### 修正 (Fixed)
- なし（初回リリースのため明示的なバグ修正履歴はなし。ただし各モジュールでエラー時の安全確保（例外キャッチ、ログ出力、フォールバック）を実装）。

### 注意事項 / 設計上の備考
- 環境変数の重要性:
  - J-Quants のリフレッシュトークンや kabu API パスワード等は必須。Settings._require が未設定時に ValueError を発生させる。
  - PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のみ有効。無効値は例外。
- 本番/ペーパートレードの DB 分離:
  - 実行エンジンは KABUSYS_ENV によって paper_trading 用 DB を使用する（本番 DB と完全分離）。
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する（監視 DB を一元化）。
- ログとファイル出力:
  - ログはコンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
- プロセス制御:
  - 起動時にプロセス優先度を "high" に設定する呼び出しが含まれる。権限不足や未対応 OS の場合は警告してスキップするので、安全に運用可能。
- セキュリティ:
  - .env はシークレットを含むため Git にコミットしないことを README / .env テンプレートで明記。
- 未実装 / 改善余地:
  - factor_research モジュールは計算関数の実装が途中（ファイル終端で切れている）。今後、DuckDB のクエリを用いた完全実装が想定される。
  - position_sizing の price 欠損時の扱いに注記（将来的に前日終値等のフォールバックを採用する可能性あり）。
  - ログや DB のパスに関する細かい挙動は実運用環境での検証が必要。

---

この CHANGELOG はコードから推測して作成しています。追加でコミット履歴やリリース日付、著者情報などを反映したい場合は実際の Git ログを提供してください。