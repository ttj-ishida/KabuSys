# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、以下の変更点は提供されたコードベースから推測して記載しています（実装/設計意図に基づく要約）。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 初期リリース: KabuSys 自動売買・リサーチ基盤を追加。
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB（data/paper_trading.db）に切り分け、MockBroker を利用可能にする。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）で安全に終了する仕組みを実装。
- 設定管理
  - config.py: .env/.env.local の自動読み込み、堅牢な .env パーサ、環境変数の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）、デフォルトパス（DUCKDB_PATH、SQLITE_PATH 等）を提供する Settings クラスを追加。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio_builder.py: シグナルの候補選択（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing.py: 銘柄ごとの発注株数算出（risk_based / equal / score）、単元（lot）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
  - portfolio パッケージのエクスポートを整備。
- 研究（Research）モジュール
  - research.factor_research: Momentum、Volatility、Value などのファクター計算を DuckDB を用いて実装（prices_daily / raw_financials テーブル参照）。
  - research.feature_exploration: 将来リターン計算（複数ホライゾン）、IC（Spearman）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージの公開 API を整備（zscore_normalize を data.stats からインポート）。
- AI / ニュース解析
  - ai.news_nlp: raw_news から銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores へ書き込む処理を実装。バッチ処理（_BATCH_SIZE=20）、トークン肥大化対策（記事数・文字数制限）、リトライ（指数バックオフ）、レスポンスバリデーション、スコアクリッピング（±1.0）等を実装。ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を提供。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を算出し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH を参照。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows と POSIX 系の差分を吸収し、アクセス権限や未対応 OS の場合はワーニングで安全にスキップする実装を含む。

### 変更 (Changed)
- Execution / Monitoring のデフォルトログ設定を INFO に統一（logging.basicConfig(level=logging.INFO)）。
- run_execution と run_monitoring は起動時にプロセス優先度を "high" に設定するよう変更（set_process_priority 使用）。
- run_execution は paper_trading 環境時に DB を分離（settings.paper_sqlite_path）し、監視テーブル初期化を冪等に保証（init_monitoring_db を呼び出し）。
- .env 自動読み込みの挙動を明示（OS 環境 > .env.local > .env の優先順）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env パーサを強化
  - export KEY=val 形式に対応
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート
  - クォートなしの行でのインラインコメント扱いを改善（直前が空白/タブの場合に # 以降をコメントとみなす）
  - 読み込み失敗時に警告を発するように変更
- position_sizing のスケールダウンロジックを詳細化（端数処理で lot 単位の安定した復元ロジックを追加）。
- risk_adjustment.apply_sector_cap は "unknown" セクターを除外対象にしない（上限適用を免除する挙動）。
- research.calc_momentum / calc_volatility 等で DuckDB SQL を活用しウィンドウ処理を最小限のクエリで実行するよう最適化。

### 修正 (Fixed)
- run_monitoring のポーリング間隔取得関数で不正値対応を追加：
  - MONITOR_POLL_INTERVAL が 0 以下・非整数の場合にデフォルト（60 秒）へフォールバックしログ警告を出すよう改善。
- run_execution/run_monitoring といったプロセスで停止フラグ（data/stop_requested.flag）検知により安全にシャットダウンする処理を追加（graceful stop）。
- .env の自動上書き処理で OS 環境変数を保護（protected set を導入）、意図しない上書きを防止。
- ai.news_nlp にて API キー未設定時に明確な ValueError を返すよう明示。

### 既知の問題 / 注意点 (Known issues / Notes)
- ai.news_nlp は複雑なバッチ送信・レスポンス検証を実装しているが、外部 API（OpenAI）やネットワークの失敗時の部分的ロールバックや再実行の取り扱いは慎重に運用する必要があります。実運用前に API レート/コストやレスポンスフォーマットの安定性を確認してください。
- position_sizing の価格欠損（price が 0.0 または None）の場合、一部ロジックでエクスポージャーが過少評価される可能性がある旨を TODO コメントで指摘しているため、将来的にフォールバック価格の導入を検討してください。
- research / factor 計算は prices_daily / raw_financials のデータ品質に依存します。欠損データや不正値による Null 伝播を考慮して DB 側の整合性確認を推奨します。
- .env 自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使用します。配布パッケージ化後やルート検出できない場合は自動ロードがスキップされます。

### セキュリティ (Security)
- OpenAI API キーや各種シークレットは環境変数依存となっています。キー管理には十分注意してください（.env の管理・アクセス権の適切化を推奨）。

---

今後の予定（候補）
- tests の追加（ユニットテスト・統合テスト）
- エラーメトリクス収集 / retry の詳細設定を外部化
- 各種設定のドキュメント整備（PortfolioConstruction.md / StrategyModel.md 等へのリンク）
- 銘柄別単元サイズや手数料モデルの拡張対応

（以上）