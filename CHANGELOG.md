# Changelog

すべての変更は「Keep a Changelog」フォーマットに従います。  
日付はリリース日 (2026-04-11) を使用しています。

## [0.1.0] - 2026-04-11

### 追加 (Added)
- 基本パッケージ初期リリース: kabusys v0.1.0 を追加。
  - __version__ = "0.1.0"
  - パッケージの主要サブパッケージとして data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の行パーサ実装（export プレフィックス、クォート文字列、インラインコメント、バックスラッシュエスケープ対応）。
  - 環境変数必須チェック用 _require 関数。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB / 監視 / システム設定など多数のプロパティ）。
  - 多数の環境変数デフォルト値とバリデーション:
    - KABUSYS_ENV: development / paper_trading / live（無効値で例外）
    - LOG_LEVEL: デフォルト INFO（有効値チェック）
    - DB パス: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - Paper Trading 用 SQLITE: PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
    - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: "instant"）
    - 監視用ファイルパス: PID_FILE_PATH, KILL_FLAG_PATH 等
    - しきい値: CPU/MEM/DISK の閾値

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を最初に "high" に設定（utils の set_process_priority 利用）。
    - SQLite / DuckDB 接続を確立し、終了時にクローズ。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の PAPER_TRADING_SQLITE_PATH を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成（モック対応）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine を起動。
    - 起動時にプロセス優先度 "high" を設定。

- 監視系ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level) を実装（Windows / POSIX 差分吸収）。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピン留め可能。
    - アクセス権限エラー等の失敗は警告ログでフォールバック。

- ポートフォリオ構築（純粋関数群、DB 参照無し）
  - kabusys.portfolio.portfolio_builder
    - select_candidates(buy_signals, max_positions): スコア降順で候補選定（タイブレークに signal_rank）。
    - calc_equal_weights(candidates): 等金額配分。
    - calc_score_weights(candidates): スコア加重配分（全銘柄のスコアが 0 の場合は等配分へフォールバック）。

  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap(...): セクター集中制限に基づき新規候補を除外（unknown セクターは除外対象外、当日売却予定は除外して計算）。
    - calc_regime_multiplier(regime): レジーム (bull/neutral/bear) に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3、未知は警告して 1.0 フォールバック）。

  - kabusys.portfolio.position_sizing
    - calc_position_sizes(...): allocation_method ("risk_based", "equal", "score") 対応の株数決定ロジック。
    - 単元株数 lot_size（デフォルト 100）への丸め、per-position 上限や aggregate cap（available_cash）によるスケーリング、cost_buffer を使った保守的コスト見積り、残余キャッシュを用いた端数処理（優先度に基づく lot 単位の追加配分）を実装。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと MA200 乖離を計算（DuckDB SQL ベース）。
    - calc_volatility(conn, target_date): ATR20、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER / ROE を計算。

  - kabusys.research.feature_exploration
    - calc_forward_returns(conn, target_date, horizons): 将来リターン計算（ホライズン検証あり）。
    - calc_ic(factor_records, forward_records, ...): Spearman ランク相関による IC 計算（有効レコード 3 件未満で None）。
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリー。
    - rank(values): 同順位は平均ランクで処理（丸め誤差対策あり）。

  - research パッケージの __init__ で zscore_normalize (kabusys.data.stats) を再エクスポート。

  - DuckDB を使った SQL + Python の実装方針により外部ライブラリ（pandas 等）に依存しない設計。

- AI 関連
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) による銘柄別センチメント評価を行い、ai_scores テーブルへ書き込む機能を提供。
    - タイムウィンドウ計算（target_date に対する前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で明示的に実装（ルックアヘッドバイアス防止のため datetime.today() を直接参照しない）。
    - バッチ処理（最大 20 銘柄）・記事数制限・文字数トリムを実装。
    - API 呼び出しの堅牢性: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ、その他エラーはスキップしてフェイルセーフに動作。
    - レスポンス検証: JSON 抽出・"results" リスト・code と score の検証、コード正規化、スコアの ±1.0 クリップ。
    - DuckDB への書き込みは冪等性を考慮してトランザクション (BEGIN/DELETE/INSERT/COMMIT) で実施。DuckDB の executemany の制約（空リスト不可）を回避する実装。
    - OpenAI クライアントの呼び出し部分は _call_openai_api に分離（テスト容易性のため patch 可能）。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull'/'neutral'/'bear'）を判定。
    - マクロニュースはキーワードベースで抽出し、最大記事数制限を設けた上で LLM で評価。API 失敗時は macro_sentiment = 0.0 として処理を継続。
    - ma200_ratio が算出不可（データ不足）な場合は中立値 1.0 を採用してフォールバック。
    - 判定結果を market_regime テーブルへ冪等的に書き込み。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の取得処理では 0 以下や非整数値を検出した場合にデフォルトへフォールバックし、ログで警告するように実装（run_monitoring）。
- DuckDB への executemany 実行における空リスト制約を回避するための防御的実装を追加（news_nlp）。

### 注意事項 / 設計上の留意点
- 多くの機能は DuckDB / SQLite の既存テーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）を前提としている。テーブルスキーマとデータ投入は別途整備が必要。
- AI 系（news_nlp / regime_detector）は外部 API（OpenAI）に依存する。API キーは引数または環境変数 OPENAI_API_KEY を使用。
- 日付・時刻処理はルックアヘッド（将来データ参照）を避ける設計になっている。target_date ベースでの明示的なウィンドウ指定を行うこと。
- run_monitoring は監視処理の DB に常に本番 sqlite_path を使用する点に注意（test / paper_trading と分離したい場合は運用側で対応）。

### セキュリティ (Security)
- 現時点でセキュリティ修正の記載はなし。

---

今後のリリースでは、テストカバレッジ、エラー監視の強化、パフォーマンス最適化、銘柄別 lot_size 対応（stocks マスタの導入）などを予定しています。