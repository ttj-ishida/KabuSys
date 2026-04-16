# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
語彙は日本語で記載しています。

なお、本 CHANGELOG はソースコードの内容から推測して作成しています（実装コメント・ログメッセージ・関数署名等に基づく記述）。

## Unreleased

（なし）

---

## [0.1.0] - 2026-04-16

初回公開リリース。自動売買システム KabuSys の基礎機能を実装しました。以下の主要機能・モジュールを含みます。

### Added

- 基盤
  - パッケージのバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数・設定管理を実装。
    - .env / .env.local の自動読み込み（OS 環境変数を保護する override/protected 機構）。
    - .env の柔軟なパース（コメント、export プレフィックス、クォート内エスケープ対応）。
    - 必須環境変数取得ヘルパー _require() と各種バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視関連パス（PID ファイル、kill フラグ等）をプロパティとして提供。

- 実行 / エンジン周り
  - run_execution.py: 実行エンジン起動スクリプト。
    - プロセス優先度設定（High）を起動時に実行。
    - Paper Trading（KABUSYS_ENV=paper_trading）時には paper_trading 用 SQLite を使用し、本番 DB と完全分離。
    - Broker クライアントのファクトリ利用（BrokerClientFactory）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行、外部 stop フラグ（data/stop_requested.flag）検知で安全停止。
    - RiskManager の初期設定パラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）をサンプル実装。

- 監視
  - run_monitoring.py: システム監視ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV に関係なく本番 sqlite_path を使用（監視情報の一元化）。
    - stop フラグ検知でループを終了、例外ハンドリングで次ポーリングまで継続。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights（score 合計が 0 の場合は等分配へフォールバック、警告あり）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限の適用。既存保有の時価ベースでセクター露出を算出し、上限超過セクターの新規候補除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告と共に 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数決定（allocation_method: risk_based / equal / score）。
      - 単元（lot_size）丸め、per-stock 上限・aggregate キャップ調整、cost_buffer（手数料等）考慮、資金不足時のスケーリング＆端数配分アルゴリズムを実装。

- 研究（Research）機能
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の算出（DuckDB + prices_daily を利用）。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比等の算出。
    - calc_value: raw_financials から株価指標（PER, ROE）を計算。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで取得。horizons 入力検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）の実装（ties を平均ランクで処理）。
    - rank / factor_summary: ランク付けユーティリティと基本統計サマリ関数。
  - research パッケージは kabusys.data.stats の zscore_normalize を再輸出。

- AI / ニュース NLP
  - ai.news_nlp
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を実装。
    - 機能: ニュースウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC で変換）、バッチサイズ・トークン対策、最大リトライ（429/5xx/タイムアウト）と指数バックオフ、レスポンス検証、スコアクリッピング、部分失敗時の安全な DB 更新戦略（対象コードのみ置換）等。
    - OpenAI API キー未設定時は明示的なエラー（ValueError）を返す。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）等。閾値判定と PASS/FAIL 判定を出力。
    - P95 計算ユーティリティ、期間フィルタリング、DB 存在チェック等を実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定。アクセス権限や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定数の CPU コアにプロセスをピン止め（権限エラーは警告でスキップ）。

### Changed

- （初回リリースのため該当なし）

### Fixed

- .env 読み込み処理で読み込み失敗時に警告を出すようにした（IOError の場合に warnings.warn）。
- 環境変数の不正値に対するフォールバックとログ出力を追加（例: MONITOR_POLL_INTERVAL の不正値 → デフォルト 60 秒、PAPER_FILL_MODE の不正値 → ValueError、KABUSYS_ENV の不正値 → ValueError）。

### Known issues / 注意点

- news_nlp は OpenAI API を利用するため、実行環境に OPENAI_API_KEY（または明示的な api_key 引数）の設定が必須です。未設定時は score_news() が ValueError を投げます。
- apply_sector_cap の注記: price_map に価格が欠損（0.0）がある場合、エクスポージャーが過少見積りとなりブロックが外れる可能性があるため、将来的に価格フォールバック（前日終値等）の導入を検討する旨の TODO コメントがあります。
- position_sizing のロジックは全銘柄共通の lot_size（デフォルト 100）を前提としており、将来的に銘柄別 lot_map への拡張が想定されています。
- DuckDB を利用するリサーチ系・AI系処理はテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores 等）のスキーマ整備が前提です。実行前に必要テーブルが存在することを確認してください。

---

今後の予定（例）
- Engine / BrokerClient の具体的な実装例（kabuステーション接続や MockBrokerClient のテスト補助など）の追加。
- 単体テスト・統合テストの充実化。
- 銘柄毎の lot_size 対応、価格フォールバックロジック、news_nlp のより堅牢な部分失敗復旧など。