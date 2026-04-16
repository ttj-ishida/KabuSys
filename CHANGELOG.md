# Changelog

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを部分的に採用しています。日付はリポジトリ内のバージョン情報・コード実装に基づいて推定しています。

## [0.1.0] - 2026-04-16

### 追加 (Added)
- 全体
  - 初期機能群を実装。自動売買システム「KabuSys」のコアモジュール群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 設定管理 (src/kabusys/config.py)
  - 環境変数と .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサー実装: export プレフィックス対応、クォート内エスケープ、行末コメント処理などをサポート。
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE API 関連トークン/ユーザID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - PAPER_FILL_MODE（instant/partial/never/reject）に対する検証
    - 監視関連: pid ファイル、kill flag パス、各種閾値（CPU/MEM/DISK）
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション
  - settings = Settings() の単一インスタンスを提供。

- 実行・監視スクリプト
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続を確立し、監視 DB の初期化を行う。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを構築（paper/live で切替）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）や pid ファイル制御、スレッドでの実行と安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化フック
  - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等実行）。

- ユーティリティ: プロセス優先度 & CPU affinity (src/kabusys/utils/process_priority.py)
  - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収する set_process_priority(level) を実装。
    - level: "high" | "normal" | "low"。OS に応じた nice / priority を設定。
    - 設定失敗時は警告を出し無視（アクセス権限などを考慮）。
  - set_cpu_affinity(cpu_count) を実装（指定が None のときは何もしない）。
    - cpu_count < 1 の検査、および利用可能コア数を超える場合の取り扱い。

- ポートフォリオ構築 (src/kabusys/portfolio)
  - 銘柄選定・配分
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を返す（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額 / スコア加重の重み計算。全スコアが 0 の場合は等重でフォールバックし警告。
  - リスク調整
    - apply_sector_cap: セクター毎上限比率を評価し、超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull", "neutral", "bear") に応じた乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
  - ポジションサイズ計算
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を計算。
      - risk_based: risk_pct, stop_loss_pct を使った株数算出。
      - equal/score: 重み・max_utilization を考慮した株数算出。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を適用。
      - cost_buffer を用いた保守的コスト見積もりと、資金超過時のスケールダウン + 端数分配（lot 単位での再配分）を実装。
      - 価格欠損時のスキップ（ログ出力）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（MA200）を DuckDB 上で計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（price と組み合わせ）。target_date 以前の最新レコードを取得するロジックを実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証あり。
    - calc_ic: ランク相関（Spearman の rho）を実装。欠損や ties の扱い、サンプル数閾値（>=3）による None 返却。
    - rank, factor_summary: ランク付け（同順位は平均ランク）、ファクター統計要約（count, mean, std, min, max, median）を実装。
  - research パッケージで zscore_normalize などを再エクスポート（kabusys.data.stats 依存）。

- AI ニュース NLP（部分実装） (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI (gpt-4o-mini) でバッチスコアリングして ai_scores テーブルに書き込む設計を実装。
  - 実装された機能:
    - ニュース収集ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 銘柄ごとの記事集約（記事数・文字数上限でトリム）。
    - バッチサイズ（最大 20 銘柄）での API 呼び出し、JSON Mode を期待するシステムプロンプト。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライ（_MAX_RETRIES・_RETRY_BASE_SECONDS）。
    - レスポンス検証、スコアの ±1.0 クリップ。
    - 部分成功時に既存スコアを保護するため、更新対象コードを限定して DELETE→INSERT する戦略（概念の説明まで実装）。
    - API キー未設定時の ValueError。
  - （注）ファイルは途中で切れているため、fetch/DB書込の完全な実装はソースに続くと想定。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成ツールを追加。
    - コマンドライン引数で期間 (--from, --to) と DB パス (--db) を指定可能。
    - P95 計算、稼働率・注文成功率・送信率・P95 レイテンシなどの指標を算出して標準出力に出力。
    - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 合格基準（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 latency <= 200 ms）を設定し、PASS/FAIL 判定を出力。
    - DB が存在しない場合のエラーメッセージ出力、SQLite のテーブル欠損（OperationalError）を耐性付け。

### 変更 (Changed)
- 環境変数読み込みの優先順位を明確化: OS 環境 > .env.local > .env。OS 環境のキーは .env に上書きされないよう保護。
- Monitoring 実行時の振る舞い: MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバック（ログ出力）。
- 実行 / 監視スクリプトで起動直後にプロセス優先度を設定するよう統一。

### 修正 (Fixed)
- None（初期リリースのため大きなバグ修正履歴はなし）。ただし実装には以下の耐性処理を含む:
  - 環境変数パースでの不正行スキップ・ファイル読み込み失敗時の警告。
  - psutil による優先度設定失敗時の警告と安全スキップ。
  - DuckDB / SQLite のテーブル未存在時にツールがクラッシュしないよう try/except によるフォールバック。

### ドキュメント / コメント
- 各モジュールに詳細な docstring を追加し、設計方針・挙動・引数・戻り値・注意点（例: 価格欠損時の注意、レジーム乗数の意味、PAPER_FILL_MODE の有効値など）を明記。
- TODO コメントで将来的な拡張（銘柄別 lot_size、価格フォールバックなど）を残す。

### 既知の制限 / TODO
- ai/news_nlp.py はファイル末尾が切れているため、記事フェッチと最終的な DB 書き込みの完全な挙動は続きの実装に依存する。
- position_sizing: 将来的に銘柄別 lot_size を導入する案あり（現在は全銘柄共通の lot_size を想定）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があり、将来的に前日終値や取得原価等でのフォールバックを検討。

---

今後のリリースでは、AI モジュールの完全実装、単体テストの追加、ドキュメント整備（ユーザ向けの運用手順やデプロイ手順）を予定しています。必要であれば各ファイルごとの変更箇所マッピング（関数一覧や主要処理フロー）を別途出力します。