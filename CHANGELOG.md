CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。日付は本リリース作成日です。

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリース: KabuSys 0.1.0
  - パッケージのメタ情報を追加（src/kabusys/__init__.py）。
- 設定 / 環境変数
  - Settings クラスによる環境変数経由の設定管理を実装（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサは export プレフィックス、クォート文字とバックスラッシュエスケープ、インラインコメント処理をサポート。
  - 環境変数の必須チェック（_require）と各種デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）。
  - 環境（development / paper_trading / live）やログレベルのバリデーションを実装。
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下はデフォルトにフォールバック。
    - 起動時にプロセス優先度を High に設定（utils/process_priority.set_process_priority を使用）。
    - 監視では環境にかかわらず本番 sqlite_path を使用する旨の設計。
    - sqlite（監視 DB）と DuckDB 接続の初期化、例外発生時のログ出力、KeyboardInterrupt の整形終了処理を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager（デフォルト RiskConfig）を組み立て ExecutionEngine を起動。
    - 起動時にプロセス優先度を High に設定。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db の利用により監視テーブルの冪等的作成を保証（run スクリプトで使用）。
- ユーティリティ
  - process_priority モジュール（src/kabusys/utils/process_priority.py）を追加。
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告ログで安全にスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を提供。引数検証・権限エラーは警告で処理。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選別、タイブレークルール実装。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）を実装。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）により候補除外を実施。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull/neutral/bear、未知レジームは警告して 1.0 にフォールバック）。
    - price 欠損時の注意点（TODO コメント）を明記。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。lot_size 単位で丸め、per-stock 上限と aggregate cap（利用可能現金）を実装。投下額超過時はスケールダウンと端数配分ロジックを実装。
    - cost_buffer による手数料・スリッページ考慮。
    - 現状は全銘柄共通の lot_size 前提（将来的に銘柄別拡張の TODO）。
- リサーチ / ファクター計算
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を prices_daily から計算。
    - calc_volatility: ATR20、ATR_pct、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER / ROE を計算（最新レポートを target_date 以前で選択）。
    - DuckDB を利用し SQL ウィンドウ関数で効率的に集計。
  - feature_exploration:
    - calc_forward_returns: 複数 horizon（デフォルト [1,5,21]）で将来リターンを計算。horizons の妥当性検査あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 件未満は None）。
    - rank / factor_summary: ランク化・統計サマリー（count/mean/std/min/max/median）を実装。
    - 標準ライブラリのみで実装（pandas 等に非依存）。
- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し銘柄別センチメント（-1.0〜1.0）を ai_scores に書き込むワークフローを実装。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス JSON の厳密バリデーション、スコアの ±1.0 クリップ、部分失敗に対する保護（該当コードのみ差し替え）等を実装。
    - OpenAI API キー未設定時は ValueError を送出。
    - ニュース集計時間ウィンドウは JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
- 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどの指標を計算して PASS/FAIL 判定を行う閾値を定義（デフォルト閾値をソース内に明記）。
    - --from / --to / --db コマンドラインオプション対応。DB 存在チェック・例外耐性あり。
- モジュールエクスポート
  - portfolio / research パッケージの __init__ に主要関数を公開するエクスポートを追加。

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされセクター上限チェックを正しく行えない可能性がある（TODO コメントあり）。
- position_sizing:
  - 現状は全銘柄共通 lot_size（例: 100）を前提。将来的な銘柄別 lot_size サポートは未実装。
- process_priority:
  - OS 標準でサポートされていない環境や権限不足時は設定をスキップして警告ログを出力する設計。
- ai/news_nlp:
  - OpenAI API キーが必須。外部 API 障害時はリトライするが最終的には部分失敗を許容して続行するフォールトトレラント設計。
- run_monitoring:
  - 監視は設計上「環境に依存せず本番 sqlite_path を使用」するため、意図的に本番監視 DB を参照する点に注意。

今後の検討事項（ソース内 TODO より）
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価等）実装。
- position_sizing の銘柄別 lot_size サポート。
- ai/news_nlp のより詳細なレスポンスバリデーション／ロギング強化。
- DuckDB のバージョン依存挙動（executemany 等）を含む互換性向上。

--- 

（注）この CHANGELOG はソースコード内のドキュメント文字列・コメント・実装内容から推測して作成しています。実際のプロジェクト管理での変更履歴と差異がある場合があります。