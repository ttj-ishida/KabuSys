# Changelog

すべての注記は Keep a Changelog の慣例に従っています。  
許容バージョニングは SemVer に準拠します。

## [Unreleased]

（今後の変更点をここに記載します）

## [0.1.0] - 2026-04-17

初期リリース — コア機能の実装とユーティリティ群を追加。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として初期化。

- 環境設定管理
  - .env / .env.local を自動ロード（OS 環境変数を優先）する機能を実装。
  - プロジェクトルート自動検出（.git / pyproject.toml 基準）により CWD に依存しない読み込みを実現。
  - .env パーサーを実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ処理、インラインコメントの扱いに対応）。
  - Settings クラスを実装し、アプリケーション構成値（API トークン、DB パス、各種閾値、環境種別など）をプロパティ経由で取得可能に。
  - 必須環境変数未設定時に明確なエラーメッセージを投げる `_require` を実装。
  - 許容される KABUSYS_ENV 値: `development`, `paper_trading`, `live`。
  - PAPER_TRADING 用のパス／モード（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）をサポート。

- 実行／監視スクリプト
  - run_execution.py を実装：
    - ExecutionEngine の起動フロー（ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、エンジンスレッドでの実行管理）。
    - Paper Trading (`KABUSYS_ENV=paper_trading`) 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理および優先度設定をサポート。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提供。
  - run_monitoring.py を実装：
    - SystemMonitor ポーリングループ。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグ検知、例外時のログ出力、リソースクリーンアップ（DB 接続クローズ）に対応。
    - 起動直後にプロセス優先度を "high" に設定。

- データベース関連
  - DuckDB 接続を受ける処理（research / ai / その他で利用）を採用。
  - 監視用テーブル初期化ヘルパー（init_monitoring_db）を利用して冪等にテーブルを保証。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - シグナルから候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights） — 全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - portfolio.risk_adjustment:
    - セクター集中制限適用（apply_sector_cap）。既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは制限を適用しない設計。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。既知レジーム（bull/neutral/bear）に対する乗数を定義し、未知レジームは警告のうえフォールバック。
  - portfolio.position_sizing:
    - 各銘柄の発注株数計算（risk_based / equal / score の配分方式をサポート）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - cost_buffer による手数料・スリッページ見積りを考慮した保守的な集計。

- 研究（research）モジュール
  - research.factor_research:
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）、Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）、Value（per / roe）ファクターを DuckDB 上の SQL で計算する関数群を実装。
    - データ不足時の None ハンドリングや集約ウィンドウの設計（営業日バッファ）を考慮。
  - research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）。任意ホライズンに対応し SQL で一括取得。
    - IC（Information Coefficient）計算（Spearman ρ）とランク関数（rank）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - research.__init__ で主要ユーティリティを公開（zscore_normalize を含む）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートをファイルまたは DB から生成する CLI ツール。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はソース内に定義）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。
    - データ欠損時のフォールバック（テーブルが存在しない場合のエラー処理）。

- AI / NLP
  - ai.news_nlp:
    - raw_news テーブルを集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む設計を実装。
    - バッチサイズ、トークン肥大化対策（記事数/文字数制限）、429/5xx/ネットワークエラーに対する指数バックオフリトライ、レスポンスの厳格な JSON バリデーションなどの考慮を含む。
    - OpenAI API キー解決（引数または環境変数 OPENAI_API_KEY）と未設定時のエラーを実装。
    - （注）ファイル末尾が途中で切れているため、fetch/書き込みの後続処理は一部未表示。実装の続きが存在する可能性あり。

- ユーティリティ
  - utils.process_priority:
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を実装（Windows と POSIX の差を吸収）。
    - CPU affinity 固定用 set_cpu_affinity を追加（コア数指定）。
    - 権限不足や未対応環境時は警告ログを出し処理をスキップするフェイルセーフ。

### 改良（設計上の注記 / 安全性）
- 実行系と監視系の DB 分離:
  - Paper Trading 実行時は paper_sqlite_path を使用して本番監視 DB と完全分離する設計。
- 監視ループ・エンジン起動の安全停止機構:
  - data/stop_requested.flag による外部からの停止指示に対応（監視・実行双方）。
- フォールバックと堅牢性:
  - 環境変数パースや設定値が不正な場合は明示的なログ/例外を投げる。MONITOR_POLL_INTERVAL の不正値処理など、外部設定ミスに対するフォールバックを実装。
- DuckDB を分析向けに採用し、ファクター計算や NLP 集約は本番の発注ロジックから独立して実行可能。

### 既知の注意点 / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0） の場合にエクスポージャーが過少見積りになる可能性があり、将来的に前日終値や取得原価を用いるフォールバックが必要とのコメントあり。
- news_nlp モジュール:
  - ファイル末尾が途中で切れており、記事取得（_fetch_articles）以降の処理の全体像はソースから完全には確認できない。実稼働前に未表示部分の実装を確認すること。
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする（明示的に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 将来的拡張案:
  - 銘柄ごとの lot_size を stocks マスタに持たせる等、position_sizing の細分化が示唆されている。

### 削除 / 非推奨
- なし（初回リリース）

### セキュリティ
- OpenAI API キー等の機密情報は環境変数を利用する設計（コード内ハードコードはなし）。必須未設定時は明示的なエラーをスロー。

---

注: 上記は提供されたソースコードから推測して作成した変更履歴です。実際のコミット履歴や変更差分がある場合は、差分に基づく追記・修正を推奨します。