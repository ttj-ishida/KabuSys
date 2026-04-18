# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/）に準拠します。

現在のバージョン: 0.1.0 — 初期リリース（初回公開）

## [0.1.0] - 2026-04-18
初期リリース。KabuSys のコア機能群を提供します。主な追加点は以下の通りです。

### 追加
- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番用の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知、例外時のログ出力、KeyboardInterrupt ハンドリングを実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、ペーパートレード専用 DB（data/paper_trading.db または環境変数で指定）に記録することで本番 DB と分離。
    - プロセス優先度を高く設定、停止フラグ検知による安全停止、エンジンのスレッド実行制御を実装。
    - 実行 PID 管理用ファイル path（data/execution.pid）に対応。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env パーサーを実装（export プレフィックス、クォート値、エスケープ、インラインコメントの取り扱いに対応）。
    - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API、DBパス、PaperTrading 設定、監視閾値等）をプロパティ経由で取得できるようにした。
    - Paper trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）を明確化。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

- 設定支援ツール / 検証
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - シークレット値はマスク表示、選択肢・デフォルト・説明付きの入力プロンプトを実装。
    - .env の読み取り/書き込みロジックを実装（既存値の再利用やキャンセル時の挙動を明確化）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース検証（PyYAML がある場合）などを実行。
    - `--strict` オプションで警告を失敗扱いにするモードを追加。
    - 本番環境向けの追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START 設定など）を実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 `setup_logging()` を追加（StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテート／30日保持）。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみ継続する堅牢性を実装。
    - 環境変数 `LOG_LEVEL`, `LOG_DIR` を優先する解決順を実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定 `set_process_priority()` を追加（Windows / POSIX に対応）。
    - CPU affinity を設定する `set_cpu_affinity()` を追加（psutil を利用、利用不可時は警告でスキップ）。
    - 権限不足等の想定外エラーに対する安全なフォールバックを実装。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等ウェイト（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存ポジション・現在価格を使ってセクターエクスポージャーを計算し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマップ、未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分メソッド（risk_based / equal / score）に対応したポジションサイズ計算を追加。
    - 単元株（lot_size）丸め、1銘柄上限・投下資金上限・コストバッファの考慮、aggregate cap 超過時のスケーリング（端数再配分アルゴリズム）を実装。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95 など）を集計し、PASS/FAIL 判定を行うレポート生成 CLI を追加。
    - デフォルト DB パスは data/paper_trading.db、環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で上書き可能。
    - 判定閾値（稼働率99%、成立率90% 等）を定義しており、結果を分かりやすくテキスト出力する。

- Research（解析）モジュール（着手）
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の設計方針と計算用定数を実装）。DuckDB を用いた価格・財務データ参照による計算を想定。
    - 実装は途中（ファイル末尾が未完）だが、設計と一部関数の骨格を含む。

- パッケージ情報
  - __init__.py によりパッケージバージョンを 0.1.0 に設定。

### 変更
- なし（初回リリースのため既存からの変更はありません）。

### 修正
- なし（初回リリース）。

### 注意事項 / 既知の制約
- run_monitoring は常に Settings.sqlite_path（本番用）を使用するため、開発環境で監視 DB を切り替える必要がある場合は Settings の環境変数を調整してください。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます（配布後 / pip install 後の挙動を想定）。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存して動作しない場合があり、失敗時は警告を出してスキップします。
- research/factor_research.py は未完の部分があります（今後の追加実装予定）。

### 将来の計画（例）
- factor_research の完全実装（全ファクターの計算と単体テストの追加）。
- ExecutionEngine / BrokerClient 周りのテストおよび Mock の整備。
- CI/CD での設定検証（validate_config の自動実行）やパッケージング向けの改善。
- 単体テスト、型チェック、ドキュメント整備の強化。

---

変更履歴に記載されていない細かな実装詳細や内部 API についてはソースコードを参照してください。リリースに関する質問や追加で必要なドキュメントがあればお知らせください。