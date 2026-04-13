CHANGELOG
=========

このプロジェクトの変更履歴は「Keep a Changelog」準拠で記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回公開リリース（v0.1.0）。
- 全体
  - パッケージエントリポイントとバージョン管理（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ処理基盤を前提にした各種モジュール実装。
  - .env ファイルの自動読み込み機能（プロジェクトルート検知: .git または pyproject.toml、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。読み込みは .env → .env.local の順で、OS 環境変数は上書き保護。
  - Settings クラスを通じた環境変数ベースの設定管理（各種パス、閾値、環境判定プロパティなど）。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。

- 実行 / 監視
  - run_execution: ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を利用し本番 DB と分離する設計（コメントに MockBrokerClient の利用を明記）。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値は警告してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動を明示。
    - 起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み算出。スコア合計が 0 の場合は等配分にフォールバックして警告を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中度チェックによる候補除外ロジック（売却予定銘柄をエクスポージャー計算から除外可能、"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未定義レジームは警告の上 1.0 にフォールバック）。コード中に設計コメント（Bear レジームで BUY シグナルが出ない旨の注意）。
    - apply_sector_cap 内に将来的な価格フォールバックの TODO コメントあり（欠損価格による過小見積への注意喚起）。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく株数決定、単元株丸め（lot_size）、per-position・aggregate 上限、cost_buffer を考慮したスケールダウンロジックを実装。スケールダウン時は残差に基づく再配分ロジックを備える。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算。true_range の NULL 伝播制御を注意深く実装。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の計算（target_date 以前の最新財務レコードを取得）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。horizons の入力検証あり（1〜252 営業日）。
    - calc_ic / rank: Spearman ランク相関（IC）計算、ランク付け（同順位は平均ランク）を実装。IC は有効レコードが 3 件未満で None を返す。
    - factor_summary: count/mean/std/min/max/median の基本統計を純粋関数で算出（None 値を除外、標準ライブラリのみで実装）。
  - research パッケージは zscore_normalize（kabusys.data.stats 依存）などをエクスポート。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を実装。
    - タイムウィンドウの算出（JST ベース、UTC へ変換）、raw_news と news_symbols の集約、1 銘柄あたりのトークン肥大化対策（記事数と文字数の上限）。
    - 最大 20 銘柄／チャンクでのバッチ送信、429/ネットワーク/5xx に対する指数バックオフでのリトライ、レスポンスの厳格なバリデーション、スコア ±1.0 のクリップ。
    - 部分成功時でも既存スコアを保護するため、更新対象コードを絞って DELETE→INSERT を行う方針（executemany 前にパラメータが空でないことを確認する注意書き）。
    - API キー未設定時は ValueError を送出する（api_key 引数または環境変数 OPENAI_API_KEY を参照）。
    - 実装にはフェイルセーフ（API 失敗時はスキップして処理継続）やバッチ処理ログ出力を含む。

- ユーティリティ
  - config._parse_env_line/_load_env_file: export プレフィックス、クォート文字列（バックスラッシュエスケープ対応）、コメントの扱い、上書き制御（protected）等に対応した .env パーサ実装。
  - utils.process_priority:
    - set_process_priority: Windows (psutil の HIGH_PRIORITY_CLASS 等) と POSIX (nice 値) を吸収して優先度を設定。未対応 OS や権限不足時は警告してスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定するユーティリティ（引数検証、権限不足時のログ処理あり）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポートを生成する CLI スクリプト（--from, --to, --db オプションをサポート）。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を計算し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 ≤ 200ms）に基づく PASS/FAIL 判定を出力。
    - DB 存在チェック、テーブル欠損時のハンドリング（sqlite3.OperationalError を捕捉して N/A や 0 を返すフォールバック）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは明示的に引数または環境変数で提供する必要があり、未設定時は例外を発生させる設計。機密情報の取り扱いは .env と環境変数に依存。

Notes / Known issues / TODO
- apply_sector_cap 内に「price が欠損（0.0）の場合のフォールバック価格を将来的に導入する」旨の TODO が存在。現状だと欠損価格によってエクスポージャーが過小見積りされ、セクター制限の判定が緩くなる可能性がある。
- news_nlp モジュールは堅牢性を重視しているが、API レスポンス処理の一部実装（大きなレスポンスの部分的失敗時の挙動等）は注意が必要。DuckDB における executemany の制約への注意コメントあり。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存のため、環境によって効果が得られない場合がある（警告ログを出力してスキップする）。
- 一部モジュールの動作は外部データ（prices_daily, raw_financials, raw_news など）に依存するため、適切なスキーマとデータ整備が前提。

作者注
- 各モジュール内には設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）の参照や将来的な拡張メモが含まれています。実運用前に各設定値（閾値・lot_size・cost_buffer・レジーム乗数等）を調整してください。

---