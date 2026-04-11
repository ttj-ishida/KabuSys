# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-11
初回リリース。主要な機能群をまとめて実装。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用して DB に接続。
    - 起動時にプロセス優先度を "high" に設定するための処理を組み込み。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視テーブルの初期化（冪等）を起動フローに含める。

- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 強化された .env パーサ:
      - export プレフィックスに対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
      - インラインコメント処理を実装（クォートなし時に # の前が空白の場合はコメント扱い）。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログ・環境の検証など多様な設定プロパティを提供。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）と paper_sqlite_path を追加。
    - `is_live`, `is_paper`, `is_dev` 等の便宜プロパティを追加。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定する `set_process_priority(level)` を追加（Windows と POSIX を吸収）。
    - `set_cpu_affinity(cpu_count)` によりプロセスを最初の N コアに固定するユーティリティを追加。
    - アクセス権限や未対応 API の場合は警告を出してフォールバックする実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター時価を計算して上限超過セクターの新規候補を除外、unknown セクターは制限対象外）。
    - レジームに応じた乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" マップと未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ決定 `calc_position_sizes` を実装:
      - allocation_method に応じた計算 ("risk_based", "equal", "score")。
      - 単元株（lot_size）丸め、1 銘柄キャップ、aggregate cap（利用可能現金を超えた際のスケーリングと残差処理）をサポート。
      - cost_buffer による保守的コスト見積りを考慮。
    - 全て純粋関数としてメモリ内計算を行い DB 参照はしない設計。

- リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - Momentum / Volatility / Value のファクター計算を DuckDB SQL で実装（prices_daily / raw_financials を参照）。
    - 各ファクターは営業日ベースの窓長・欠損ハンドリング・行数チェック等を実装。
  - research/feature_exploration.py
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、入力検証あり）。
    - IC（Spearman の ρ）計算 `calc_ic` とランク変換 `rank`（同順位は平均ランク）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - いずれも外部ライブラリに依存せず標準ライブラリ + DuckDB を使用する方針。

- AI 関連
  - ai/news_nlp.py
    - raw_news から銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む処理を実装。
    - 処理のポイント:
      - 対象時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算しルックアヘッドを防止。
      - 1 銘柄あたり記事数と文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄/チャンクでのバッチ送信、429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ。
      - レスポンスの厳格なバリデーション（JSON モード対応や前後余剰テキスト復元、results 構造チェック、スコア数値チェック、未知コード除外）。
      - スコアを ±1.0 にクリップ。
      - DuckDB の executemany に関する互換性を考慮し、空パラメータ回避や個別 DELETE → INSERT の冪等な書き込みを実装。
      - API キー解決（引数 or 環境変数 OPENAI_API_KEY）、未設定時は ValueError。
      - フェイルセーフ設計: API 失敗時は該当チャンクをスキップし他銘柄処理を継続。
  - ai/regime_detector.py
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定するモジュールを追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してレジームスコアを算出。
    - ルックアヘッド防止のため target_date 未満のみを使用、マクロ記事がない場合は LLM 呼び出しをスキップしてフォールバック。
    - OpenAI 呼び出しで失敗した場合は macro_sentiment=0.0 で継続するフェイルセーフ。
    - 判定結果を market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - news_nlp の calc_news_window を利用して時間ウィンドウを整合。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは環境変数または明示引数で供給する設計。キー未設定時はエラーとして扱い誤使用を防止。

---

注記:
- 本 CHANGELOG はコードから推測して作成しています。実際のリリースノートに使用する場合は、担当者によるレビューと日付調整を推奨します。