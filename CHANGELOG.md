Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」を準拠しています。

既知のバージョン
---------------

Unreleased
----------
（このスナップショットはリリースノート作成のためのソースコードから推測して作成しています。実際のコミット履歴がある場合はそちらを優先してください。）

v0.1.0 - 2026-04-17
-------------------
初回公開（推定） — 以下の主要機能と改善を実装しました。

Added
- パッケージ基盤
  - パッケージメタ情報とエクスポートを追加（kabusys.__init__ に __version__ = "0.1.0" を設定）。
  - モジュール構成: data, strategy, execution, monitoring, portfolio, research, ai, tools, utils 等のモジュール群を提供。

- 環境設定 / ロード
  - Settings クラスを実装。環境変数から設定値を取得する統一 API を提供（KABUSYS_ENV, LOG_LEVEL, JQUANTS_REFRESH_TOKEN 等）。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - .env パーサーを実装し、以下に対応:
    - コメント行、空行の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォートの内部エスケープ処理
    - インラインコメントの取り扱い（クォートの有無で挙動を分離）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数の保護（OS 環境変数を上書きしない挙動）を実装。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。pid ファイルと停止フラグ（data/stop_requested.flag）を扱う。
    - 停止フラグ検知でエンジンを安全に停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する（監視は実運用 DB を参照）。
    - 停止フラグファイルでループ終了を検知。

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しにより、監視テーブルが存在することを保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用 SQLite を読み込み、期間フィルタ指定可能な検証レポートを標準出力へ出力。
  - 指標:
    - 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ
  - 判定基準（デフォルト閾値）:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH 環境変数にも対応）

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（同スコアは signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックして候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告して 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に応じた株数決定ロジックを実装。
    - 単位株（lot_size）切り捨て／追加分配のロジック、ポジション上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer を用いた保守的コスト見積りを実装。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials と prices_daily を用いて PER, ROE を計算（target_date 以前の最新財務レコード選択）。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時 (n<3) は None を返す。
    - factor_summary, rank: 基本統計量・ランク変換のユーティリティを実装。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- AI / ニュース NLP
  - ai.news_nlp:
    - raw_news テーブルからニュースを集約し、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメントを算出、ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ（JST ベース）計算ユーティリティ calc_news_window を実装（前日 15:00 JST ～ 当日 08:30 JST）。
    - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、429/5xx/タイムアウト等に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗耐性（対象コードのみ置換する更新）を実装。
    - OpenAI API キー未設定時に明確なエラーを返す。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）を吸収するクロスプラットフォーム実装。権限不足や未対応 OS の場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への固定（権限不足や未対応環境は警告してスキップ）。
    - 既定優先度レベルは "high" / "normal" / "low"。

Changed
- DB 接続と環境分離ポリシー
  - 監視（run_monitoring）は常に本番 sqlite_path を使用する方針を明示（環境にかかわらず監視は本番データを参照）。
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離。

- 安定性・フェイルセーフ
  - 各所での入出力・DB 存在チェック、sqlite3.OperationalError によるフォールバック処理、ファイルベースの停止フラグ検知を導入。
  - MONITOR_POLL_INTERVAL の不正値に対する警告とデフォルトフォールバックを追加。

Fixed
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメント処理の改善により、より実用的な .env ファイルの記述に耐性を持たせた。

- リサーチ / 指数計算の NULL ハンドリング
  - ATR / true_range 計算で high/low/prev_close が NULL の場合に true_range を NULL にしてカウントを正しく扱うよう修正（過大評価を回避）。

Notes / Implementation details
- 多くのモジュールは DuckDB のコネクションを受け取り SQL と Python を組み合わせてデータ処理を行う設計。
- Execution 系は BrokerClientFactory 等の外部コンポーネントに依存しており、paper_trading モードでは MockBrokerClient を用いる設計が意図されている（コード上での生成箇所あり）。
- 一部の参照（SystemMonitor 本体、ExecutionEngine 内部、モニタリング DB の具体的スキーマ等）はこのスナップショットに含まれていないため、詳細は該当ファイルの実装を参照してください。

Deprecated
- なし（このスナップショットでは非推奨 API は検出されませんでした）。

Security
- OpenAI API キーの扱いは環境変数 OPENAI_API_KEY または明示的引数を想定。キー未設定時は操作を中断する実装。

今後の改善提案（コードからの推測）
- position_sizing: 銘柄ごとの lot_size を持つ設計への拡張（TODO コメントあり）。
- apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）を導入してエクスポージャー算出の堅牢化。
- AI モジュール: 大量 API 呼び出しに対するレート制御（別スレッド/ワーカー）やローカルキャッシュの導入でコスト削減。
- テストカバレッジ: 各純粋関数（portfolio / research / feature_exploration）向けのユニットテスト整備。

以上。