# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

（現在対象なし）

## [0.1.0] - 2026-04-16

### 追加 (Added)
- パッケージ初期リリース。以下の主要機能を実装。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルート/data/stop_requested.flag ファイルを検出して行う。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db など）と MockBrokerClient を使用して本番 DB と分離。停止フラグ・PID 管理・スレッドでのエンジン実行制御を実装。
  - 設定管理
    - config.py: 環境変数/.env/.env.local の自動読み込み（プロジェクトルート判定）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化、OS 環境変数保護（上書き禁止）対応。クォート・エスケープ・コメント処理に対応した .env パーサを実装。Settings クラスで各種設定（DB パス、PID/フラグパス、Paper Trading 設定、閾値など）を取得可能に。
  - ユーティリティ
    - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows / POSIX 対応）。CPU アフィニティ設定機能も提供。権限不足や未対応 OS の場合は安全にスキップして警告を出力。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数計算アルゴリズム（risk_based / equal / score）を実装。単元株丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケールダウン）を実装。cost_buffer による手数料・スリッページ考慮。
  - リサーチ / ファクター計算
    - research/factor_research.py: Momentum / Volatility / Value の各ファクター計算を実装（DuckDB 接続を受け取り SQL で計算）。MA200、ATR20、各種リターンなど。
    - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク化ユーティリティ（rank）。
    - research パッケージは外部依存（pandas 等）を使わず標準ライブラリと DuckDB で動作する設計。
  - AI / ニュース NLP
    - ai/news_nlp.py（部分実装）: raw_news テーブルのニュースを OpenAI API (gpt-4o-mini) でセンチメント評価し、銘柄ごとの ai_scores テーブルへ書き込む処理を設計・実装（バッチ化、トークン肥大化対策、結果バリデーション、スコアクリップ、リトライ戦略などを含む）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を行う。コマンドライン引数 --from/--to/--db をサポート。
  - DB / データ連携
    - DuckDB 統合: DuckDB 接続を受けて prices_daily / raw_financials 等のテーブルを参照する処理を多数実装。
  - パッケージ情報
    - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### 変更 (Changed)
- （初版のため変更履歴なし）

### 修正 (Fixed)
- .env パーサ: export プレフィックスの処理、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等を実装して堅牢性を向上。
- calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし WARNING を出力。
- factor_research / feature_exploration: 欠損値やデータ不足時に None を返すよう安全に処理（count 条件、NULL 伝播制御、窓サイズチェック）。
- position_sizing: aggregate cap のスケーリングで lot_size 単位の丸めと残差処理（fractional remainder による追加配分）を実装し、投下資金の公正な分配を図る。
- apply_sector_cap: "unknown" セクターを上限チェック対象外とする挙動を明文化。
- process_priority: 未対応 OS / 権限エラー時に警告を出すようにして起動妨害を防止。

### 既知の問題 / 制限 (Known issues)
- ai/news_nlp.py は大部分が実装されているが、この配布スナップショットではファイル末尾が途中で切れているように見えます（関数内部の続きが欠落）。OpenAI API 呼び出し周りの最終的な DB 書き込みロジック等は本リリースでは要確認。
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値等でフォールバックすることが推奨される。
- position_sizing: lot_size は現在グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map への拡張が想定されている（TODO コメント）。
- process_priority.set_process_priority / set_cpu_affinity: 権限不足時（非 root / 管理者）や未対応 OS では設定がスキップされる。動作確認は実行環境で行ってください。
- paper_verification_report は DuckDB ではなく SQLite（paper_trading.db）を参照する設計。テーブルが存在しない場合は対象指標を N/A として扱う箇所がある（OperationalError を捕捉）。

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用する設計。秘匿管理に注意してください（コード上で平文で埋め込まないこと）。

---

## マイグレーション / 利用上の注意
- 環境変数:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。整数 1 以上を指定。無効値はデフォルト 60 秒にフォールバック。
  - KABUSYS_ENV: 有効値は "development" / "paper_trading" / "live"。paper_trading の場合、run_execution は paper_sqlite_path を使用して本番 DB と分離します。
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite のパス（デフォルト data/paper_trading.db）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化できます（テスト用途など）。
  - PAPER_FILL_MODE: Paper Trading の MockBrokerClient 挙動 ("instant" | "partial" | "never" | "reject")。
- CLI:
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DB:
  - Monitoring 用の SQLite は settings.sqlite_path（デフォルト data/monitoring.db）。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使う点に注意。
  - DuckDB は prices_daily / raw_financials 等のリサーチ処理で使用。パフォーマンス上の理由から適切にファイルパスを設定してください。

---

もし特定機能の詳細（例: position_sizing のパラメータ調整方法や news_nlp の未実装箇所の補完案）について追記や分割リリースの作成が必要であれば、その旨を教えてください。