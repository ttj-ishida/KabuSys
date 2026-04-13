CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」仕様に従って記録しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在のコードベースからは未リリース扱いの差分はありません。将来の変更はここに記載します。）

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初回公開リリースとして、KabuSys 自動売買フレームワークのコア機能群を追加。
  - パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。

- 設定・環境変数管理 (src/kabusys/config.py)
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を基準）。
  - .env / .env.local の自動読み込みを実装（OS 環境変数優先、.env.local は上書き可能）。
  - 読み込みの自動無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB / 監視 / システム設定など主要設定値をプロパティ経由で提供。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など Paper Trading 用設定を追加。
  - KABUSYS_ENV の検証（development/paper_trading/live）および LOG_LEVEL の検証を実装。

- 実行エントリポイント
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度を起動時に High に設定。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを作成（paper_trading では Mock を利用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を run_session() で実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を明示。
    - DuckDB をデータ処理用に接続。

  - Monitoring 起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を High に設定。

- 監視 DB 初期化
  - init_monitoring_db を用いた監視テーブルの冪等な初期化処理を導入（Execution / Monitoring 両起動で保証）。

- Utilities (src/kabusys/utils/process_priority.py)
  - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを提供。
  - Windows/Linux/macOS/FreeBSD に対応し、nice 値または HIGH_PRIORITY_CLASS を設定。
  - 許可エラー（AccessDenied）や未サポート環境では警告を出してフォールバック。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity() を追加（引数検証・権限エラーは警告でスキップ）。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順＋signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment
    - apply_sector_cap: セクター集中制限ロジックを実装。既存ポジションからセクター暴露を計算し、閾値超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告後 1.0 にフォールバック。
  - position_sizing
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）でのスケールダウン、cost_buffer を使った保守的コスト見積り、残差処理によるロット単位の再配分などのロジックを実装。

- 研究（Research）機能 (src/kabusys/research/)
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率を DuckDB の SQL で計算。データ不足時の None 処理を実装。
    - calc_volatility: ATR20, 相対 ATR, 20日平均売買代金, 出来高比率を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算。prices_daily と結合。
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に1クエリで取得。ホライズン検証とスキャン範囲の制限を実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（null 除外、記録数が少なければ None）。
    - rank / factor_summary: 同順位を平均ランクで扱うランク関数、基本統計量（count/mean/std/min/max/median）を実装。
  - いずれも外部ライブラリに依存せず標準ライブラリと DuckDB で完結する設計。

- AI ニュース解析 (src/kabusys/ai/news_nlp.py)
  - raw_news から銘柄ごとの記事を集約し、OpenAI API（gpt-4o-mini）でセンチメントを -1.0〜1.0 で採点して ai_scores に書き込む処理を実装。
  - バッチサイズ（最大 20 銘柄）、1銘柄あたりの最大記事数 / 文字数制限（トークン肥大化対策）、スコアの ±1.0 クリップを導入。
  - JSON Mode の期待応答（{"results":[{"code":"XXXX","score":0.0}, ...]}）を SYSTEM_PROMPT で強制。
  - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフの共通リトライ実装（最大リトライ回数・バックオフ基礎秒数）。
  - タイムウィンドウ計算（JST ベース: 前日 15:00 〜 当日 08:30 を UTC に変換）を提供する calc_news_window()。
  - API 応答のバリデーション、部分失敗時に他銘柄の既存スコアを保護する（DELETE→INSERT をコード絞り込みで実施）方針。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成ツールを追加。
  - コマンドライン引数 --from / --to / --db に対応し、指定期間の system_status / trade_logs / risk_logs から以下指標を算出して標準出力に表示:
    - 稼働率 (uptime %)、総ポーリング数、エラー数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）
    - リスク却下数
    - 平均/最大/P95 レイテンシ（ms）
  - デフォルト閾値（PASS/FAIL 判定）を設定:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - P95 計算や日付フィルタの組み立て、DB 存在チェック、DB の存在しない場合のユーザ向けメッセージを実装。

Changed
- 実装上の設計意図や動作方針をドキュメント文字列・コメントで詳細に明記（例: レジーム処理、フォールバック挙動、フェイルセーフ方針、外部依存の制限など）。
- DuckDB を分析・研究用途の主要クエリ実行エンジンとして採用し、prices_daily / raw_financials テーブルを前提とした計算に統一。
- 実行スクリプトで起動直後にプロセス優先度を上げる挙動を全体で統一（run_execution / run_monitoring）。

Fixed
- N/A（このリリースは初期機能の追加が中心のため明示的なバグ修正項目はありません）。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を送出して無保証な動作を防止。

Notes / Known limitations
- position_sizing の価格欠損（price が 0.0）時の挙動について TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- process_priority / cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告を出してスキップする設計。
- ai/news_nlp の OpenAI 呼び出しはネットワーク/料金/レート制限の影響を受ける。部分失敗時のデータ保護は行うが、完全なトランザクション保証は外部 API に依存する。
- research モジュールは DuckDB 上のテーブル構造（prices_daily, raw_financials 等）に依存。スキーマ不整合時は OperationalError が発生する可能性があり、呼び出し側での例外ハンドリングを想定。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードから挙動・設計を推測して作成しています。実際の変更履歴やコミットメッセージがある場合は、それに合わせて差し替えてください。