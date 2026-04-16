CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」のフォーマットに準拠しています。
重要な変更点はセクション別にまとめています（Added / Changed / Fixed / Removed / Security）。

Unreleased
----------

（現在のところ未リリースの項目はありません）

0.1.0 - 2026-04-16
-----------------

Added
- 初回リリース: KabuSys の基本機能群を追加しました。
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 実行用エントリスクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - エンジンはスレッドで稼働し、プロジェクトルート下の停止フラグ (data/stop_requested.flag) を検知して安全停止。
    - デフォルトのリスク設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
- 監視用エントリスクリプトを追加
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値時はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一元管理）。
    - 停止フラグによりループを終了。例外はログ出力して次ポーリングに継続。
- 設定・環境読み込み機能を追加
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml を起点）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env パーサは export 形式、クォート文字列、インラインコメント（条件付き）に対応。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）と便利な Path 型プロパティを提供。
- ポートフォリオ構築ロジック（純粋関数群）を追加
  - src/kabusys/portfolio/portfolio_builder.py
    - 信号のソート（score 降順 / signal_rank による同点ブレーク）および候補選定 select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター露出を計算して新規候補を除外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear に基づく乗数、未知レジームは警告の上フォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method による株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、銘柄ごとの上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り。
- 研究・リサーチ機能を追加（DuckDB を利用）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリューのファクター計算（prices_daily / raw_financials を利用）。
    - 各関数は DuckDB 接続を受け取り SQL で効率的に計算。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク化ユーティリティを実装。
    - 外部ライブラリに依存せず純 Python で実装。
- AI ニュース NLP スコアリング機能を追加
  - src/kabusys/ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 最大バッチサイズ、文字数・記事数トリム、エクスポネンシャルバックオフによる再試行、レスポンス検証、スコアクリップ、部分更新時の安全な DB 書き換え戦略（削除→挿入）を実装。
    - タイムウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30）を提供し、ルックアヘッドバイアスを回避。
- ユーティリティを追加
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収したプロセス優先度設定。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定（AccessDenied 等はログ警告でスキップ）。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト（CLI）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を行う。デフォルトの閾値を定義。
    - --from/--to/--db オプションをサポート。DB が存在しない場合はエラーメッセージを出力。
- DB 初期化ヘルパー
  - 監視用 DB の初期化を行う init_monitoring_db を各起動スクリプトから呼び出し（冪等に保証）。

Changed
- パッケージ公開方針として、研究・解析関数は DuckDB のみを参照し、発注・本番 API へアクセスしない設計に統一。
- 環境変数ロードの優先度を明確化（OS 環境 > .env.local > .env）。OS 環境キーは protected として .env による上書きを防止。

Fixed
- .env パースの堅牢化
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを改善。
- calc_score_weights のゼロスコアケースで警告出力と等配分フォールバックを実装。
- calc_position_sizes のスケーリングと単元丸めロジックで、残余キャッシュによる lot_size 単位での追加配分を実装（再現性のため二次キーに code を使用）。
- utils/process_priority の未対応 OS と権限不足時の安全動作（警告ログでスキップ）を追加。
- run_monitoring の MONITOR_POLL_INTERVAL 不正値時のフォールバック（ログ警告）を追加。

Removed
- 該当なし（初回リリース）

Security
- 該当なし（このリリースで新たに導入されたセキュリティ問題は報告されていません）。
  - 注意: OpenAI API キーは環境変数または明示的引数で渡す設計。キー管理は運用で適切に実施してください。

Notes / 備考
- 多くのコンポーネントは外部リソース（SQLite / DuckDB / ブローカー API / OpenAI）に依存します。実行時には環境変数の設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）とデータベースファイルの存在を確認してください。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます。テスト時やカスタム環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- 今後の予定: lot_size を銘柄別に設定する拡張や価格フォールバック（前日終値等）の導入、AI モデルの冗長化・メトリクス強化などを検討しています。

もし、リリースノートの粒度（もっと詳細なファイル別の変更やコミット参照、互換性注記など）を追加希望であれば教えてください。