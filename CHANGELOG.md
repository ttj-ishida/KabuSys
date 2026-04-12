# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルには、コードベースから推測できる機能追加・改善・修正点を記載しています。

履歴フォーマット:
- Unreleased: 今後の変更（現時点では未リリース）
- 各バージョン: リリース日と主要な変更点

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-12
初回公開（コードベースに基づく機能実装のスナップショット）

### Added
- 全体
  - パッケージ初期実装。バージョニングは `kabusys.__version__ = "0.1.0"`。
  - 環境変数/設定読み込みのための `kabusys.config.Settings` を実装。
    - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（環境変数で無効化可能）。
    - 必須キー検出用の `_require()`、各種設定プロパティ（DBパス、PID/KILL ファイルパス、閾値、環境種別など）。
    - 入力値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
- 実行エントリポイント
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合に paper 専用 SQLite を使用して本番 DB と分離。
    - プロセス優先度を設定（`utils.process_priority.set_process_priority`）。
    - Broker クライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計。
- ポートフォリオ関連（kabusys.portfolio）
  - `portfolio_builder.py`
    - BUY シグナルの候補選定（スコア降順、タイブレークに signal_rank）。
    - 等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights、スコアが全て 0 の場合は等分にフォールバック）。
  - `risk_adjustment.py`
    - セクター集中制限を検査する apply_sector_cap（当日売却予定の除外や "unknown" セクター扱いのルールを含む）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）。
  - `position_sizing.py`
    - 各銘柄の発注株数算出（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を用いた保守的見積り、残差分の分配ロジックを実装。
- リサーチ / ファクター計算（kabusys.research）
  - `factor_research.py`
    - Momentum/Volatility/Value の計算関数（DuckDB を利用して prices_daily / raw_financials を参照）。
    - 各種ウィンドウ・欠損ハンドリング（必要行数未満は None を返す等）。
  - `feature_exploration.py`
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの公開 API を exports。
- ニュース NLP（AI 統合）
  - `ai/news_nlp.py`
    - raw_news テーブルを元に OpenAI（gpt-4o-mini）へバッチで問い合わせ、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むロジック。
    - 1チャンクあたり最大 20 銘柄、1銘柄当たり記事数・文字数上限でトリム。
    - API エラー（429、ネットワーク、5xx、タイムアウト）に対する指数バックオフでのリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時でも既存スコアを保護する書き込み戦略を採用。
    - ニュースウィンドウ計算（JST 時間 → UTC 変換）を提供（calc_news_window）。
- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用検証レポート生成スクリプト（CLI）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db、期間フィルタ (--from/--to) に対応。
- ユーティリティ（kabusys.utils）
  - `process_priority.py`
    - Windows と POSIX（Linux/Mac/FreeBSD）でのプロセス優先度設定（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定のヘルパー実装。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。

### Changed
- 設計上の注意点・フェイルセーフ
  - 各モジュールで API キー未設定や DB 未存在などのケースに対する明示的なエラーメッセージや早期リターンを実装。
  - DuckDB / SQLite を使った分析・運用処理において、SQL 側で NULL を適切に扱うようクエリ設計済み（COUNT/CASE/NULL チェック等）。
  - .env 読み込みは OS 環境変数を保護するため protected キーを導入し、`.env.local` は上書き適用可能に設計。

### Fixed
- 入力検証の強化（想定外の値に対する挙動改善）
  - `MONITOR_POLL_INTERVAL` の不正値（0 以下や数値以外）に対してデフォルトにフォールバックし、警告ログを出力。
  - `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` の許容値チェックを追加し、不正値で早期に ValueError を投げるようにした。
  - 環境変数パースの強化（`_parse_env_line`）:
    - export プレフィックス対応、クォート内でのバックスラッシュエスケープ、インラインコメント処理、空行・コメント行の無視などを実装し `.env` の互換性を高めた。

### Security
- API キー・シークレットの取り扱い
  - OpenAI API キーは引数または環境変数から解決し、未設定時は明確なエラーを出す。ログにキーの中身を出力しない設計。
  - `.env` 自動ロード時に OS 環境変数を上書きしない既定挙動とし、意図せぬ上書きを防止する保護機構を実装。

### Notes / Known limitations
- position_sizing の価格欠損時の挙動（price が 0.0 の場合は露出が過少見積もられる）は TODO として記載されており、前日終値などのフォールバック価格の導入が検討課題となっている。
- news_nlp の出力は厳密な JSON を期待するため、外部 API のフォーマット変更に弱い点がある（現在は厳密な検証とフェイルセーフで一部を保護）。
- 一部の OS/権限によりプロセス優先度・CPU affinity の設定が失敗する可能性があり、その場合は警告ログを出してスキップする。

---

参考:
- 実装ファイル群:
  - src/kabusys/config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/portfolio/*
  - src/kabusys/research/*
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/utils/process_priority.py

（この CHANGELOG は提供されたコード内容から推測して作成しています。実際のコミット履歴や過去のリリースノートが存在する場合は、そちらを優先して更新してください。）