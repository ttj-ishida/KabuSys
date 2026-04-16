# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。  
このファイルは、提供されたコードベースの内容から推測して作成した変更履歴（リリースノート）です。

全般的な注意
- 日付はコード解析時点（2026-04-16）を基準に記載しています。
- 実装上の振る舞いや既定値、環境変数の仕様・バリデーションなどはソースコードから推測してまとめています。

## [0.1.0] - 2026-04-16

### Added
- 初期リリース。日本株自動売買システム "KabuSys" のコア機能群を実装。
- パッケージメタ情報
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止判定はプロジェクトルートの `data/stop_requested.flag` ファイルで行う。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して接続する仕様。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用して paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離。
    - 実行時に `data/execution.pid` を利用し、`data/stop_requested.flag` による安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。

- 設定・環境変数管理
  - config.Settings クラスを提供。環境変数や `.env` / `.env.local` の自動読み込み（プロジェクトルート検出に基づく）。
  - .env のパースは quotes / export 構文 / インラインコメントなどに耐性を持つ実装。
  - 自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, PID / kill フラグのパス, 環境判定等）。
  - 入力値のバリデーション:
    - `PAPER_FILL_MODE` は "instant"|"partial"|"never"|"reject" のみ許容。
    - `KABUSYS_ENV` は "development"|"paper_trading"|"live" のみ許容。
    - `LOG_LEVEL` は標準的なログレベルのみ許容。

- 監視（monitoring）関連
  - 監視テーブルの初期化を行う init_monitoring_db を起動時に呼び出し、冪等にテーブルを保証。

- Execution コンポーネント（実行エンジン周辺）
  - BrokerClientFactory によるブローカークライアントの抽象化。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動フローを実装。
  - RiskManager 用のデフォルト構成をコード上に定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window, max_drawdown 等）。
  - ExecutionEngine はデーモンスレッドで run_session を実行し、stop flag による停止をサポート。

- Portfolio（銘柄選定とポジション決定）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合に等配分へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェック（既存ポジションを時価で計算、売却予定銘柄は除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピング）を実装。未知レジームは 1.0 でフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 複数の allocation_method ("risk_based", "equal", "score") に対応。
    - risk_based: 損切り幅と許容リスク率から株数を算出。
    - equal/score: ポートフォリオ価値と重みから配分を計算。
    - lot_size（単元）丸め、per-stock と aggregate の上限適用。
    - cost_buffer を用いた保守的なコスト見積りと、利用可能現金を超過した際のスケールダウン（端数処理で残余キャッシュを remainders 順に配分）。

- 研究（research）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率 を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金・出来高比 を計算。
    - calc_value: raw_financials から直近の財務データ取得→ PER / ROE を計算。
    - 実装は DuckDB 接続を受け取り SQL ベースで高速実行。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）の一括計算。
    - calc_ic: スピアマンランク相関による IC（Information Coefficient）計算。
    - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。
    - rank: ランク変換（同順位は平均ランク）。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI（デフォルト model "gpt-4o-mini"）へバッチ送信し、銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ書き込み。
    - バッチサイズ制限（既定 20）、1銘柄あたりの記事数制限・文字数制限、レスポンスの JSON バリデーションを実装。
    - エラー（429 / ネット断 / タイムアウト / 5xx）は指数バックオフでリトライ。
    - スコアは ±1.0 にクリップする実装。
    - ニュース収集ウィンドウは JST ベース（前日 15:00 JST 〜 当日 08:30 JST）を UTC に変換して使用するユーティリティ calc_news_window を提供。
    - OpenAI API キーは引数か環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI を提供（引数で期間指定可能）。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ 等。
    - デフォルト閾値を定義（稼働率 >= 99%、fill rate >= 90% 等）して PASS/FAIL 判定を出力。
    - DB が存在しない場合はエラーメッセージを出力。
    - SQLite のテーブル欠損に備えた例外ハンドリングを備える。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux / macOS / FreeBSD）に跨るプロセス優先度設定を提供（"high"/"normal"/"low"）。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップするフェールセーフ。

### Changed
- なし（初期リリースのため該当なし。内部設計・API は上記に含む）。

### Fixed
- なし（初期リリースのため該当なし）。

### Security
- OpenAI API キー等の機密情報は環境変数を通じて取り扱う設計。`.env` 自動読み込み時に OS 環境変数を保護する仕組み（protected keys）を実装。

### Notes / Implementation details / Limitations
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml 存在箇所）を基準に行うため、CWD に依存しない。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- run_monitoring は監視用の DB（monitoring テーブル等）を「環境にかかわらず」 settings.sqlite_path で接続する設計になっているため、paper_trading 環境でも監視は本番 DB を参照する点に注意。
- run_execution は paper_trading 環境時に専用 DB を使うよう分離している。
- position sizing: lot_size 単位で丸められる、また price が欠損（0.0）だと当該銘柄はスキップされる点が設計上の制約として明記されている。
- ai.news_nlp は API 呼び出しの堅牢性（バッチ／リトライ／検証）を考慮した実装だが、外部 API の可用性や呼び出し料金には注意が必要。
- research モジュールは DuckDB の prices_daily / raw_financials 等のスキーマに依存する。十分な履歴データがない場合は None を返す設計。

---

今後の改善候補（ソースから推測）
- ニュース NLP の処理完了後の部分的な障害耐性をさらに強化（部分成功時のロールバック戦略等）。
- price が欠損している場合のフォールバック価格（前日終値や取得原価）を導入して position sizing のスキップを減らす。
- run_monitoring/run_execution のログレベルやログ出力先の設定をより柔軟に（ファイル出力・ローテーション等）。
- tests と CI による自動検証（特に financial 算出ロジック・リスク制約の単体テスト）。

以上。必要であれば、各モジュールごとのより詳細な項目（例: 主要関数の入出力仕様、環境変数一覧など）を CHANGELOG または別ドキュメントに追記できます。どのレベルの詳細を追加するか指示ください。