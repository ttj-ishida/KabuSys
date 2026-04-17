CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys コア機能群を追加しました。
  - 実行・監視ランナー
    - run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、エンジンのデーモンスレッド起動・停止処理を実装。
      - 起動時・実行中の停止判定に data/stop_requested.flag を使用し、PID ファイル管理（data/execution.pid）をサポート。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit 等）を含む初期構成を実装。
    - run_monitoring.py
      - SystemMonitor をポーリングで実行する監視ループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を "high" に設定する処理を実行（set_process_priority 使用）。
      - 監視ループ内での例外を捕捉して次のポーリングまで待機する耐障害性を実装。
  - 設定・環境変数管理
    - config.py
      - .env / .env.local の自動読み込み機能を実装（優先順位: OS 環境 > .env.local > .env）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
      - OS 環境変数を保護するため protected オプションを導入（.env.local で既存 OS 変数を上書きしない等を実現）。
      - Settings クラスを追加し、各種環境変数（JQUANTS, KABU API, LINE, DB パス, 監視閾値, PAPER_FILL_MODE 等）を取得・バリデーションするプロパティを提供。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
      - KABUSYS_ENV / LOG_LEVEL 等の許容値チェックを実装。
  - ポートフォリオ関連（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア順・signal_rank タイブレーク）、等金額配分、スコア加重配分（スコア合計が0のとき等配分へフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が上限を超える場合に新規候補を除外。
      - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear、および未知レジームでのフォールバック）。
    - portfolio/position_sizing.py
      - allocation_method に基づく株数計算を実装（risk_based / equal / score）。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮。
      - price 欠損時のスキップ、各種安全弁（max_per_stock 等）を導入。
  - 研究・リサーチ機能（DuckDB ベース）
    - research/factor_research.py
      - Momentum / Volatility / Value ファクター計算を追加（prices_daily / raw_financials テーブル参照）。MA200, ATR20, 1/3/6M リターンなどを計算。
      - SQL でのウィンドウ関数活用により効率的に計算し、データ不足時は None を返す堅牢な設計。
    - research/feature_exploration.py
      - 将来リターン（calc_forward_returns）、IC（calc_ic: スピアマンランク相関）、ランク付けユーティリティ、ファクター統計サマリーを追加。
      - pandas に依存せず標準ライブラリのみで実装。ties の平均ランク処理や丸めによる ties 検出強化を行う。
    - research/__init__.py に主要関数をエクスポート。
  - AI ニュース NLP（OpenAI 統合）
    - ai/news_nlp.py（実装途中まで）
      - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む設計を追加。
      - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST → UTC に変換）やバッチサイズ、トークン肥大化対策（記事数・文字数トリム）、リトライ・バックオフ戦略、レスポンスバリデーション、スコア範囲クリップ等を設計。
      - API キー未指定時は例外を送出する（score_news）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成ツールを追加（CLI: --from / --to / --db）。
      - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計し、閾値判定（稼働率 99%, 成功率 90% 等）で PASS/FAIL を出力。
      - P95 計算ユーティリティ、SQL の日付フィルタ生成、安全な OperationalError ハンドリングを実装。
  - ユーティリティ
    - utils/process_priority.py
      - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
      - set_cpu_affinity による CPU affinity 固定機能を追加。
      - 権限不足や未サポート環境での例外を穏やかにログに落として処理継続する設計。

Changed
- パッケージ初期化でバージョン情報を追加（kabusys.__init__.__version__ = "0.1.0"）。
- research パッケージに zscore_normalize（kabusys.data.stats）等を組み合わせた公開 API を定義。

Fixed / Robustness
- .env パーサーの改善
  - クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメント処理を正しくサポート。
  - 空行・コメント行を無視するロジックを実装。
- run_monitoring のポーリング間隔取得で不正値にフォールバックする処理を追加し、time.sleep に渡す不正な値による例外を防止。
- position_sizing / portfolio ロジックで価格欠損時にスキップする等、実運用での欠損データ耐性を強化。
- research.feature_exploration.rank において丸め（round(..., 12)）を導入し、浮動小数点の丸め誤差による ties 判定漏れを低減。
- utils/process_priority の権限・未実装例外に対して警告ログを出し処理を継続するように改善。

Known issues / Notes
- ai/news_nlp.py はファイル末尾で切れており（処理フローの続きが未収録）、完全実装は別途必要。
- portfolio.risk_adjustment.apply_sector_cap 内で price が 0.0（欠損）の場合にエクスポージャーが過少見積もられる旨の TODO コメントあり。将来的に前日終値や取得原価でフォールバックする検討が必要。
- DuckDB を使用するクエリは prices_daily / raw_financials / ai_scores 等の所定テーブルを前提としています。実行環境でのスキーマ整備が必要です。
- ExecutionEngine / SystemMonitor 等の内部実装（別ファイル）はこの差分一覧に含めていません。実行時は各コンポーネントの依存（DB スキーマ、BrokerClient 実装、OpenAI キー等）を満たしてください。

参考: 環境変数とデフォルト
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: data/monitoring.db（監視用 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の専用 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60。正の整数であること）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の埋め方挙動）
- OPENAI_API_KEY: news_nlp に必要

今後の予定（例）
- ai/news_nlp の残り実装（API バッチ送信・レスポンス検証・DB 書き込み）。
- position_sizing の lot_size を銘柄別に扱う拡張（stocks マスタ導入）。
- セクターエクスポージャー算出での価格フォールバックの改善。
- テストカバレッジの拡充（特に DB 絡みのユニット／統合テスト）。

--------------------
この CHANGELOG はコードから推測して作成しています。実際のコミット履歴や意図と異なる場合がありますので、必要に応じて調整してください。