# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本 CHANGELOG はリポジトリ内のソースコードを基に内容を推測して作成しています（自動生成ではなく手作業での要約です）。

## [0.1.0] - 2026-04-19 (初回公開)
最初の公開リリース。日本株自動売買システム「KabuSys」のコア CLI / ライブラリ機能を収録。

### 追加
- 全体
  - パッケージの初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 環境変数や .env ファイルを扱う Settings / 自動ロード機構を実装。
    - プロジェクトルートの自動検出（.git / pyproject.toml を基準）により、CWD に依存しない .env 自動読み込みを提供。
    - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 必須環境変数チェック用のヘルパーを提供（_require）。
  - 対話式環境設定ウィザード（config_setup）を追加。
    - .env の初期作成・更新を対話的に支援（シークレット入力、デフォルト、選択肢をサポート）。
  - 設定検証ツール（validate_config CLI）を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と簡易パース（PyYAML がある場合）等をチェック。
    - --strict オプションで警告を失敗扱いにするモードを提供。
  - ログ設定ユーティリティ（utils.logging_setup）を追加。
    - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーへ統一的に設定。
    - ログディレクトリの作成失敗やファイルハンドラ生成失敗時にはフォールバックしてコンソール出力のみで動作。
  - プロセス優先度／CPU affinity ユーティリティ（utils.process_priority）を追加。
    - Windows/Linux（および一部 POSIX）を透過的に扱い、"high"/"normal"/"low" の優先度設定を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（失敗時は警告を出してスキップ）。
  - 実行系 / 監視系起動スクリプトを追加
    - run_execution: ExecutionEngine 起動スクリプト
      - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
      - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading 時は MockBrokerClient 想定）。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全停止。
      - 起動時にプロセス優先度を "high" に設定。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
      - 監視は環境に関わらず本番の sqlite_path を使用する設計（監視 DB の初期化を保証）。
      - duckdb 接続サポート、停止フラグ監視、例外発生時のログ出力とループ継続。
      - 起動時にプロセス優先度を "high" に設定。
  - Execution / Monitoring 共通
    - 監視用 DB テーブルの初期化ヘルパー（monitoring.monitoring_db.init_monitoring_db）を起動時に実行し冪等性を確保。
    - 停止フラグ / PID ファイルの取り扱い（data/*.flag / data/*.pid）。
  - ポートフォリオ構築関連（pure function）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額/スコア加重（calc_equal_weights / calc_score_weights）。
      - calc_score_weights は全銘柄のスコアが 0 の場合に等金額配分へフォールバックして警告を出す。
    - portfolio.risk_adjustment: セクターキャップ適用（apply_sector_cap）、レジーム乗数計算（calc_regime_multiplier）。
      - セクター不明 ("unknown") の扱いや、レジームラベルに対するデフォルトフォールバックを実装。
    - portfolio.position_sizing: 発注株数計算（calc_position_sizes）
      - risk_based / equal / score の割当方式をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate キャップ（available_cash）に基づくスケーリング、コストバッファ(cost_buffer) を考慮。
      - 小数スケールでの残差処理（remainders）により追加配分を行い再現性を確保。
  - Paper Trading 検証レポート（tools.paper_verification_report）
    - paper_trading DB（デフォルト data/paper_trading.db）から各種指標を集計して PASS/FAIL 判定を行う CLI スクリプトを提供。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 など。
    - デフォルト閾値（稼働率 99%、成功率 90% 等）に基づく判定を実装。日付フィルタ（--from / --to）をサポート。
  - research.factor_research（骨格）
    - DuckDB を用いたファクター計算用モジュールを追加（モメンタム/ボラティリティ/バリュー等設計）。
    - calc_momentum の骨格と定数が含まれる（実装途中の箇所あり）。

### 変更
- 環境読み込みの優先順を確定
  - OS 環境変数 > .env.local > .env の順で読み込み。テスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- ログ設定
  - デフォルトで stdout に出力しつつ、logs/<app_name>.log に日次ローテーションでファイル出力（30 日保持）を行う。ログ作成失敗時はファイル出力をスキップして stdout のみで継続する。

### 修正（バグフィックス / 安全性）
- .env パーサーの堅牢化
  - export プレフィックス、引用符付き値のエスケープ、インラインコメントの扱い（クォートあり/なしでの差分）を正しく処理するように実装。
- 環境値のバリデーション強化
  - Settings.paper_fill_mode の入力検証（有効値のみ許容）。
  - Settings.env / log_level の許容値チェックを実装し不正値で例外を出すように。
- run_monitoring のポーリング間隔取得関数で 0 以下や不正フォーマットを安全に扱い、ログに警告を残してデフォルトへフォールバック。
- process_priority と CPU affinity の操作で権限不足や非対応環境時に例外を握り潰して警告を出すようにし、起動の妨げにならないよう改善。
- Logging setup でログディレクトリ作成に失敗した場合にも、明示的な警告を出してコンソールログのみで継続するように。

### 既知の問題 / 注意点
- research.factor_research.calc_momentum はファイル末尾で実装が途中（start_da で切れている）になっており、完全実装は今後の課題。
- portfolio.position_sizing 内の price 欠損（price == 0.0）に対するフォールバック処理は TODO コメントが残っている（将来的に前日終値などのフォールバックを検討）。
- 本バージョンでは一部機能（ExecutionEngine、BrokerClient 等）の詳細実装は別モジュールに依存しており、それらの挙動（特に本番ブローカーとのインタラクション）は統合テストでの検証が必要。
- Paper Trading と本番 DB の分離は行われているが、設定ミスにより本番 DB を参照する可能性があるため、KABUSYS_ENV の確認と validate_config の利用を推奨。

### セキュリティ
- API シークレット等は .env に保存される想定。config_setup の注意書きに従い .env は Git にコミットしないこと。

---

今後の予定（例）
- research.factor_research の完全実装（ファクター群の SQL 実装とユニットテスト）。
- ExecutionEngine / Broker クライアント周りの統合テスト追加。
- ログ・メトリクスのさらなる拡充（Prometheus / メトリクス出力等）。
- config/ YAML の雛形自動生成スクリプト強化。