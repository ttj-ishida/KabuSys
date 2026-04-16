# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 本 CHANGELOG はリポジトリ内のソースコードから機能・挙動を推測して作成したものです。実際の変更履歴やコミットメッセージに基づくものではありません。

## [Unreleased]

### Added
- ニュースNLP スコアリングモジュール (kabusys.ai.news_nlp)
  - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む設計を導入。
  - バッチサイズ、トークン肥大化対策（記事数・文字数の上限）、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフ等の考慮を実装予定。
  - OpenAI API キーの解決ロジック（引数 > 環境変数）を実装。
  - ニュース時間ウィンドウ計算ユーティリティを追加（JSTベース→UTC変換）。

### Changed
- なし（進行中の作業により後続リリースで反映予定）

### Known issues / In progress
- kabusys.ai.news_nlp の実装は未完（ソースが途中で切れているため、記事取得処理の続き／DB書き込みロジックの検証が必要）。
- 実装中の部分はフェイルセーフ設計だが、ユニットテストと統合テストが必要。

---

## [0.1.0] - 2026-04-16

最初の公開リリース（ソースから推測した機能群を収録）。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を導入（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の優先順位を実装（OS 環境変数を保護）。
  - 複雑な行パースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント扱いの制御）。
  - 必須 env の検証ヘルパー `_require`、各種設定プロパティ（DB パス、paper_trading 用設定、監視閾値、環境判定、ログレベル検証など）を実装。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。paper_trading 環境時は paper 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、ExecutionEngine のスレッド起動と停止フラグ検知機構を実装。
    - プロセス優先度を起動時に高く設定する処理を追加（set_process_priority）。
    - 停止フラグ (data/stop_requested.flag) と PID ファイルの扱い。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する旨を明示。
    - poll 間隔の不正値に対するワーニングとフォールバック実装。

- 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db を各起動時に冪等で呼ぶ）

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows / POSIX の差分吸収、psutil 使用）。
  - set_cpu_affinity(cpu_count) を実装（指定コア数にプロセスを固定、権限不足や未対応プラットフォームを安全にスキップ）。
  - 期待しない例外（AccessDenied 等）をワーニングで扱う設計。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア順・タイブレーク）、等金額配分、スコア加重配分（全スコア0時はフォールバック）。
  - risk_adjustment: セクター集中制限 apply_sector_cap、market regime に基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングと未知レジームフォールバック）。
  - position_sizing: allocation_method に応じた株数決定（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、コストバッファを考慮した安全弁ロジック。
  - 一部に将来の拡張 TODO（銘柄別 lot_size 等）。

- リサーチ機能（kabusys.research）
  - factor_research: Momentum / Volatility / Value 等ファクター計算（DuckDB を用いた SQL ベース実装）。MA200、ATR、20日平均売買代金、PER/ROE などを計算。
  - feature_exploration: 将来リターン計算、Spearman ランク相関による IC 計算、ファクターの統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。rank ユーティリティ実装（同順位は平均ランク）。
  - research/__init__.py で主要関数をエクスポート。

- Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
  - CLI で paper_trading DB（デフォルト: data/paper_trading.db）を読み込み、システム稼働率・注文成功率・送信率・P95 レイテンシ 等を集計してレポート出力。
  - 判定基準値を定義（稼働率 >=99%、注文成功率 >=90% 等）。P95 計算、日付フィルタ対応、DB 存在チェック、OperationalError のフォールバック保護を実装。

### Fixed
- なし（初期実装）

### Changed / Design notes
- DuckDB / SQLite の役割分離を明確化:
  - DuckDB を時系列・ファクター計算などの分析用途（prices_daily / raw_financials 等）で使用。
  - SQLite を監視・トレードログなどトランザクション的小規模データに使用。paper_trading 環境では paper 用専用 SQLite を使用して本番 DB と分離。
- .env 自動ロードはプロジェクトルートが見つからない場合はスキップされる（配布後の動作を想定）。
- ログレベル・環境名のバリデーションを強化（許容されない値は ValueError）。

### Removed / Deprecated
- なし

### Security
- OpenAI API キーなど機密情報は環境変数参照により管理。`.env` 自動読み込みは OS 環境変数を保護する設計（override の際に protected set を使用）。

### Known issues / TODOs
- position_sizing の価格欠損処理: price が欠損（0.0）の場合にエクスポージャー過少見積りとなる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- news_nlp モジュールは設計が詳細に記述されているが、実装は途中のため実行時エラーとなる可能性あり（記事取得関数の未実装など）。
- DuckDB executemany の挙動（パラメータが空の場合の制約）に注意した実装になっているが、実運用での追加検証が必要。
- set_process_priority / set_cpu_affinity は権限不足で失敗する可能性があるため、運用時は実行権限・プラットフォーム依存性に注意。

---

作成者: 自動生成（ソースコード解析に基づく推測）
補足: 正確な変更履歴（コミット単位）を得たい場合は git のログを使用してください。