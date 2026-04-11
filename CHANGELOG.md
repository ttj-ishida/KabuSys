# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。重要な機能追加・変更・修正をコードベースから推測して日本語でまとめています。

なお、このファイルは自動生成的にコード内容から推測して作成しています。実際のリリース履歴・担当者コメントと差異がある場合は適宜編集してください。

## [Unreleased]

### Added
- 実行用スクリプトを追加／整備
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。プロセス優先度を設定し、BrokerClientFactory を利用してブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。

- Portfolio（銘柄選定・配分）関連の純粋関数群を追加
  - select_candidates: BUY シグナルのスコア順ソートと上位 N 抽出。
  - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。全スコアが 0 の場合は等分配にフォールバックし WARNING を出力。

- Position sizing（株数決定）実装
  - calc_position_sizes: risk_based / equal / score の各方式に対応。損切り率・リスク率・ポジション上限・単元（lot_size）で丸め、aggregate cap（利用可能現金）に基づくスケールダウン処理を実装。手数料・スリッページ見積りの cost_buffer による保守見積りをサポート。

- リスク調整機能（セクター上限・レジーム乗数）
  - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。unknown セクターは上限ルールの対象外。
  - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に応じた投下資金乗数を提供。未知レジームは警告を出して 1.0 でフォールバック。

- Research（ファクター計算 / 特徴量解析）
  - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。必要行数不足時は None を返す設計。
  - calc_forward_returns: 指定ホライズンの将来リターンを一括取得するクエリを実装（ホライズンはバリデーションあり）。
  - calc_ic / rank / factor_summary: スピアマン（ランク）IC、ランク付け（同順位は平均ランク）、統計サマリーを提供。ties を考慮した安定的なランク処理。

- AI 関連
  - ai.news_nlp.score_news: raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores テーブルへ書き込む機能を追加。バッチ処理、チャンクサイズ制限、文字数制限、リトライ（429 / ネットワーク / 5xx）やレスポンス検証を実装。部分失敗時に他銘柄の既存スコアを守るため、書き込みは対象コードのみの DELETE → INSERT を行う。
  - ai.regime_detector: ETF（1321）の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定・書き込みする機能を実装。ルックアヘッド回避のため target_date 未満のみを参照し、API失敗時は macro_sentiment=0.0 で継続する堅牢設計。

- 設定管理と自動 .env ロード
  - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供（DB パス、API トークン、閾値、PID/kill flag 等）。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込みを導入（.env → .env.local の優先順）。OS 環境変数保護（protected set）や export 形式・クォート・エスケープ・コメント処理に対応したパーサを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- ユーティリティ
  - process_priority: Windows / POSIX ごとの差分を吸収してプロセス優先度（high/normal/low）と CPU affinity の設定を提供。権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- パッケージ情報
  - __version__ を 0.1.0 に設定。

### Changed
- DB 周りの取り扱いを明確化
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用するよう明言（監視は production DB を参照）。
  - run_execution は paper_trading 環境の場合に専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。

- DuckDB を分析用途のローカル処理に利用（各研究・AI モジュールが DuckDB 接続を受ける設計に統一）。

### Fixed
- 入力不正やデータ欠損に対する堅牢化
  - .env パースで不正な行やクォート内のエスケープを正しく処理するように改善。読み込み失敗時は警告出力。
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等分配へフォールバックして WARNING を出す。
  - calc_position_sizes: 価格欠損（None/0）の銘柄はスキップするようにし、ログを出力して無視する挙動に統一。
  - AI モジュールの API 呼び出しにおいて、JSON の不正応答を保護的に解析（外側の最初と最後の {} を抽出して再パース）し、検証失敗はそのチャンクだけスキップするように実装。

### Security
- OpenAI API キーや外部 API に関する扱い
  - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で提供する仕様。未設定時は ValueError を送出して明示的に失敗させる（credentials の漏洩を防ぐため / 明示的設定を要求）。

### Notes
- 多くの関数（portfolio / position_sizing / risk_adjustment / research）を純粋関数として設計しており、テスト容易性を考慮。これらは副作用なしでメモリ内計算のみを行う。
- 実行・監視スクリプトはプロセス優先度の設定（set_process_priority("high")）を起動直後に行う設計。
- AI 系の外部呼び出し周りはエクスポネンシャルバックオフや明示的なリトライ回数を実装し、部分失敗が全体を壊さないように配慮。

---

## [0.1.0] - 2026-04-11

初回公開想定の機能セット（上記 Unreleased の内容を包含する想定リリース）。

### Added
- 初期実装: 自動売買システムのコア機能群を追加
  - 実行エンジン（ExecutionEngine 起動スクリプト / ブローカークライアント統合 / Order 管理 / Risk 管理 / Reconciler）
  - 監視プロセス（SystemMonitor ポーリングスクリプト）
  - ポートフォリオ構築（候補選定、重み計算）
  - ポジションサイジング（リスクベース・等分配・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - 研究モジュール（モメンタム / ボラティリティ / バリュー / 将来リターン / IC / 統計サマリー）
  - AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定のためのマクロセンチメント）
  - 設定管理（Settings クラス、.env 自動読み込み）
  - プロセス管理ユーティリティ（優先度・CPU affinity）
  - DuckDB を使った分析パイプラインの基盤

### Changed
- パッケージメタ情報にバージョン 0.1.0 を設定。

### Fixed
- 各種入力・環境設定のバリデーションとフォールバック処理を整備（無効値やデータ不足時の安全挙動を実装）。

### Security
- OpenAI の API キーは明示的に要求。API 呼び出しの失敗時に安全にフォールバックする設計（macro sentiment のデフォルト 0.0 等）。

---

過去のリリース歴や担当コメントがあれば、この CHANGELOG はそれに合わせて調整してください。必要なら「変更点をもっと詳しく分割する」「個別ファイルごとの著者・コミット参照を追加する」など編集を手伝います。