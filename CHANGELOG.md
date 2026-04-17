# Changelog

すべての重要な変更点をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

次のバージョンは semver に従って管理してください。リリースノートは実装内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 全体
  - パッケージ初期リリース（__version__ = 0.1.0）。
  - モジュール構成: execution, monitoring, portfolio, research, ai, tools, utils など主要コンポーネントを追加。

- 実行 / デーモン
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで run_session を実行し、 data/stop_requested.flag による外部停止制御をサポート。
    - PID ファイル path を data/execution.pid に記録（設定から上書き可能）。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py: システム監視（SystemMonitor）ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値 / 0 以下はデフォルトにフォールバックして警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（monitoring のデータは本番 DB を参照する設計）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) の検知による安全な終了処理を実装。

- 設定 / 環境変数読み込み
  - config.py: Settings クラスを追加。
    - .env / .env.local の自動ロード機能を実装（OS 環境変数の優先、.env.local が上書き）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で使用）。
    - .env パーサを実装（コメント行、`export KEY=val` のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理ルールなど）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル / 環境種別判定等）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant, partial, never, reject）。不正値は ValueError。
    - KABUSYS_ENV と LOG_LEVEL の入力検証。無効値は ValueError。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db が参照され、起動時に監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築（Portfolio）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア全体が 0 の場合は等配分へフォールバックして警告。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、1 セクター上限超過時に当該セクターの新規候補を除外。unknown セクターは制限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を実装（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックして警告ログ。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）や aggregate 上限（available_cash）を考慮したスケーリングを実装。
    - cost_buffer による手数料・スリッページの保守的見積りを反映。
    - 利用可能現金を超える場合はスケールダウンし、残余キャッシュで fractional 残差順に lot_size 単位で追加配分する仕組みを導入。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ma200_dev）を DuckDB SQL で計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value: raw_financials の最新財務データと当日株価から PER / ROE を計算（EPS が 0 または欠損時は None）。

  - research.feature_exploration
    - calc_forward_returns: 指定日から将来リターン（任意ホライズン）を一回のクエリで取得。horizons 引数の検証（正の整数かつ <=252）。
    - calc_ic / rank / factor_summary: スピアマン IC、ランク付け（同順位は平均ランク）、ファクター統計要約（count/mean/std/min/max/median）を実装。外部依存を使わず純粋 Python 実装。

  - research.__init__: zscore_normalize を data.stats からエクスポートし、主要関数を公開。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収しクロスプラットフォームで優先度（high/normal/low）を設定。アクセス権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアに固定。無効な値は ValueError。権限不足は警告でスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。
    - CLI: --from/--to/--db オプションをサポート。
    - デフォルト DB パス: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出。
    - 合格基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントスコア（-1.0〜1.0）を算出し ai_scores テーブルへ書き込みする機能を追加。
    - バッチ処理（銘柄ごと最大 20 銘柄 / バッチ）、1 銘柄あたりの文字数・記事数上限を導入してトークン肥大化を抑制。
    - リトライ戦略（429 / ネットワーク / 5xx に対する指数バックオフ、最大リトライ回数あり）を実装。
    - レスポンス検証・数値クリップ（±1.0）・部分成功時のテーブル更新戦略（対象コードのみ置換）などフェイルセーフな設計。
    - API キー未指定時は ValueError を送出（api_key 引数または環境変数 OPENAI_API_KEY を必須）。

### Changed
- なし（初版のため該当なし）

### Fixed
- なし（初版のため該当なし）

### Deprecated
- なし

### Security
- OpenAI API の利用に際しては環境変数 OPENAI_API_KEY を使用する設計。API キー管理は利用者側で適切に行ってください。

---

## 重要な運用メモ / マイグレーション
- 監視サービス（run_monitoring）は KABUSYS_ENV にかかわらずデフォルト sqlite_path（SQLITE_PATH 環境変数で上書き可）を使用します。paper_trading 環境でも監視 DB を分離したい場合は SQLITE_PATH を明示的に指定してください。
- 実行エンジン（run_execution）は paper_trading 環境で PAPER_TRADING_SQLITE_PATH（または Settings.paper_sqlite_path）を使用して本番 DB と分離します。paper_trading を利用する場合はこの DB のバックアップ / 初期化を用意してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL はポーリング秒数（正の整数）を指定します。不正値（0 や負、非整数）は無視されデフォルト 60 秒にフォールバックします。
- ニュース NLP を利用するには OPENAI_API_KEY を設定してください。API 呼び出しはレート制限・ネットワークエラーに対するリトライを実装していますが、コスト管理には注意してください。
- process_priority / set_cpu_affinity は権限不足で失敗する場合があります（warning ログで通知）。必要ならば起動ユーザーの権限を調整してください。

---

この CHANGELOG はコードベースから推測して作成したものです。リリース時は実際の変更履歴（コミットメッセージ・差分）に基づいて更新してください。