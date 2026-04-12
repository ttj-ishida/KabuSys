# CHANGELOG

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

- ドキュメント・ユーティリティの追加や小さな内部改善予定。

---

## [0.1.0] - 2026-04-12

初回公開リリース。以下はコードベースから推測される主要な機能・仕様・修正点の要約です。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開。
  - プロジェクト設定管理モジュールを追加（kabusys.config）。
    - .env / .env.local の自動ロード（プロジェクトルート検出：.git または pyproject.toml）。
    - 環境変数の堅牢なパース実装（コメント・クォート・export 対応）。
    - 必須変数取得時に未設定なら例外を投げる _require() を実装。
    - Settings クラスで各種設定値をプロパティとして提供（DBパス、APIキー、監視閾値、環境判定など）。
- 実行系
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV に応じて paper_trading の場合は専用の SQLite（data/paper_trading.db デフォルト）を使用。
    - BrokerClientFactory を通じたブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てとセッション起動。
    - Execution 起動時にプロセス優先度を高く設定するユーティリティ呼び出し。
- 監視系
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視は常に本番 sqlite_path を参照して監視テーブルを初期化（init_monitoring_db）。
    - SystemMonitor を用いた単一チェックループを実装（エラーはログ出力して継続）。
- ポートフォリオ構築
  - ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio.*）。
    - portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。
    - risk_adjustment: セクターキャップ適用(apply_sector_cap)、レジーム乗数(calc_regime_multiplier)。
    - position_sizing: 各銘柄の発注株数算出(calc_position_sizes) — risk_based / equal / score の配分方式と aggregate cap 対応、lot_size 単位処理、cost_buffer を考慮したスケーリング。
- 研究（Research）
  - ファクター計算 / 研究モジュールを追加（kabusys.research）。
    - factor_research: モメンタム、ボラティリティ、バリューファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。
    - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（スピアマンランク相関）計算(calc_ic)、統計サマリー(factor_summary)、ランク変換(rank)。
    - DuckDB を想定した効率的な SQL 集約クエリを使用（ウィンドウ関数等）。
- AI / NLP
  - ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）。
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を取得して ai_scores に書き込む処理を実装。
    - バッチ化（最大 20 銘柄/コール）、記事/文字数トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)、429/5xx/ネットワークエラーに対する指数バックオフ再試行を実装。
    - 出力のバリデーションとスコアの ±1.0 クリップを適用。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX(Linux/macOS/FreeBSD) を吸収した優先度設定（high/normal/low）。
    - CPU affinity 固定機能（最初 N コアに固定）。
    - 権限不足や未サポート環境では警告を出して安全にフォールバック。
- ツール
  - Paper Trading 検証レポートジェネレータを追加（kabusys.tools.paper_verification_report）。
    - SQLite（paper_trading DB）から system_status / trade_logs / risk_logs を読み出し、稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - コマンドライン引数 --from / --to / --db をサポート。
- DB
  - DuckDB を研究・AI系で活用（duckdb 接続を受け取る API を各所に実装）。
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を起動時に呼び出すことでテーブル存在を保証（冪等）。

### 変更 (Changed)
- 設定周り
  - 環境変数ロード順序を明確化: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスで env 値の検証（"development" / "paper_trading" / "live" のみ許容）および LOG_LEVEL 検証を追加。

### 修正 (Fixed)
- 入力検証・フォールバックの強化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を補足してデフォルトにフォールバックするように変更（監視ループの ValueError を回避）。
  - PAPER_FILL_MODE の不正値検出と ValueError を追加（有効値: instant|partial|never|reject）。
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出力するように実装。
  - position_sizing: 価格欠損時はスキップし、lot_size 単位で丸めるなど実運用での安全な振る舞いを実装。
  - risk_adjustment: セクター不明 ("unknown") の扱いを明確化（セクター上限チェック対象外）。

### その他（ドキュメント/運用に関する注記）
- 実行時のログレベルはデフォルト INFO。各スクリプトは logging.basicConfig を設定して INFO レベルで起動する。
- 実運用では以下の環境変数を適切に設定する必要あり:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（ニュース NLP を利用する場合）
  - KABUSYS_ENV（development | paper_trading | live）
  - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH（DBパス）
  - PID_FILE_PATH / KILL_FLAG_PATH 等（監視用ファイルパス）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、専用の SQLite（デフォルト: data/paper_trading.db）に書き込む設計。
- AIニュース処理は API キー必須。失敗時はフェイルセーフでスキップし、処理済みデータだけを差し替える方式で部分失敗への耐性を確保。

### 既知の制限 / TODO
- 一部の価格欠損（open/price が 0.0）の取り扱いが簡素で、将来的には前日終値等のフォールバック追加を検討（コメントあり）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map へ拡張予定）。
- news_nlp の処理中断や部分失敗時の完全なロールバックは実装されておらず、部分更新戦略で既存スコアを保護する方針。
- research / factor モジュールは DuckDB のテーブル構成（prices_daily / raw_financials 等）に依存するため、スキーマ変更時にクエリの見直しが必要。

---

メンテナンス上の注意:
- この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴・コミット履歴やリリースノートがある場合はそちらを優先してください。