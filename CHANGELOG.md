# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成したもので、実際のコミット履歴ではありません。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - SystemMonitor のポーリングループを起動するエントリポイントを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
  - 停止フラグファイル（data/stop_requested.flag）検知で安全にループを終了。
  - 監視処理は常に本番用の sqlite_path を使用する設計。

- run_execution 起動スクリプトを追加
  - ExecutionEngine を初期化して別スレッドで実行するエントリポイントを実装。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用して本番 DB と分離。
  - 停止フラグの検知でエンジンを停止。起動時に停止フラグが立っている場合は起動せず終了。
  - エンジンの PID を data/execution.pid に書き出す想定（pid_file を利用）。

- 設定管理（kabusys.config）を改善
  - プロジェクトルートの自動検出（.git または pyproject.toml）を実装し、.env/.env.local を自動ロード（OS 環境変数優先、.env.local は上書き）。
  - export KEY=val 形式やクォート付き値、行内コメントなどを考慮した .env パーサを実装。
  - 必須環境変数取得ヘルパー _require を用意（未設定時は明示的な例外）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）を追加。
  - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH 等のデフォルトパスを提供。
  - 監視・閾値関連設定（cpu/memory/disk の閾値、kill_flag のパス 等）をプロパティで提供。
  - KABUSYS_ENV / LOG_LEVEL の検証を追加。

- ポートフォリオ構築モジュールを実装（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額/スコア重み付けを実装。
  - risk_adjustment: セクター上限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing: リスクベース・等分配・スコア配分に基づく株数算出、単元株丸め、単銘柄上限・総投資上限の考慮、コストバッファを考慮したスケーリング処理を実装。
  - 複数の安全弁（価格欠損時のスキップ、上限超過時のスケールダウン、残余キャッシュでの lot 単位の追加配分）を実装。

- 研究用モジュールを実装（kabusys.research）
  - factor_research: Momentum / Volatility / Value の定量ファクター計算を DuckDB SQL で実装（MA200、ATR20、リターン等）。
  - feature_exploration: 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
  - DuckDB 接続を受け取り SQL と純粋 Python ロジックで結果を返す設計。

- ユーティリティの追加（kabusys.utils）
  - process_priority: プラットフォーム差異を吸収するプロセス優先度設定（Windows と POSIX をサポート）と CPU affinity 設定関数を追加。アクセス権限不足や未サポート環境では警告してフォールバック。

- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - paper_trading の SQLite DB を解析して稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、PASS/FAIL 判定を出力する CLI を実装。
  - 日付フィルタ（--from / --to / --db）対応、P95 の算出ロジック、各種閾値を定義してレポート出力。

- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp）
  - raw_news からニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントを JSON で取得し ai_scores テーブルへ書き込む設計を実装。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数トリム）、リトライ（指数バックオフ）、スコアの ±1.0 クリップ、部分書き換えによる部分失敗耐性等を計画。
  - （注）ソースは大きく実装されているが、コード断片が途中で切れているため実行前に追加実装・検証が必要。

### Changed
- パッケージ初期化とバージョン定義を追加（kabusys.__init__ の __version__ = "0.1.0"）
- research パッケージの公開 API を整理（zscore_normalize を data.stats から再エクスポート等）。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、行内コメントの扱いなどを改善。
  - .env ファイルの読み込み失敗時に warnings.warn を出して継続。

### Documentation / Comments
- 各モジュールに設計意図・参照ドキュメント・注意点を詳細にコメントとして追加（PortfolioConstruction.md / StrategyModel.md 等を参照する旨を明記）。
- 関数やプロパティに docstring を整備（引数・戻り値・例外・注意点を記載）。

---

## [0.1.0] - 2026-04-16

初回リリース相当のまとめ（コードベースから推測）。

### Added
- 基本的な自動売買システムのコアコンポーネントを追加
  - ExecutionEngine 起動フロー（run_execution）
  - SystemMonitor 起動フロー（run_monitoring）
  - 設定管理（自動 .env ロード、環境変数ラッパ）
  - データ処理 / ポートフォリオ構築 / リスク調整 / 取引サイズ算出の純粋関数群（kabusys.portfolio）
  - 研究用ファクター計算（momentum/volatility/value）および評価ツール（IC, forward returns, summary）
  - Paper Trading 向け検証レポート生成ツール
  - OpenAI を用いたニュース NLP スコアリングの骨組み
  - プロセス優先度・CPU affinity のユーティリティ
  - DuckDB / SQLite を利用したデータ入出力設計

### Changed
- 初期設計時点の API 仕様・設定名を決定（KABUSYS_ENV, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）
- ファイル配置・デフォルトデータパスを data ディレクトリ中心に統一

### Known limitations（既知の制約・TODO）
- news_nlp モジュールは大部分が実装済みだが、コードが途中で切れている箇所があり（ファイル末尾）、実運用前に補完が必要。
- position_sizing の price 欠損時のフォールバックは TODO コメントとして残してあり、将来的に前日終値や取得原価でのフォールバックを検討予定。
- 一部機能は DuckDB / SQLite のスキーマや外部モジュール（ExecutionEngine, BrokerClient 等）の実装依存。統合テスト・実稼働前の検証が必要。

---

注: 上記はリファクタリング・実装された機能をコードから推測してまとめた CHANGELOG です。実際の変更履歴（コミットログ）を基にした正確な履歴が必要な場合は、git log 等の履歴情報を提供してください。