# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングに従います。

現在のバージョンはパッケージ定義 (kabusys.__version__) に基づき `0.1.0` です。

## [Unreleased]

### 注意事項 / TODO
- ai/news_nlp.py の実装は途中で切れている箇所があり（記事取得→API送信→DB書き込みの後半処理が未完）、完全なスコアリングパイプラインの動作確認および追加のエラーハンドリング実装が必要です。
- position_sizing.calc_position_sizes において price が欠損した場合のフォールバック（前日終値や取得原価など）について注記があり、将来的な拡張（銘柄別 lot_size マップ等）が想定されています。
- DuckDB への executemany 実行前にパラメータが空でないことを確認する等、いくつかの運用上注意点がコメントとして残されています。

---

## [0.1.0] - 初回リリース（推定）
リリース日: 未設定

### Added
- 基本パッケージ情報
  - kabusys.__version__ を `0.1.0` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを抜ける仕組みを実装。
    - 監視用 DB は KABUSYS_ENV に関係なく本番 sqlite_path を使用して初期化。
    - プロセス優先度を高く設定する処理を起動時に呼び出す（utils.process_priority）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動／停止処理を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用。

- 設定管理
  - config.Settings
    - .env / .env.local の自動読み込み（プロジェクトルート検出に .git または pyproject.toml を使用）。
    - OS 環境変数の保護（読み込み時に既存キーを保護）。
    - 多数の設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別、ログレベル判定など）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動 .env 読み込みを無効化可能。
    - `PAPER_FILL_MODE` の妥当性チェック（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の検証ロジックを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を防ぐため既存保有比率に基づく候補除外ロジックを実装。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。

  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数を allocation_method（risk_based/equal/score）に応じて決定。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウンと残余処理を実装。
    - cost_buffer による手数料/スリッページ想定を反映。

  - portfolio パッケージの __all__ エクスポートを提供。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX(Linux/Mac/FreeBSD) に対応したプロセス優先度（nice/HIGH_PRIORITY）設定ユーティリティ。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を提供。
    - アクセス拒否や未実装例外時は警告を出して安全にフォールバック。

- リサーチ機能（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: latest raw_financials を使った PER / ROE の計算。
    - DuckDB を用いた SQL ベースの高効率集計を採用。

  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）を取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティを実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

  - research パッケージのエクスポート（zscore_normalize を含む）。

- AI ニュース NLP（部分実装）
  - ai.news_nlp
    - ニュース記事を銘柄ごとに集約して OpenAI (gpt-4o-mini) へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む設計。
    - API キー解決、タイムウィンドウ（JST → UTC 変換）の算出、バッチサイズ、トークン肥大化対策（記事数・文字数制限）、リトライ方針（指数バックオフ）、スコアのクリップ等を実装。
    - 実装方針・制約（JSON Mode 応答検証・部分成功時の DB 保護）をドキュメント化。
    - ただし実装ファイルは途中で終了しており、本番運用前に完了が必要（Unreleased 参照）。

- 運用／検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計して、稼働率・注文成功率・送信率・P95 レイテンシ等を出力する CLI ツールを実装。
    - デフォルトの閾値（PASS/FAIL 判定）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from, --to）、--db オプション、環境変数経由の DB パス指定をサポート。
    - 出力は可読なテキストレポート形式。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを run_monitoring/run_execution で実行し、監視テーブルが存在することを保証（冪等処理）。

### Changed
（初回リリースのため該当なし。ただし設計上の決定点を記録）
- 監視（monitoring）は KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計（監視データは常に本番を参照）。
- run_execution は paper_trading 環境時に DB を完全分離する（paper_sqlite_path を使用）。

### Fixed
- なし（初回リリース想定）

### Removed
- なし（初回リリース想定）

### Security
- OpenAI API キーやその他機密情報は Settings 経由で環境変数から取得する設計。自動 .env 読み込みは OS 環境変数を保護する仕組み（protected set）を導入。

---

開発者向け補足
- 多くのモジュールは外部通信（ブローカー API、OpenAI など）への依存を想定しており、paper_trading 環境では Mock Client と専用 DB を用いて本番と切り離して検証可能です。
- DuckDB を活用したリサーチ系処理はパフォーマンス指向で SQL を多用しています。テーブルスキーマ（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / trade_logs / risk_logs / system_status など）を前提としているため、DB スキーマ整備が前提です。
- 今後の作業候補:
  - ai/news_nlp.py の完成（取得 → OpenAI 送信 → レスポンス検証 → ai_scores 部分更新のフルパイプライン実装）。
  - position_sizing の価格フォールバック実装、銘柄別 lot_size サポート。
  - 単体テスト & CI の整備（設定読み込み・DB 初期化・外部 API のモックを含む）。

もし変更履歴の粒度（コミット単位や日付、特定の issue/PR 参照など）をより詳細にしたい場合は、リポジトリの Git 履歴や issue 履歴を提供してください。それに基づきバージョンごとの正確な CHANGELOG を作成します。