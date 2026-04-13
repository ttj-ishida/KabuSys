# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般的な注意:
- リポジトリのバージョンは `src/kabusys/__init__.py` の `__version__` に一致します（本ログでは 0.1.0 を初版として記載）。
- 記載内容はソースコードから推測した機能追加・仕様・安全対策等に基づき作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージの初期実装を追加。
  - パッケージバージョン: 0.1.0 (`src/kabusys/__init__.py`)。
- 実行起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを提供。
    - 環境変数 `KABUSYS_ENV` が `paper_trading` の場合は paper 専用の SQLite DB（`data/paper_trading.db`／`PAPER_TRADING_SQLITE_PATH`）を使用し、MockBrokerClient による分離された動作をサポート。
    - プロセス優先度を高に設定するユーティリティ呼び出しを導入（`utils.process_priority.set_process_priority`）。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等のコンポーネントを組み立ててセッション実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はログ警告後にデフォルトにフォールバック。
    - 監視用 DB は環境に関わらず本番 `sqlite_path` を使用（監視は本番 DB を見に行く設計）。

- 設定管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。
  - `.env` / `.env.local` の読み込み順を実装（OS 環境変数の保護機構あり）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーはクォート・エスケープ、インラインコメント（クォートなしで直前が空白/タブの場合）等に対応。
  - Settings クラスを導入し、API トークン、DB パス、監視閾値、環境種別検証（development, paper_trading, live）などをプロパティ経由で取得可能に。
  - `PAPER_FILL_MODE` の検証（有効値: instant/partial/never/reject）を実装。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - portfolio_builder
    - 候補選定（select_candidates）：スコア降順、同点は signal_rank の昇順でタイブレーク。
    - 等金額配分 / スコア加重配分（calc_equal_weights / calc_score_weights）。全銘柄スコアが 0 の場合は等金額配分にフォールバックして警告を出力。
  - risk_adjustment
    - セクター集中制限（apply_sector_cap）：既存保有からセクターごとのエクスポージャーを計算して、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）：regime ラベルに応じて乗数を返す（bull/neutral/bear のマッピング、未知のレジームは 1.0 にフォールバックして警告）。
  - position_sizing
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - リスクベース計算、単元株（lot）丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮したスケールダウンと残余の再配分ロジックを実装。

- 研究用モジュール（src/kabusys/research/）
  - factor_research
    - calc_momentum / calc_volatility / calc_value：DuckDB 接続を受け、prices_daily / raw_financials を参照してファクターを計算。200日移動平均やATR等の計算実装を含む。
  - feature_exploration
    - calc_forward_returns：将来リターンをまとめて取得するクエリ実装（複数ホライズン対応）。
    - calc_ic：スピアマンランク相関（IC）を実装（必要件数未満で None を返す）。
    - rank / factor_summary：ランク化・統計サマリーユーティリティを実装。
  - research パッケージは zscore_normalize などのユーティリティも再エクスポート。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini を想定）でセンチメント分析し、銘柄ごとの ai_scores テーブルへ書き込むロジックを実装。
  - 処理フロー: タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）、記事集約、バッチ送信（最大 20 銘柄/チャンク）、レスポンス検証、スコアクリップ（±1.0）、部分成功時の DB 保護（対象コードのみ置換）等をサポート。
  - API キーが未設定の場合は ValueError を送出。
  - レート制限・ネットワークエラー・5xx 等に対する指数バックオフリトライを想定した設計。
  - ルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を直接参照しない設計。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 向け検証レポート生成スクリプトを追加。
  - 検証指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等。既定の閾値を定義して Pass/Fail を判定。
  - SQLite DB（paper_trading DB）を直接参照して system_status, trade_logs, risk_logs から集計。日付フィルタ指定 (--from/--to) に対応。
  - P95 の計算・出力フォーマットを実装、DB が存在しない場合のエラーメッセージあり。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プロセス優先度設定ユーティリティを追加。
  - Windows / POSIX（Linux, Darwin, FreeBSD）に対応した nice/priority 設定を抽象化。アクセス拒否等の例外は警告ログでスキップ。
  - set_cpu_affinity 関数でプロセスの CPU affinity を最初の N コアに固定可能（検証・例外時は警告でスキップ）。

### Changed
- 設計上の注意点と安全策を明示
  - research / ai モジュールは外部取引 API を呼ばない、ルックアヘッドを避ける等、研究・AI スコア生成での安全対策をコード内コメントで明示。
  - 設定ロード時に OS 環境変数を保護する仕組みを導入（`.env.local` の override でも OS 環境変数は上書きされない）。

### Fixed
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープや、クォートなしのインラインコメント処理を実装して .env のパースミスを減らす。
- ポーリング間隔の不正値ハンドリング
  - `MONITOR_POLL_INTERVAL` が不正（整数以外、0 以下）な場合に警告ログを出して安全にデフォルトへフォールバックするよう修正。

### Security
- API キーの未設定時に明確にエラーを出す（OpenAI 関連）。
- 環境変数自動読み込みはプロジェクトルートが特定できない場合にスキップ。自動ロードの無効化フラグ (`KABUSYS_DISABLE_AUTO_ENV_LOAD`) を追加。

### Performance / Behavior Notes
- DuckDB を多用する設計（research / ai / tools）により大量データの集計をローカルで効率的に行う前提。
- position_sizing の aggregate cap のスケーリングは lot_size 単位での再配分を行うため、スケールダウン時の決定は再現性（安定ソート）を考慮している。
- process priority / CPU affinity の設定は権限不足や未対応 OS の場合はログ警告で安全にスキップする。

### Dependencies
- duckdb（分析用）
- psutil（プロセス優先度 / CPU affinity）
- openai（AI スコアリング）
- 標準ライブラリ（sqlite3, logging, argparse, datetime, math など）

---

今後のリリース候補に含める可能性のある項目（リファクタ案）
- position_sizing: 銘柄ごとの単元株（lot）をマスタで管理し、関数引数で渡せるようにする拡張（TODO コメントあり）。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価など）の導入。
- ai/news_nlp: API リトライ・バックオフの詳細実装（現在は設計方針として文書化されている）。
- run_* スクリプトのデーモン化・ログ出力周りの改善（ログレベル設定を Settings から反映する等）。

もし特定のファイルや機能について、より詳しい変更点（例: 関数単位の変更理由や既知の制約）をCHANGELOGに追記希望でしたら、その対象を指定してください。