CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
タグ付け: [Unreleased] / [0.1.0] など。

## [Unreleased]

（現時点での未リリース変更はありません）

## [0.1.0] - 2026-04-16
初回リリース。日本株自動売買システム KabuSys のコア機能群を実装しました。

### 追加 (Added)
- 基本設定・環境変数読み込み機能を追加
  - kabusys.config.Settings クラスを実装。多数の設定プロパティ（DB パス、API トークン、監視しきい値、環境種別など）を提供。
  - プロジェクトルート検出(_find_project_root)および .env / .env.local の自動読み込みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 環境変数未設定時に例外を出す _require() ユーティリティを提供。

- 実行・監視プロセス起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、Engine の起動と停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) のサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトへフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 監視 DB 初期化フック (monitoring_db.init_monitoring_db) への統合（存在チェック・冪等に対応）。

- プロセス優先度 / CPU アフィニティ ユーティリティを追加
  - kabusys.utils.process_priority.set_process_priority(level)
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収して優先度を設定。
    - アクセス権限不足や未対応 OS を安全にスキップするログ出力あり。
  - set_cpu_affinity(cpu_count) 実装（利用可能なコア数チェック・エラー時は警告してスキップ）。

- ポートフォリオ構築モジュールを追加 (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank のタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全体が 0 の場合は等配分へフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクターごとのエクスポージャーを計算し、最大セクター比率超過時に当該セクターの新規候補を除外。
    - calc_regime_multiplier: レジームラベル ("bull"/"neutral"/"bear") に基づく投下資金乗数を実装（未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に対応した株数決定ロジックを実装。
    - 単元株丸め(lot_size)、max_position_pct、max_utilization、cost_buffer を考慮する aggregate scaling ロジックを実装。
    - 取引コストを保守的に見積もるための cost_buffer を導入。現金が不足する場合はスケーリングして残余キャッシュで再配分。

- リサーチ / ファクター計算モジュールを追加 (kabusys.research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB を使って計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算（データ不足時は None を返す）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン (デフォルト: 1/5/21 営業日) を計算。horizons 検証あり。
    - calc_ic: スピアマンランク相関（IC）計算。外部ライブラリに依存せず実装。
    - factor_summary / rank: 基本統計量とランク処理実装。
  - DuckDB 接続を受け取り SQL と純粋 Python による処理で実装（外部 API へのアクセスは行わない設計）。

- AI ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメントを JSON で取得。
  - バッチサイズ、記事数/文字数制限、エクスポネンシャルバックオフ（429/ネットワーク/5xx）などの堅牢性設計。
  - レスポンスバリデーション、スコア ±1.0 のクリップ、部分成功時に既存スコアを保護する部分置換 INSERT 戦略を採用。
  - calc_news_window: JST→UTC のウィンドウ計算ユーティリティを実装。

- ツール: Paper Trading 検証レポート生成スクリプトを追加
  - kabusys.tools.paper_verification_report
    - CLI: --from / --to / --db オプションをサポート。
    - 指標: 稼働率(uptime), 注文成功率(fill rate), 送信率(send rate), P95 レイテンシ、リスク却下数などを集計して PASS/FAIL 判定。
    - デフォルト閾値: uptime >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
    - 空データやテーブル未存在時のフォールバック処理を実装。

- パッケージメタ情報
  - __version__ = "0.1.0" を設定。
  - package の __all__ を整備（portfolio, research などのエクスポート）。

### 変更 (Changed)
- 初版リリースのため特に "変更" はありません（新規実装中心）。

### 修正 (Fixed)
- 設定値・引数の厳密なバリデーションを追加
  - MONITOR_POLL_INTERVAL の不正値フォールバック。
  - PAPER_FILL_MODE の有効値チェック。
  - LOG_LEVEL / KABUSYS_ENV の許容値チェック。
  - calc_forward_returns の horizons 引数検証（正の整数かつ <= 252）。

- DB / I/O の堅牢性強化
  - .env 読み込みでファイル読み込み失敗時に警告を発し処理継続。
  - DuckDB/SQLite のクエリでテーブル未存在（OperationalError）を捕捉してフォールバックする処理を Paper レポートに実装。

### 既知の問題 (Known issues)
- ai/news_nlp モジュールのソースが途中で切れている（この状態のままでは一部処理が未完了）。（注: 提供されたコードファイル末尾で切断あり）
- position_sizing の価格欠損時（price が 0.0 や None）にエクスポージャーを過少見積もる可能性があり、TODO コメントでフォールバック価格（前日終値や取得原価）の導入が示唆されています。
- set_cpu_affinity / set_process_priority は権限不足や未対応プラットフォームで設定に失敗する場合があり、その場合はログ出力してスキップします（安全側設計）。

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定する設計。未設定時は例外を送出するため、秘匿管理を必須とします。
- .env 自動読み込みはデフォルトで有効だが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能。

### 備考 (Notes)
- 監視プロセスは「本番 monitoring DB」を参照する設計（KABUSYS_ENV に依存せず sqlite_path を使用）。paper_trading の場合も monitoring DB は分離されない点に注意してください（run_execution は paper_trading 時に paper_sqlite_path を使用）。
- MONITOR_POLL_INTERVAL の設定ミスがあるとログに警告が出てデフォルト 60 秒に戻ります。
- Paper Trading の検証ツールは、実運用データの品質チェックおよび回帰確認に便利です。阈値は現状のデフォルトから運用に合わせて調整してください。

---

変更履歴はソースコードのコメント・実装から推測して作成しています。必要であれば、個々の機能（例: risk_manager の挙動、ExecutionEngine の詳細、AI スコア書き込みロジック等）について、より詳細なリリースノートや移行ガイドを作成します。