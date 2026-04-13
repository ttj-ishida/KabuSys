CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。
リリース日付はコードベースから推測して付与しています（変更時に適宜更新してください）。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除

[Unreleased]
-------------

（現時点では未リリースの差分はありません。次回リリース時にここに記載してください。）

[0.1.0] - 2026-04-13
-------------------

Added
- 全体
  - 初回リリースとして、自動売買システム "KabuSys" の基礎モジュール群を追加。
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として定義。

- 設定・環境変数管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env ファイルパーサを強化:
    - 行頭の "export KEY=val" 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメント（クォート無しの #）の扱い制御。
  - _load_env_file により既存 OS 環境変数を保護しつつ .env と .env.local を順次読み込み（.env.local は上書き可能）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを追加し、主要な環境設定をプロパティとして提供：
    - データベースパス: DUCKDB_PATH、SQLITE_PATH（デフォルト: data/kabusys.duckdb / data/monitoring.db）
    - Paper Trading 用設定: PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE（有効値: instant/partial/never/reject）
    - 監視・プロセス管理: PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START
    - 閾値設定: CPU_THRESHOLD_PCT、MEMORY_THRESHOLD_PCT、DISK_THRESHOLD_PCT
    - ログレベル・実行環境バリデーション（KABUSYS_ENV の有効値: development/paper_trading/live）
  - 必須環境変数取得ヘルパ (_require) を実装（未設定時に ValueError を送出）。

- 実行／監視エントリポイント
  - run_execution.py:
    - ExecutionEngine を立ち上げる起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value を broker.get_available_cash() から取得。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視は常に本番 DB に記録）。
    - 起動時にプロセス優先度を上げる（set_process_priority("high")）。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX (Linux, Darwin, FreeBSD) に差分吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) を実装（指定が None の場合は設定しない）。権限不足や未サポート環境では警告を出力してスキップ。
  - アクセス権限等の例外時は安全にスキップするフォールトトレランス実装。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（タイブレーク: signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。スコアが全て 0 の場合は等分配にフォールバック（警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター別エクスポージャーを計算し、既存保有がセクター上限を超える場合は同セクターの新規候補を除外。unknown セクターは上限対象外。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算を実装。
    - 損切り率 / risk_pct に基づくリスクベース算出、単元株（lot_size）丸め、1銘柄上限・全体キャッシュ上限へのスケーリング、cost_buffer（手数料・スリッページ見積り）をサポート。
    - aggregate cap を超える場合の比例スケーリングと残差ロジック（lot_size 単位で追加配分）を実装。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離（MA200）を DuckDB の prices_daily から算出。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を算出（true_range の NULL 伝播を適切に扱う）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（target_date 以前の最新財務データを使用）。
    - いずれも DuckDB 接続を受け取り SQL ベースで高速に計算。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。horizons の検証と最大ホライズンに基づくスキャン範囲制御を実装。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）、各ファクターの基本統計量を提供。
  - 依存は DuckDB と標準ライブラリのみ（pandas 等には依存しない設計）。

- AI（ニュース）スコアリング (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄別 ai_score を ai_scores テーブルに書き込む機能を実装（score_news）。
  - 処理方針:
    - タイムウィンドウ: target_date に対して前日 15:00 JST 〜 当日 08:30 JST（UTC 換算で前日 06:00 ～ 23:30）を対象。
    - 記事集約時に 1 銘柄あたりの最大記事数 (_MAX_ARTICLES_PER_STOCK=10) と最大文字数 (_MAX_CHARS_PER_STOCK=3000) を適用してトリム。
    - 1 API 呼び出しで最大 20 銘柄ずつバッチ送信（_BATCH_SIZE）。
    - 429 / ネットワーク断 / タイムアウト / 5xx をエクスポネンシャルバックオフで再試行（最大 _MAX_RETRIES 回）。
    - レスポンス検証（JSON 形式: {"results": [{"code":"XXXX","score":0.0}, ...]}）、スコアを ±1.0 にクリップして保存。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未指定の場合は ValueError。
    - フェイルセーフ設計: API 失敗時は部分的にスキップして残りを継続、書き込みは成功した銘柄のみ差替え。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
  - 指標と閾値:
    - 稼働率 (uptime) >= 99.0%
    - 注文成功率 (fill rate) >= 90.0%
    - 送信率 (send rate) >= 95.0%
    - P95 レイテンシ <= 200 ms
  - SQLite DB 統計を利用して system_status / trade_logs / risk_logs からメトリクスを抽出し、PASS/FAIL 判定を出力。
  - --from / --to / --db オプションで期間と DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能。

Changed
- なし（初回リリースのため変更履歴はなし）。

Fixed
- なし（初回リリースのため修正履歴はなし）。

Notes / Implementation details
- 多くの計算ロジック（ポートフォリオ構築、ポジションサイズ計算、ファクター計算）は純粋関数として実装され、DB 参照が必要な部分は明確に分離（DuckDB / SQLite）されているため、ユニットテストやリサーチ用途での再利用性を考慮。
- run_monitoring は監視データを本番 sqlite_path に記録する設計になっているため、テストや paper_trading 環境では注意が必要。
- process priority / CPU affinity は OS や権限に依存する処理であり、失敗時は警告を出してスキップするフォールトトレランスを持つ。
- OpenAI を使ったニュース NLP 部分は外部 API に依存するため、API キー管理とリトライ・レートリミット制御が組み込まれている。レスポンスの形式と値検証を厳格に行う設計。

今後
- 変更や追加機能は本 CHANGELOG の Unreleased セクションに記録後、新バージョンとしてタグを切ることを推奨します。
- position_sizing の lot_size を銘柄別に拡張する、価格フォールバック実装（apply_sector_cap の TODO）などの改善候補あり。