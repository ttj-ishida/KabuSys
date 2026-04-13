# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリース日: 2026-04-13

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-13
### Added
- 基本的な自動売買システム「KabuSys」を初版として追加。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 実行エントリ / プロセス管理
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）して本番 DB と完全に分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト構成値（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）を設定し、初期ポートフォリオ値をブローカーから取得して使用。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して監視テーブルを扱う設計。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 や非数値）ではデフォルトにフォールバックし、警告を出力。
    - モニタリングループは check_once() の例外をロギングしてループを継続するフェイルセーフ実装。
    - PID ファイルや duckdb 接続を ExecutionEngine と同様に使用。

- 設定管理
  - config.py: 環境変数読み込み・設定管理モジュールを追加。
    - プロジェクトルート自動検出ロジック (`.git` または `pyproject.toml`) に基づく .env 自動読み込み（`.env` → `.env.local`、OS 環境変数を保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - .env のパースはコメント、export プレフィックス、クォート文字列、バックスラッシュエスケープに対応する堅牢な実装。
    - Settings クラスを提供し、各種設定値（API トークン、DB パス、Paper Trading 関連、監視閾値、環境モード判定等）をプロパティで取得可能。
    - PAPER_FILL_MODE（paper trading の mock fill モード）のバリデーション（instant/partial/never/reject）。
    - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性チェック。

- データベース / 分析
  - DuckDB / SQLite を利用したデータ処理基盤を追加（duckdb 接続を受ける設計）。
  - research モジュール:
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離率を計算。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
      - calc_value: PER / ROE を raw_financials と prices_daily から計算（EPS が無効な場合は None）。
      - いずれも DuckDB に対する SQL ベースの実装で、データ不足時は None を返す安全設計。
    - feature_exploration.py:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算（有効レコードが不足する場合は None を返す）。
      - factor_summary / rank: 基本統計量やランク付けユーティリティを実装。
    - research パッケージは外部ライブラリ（pandas 等）に依存せず、DuckDB + 標準ライブラリで完結する実装方針。

- ポートフォリオ構築（純粋関数群、メモリ内計算）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで整列し上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別の既存エクスポージャを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは免除）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックして 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
      - リスクベース（risk_pct, stop_loss_pct）による株数計算、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）スケーリング、cost_buffer を使った保守的コスト見積り、スケーリング時の端数配分ロジックなどを実装。
      - price 欠損や非正値に対するスキップ処理とログ出力。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX（Linux, macOS, FreeBSD）で優先度を設定するユーティリティ。未対応 OS はスキップ。アクセス権限不足等は警告してフォールバック。
    - set_cpu_affinity(cpu_count): 指定数の最初の CPU コアにプロセスを固定するユーティリティ。入力検証と例外ハンドリングを実装。

- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp:
    - raw_news を OpenAI（デフォルトモデル: gpt-4o-mini）に対してバッチで送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を追加。
    - ニュース収集ウィンドウ（JST ベース）を厳密に定義し UTC に変換して DB クエリに使用（calc_news_window）。
    - 1 回あたり最大 20 銘柄のバッチ、各銘柄ごとに最大記事数・文字数でトリム（トークン肥大化対策）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ（上限あり）。
    - レスポンスの JSON バリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護する書き込み戦略（該当コードのみ置換）を採用。
    - OPENAI_API_KEY が未設定の場合は明示的に ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加。
      - オプション: --from / --to（日付で期間指定）、--db（DB パス指定）。
      - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等を算出。
      - 合格/不合格判定基準（デフォルト閾値）を定義（稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
      - DB が存在しない / テーブルが無い場合は適切にメッセージを出力し安全に終了。

### Changed
- （初版のため履歴上の変更はありません。上記は本リリースで導入された機能群です）

### Fixed
- （初版のため既知のバグ修正はありません）

### Security
- 外部 API キー（OpenAI 等）は Settings / 環境変数経由で扱い、未設定時は明示的エラーを出す実装。環境自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト用途）。

---

注記:
- 多くのコンポーネント（ExecutionEngine、SystemMonitor、AI スコアリング等）は外部のブローカークライアントや DB スキーマに依存します。実運用時は環境変数設定・DB マイグレーション・権限周り（優先度設定など）に注意してください。
- ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）を参照する設計注記がコード内に多数含まれており、将来的な改善や拡張を想定した実装になっています。