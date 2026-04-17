Keep a Changelog
=================
すべての注目すべき変更をこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを採用します。

Unreleased
----------
追加 / 進行中の実装、実験的な機能や既知の未完成箇所を記載します。

- Added
  - AI ニューススコアリングモジュール (kabusys.ai.news_nlp) の初期実装を追加。
    - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント集約／スコア化処理の設計を実装。
    - バッチ処理、レスポンス検証、スコアの ±1.0 クリップ、再試行ポリシー（指数バックオフ）の骨格を実装。
    - ニュース収集ウィンドウ（JST→UTC の変換）ユーティリティを実装。
  - DuckDB を使った AI スコア／記事集計処理の下準備を追加。

- Changed / Notes
  - news_nlp モジュールは途中で切れている（実行時に未完成のコードパスが存在）。本番運用前に以下を要確認・実装:
    - 記事取得部分の続き（_fetch_articles の統合）。
    - DuckDB への書込み（部分更新ロジック）の完成。
    - API 呼び出しとエラーハンドリングの最終調整。
  - 現時点では API キー管理に注意（OPENAI_API_KEY 必須）。未設定時は明示的なエラーを出す設計。

- Known issues / TODO
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーの過少推定となる可能性がある旨の TODO（価格フォールバック未実装）。
  - news_nlp における部分的失敗時の部分更新ロジックや JSON レスポンス検証の堅牢化が必要。

0.1.0 - 2026-04-17
------------------
初回公開リリース。主要な機能群とユーティリティをまとめて追加。

- Added
  - 基本パッケージ情報
    - パッケージバージョンを __version__ = "0.1.0" として設定。
  - 設定管理 (kabusys.config)
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml による）。
    - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い対応を備えた .env パーサ実装。
    - 環境変数取得のラッパ Settings クラスを提供（J-Quants / kabu / LINE / DB / 監視閾値等のプロパティを定義）。
    - 環境（KABUSYS_ENV）の検証（development, paper_trading, live）と各種デフォルト値を明示。
    - PAPER_FILL_MODE（paper_trading 時の MockBroker の挙動）や PAPER_TRADING_SQLITE_PATH など紙トレード用設定を追加。
  - 実行系スクリプト
    - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
      - 環境に応じて本番 DB または paper_trading 専用 DB を使い分ける（paper_trading は data/paper_trading.db がデフォルト）。
      - BrokerClientFactory を利用してブローカークライアントを生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動する仕組みを実装。
      - 停止フラグ（data/stop_requested.flag）によるグレースフルシャットダウン対応。
      - デフォルトでプロセス優先度を "high" にセットする呼び出しを導入。
    - 監視ポーリング起動スクリプト (src/kabusys/run_monitoring.py)
      - SystemMonitor のポーリングループを実装。
      - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔オーバーライドと入力検証（無効値はデフォルト60秒へフォールバック）。
      - 監視 DB 初期化 (init_monitoring_db) と DuckDB 接続を確立。
      - 停止フラグ検知でループを終了する仕組み。
  - 監視 DB 初期化フック (monitoring.monitoring_db を利用して全体で呼び出し)
    - 実行・監視の開始時に監視テーブルが存在することを保証（冪等に初期化）。
  - Portfolio 構築関連 (kabusys.portfolio)
    - portfolio_builder
      - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
      - スコアが全て 0 の場合のフォールバック（等配分）と警告ログ。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮し、該当セクターの新規候補を排除）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング）を実装。
    - position_sizing
      - 各銘柄の発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。
      - 単元株（lot_size）で丸め、per-position 上限・aggregate cap を考慮したスケーリング、cost_buffer を考慮した保守的見積りを実装。
      - available_cash を超えた場合のスケールダウンと残余キャッシュでの端数処理（lot 単位で追加配分）。
  - リサーチ / ファクター計算 (kabusys.research)
    - factor_research
      - モメンタム（1/3/6ヶ月リターン、MA200 乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）ファクター計算を DuckDB を使って実装。
      - データ不足判定（ウィンドウ内行数不足時は None を返す等）を考慮。
    - feature_exploration
      - 将来リターン計算（複数ホライズンをサポート）、IC（Spearman ランク相関）計算、ファクター統計サマリを実装。
      - pandas に依存せず標準ライブラリのみで実装。
    - research パッケージの公開 API を整備（zscore_normalize の re-export 等）。
  - ユーティリティ
    - process_priority (kabusys.utils.process_priority)
      - Windows と POSIX(Linux/Mac/FreeBSD) の差を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。
      - 指定コア数で CPU affinity を固定する set_cpu_affinity 実装。
      - アクセス拒否や未サポート API を考慮した警告でのフォールバック実装。
  - ツール
    - paper_verification_report (kabusys.tools.paper_verification_report)
      - Paper Trading 用の検証レポート生成ツールを実装。コマンドライン引数（--from/--to/--db）に対応。
      - 指標: 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数 等を集計して PASS/FAIL 判定を行う。
      - デフォルト閾値を設定（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
  - DB 接続
    - sqlite3（監視 / paper_trading 用）と DuckDB（時系列・調査用）の両方を組み合わせて使用する基盤を整備。
  - ロギング / エラーハンドリング
    - 実行スクリプト・ループでの例外捕捉・ログ出力を追加し、単一エラーがループ全体を止めないように堅牢化。

- Changed
  - 主要スクリプト（run_execution/run_monitoring）は起動時にプロセス優先度を "high" に設定するように変更（set_process_priority を利用）。
  - Settings による環境ごとの DB パス選択ロジック（paper_trading の分離）を導入。

- Fixed
  - .env パーサの堅牢性向上（export prefix、クォート／エスケープ、コメント判定）により環境変数読込の誤動作リスクを低減。
  - run_monitoring の MONITOR_POLL_INTERVAL の不正値に対するフォールバック（0以下や非整数を扱う際のエラー回避）を追加。
  - run_execution / run_monitoring 終了時に sqlite3 / duckdb 接続を確実にクローズするように修正。

- Security
  - OpenAI キーや各種トークンは Settings 経由で環境変数から読み込む設計。未設定時は明示的にエラーを返すかデフォルト空文字列を使う箇所があるため、シークレット管理に注意が必要。

- Known issues / Notes
  - news_nlp は現状で未完の箇所があり、release 0.1.0 時点でプロダクション用途としては未成熟（Unreleased に移行予定）。
  - 一部の TODO（価格フォールバック、銘柄別 lot_size の拡張等）が残っている。
  - DuckDB の executemany に関する挙動（パラメータが空だと失敗する等）を考慮した実装上の注意が散見されるため、大量データ処理部分は実運用前に検証推奨。

貢献・修正履歴の提案
--------------------
- 新機能の追加や修正を行う際は、ChangeLog に該当バージョン（Unreleased → 次のリリース番号）を追加してください。
- 重大なバグ修正やセキュリティ修正は "Fixed" / "Security" セクションで明確に記載してください。

以上。必要であれば、各ファイルごとのより詳細な変更点（関数レベルの説明や既知のバグ箇所のコード参照）を追記します。どの程度の詳細が必要か教えてください。