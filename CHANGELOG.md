# CHANGELOG

すべての注目すべき変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

注: この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートではありません。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 実行・監視起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時には paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）と MockBrokerClient を使用する設計。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による起動／停止制御。
    - ExecutionEngine を別スレッドで実行し、停止フラグを検知すると安全に停止するループを実装。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てる処理を追加。
    - RiskManager 初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検出と例外時のログ出力を実装。
- 設定管理モジュールを追加（config.py）。
  - .env 自動読み込み（プロジェクトルート探索: .git または pyproject.toml 基準。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env ファイルパーサ（export プレフィックス・クォート内エスケープ・インラインコメント対応）。
  - 必須 env 取得ヘルパー (_require) と Settings クラス。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / paper trading 用設定 / 監視閾値 / 環境判定など）。
  - PAPER_FILL_MODE および KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）。
  - portfolio_builder.py
    - select_candidates（スコア降順選定）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合のフォールバック）を実装。
  - risk_adjustment.py
    - apply_sector_cap（セクター集中制限、既存保有を踏まえた候補除外）、calc_regime_multiplier（market regime による投下資金乗数）を実装。
  - position_sizing.py
    - calc_position_sizes（risk_based / equal / score の各配分方式、単元株丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer 対応）を実装。
- 研究・リサーチモジュールを追加（kabusys.research）。
  - factor_research.py
    - calc_momentum（1/3/6 か月リターン、MA200 乖離）、calc_volatility（ATR20、相対ATR、20日平均売買代金等）、calc_value（PER / ROE の計算）を DuckDB を用いて実装。
  - feature_exploration.py
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計量）、rank（平均ランクによる同値処理）を実装。
  - research パッケージ __all__ を通じて主要 API をエクスポート。
- AI ニュース NLP モジュールを追加（kabusys.ai.news_nlp）。
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ問い合わせし、銘柄ごとの ai_score を ai_scores テーブルに書き込むフローを実装（バッチサイズ・トークン肥大化対策・429/5xx/タイムアウトに対する指数バックオフ・レスポンスバリデート・スコアクリップ等）。
  - ニュース収集ウィンドウ計算（JST→UTC 変換）を実装。
  - 実装はフェイルセーフ（API キー未設定で ValueError、API エラーはリトライ / スキップ）を想定。
  - （注: 提供コードは途中で切れており、_fetch_articles 等の実装が続く想定）
- ユーティリティを追加（kabusys.utils）。
  - process_priority.py
    - set_process_priority（Windows / POSIX を吸収して優先度設定）、set_cpu_affinity（最初 N コアに固定）を実装。権限不足等で失敗した場合はログで警告してスキップするフェイルセーフあり。
- ツール／レポートを追加（kabusys.tools.paper_verification_report）。
  - Paper Trading 検証レポート生成コマンドラインツールを実装。
  - 指標: 稼働率 (uptime)、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値を定義）。
  - 日付フィルタ (--from / --to) と DB パス指定 (--db) をサポート。
- DB 初期化・統合
  - SQLite（監視用 / Paper Trading 用）と DuckDB（時系列・リサーチ用）の接続を各起動スクリプトで使用。
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

### 変更 (Changed)
- ログ出力・例外ハンドリングを強化。
  - long-running プロセス（監視・実行）での KeyboardInterrupt や予期しない例外に対してログを残し、接続をクローズして終了するように調整。
- .env の自動読み込み優先順位を定義（OS 環境 > .env.local > .env）。OS 環境を保護する protected セットを導入。

### 修正 (Fixed)
- 入力検証とフォールバックを多くの箇所で追加:
  - MONITOR_POLL_INTERVAL が不正（0以下や非数）の場合は警告を出してデフォルトを使用。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの環境変数に対する不正値チェックを追加。
  - ファクター計算・レポート集計でデータ不足時に None を返すなど、NULL 安全性を意識した実装。
- position_sizing の aggregate cap スケーリングで端数処理を安定化（lot_size 単位での再配分ロジックを実装）。

### 既知の制限 (Known issues)
- ai.news_nlp の本文は途中で切れており、記事フェッチ（_fetch_articles）や DB への書込の完全実装は別途必要。現状は設計概要と一部処理が実装済み。
- 一部関数に TODO コメントあり（例: price のフォールバック戦略や lot_size の銘柄別対応など）。
- 単体テストや統合テストのコードは同梱されていないため、実運用前に十分なテストが必要。
- Windows / POSIX でのプロセス優先度変更や CPU affinity の挙動は権限・環境に依存する箇所があるため、実行環境での確認が必要。

### セキュリティ (Security)
- OpenAI API キーは明示的に指定するか環境変数 OPENAI_API_KEY を利用する設計。API キー未設定時は例外を送出するため、運用時に漏洩しないよう環境変数管理を行ってください。

---

これは初期リリース相当の想定 CHANGELOG です。必要であれば各モジュールごとのより詳細な項目（例: 各関数の挙動、引数・戻り値の変更履歴、設計上の注意点）を追加して拡張できます。どの粒度で記録したいか指示してください。