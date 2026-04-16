# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-16
初期リリース。システム監視、Execution エンジン起動、ポートフォリオ構築、リサーチ、ニュースNLP 等の主要機能を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を使用）。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にループ終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して接続。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler 等の組み立ておよび ExecutionEngine の起動を行う。
    - スレッドで engine を起動し、停止フラグ検知で安全停止を行う。PID ファイルパスをサポート。
    - 起動時にプロセス優先度を設定。

- 設定管理
  - src/kabusys/config.py を新規追加
    - .env / .env.local の自動ロード機能（プロジェクトルートの検出基準: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パースの堅牢化（export プレフィックス、シングル/ダブルクォート、インラインコメント等に対応）。
    - 環境変数の必須チェックを行う _require() を提供。
    - 多数の設定プロパティを追加（J-Quants トークン、kabu API、LINE API、duckdb/sqlite パス、paper_trading 用 DB パス、PID/KILL フラグパス、しきい値、環境種別検証、ログレベル検証等）。
    - PAPER_FILL_MODE の入力検証を追加（instant/partial/never/reject のみ許容）。

- 監視 / モニタリング関連
  - monitoring_db 初期化を起動スクリプトで行うことで監視テーブルの整合性を保障（init_monitoring_db を使用）。

- ユーティリティ
  - utils/process_priority.py を追加
    - Windows と POSIX 系を抽象化してプロセス優先度（high/normal/low）を設定する set_process_priority を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォーム時に安全にスキップするロバスト実装。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用 SQLite データを解析し検証レポートを標準出力に出力する CLI ツール。
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数等を集計し PASS/FAIL 判定を行う。
    - 日付範囲フィルタ（--from/--to）と --db オプションをサポート。
    - P95 の計算、DB 存在チェック、テーブル欠損時のフォールバックを実装。

- ポートフォリオ構築（純関数群）
  - src/kabusys/portfolio/
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順で選別するユーティリティ。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重でウェイト計算。
      - スコア合計が 0 の場合等金額配分へフォールバック。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外。
      - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
    - position_sizing.py
      - calc_position_sizes: 重み・候補・ポートフォリオ状態を元に各銘柄の発注株数を計算（risk_based / equal / score）。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap とコストバッファを考慮したスケーリング、残余の再配分アルゴリズムを実装。

- リサーチ / ファクター計算
  - src/kabusys/research/
    - factor_research.py
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB 経由、prices_daily を参照）。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials から PER/ROE を計算（最新報告日までのデータを結合）。
      - 各関数は不足データの場合に None を返す等、堅牢化。
    - feature_exploration.py
      - calc_forward_returns: target_date から指定ホライズン先の将来リターンを計算（デフォルト horizons=[1,5,21]）。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None。
      - factor_summary / rank: 基本統計量およびランク付けユーティリティ。
    - research パッケージ初期化で zscore_normalize を re-export。

- AI / ニュース NLP（基盤実装）
  - src/kabusys/ai/news_nlp.py を追加（部分実装）
    - raw_news テーブルから記事を集約し、OpenAI API (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む設計。
    - バッチサイズ、トークン肥大対策（記事数・文字数トリム）、レスポンスバリデーション、スコアクリップ、リトライ（指数バックオフ）等の方針と定数を定義。
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を実装。
    - score_news の API キー解決とウィンドウ計算まで実装（ファイル末尾で未完の可能性あり）。

### Changed
- 起動時の挙動
  - run_monitoring.py / run_execution.py で起動直後にプロセス優先度を "high" に設定するように変更（リソース確保を優先）。
- .env 読み込み順序
  - OS 環境 > .env.local > .env の優先順で読み込む仕様を導入。既存 OS 環境変数は保護される（protected set）。
- DuckDB / SQLite のパスにデフォルト値を設定（data ディレクトリ内のファイルを使用）。

### Fixed
- .env のパースにおける多くのケースを修正・堅牢化
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ、インラインコメントの扱いを改善。
  - 無効行のスキップ、読み込み失敗時の警告出力を追加。

### Potential breaking changes / 注意点
- run_monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用する動作になっています。テスト環境や paper_trading 環境で監視を分離したい場合は設定の見直しが必要です。
- set_process_priority / set_cpu_affinity はプラットフォーム依存の権限により失敗する可能性があり、失敗時はログ警告の上スキップされます。運用環境での権限（root / 管理者）や psutil の利用可能性を確認してください。
- ai/news_nlp.py は設計・リトライ等のロジックを含むものの、ファイル末尾が途中で切れている可能性があるため、実運用前に完全実装とテストが必要です。

### Notes
- 全体的に「DB は読み取り/書き込みの場所を明確に分離」「リサーチ（DuckDB）と実取引（SQLite/ブローカー）は分離」「環境変数の堅牢な管理」を設計方針として実装しています。
- 各モジュールは外部 API 呼び出しを最小化し、DuckDB / SQLite のローカルデータを用いて再現可能な計算を行うように設計されています。

---
この CHANGELOG はソースコードから推測して作成しています。運用上の正確なリリースノートやリスクの判断は実際の差分・コミット履歴およびテスト結果を参照して補完してください。