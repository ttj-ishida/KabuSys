# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。  
現在のリリース: 0.1.0（初回公開）

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys v0.1.0 を導入。
- 環境設定周り
  - Settings クラスを追加し、環境変数から各種設定を取得する統一インターフェースを提供。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env のパーサーを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - 必須/オプションの設定項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、LINE 通知設定 等）を Settings で公開。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH（ペーパートレード専用DB）の設定を追加。
  - 環境フラグ判定プロパティ（is_live / is_paper / is_dev）を追加。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。既存値の再利用、シークレットのマスク表示、保存確認を実装。
  - validate_config: .env と config/*.yaml の整合性検証 CLI を追加。必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、PyYAML がインストールされていれば YAML のパース検証を行う。--strict オプションで警告も失敗扱いにできる。
  - validate_config は本番時の安全ガード（LINE 通知設定 / KILL_FLAG_CLEAR_ON_START の警告）を含む。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH を使用可）。
    - BrokerClientFactory を通じたブローカークライアント切替、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。スレッドで実行し停止フラグをポーリングして安全に停止可能。
    - 停止・PID 管理用のファイルパス（data/execution.pid, data/stop_requested.flag）に対応。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番の sqlite_path を使用する仕様（意図的な挙動）。
    - DuckDB 接続、監視 DB 初期化、停止フラグ検出、例外時のログとポーリング継続を実装。
    - 起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築・リスク・ポジション管理（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選抜（同点時は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補除外ロジック。売却予定銘柄をエクスポージャー計算から除外。unknown セクターは上限適用除外。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear をサポート、未知は 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。lot_size（単元株）単位で丸め、1銘柄上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的見積り、残差処理による追加配分ロジックを実装。

- リサーチ（ファクター計算）
  - research/factor_research: DuckDB 接続を受けて各種ファクター（Momentum, Volatility, Liquidity, Value 等）を計算するモジュールを追加。以下の点を実装／想定：
    - mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）等の計算（データ不足時は None を返す）。
    - ATR / avg_turnover / volume_ratio 等のボラティリティ・流動性指標を計算。
    - DuckDB SQL を活用したウィンドウ関数利用の実装。
    - 研究用途の純粋関数設計（外部 API にはアクセスしない）。

- ユーティリティ
  - utils/process_priority:
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）を吸収して現在プロセスの優先度を設定。psutil を利用。未対応 OS は警告でスキップ。権限不足等の際は警告を出して安全にフォールバック。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めする機能（optional）。
  - utils パッケージ構成を追加。

- 監視 / 検証ツール
  - tools/paper_verification_report:
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH または --db）から検証レポートを生成する CLI を追加。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計・表示。
    - デフォルトの合否基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms 等）を定義し、PASS/FAIL を判定。
    - P95 計算、日付フィルタ（--from/--to）に対応。DB が欠けているテーブルやデータ不足時は N/A を表示。

- データベース関連
  - monitoring_db の初期化呼び出しを各起動スクリプトで冪等に実行（監視テーブルの有無を保証）。
  - DuckDB と SQLite の併用設計（分析用に DuckDB、監視/履歴に SQLite を利用）。

### 変更
- なし（初回リリースのため該当なし）

### 修正
- なし（初回リリースのため該当なし）

### 既知の注意事項 / マイグレーションノート
- run_monitoring は「環境に関わらず本番 sqlite_path を使用する」挙動に注意してください。本番監視を意図しているための設計です。テスト環境で監視データを分離したい場合は sqlite_path を明示的に上書きしてください。
- process priority / CPU affinity の設定はプラットフォーム依存かつ権限を必要とします。権限不足時は警告が出て処理は続行されますが、期待どおりの優先度にならない可能性があります。
- config/*.yaml のパース検証は PyYAML インストール時のみ実行されます。PyYAML がない場合は警告を出してスキップします。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単元対応を想定した拡張ポイントがあります（TODO コメントあり）。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- paper_trading 用 DB と本番 DB は分離して設計されていますが、設定ミスで上書きしないよう .env の内容を validate_config で事前確認することを推奨します。

### セキュリティ
- なし（初回リリースにおける特別なセキュリティ修正は含まれていません）

---

今後の予定（例）
- Strategy / Execution コンポーネントの詳細な単体テスト追加
- 銘柄別 lot_size 対応、手数料・スリッページの精緻化
- monitoring のアラート通知（LINE）統合の強化
- DuckDB を用いた定期バッチ処理の CLI 化

もし特定のファイルや機能について、より詳細な変更ログや開発履歴（コミット単位の差分）を希望される場合は教えてください。コードの差分やコミットメッセージがあると、より厳密な CHANGELOG を作成できます。