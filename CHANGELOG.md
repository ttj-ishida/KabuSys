# CHANGELOG

すべての注目すべき変更点をこのファイルに記載します。本ファイルは「Keep a Changelog」準拠の形式で記述しています。

## [0.1.0] - 2026-04-17

初回リリース。プロジェクトのコア機能群を実装しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 環境・設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み挙動:
    - OS 環境変数優先、.env → .env.local の順で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export 付き行、クォート付き値、インラインコメント等のパースに対応。
  - Settings クラスを実装し、環境変数から各種設定（API トークン、DB パス、監視閾値、ロギング等）をプロパティとして提供。
  - 入力値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の検証など）を実装。

- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock 対応を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ (data/stop_requested.flag) の検知によるグレースフルな停止処理。
    - PID 書き出し用ファイルパスと停止フラグの扱い（data/execution.pid, data/stop_requested.flag）。
    - init_monitoring_db による監視テーブルの冪等な初期化。
    - duckdb 接続を併用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用（監視は本番 DB に対して動作する設計）。
    - 停止フラグ (data/stop_requested.flag) によるループ停止、KeyboardInterrupt での終了処理、コネクションの確実なクローズを実装。
    - init_monitoring_db による監視テーブルの初期化。

- プロセス運用ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX(Linux/Mac/FreeBSD) に対応してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。
  - set_cpu_affinity(cpu_count) 実装（first N コアへピン留め）。
  - 実行環境で権限がない場合や未対応 OS の場合は警告を出してフォールバックする「ベストエフォート」挙動を採用。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重の重み計算。スコア合計が 0 の場合は等分にフォールバックし警告を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター毎のエクスポージャを計算し、最大セクター比率を超えるセクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返却（未知レジームは 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株( lot_size )丸め、per-position 上限、aggregate cap（available_cash）によるスケーリング、cost_buffer を用いた保守的見積り、スケーリング後の端数処理（残余キャッシュでの lot 単位追加）を実装。

- 研究・リサーチ (kabusys.research)
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算。
    - いずれも DuckDB 接続を受け取り SQL で効率的に計算。
  - feature_exploration.py
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。必要件数不足時は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージは zscore_normalize 等のユーティリティと合わせてエクスポート。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を基に OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を実装。
  - 設計:
    - 指定のタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）にある記事を集約し、銘柄ごとに上限記事数・上限文字数でトリム。
    - 最大 20 銘柄ずつバッチ送信。JSON Mode で厳密な JSON 出力を期待。
    - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ（上限あり）。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - 成功分のみ ai_scores テーブルを書き換える（部分失敗時に他銘柄の既存スコアを保護）。
  - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
  - （注）実装ファイルは大きいため、処理詳細（トークン制限対策、retry ロジック等）を盛り込んでいる。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 検証レポート生成スクリプトを追加。
  - 機能:
    - paper_trading の SQLite（デフォルト data/paper_trading.db）から統計を集計し、稼働率 / 注文成功率 / 送信率 / P95 レイテンシ等の指標を表示。
    - パス/フェイル基準を定義（例: 稼働率 >= 99%, fill_rate >= 90% 等）。
    - 日付フィルタ (--from / --to)、--db オプションをサポート。
    - DB が存在しない場合はエラーを表示して終了。
    - DuckDB を使わず sqlite3 の直接クエリで集計。
  - 出力は人間向けのコンソールレポート（PASS/FAIL 判定付）。

- DB 関連
  - sqlite3 と DuckDB の両方を併用する設計。
  - init_monitoring_db を呼び出し、監視テーブルの存在を保証する（冪等性）。
  - paper_trading と本番 DB の分離を明確化（PAPER_TRADING_SQLITE_PATH）。

### 変更 (Changed)
- なし（初回リリースのため新規実装が中心）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 / マイグレーション
- 環境変数の整理:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings の一部プロパティは未設定時に ValueError を送出します）。
  - KABUSYS_ENV の有効値: development / paper_trading / live。値が不正な場合は起動時に例外。
  - PAPER_FILL_MODE の有効値: instant / partial / never / reject。
  - DB パスのデフォルト:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 実行・運用:
  - run_execution と run_monitoring はプロセス優先度を最初に "high" へ設定しようとします。権限がない場合は警告が出て処理は継続します。
  - 停止制御はプロジェクトルート直下の data/stop_requested.flag（または Settings による上書きパス）を利用する設計です。CI/運用側でこのフラグを作成することで安全に停止できます。
  - paper_trading モードは実トレードと完全に分離された専用 SQLite DB に書き込みます。生データを誤って本番 DB に書き込まないよう注意してください。
- 外部依存:
  - psutil を使用（プロセス優先度／CPU affinity）。
  - openai ライブラリを使用（AI ニューススコアリング）。OpenAI API キーの管理に注意。
  - duckdb, sqlite3 を使用。
- フェイルセーフ:
  - 多くの箇所で失敗時は警告ログを出力して処理をスキップする「フェイルセーフ」設計を採用しています（例: プロセス優先度設定失敗、API 失敗、データ不足時の None 返却など）。

---

今後の予定（想定）:
- ExecutionEngine / SystemMonitor の単体テスト、統合テストの充実。
- ニュース NLP 部分のテスト・エラーハンドリング強化（API レート制御の改善、レスポンスの厳密な検証）。
- ポートフォリオ構築ロジックの追加ユニットテストとドキュメント（PortfolioConstruction.md への参照がコード内にあります）。
- 銘柄毎の lot_size マスタ対応など、position_sizing の拡張。

（以上）