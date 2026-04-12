# Changelog

すべての重要な変更はここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-12

初回公開リリース。KabuSys のコア機能群・ツール・ユーティリティを含む基盤実装を追加しました。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV によって paper_trading モードを切り替え、paper_trading では MockBrokerClient を使用して data/paper_trading.db に記録する（本番 DB と分離）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きに対応（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。

- 設定管理
  - config.py: 環境変数 / .env(.local) の自動ロード機能を導入。プロジェクトルートの検出 (.git / pyproject.toml) に基づき .env を読み込み、.env.local は上書き。OS の既存環境変数を保護する仕組み（protected）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化 をサポート。
  - Settings クラスを提供し、各種設定値（DB パス、API トークン、PID ファイル / kill フラグ、閾値、ログレベル、環境判定など）をプロパティ経由で取得可能にした。
  - 各設定値には入力検証を追加（例: KABUSYS_ENV の有効値チェック、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額／スコア加重配分（calc_equal_weights, calc_score_weights）。
  - portfolio.position_sizing: position sizing（calc_position_sizes）を実装。risk_based / equal / score の配分方式、単元株（lot_size）処理、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料・スリッページ見積り）対応。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市況レジームに応じた乗数（calc_regime_multiplier）を実装。

- 研究用モジュール（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算（mom_1m/3m/6m、ma200 乖離、ATR20、20日平均売買代金、PER/ROE 等）。DuckDB の SQL ウィンドウ関数を活用した実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランク変換、ファクターの統計サマリ（factor_summary）。外部ライブラリに依存せずに実装。

- ニュース NLP（AI スコアリング）
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores に書き込む処理を実装。バッチサイズ、文字数/記事数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証やスコアの ±1.0 クリップなどフェイルセーフ設計を導入。
  - calc_news_window により JST ベースのニュース収集ウィンドウ計算を提供（UTC 変換付き）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う。閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）は定数として定義。コマンドライン引数 --from / --to / --db をサポート。

- ユーティリティ
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。アクセス権限不足や未対応 OS では警告を出して安全にスキップ。
  - 共通初期化モジュール（パッケージ __init__、tools/__init__ など）。

### Changed
- パッケージ構成
  - 各モジュールの責務を明確化し、純粋関数群（portfolio / research）とサイドエフェクトを持つ起動スクリプト・エンジン側を分離。
- DB 接続ポリシー
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計に決定（監視データの一貫性確保）。
  - 実行エンジン（run_execution）は paper_trading 環境では paper_sqlite_path を使用して本番データと隔離。

### Fixed
- エッジケースと入力検証の強化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対してデフォルトにフォールバックし、警告を出すように修正（run_monitoring）。
  - .env パーシングの強化（クォート内のバックスラッシュエスケープ処理、コメント処理、export キーワードサポート、無効行スキップ）。
  - calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックするようにしてゼロ除算や意図しない動作を回避。
  - position_sizing のスケールダウン処理で lot 単位切り捨て／残余の再配分ロジックを実装して再現性を確保。
  - research.calc_momentum / calc_volatility / calc_value などでデータ不足時に None を返すようにして downstream の扱いを安定化。
  - feature_exploration.calc_ic: 有効レコードが 3 件未満の場合は None を返す（統計的に不安定な場合の保護）。
  - news_nlp: OpenAI API キー未指定時は明確な ValueError を送出。

### Security
- 環境変数ロード時に OS 環境変数を上書きしない既定動作（.env は既存 OS 環境変数を保護）を採用。必要時は .env.local による上書きを使用できる。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Notes / Known limitations
- ai.news_nlp の外部 API 呼び出しはネットワーク/レート制限に依存するため、完全な冪等性や部分失敗時のロールバックは限定的。部分成功時は影響のあるコードのみ書き換える戦略を採用して既存データ保護を優先しているが、運用時には API 制限を考慮したスケジューリングが必要。
- position_sizing は現状すべての銘柄で共通の lot_size（デフォルト 100）を前提としている。将来的に銘柄ごとの lot_size マスタを取り込む拡張が想定されている（TODO コメントあり）。
- run_monitoring / run_execution は psutil によるプロセス操作や PID ファイルを用いるため、実行環境の権限やプラットフォーム差異により一部機能が無効化される場合がある（警告ログで通知）。

---

著者注: この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、差分・コミットログ・リリース日など実データでの検証をお願いします。