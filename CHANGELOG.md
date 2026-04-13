Keep a Changelog準拠 — 変更履歴 (日本語)
====================================

このCHANGELOGは、提示されたコードベースの内容から推測して作成しています。実際のコミット履歴に基づくものではなく、コードに現れた新規機能・挙動・注意点をまとめたものです。

v0.1.0 — 2026-04-13
-------------------

Added
- 全体
  - パッケージ初期リリース。モジュール群（実行エンジン、監視、ポートフォリオ構築、研究用ファクター計算、ニュースNLP、ユーティリティ等）を提供。
  - DuckDB と SQLite を併用するデータパイプラインを標準採用（prices_daily / raw_financials 等は DuckDB、監視/発注ログ等は SQLite）。

- 実行 & 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV に応じて paper_trading モードを分離（paper_trading の場合は専用 SQLite を使用し、本番 DB と完全分離）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
    - RiskManager のデフォルト設定を明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value をブローカーの利用可能現金から初期化。
    - プロセス優先度を起動時に High に設定する仕組みを導入（utils.process_priority）。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用する点に注意（コード上の挙動）。
    - DB 初期化（init_monitoring_db）を行い、duckdb も接続して監視を行う。

- 設定管理
  - config.py:
    - .env / .env.local の自動読み込み機能をプロジェクトルート（.git または pyproject.toml を基準）から実装。OS 環境変数を保護するため protected 上書き制御を導入。
    - .env のパースを強化（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
    - Settings クラスを導入し、各種環境変数をプロパティで取得・検証:
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
      - PID/KILL フラグパス、各種閾値（CPU/MEM/DISK）
      - KABUSYS_ENV のバリデーション（development, paper_trading, live）
      - LOG_LEVEL の検証
    - settings = Settings() をエクスポート。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - シグナル選定 (select_candidates)：スコア降順、同点は signal_rank の昇順でタイブレーク。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重）。スコア合計が 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap：既存保有のセクター暴露に基づき、セクター上限超過時に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。未知レジームは 1.0 へフォールバックして WARNING を出力。
  - portfolio/position_sizing.py:
    - calc_position_sizes：複数の配分方式を実装（risk_based / equal / score）。
      - 単元整列（lot_size）で丸め、1 銘柄上限・aggregate cap を適用。
      - cost_buffer を考慮した保守的なコスト見積り、利用可能現金を超えた場合はスケーリングして lot 単位で再配分（残差を利用した追加配分アルゴリズム）を実装。
      - price 欠損や非正の価格はスキップする安全策を採用。

- 研究・特徴量
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB のウィンドウ関数を用いた高効率な SQL 実装。
    - モメンタム・MA200乖離、ATR、平均売買代金、PER/ROE などを計算。
    - データ不足時は None を返す設計。
  - research/feature_exploration.py:
    - calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - calc_ic（Spearman ランク相関の実装。記述通りの tie 処理でランクを算出）。
    - rank、factor_summary（count/mean/std/min/max/median）を実装。
  - research/__init__.py で主要関数を公開し、zscore_normalize（data.stats）を再エクスポート。

- AI / ニュース
  - ai/news_nlp.py:
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとにセンチメントを -1.0〜1.0 でスコア化して ai_scores テーブルへ書き込む機能を実装。
    - 処理フロー:
      - ニュース収集ウィンドウの計算（JST基準 → UTC 変換）
      - 銘柄毎の記事トリム（上限記事数・文字数）
      - 最大 _BATCH_SIZE（20） 件ずつ API 呼び出し
      - 429 / ネットワーク断 / 5xx などに対する指数バックオフリトライ（上限 _MAX_RETRIES）
      - レスポンス検証・スコアクリップ（±1.0）
      - 安全な DB 更新（部分失敗時に既存スコアを保護するためコード絞り込みで DELETE → INSERT）
    - OpenAI API キー未設定時は ValueError を発生させる（api_key 引数または環境変数 OPENAI_API_KEY を参照）。
    - フェイルセーフ設計（API失敗時はスキップして継続する等）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からレポートを生成する CLI ツールを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - 閾値に基づく PASS/FAIL 判定と分かりやすい出力フォーマットを提供。
    - DB 未存在やテーブル欠損時に安全にフォールバックしてレポート作成（OperationalError をキャッチして N/A を扱う）。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows と POSIX を吸収し、簡単にプロセス優先度を設定できるユーティリティを追加。Unsupported OS は警告でスキップ。
    - set_cpu_affinity(cpu_count): プロセスの CPU affinity を設定する補助関数を追加（None は何もしない）。アクセス権限エラー等は警告でスキップ。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI キーや各種重要設定は Settings 経由で環境変数管理を推奨。.env 自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテストやデプロイ環境の安全性に配慮。

注意事項 / Breaking changes（重要）
- run_monitoring.py は「監視用 DB」として Settings.sqlite_path（本番用）を常に使用する実装になっています。環境（KABUSYS_ENV）が paper_trading でも監視は production sqlite_path を参照するため、監視データを分離したい場合は実装の見直しが必要です。
- PAPER_TRADING_SQLITE_PATH を使うのは run_execution.py（paper_trading モード）のみで、paper_trading 以外のコンポーネントはデフォルトの sqlite_path を参照します。
- position_sizing の lot_size 丸めや aggregate cap スケーリングにより、期待する株数が単元切り捨てで減少することがあります。細かな挙動はコメントに記載のアルゴリズムに従います。
- .env の自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。パッケージ配布後やルートが見つからない環境では自動ロードがスキップされます。

今後の提案（推奨改善点）
- ai/news_nlp.py の OpenAI 呼び出し周りでの詳細なエラーハンドリング／メトリクス収集（リトライ統計・レイテンシ等）を強化。
- position_sizing に銘柄別 lot_size マスタを導入し、銘柄ごとの単元対応を可能にする拡張。
- monitoring の DB 参照先を設定可能にして、paper_trading 環境での監視データ分離を明確にする。
- research モジュールのユニットテスト（DuckDB を使った固定データでの回帰テスト）を整備。

以上。必要であれば、この CHANGELOG を英語版にする、あるいは個別の変更点に対して詳細な説明（各関数の入出力例、想定される影響など）を追記します。どの形式を希望しますか。