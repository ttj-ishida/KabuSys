# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

※この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-04-13

### Added
- 全体
  - 初回公開相当の機能群を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定・環境変数読み込み（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み（OS 環境変数が優先）。
  - .env の独自パーサ実装: export プレフィックス、クォート／エスケープ、インラインコメント処理等に対応。
  - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグをサポート。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視閾値 / 実行環境フラグ等）。
  - 環境変数値のバリデーション（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）。

- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite DB を使用し、MockBrokerClient 経由で動作する設計（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててセッションを実行。
    - RiskManager に対するデフォルト設定（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker など）を提供。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）を行う。注: Monitoring は環境にかかわらず本番 `sqlite_path` を使用する挙動になっている。

- 監視データベース初期化（monitoring.monitoring_db）
  - 監視テーブルの初期化を行うユーティリティ関数を用意（冪等で呼べるように実装）。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度 (nice / HIGH_PRIORITY_CLASS 等) を設定する `set_process_priority` を追加。
  - 指定コア数で CPU affinity を固定する `set_cpu_affinity` を追加。
  - 権限不足や未対応環境では警告を出して安全にスキップする実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - BUY シグナルから候補選定 (score 降順、同点は signal_rank でタイブレーク)。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバックして警告）。
  - risk_adjustment
    - セクター集中制限 apply_sector_cap（既存保有のセクター露出計算、上限超過セクターの候補除外）。"unknown" セクターは制限を適用しない。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull":1.0, "neutral":0.7, "bear":0.3。未知レジームは 1.0 でフォールバック）。
  - position_sizing
    - 株数決定ロジック calc_position_sizes を追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（available_cash）に基づくスケーリング機構を実装。
    - cost_buffer を考慮した保守的見積りと、スケールダウン時の残差分配アルゴリズムを実装。
    - price 欠損時のスキップ処理やログ出力を実装。

- リサーチ（kabusys.research）
  - factor_research
    - DuckDB を用いたファクター計算モジュールを提供：
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日未満は None）。
      - calc_volatility: 20 日 ATR / atr_pct / avg_turnover / volume_ratio（データ不足は None）。
      - calc_value: PER / ROE（raw_financials と prices_daily を組合せ）。
    - 各種ウィンドウ長やスキャン範囲を定義した定数を備える。
  - feature_exploration
    - 将来リターン calc_forward_returns（複数ホライズンを同時取得、ホライズン検証）。
    - IC（Spearman）の計算 calc_ic（ランク付け、同順位の平均ランク処理を含む）。
    - rank / factor_summary（基本統計量計算）を実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）と合わせて提供する設計。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄別にテキストを集約し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込むワークフローを実装。
  - 処理上の設計ポイント:
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 銘柄ごとに記事数／文字数上限を設ける（記事数最大 10、文字数最大 3000）。
    - 1 API 呼び出しで最大 20 銘柄ずつバッチ送信。
    - 429 / ネットワーク断 / 5xx などに対する指数バックオフのリトライ（上限あり）。
    - レスポンス検証・スコアを ±1.0 にクリップ。
    - 成功した銘柄のみを部分的に置換（DELETE WHERE date=? AND code IN (...) → INSERT）して部分失敗時のデータ保護を実現。
    - API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成ツールを追加（コマンドラインで実行可能）。
  - 指標:
    - 稼働率（uptime）・注文成功率（fill rate）・送信率（send rate）・API レイテンシ（P95）等を計算。
  - デフォルト閾値（PASS/FAIL 判定基準）を定義:
    - 稼働率 >= 99.0%
    - 注文成立率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
  - DuckDB/SQLite のテーブルが存在しない場合のフォールバック処理を実装。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーはパラメータか環境変数で指定する仕様。未設定時は明示的にエラーを出す実装により不正なデフォルト利用を防止。

### Notes / Known issues / TODO（コード中の注記に基づく）
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある旨の TODO がある。将来的に前日終値や取得原価でのフォールバックを検討。
- run_monitoring:
  - 監視機能が「環境にかかわらず本番 sqlite_path を使用」する点は運用で注意が必要（paper_trading と分離したい場合は運用ルールで対応）。
- position_sizing:
  - lot_size が現状グローバル固定（想定値 100）。将来的に銘柄別単元対応の拡張予定あり（stocks マスタ等）。
- news_nlp.score_news の末尾処理に続きの実装がある想定（提示されたコード断片は途中で終わっているため、部分的実装状態の可能性あり）。

---

以上。追加の差分や過去リリース履歴が与えられれば、より詳細な CHANGELOG（リリース間の変更点一覧）を作成できます。