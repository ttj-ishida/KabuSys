# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- 重要な変更はバージョンごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）
- 日付は変更が取り込まれた想定日を示します

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で整理（portfolio/research/monitoring 等の主要機能をエクスポート）。

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを強化:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理をサポート
    - インラインコメント処理（クォート外の '#'）に対応
  - Settings クラスを実装し、環境変数の取得・検証用プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須チェック（未設定時は ValueError）
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値を限定）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、各種監視閾値、PID/kill フラグパスなどをプロパティ化
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）

- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと実行制御（スレッド起動、停止フラグ監視、PID 管理）
    - RiskManager のデフォルト RiskConfig（max_position_pct 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() で取得

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計
    - 停止フラグ（data/stop_requested.flag）検知でループを終了
    - プロセス優先度を起動時に high に設定

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run_execution / run_monitoring で行い、監視テーブルが存在することを担保（冪等）

- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差を吸収したプロセス優先度設定機能を実装（high/normal/low）
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装
    - psutil アクセス権限例外などは警告にフォールバック

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分
    - スコア合計が 0 の場合は等金額にフォールバック（警告ログ）
  - risk_adjustment.py
    - apply_sector_cap: セクターごとの既存保有比率を計算し、上限超過のセクターの新規候補を除外
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供
    - unknown セクターの挙動（除外しない）や将来のフォールバック（価格欠損時）についての注意コメントを追加
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく銘柄ごとの発注株数計算
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でのスケールダウンロジックを実装
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的計算、残差配分ロジックを実装
    - 無効な価格データや lot_size の取り扱いに関するログ出力と安全弁を実装
  - package-level exports を追加（kabusys.portfolio.* を __all__ で公開）

- リサーチ / ファクター計算（kabusys.research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB 上で計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新報告書を取得）
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照する設計（外部 API 不使用）
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンのランク相関（IC）を計算（十分なサンプル数がない場合は None）
    - factor_summary / rank: 基本統計量・ランク付けユーティリティを実装
  - research パッケージのエクスポートを整理（zscore_normalize を含む）

- AI ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む仕組みを実装
  - 主な設計/実装点:
    - ニュース収集ウィンドウを JST 基準で設定（前日 15:00 ～ 当日 08:30、内部では UTC に変換）
    - 記事を銘柄ごとに集約し、1銘柄あたり記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 最大バッチサイズ 20 銘柄で API に送信、429/ネットワーク/5xx は指数バックオフでリトライ（上限あり）
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分的成功時でも既存スコアを保護する更新手順（DELETE→INSERT の範囲指定）
    - OPENAI_API_KEY の未設定は明示的なエラーとして扱う

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加
    - デフォルト DB は data/paper_trading.db、コマンドライン引数 --from/--to/--db をサポート
    - システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計・表示
    - 合格基準（閾値）を定義し PASS/FAIL を判定（閾値はソース内で定義）
    - DB が存在しない・テーブルが無い場合は安全に N/A を表示

### Changed
- （初回リリースのため過去からの変更はありませんが、各モジュールで設計方針・注釈を明記）
  - リサーチ / AI / ポートフォリオ各モジュールは「外部 API に依存しない」「DuckDB / メモリ計算中心」「ルックアヘッドバイアスを避ける」設計が徹底されている点を強調。

### Fixed
- （リリースに向けた安定化処理、例外処理の追加）
  - .env ファイル読み込み時のファイルアクセス失敗を警告にフォールバック
  - process_priority / cpu_affinity の権限エラーを警告化して処理を継続
  - run_monitoring のポーリング間隔環境変数の不正値処理（ログ警告してデフォルトに落とす）
  - paper_verification_report の SQL 実行でテーブル欠如時に例外を捕捉して N/A を返すように修正

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の必須チェック（API キー・パスワード等）により未設定での起動を検出して明示的にエラーを出す設計を導入（誤設定による無防備な起動を防止）

---

## 運用上の注意 / マイグレーション情報
- 環境変数名:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（整数秒）。不正値はデフォルト 60 秒にフォールバック。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 環境用の SQLite パス（run_execution / tools で利用）。
  - KABUSYS_ENV: allowed values = development, paper_trading, live（不正値は ValueError）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合は "1" を設定。
  - OPENAI_API_KEY: news_nlp のスコアリングで必須。
  - PAPER_FILL_MODE: paper トレードのフィルモード（instant / partial / never / reject）。不正値は起動エラー。

- DB 分離:
  - paper_trading 環境では paper_trading 用 DB が使用され、本番モニタリング DB とデータが分離される（意図的な設計）。
  - monitoring は設計上「本番 sqlite_path を使用する」点に注意（run_monitoring の動作仕様）。

- 停止制御:
  - 両エントリポイントはプロジェクト直下 data/stop_requested.flag（もしくは Settings の kill/flag path）を参照して停止する設計。運用時はこのファイルで安全にプロセスを停止できる。

- 権限・プラットフォーム:
  - process_priority / cpu_affinity は OS と権限に依存するため、権限不足時は警告が出力され設定はスキップされる。

---

変更点・バグ修正の詳細や追加希望点があれば、対象のファイル名や関心領域（例: ポジションサイジングのスケーリング挙動、news_nlp のレトライポリシー等）を指定してください。必要に応じてリリースノートをより細かく分割して再作成します。