# Keep a Changelog — KabuSys

すべての変更は Keep a Changelog の形式に従って記載しています。  
Semantic Versioning（semver）を目安に運用してください。

なお、以下は提示されたソースコードから機能追加・修正点を推測して作成した変更履歴です。

## [Unreleased]

### Added
- 新規プロジェクト初期実装を追加（バージョン 0.1.0 相当の機能群を含む）。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。  
    - Broker クライアント生成（BrokerClientFactory）・OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。  
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag により安全に停止可能。PID ファイルを書き込む仕組みを搭載。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は設定にかかわらず本番用 sqlite_path を使用する仕様（意図的な分離）。

- 環境設定・ロード
  - config.py: .env / .env.local の自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）。  
    - 行パーサーは `export KEY=val`／クォート文字列／インラインコメント等に対応。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止をサポート。  
    - 各種設定プロパティを提供（DB パス、Paper Trading 設定、監視閾値、ログレベル等）。  
    - PAPER_FILL_MODE のバリデーション（有効値: instant|partial|never|reject）を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights（スコアが全て 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップし未知のレジームは警告してフォールバック）。
  - portfolio.position_sizing: 株数計算 calc_position_sizes を実装。  
    - risk_based / equal / score の配分方式に対応。単元株（lot_size）丸め、単銘柄上限・合算上限（aggregate cap）を考慮したスケーリング、手数料・スリッページを見越した cost_buffer を考慮。

- 研究（Research）モジュール
  - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB SQL＋Python で実装（ma200/ATR/avg turnover 等）。  
  - research.feature_exploration: 将来リターン算出（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク関数、ファクター統計サマリー（factor_summary）を実装。  
  - research.__init__: 外部に公開する API を整理（zscore_normalize を data.stats から再公開）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - コマンドライン引数: --from / --to / --db。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。  
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を行う（閾値はスクリプト内定義）。  
    - テーブル欠如時の耐障害処理（sqlite3.OperationalError を捕捉して N/A を出力）を実装。

- AI ニュース NLP（実験的）
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。  
    - バッチサイズ、トークン肥大化対策、429/5xx 等に対する指数バックオフリトライ、結果バリデーション、±1.0 でのクリッピング、部分更新（対象コードのみ DELETE→INSERT）等の設計を含む。  
    - （注）提示ソースではファイル末尾が途中で切れており一部実装が継続している可能性あり（後述の既知の制限参照）。

- ユーティリティ
  - utils.process_priority: set_process_priority（Windows / POSIX を抽象化してプロセス優先度を設定）を実装。psutil の権限エラー等は警告してフォールバック。  
  - utils.process_priority: set_cpu_affinity を追加し、最初の N コアにプロセスをピン留め可能（引数チェック・権限エラーは警告でスキップ）。

### Changed
- なし（このリリースは初期機能の追加が中心のため「追加」中心の記載）。

### Fixed
- 環境ファイルの読み込みで発生しうる文字列・コメントのパース不具合を考慮した堅牢化を実装（_parse_env_line）。  
- paper_verification_report: P95（パーセンタイル）計算・欠損データに対する安全処理を実装。

### Security
- なし

## [0.1.0] - 2026-04-17

- 初期公開リリース。上記「Added」に記載の通り、実行/監視/ポートフォリオ構築/リサーチ/ツール/AI ニューススコアリング等のコア機能を含む。

---

既知の制限・TODO
- ai/news_nlp.py: 提示されたソースが途中で切れており（ファイル末尾が不完全）完全動作を確認できない箇所があります。OpenAI 連携ロジックは概ね実装方針があるものの、実運用前に完全なエンドツーエンドのテストおよびエラーパスの確認が必要です。
- portfolio.position_sizing: lot_size は現在グローバルで共通の想定（例: 100）。将来的には銘柄別単元マスタを受け取る拡張（lot_map）を検討する旨の TODO コメントあり。
- apply_sector_cap: price_map に価格欠損（0.0）がある場合、エクスポージャーが過少見積りされる可能性がある旨の注記。前日終値等のフォールバック導入を検討。
- process_priority / set_cpu_affinity: OS 権限や環境によって設定が無視される場合がある。アクセス権限がない場合は警告を出してスキップする設計。
- run_monitoring における「監視は常に本番 sqlite_path を使用」する仕様は意図的に実装されていますが、テスト目的やデバッグ時は注意が必要。

リリースに関する問い合わせ・不明点はソースコメントや該当ファイル内の docstring を参照してください。