# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。
このファイルでは主に機能追加・設計意図・注意点（破壊的変更）を日本語でまとめます。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- パッケージ初期リリース相当の主要機能群を追加：
  - kabusys パッケージのエントリポイントとバージョン（__version__ = "0.1.0"）。
  - 環境設定管理モジュール（kabusys.config.Settings）：
    - .env / .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - export KEY=val 形式、クォート文字列、インラインコメントの取り扱いなどを考慮した .env パーサ実装。
    - 必須環境変数取得用の _require と、各種設定プロパティ（J-Quants、kabuAPI、LINE、DB パス、監視設定、しきい値等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - env/log_level 等の値検証（有効値チェック）を実装。
  - 実行制御ユーティリティ（kabusys.utils.process_priority）：
    - プラットフォーム非依存でプロセス優先度（high/normal/low）を設定する set_process_priority。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity。
    - アクセス権限不足や未サポート環境を考慮してログ警告でフォールバック。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）：
    - プロセス優先度を高に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db か PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動およびスレッド運用を実装。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルト化。
    - 実行中の停止制御（data/stop_requested.flag の検知で engine.stop() を呼び出す）と実行 PID 保持（data/execution.pid）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の設計（監視データは本番 DB を参照）。
    - SystemMonitor を用いた check_once の定期実行、例外はログに出力して次回ポーリングへ継続。
    - 停止フラグ（data/stop_requested.flag）とプロセス優先度設定。
  - 監視 DB 初期化ユーティリティ（monitoring_db を呼び出す初期化処理）は起動時に冪等に実行。
  - portfolio モジュール：
    - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）：
      - select_candidates（スコア降順、signal_rank によるタイブレーク）
      - calc_equal_weights（等金額配分）
      - calc_score_weights（スコア正規化／全スコア 0 の場合は等配分へフォールバック）
    - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）：
      - apply_sector_cap（既存保有をセクター別に計算し上限超過セクターの新規候補を除外、"unknown" セクターは除外対象外）
      - calc_regime_multiplier（"bull" / "neutral" / "bear" -> 1.0 / 0.7 / 0.3、未知レジームは 1.0 でフォールバック）
    - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）：
      - calc_position_sizes（allocation_method="risk_based" / "equal" / "score" をサポート）
      - 単元（lot_size）丸め、per-position と aggregate のキャップ、cost_buffer を用いた保守的コスト見積り、投下金額超過時のスケーリングと端数配分ロジックを実装。
  - research モジュール（kabusys.research）：
    - ファクター計算（kabusys.research.factor_research）：
      - calc_momentum（1M/3M/6M リターン、MA200 乖離）
      - calc_volatility（20日 ATR、ATR 比・20日平均売買代金・出来高比率）
      - calc_value（PER / ROE。raw_financials から最新報告を取得）
      - 各関数は DuckDB 接続を受け prices_daily / raw_financials を参照する純関数として設計。
    - 特徴量探索（kabusys.research.feature_exploration）：
      - calc_forward_returns（複数ホライズンの将来リターン計算、horizons のバリデーション）
      - calc_ic（ファクターと将来リターンのスピアマン rank 相関（IC）計算）
      - rank（同順位は平均ランク）
      - factor_summary（count/mean/std/min/max/median）
    - zscore_normalize を含むエクスポートの統合（kabusys.research.__init__）。
  - ai ニュース NLP モジュール（kabusys.ai.news_nlp）：
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、429/5xx/ネットワーク障害に対する指数バックオフによるリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードのみ置換）等の設計を導入。
    - news ウィンドウ算出 util（calc_news_window）を実装（JST ベースの前日15:00～当日08:30 を UTC naive datetime に変換）。
  - ツール群（kabusys.tools）：
    - paper_verification_report（kabusys.tools.paper_verification_report）を追加：
      - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）に対して稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
      - CLI 引数 --from / --to / --db をサポート。
      - 判定基準（しきい値）を次の通り定義：
        - 稼働率 >= 99.0%
        - 注文成功率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
      - 各種 SQL クエリに対する OperationalError を保護してフォールバック。
  - パッケージの __all__ エクスポートを整理（portfolio / research 等）。

### Changed
- （初回リリースのため変更履歴はなし。将来のバージョンで差分を記載予定）

### Fixed
- （初期実装。既知の既定値やエラー処理を含むが、バグ修正は未適用）

### Breaking Changes / Important notes
- 監視（run_monitoring）は設計上、KABUSYS_ENV の値にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します。監視データを paper_trading 用 DB と分離したい場合は注意してください。
- run_execution は paper_trading 環境（KABUSYS_ENV=paper_trading）の場合に paper_sqlite_path を使用して DB を分離します。運用環境では意図した DB パスが設定されていることを確認してください。
- .env の自動読み込みはデフォルトで有効です。テストや特殊環境で自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API キーは明示的に api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は news_nlp.score_news が ValueError を投げます。
- process_priority / cpu_affinity はプラットフォームや権限に依存します。設定に失敗した場合は警告ログを出力してフォールバックします。

### Security
- OpenAI API キーは環境変数や引数で扱う設計です。ログや標準出力にキーを出力しないよう実装上配慮していますが、運用上の秘匿管理に注意してください。

---

今後のリリースでは以下を検討：
- position_sizing の lot_size を銘柄別にサポートする拡張（stocks マスタの導入）。
- price の欠損時に前日終値や取得原価でフォールバックする改善（risk_adjustment の TODO に記載）。
- ai.news_nlp の完全実装（ファイル末尾が途中で切れているため、フェッチ・API 呼び出し・DB 書き込み処理の最終フローを完成）。
- 単体テスト・統合テストの整備とドキュメント・使用例の追加。

以上。