# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

全般方針:
- 変更は「Added / Changed / Fixed / Deprecated / Removed / Security」で分類しています。
- 各項目はソースコードから推測できる新機能・改善・バグ対策・既知の制限点などを記載しています。

## [0.1.0] - 2026-04-16

### Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV に依存せず本番の sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。paper_trading 環境時は MockBrokerClient を使用し、paper_trading 用 DB に完全分離して記録する。停止フラグ・PID ファイル連携を備える。

- 設定・環境管理
  - Settings クラスを追加して環境変数を集中管理。多くの設定（DB パス、API トークン、監視閾値、環境種別など）をプロパティで提供。
  - .env 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml に基づく）。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（クォート・エスケープ・コメント処理・export 形式に対応）。

- モジュール群（ポートフォリオ構築、リスク制御、ポジションサイジング）
  - kabusys.portfolio: 銘柄選定 (select_candidates)、重み計算 (calc_equal_weights, calc_score_weights)、セクター上限適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)、株数算出 (calc_position_sizes) を実装。
  - position_sizing: risk_based / equal / score の配分方式に対応。単元株丸め、最大ポジション上限、aggregate cap に基づくスケーリングと端数処理（残差の贈与ロジック）を実装。

- リサーチ機能
  - kabusys.research: ファクター計算（モメンタム、ボラティリティ、バリュー）を DuckDB 経由で実装。
  - feature_exploration: 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）、ファクター統計サマリー、rank ユーティリティを提供。外部ライブラリに依存しない純粋 Python 実装。

- ニュース NLP（AI スコアリング）
  - kabusys.ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント解析し、銘柄別 ai_scores に書き込むワークフローを実装。バッチ処理、トークン肥大対策（記事数・文字数制限）、API エラーに対する指数バックオフ・リトライ、レスポンスバリデーション、スコアクリッピングを含む。

- 運用ユーティリティ
  - process_priority ユーティリティを追加。Windows と POSIX（Linux/Mac 等）を吸収してプロセス優先度設定を行う set_process_priority()、および CPU affinity を設定する set_cpu_affinity() を実装。アクセス権限や未対応環境では警告を出して安全にスキップする。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを計算して標準出力にレポートを出力。期間指定や DB パス指定を CLI 引数で受け付ける。

### Changed
- データベース利用方針の明示化
  - 監視処理は KABUSYS_ENV に依存せず production 用 sqlite_path を使用する（run_monitoring.py の設計）。
  - 実行エンジンは paper_trading 環境で専用の paper_sqlite_path を使用することで本番 DB と完全分離。

- 設定ロードの振る舞い
  - .env の読み込み時に OS 環境変数を保護（protected set）して .env.local/.env による上書きを制御。

- ロギング・エラーハンドリング
  - 各モジュールで詳細なログメッセージを追加（起動環境表示、ポーリング開始/停止、API エラーでの例外ログなど）。
  - run_monitoring の polling loop で monitor.check_once() の例外をキャッチし例外とスタックトレースをログに残して次のポーリングに継続するようにした。

### Fixed
- 環境変数パースの堅牢化
  - MONITOR_POLL_INTERVAL の解析で不正な値（非整数・0 以下）を検出した場合にデフォルトへフォールバックし、警告ログを出力するようにした（ValueError による time.sleep のクラッシュ回避）。

- DB 初期化の冪等化
  - init_monitoring_db(sqlite_conn) を実行開始時に呼ぶことで監視テーブルが存在することを保証（重複実行時に安全）。

- 集計・統計処理の安全化
  - P95 計算（_p95）で空リストに対して None を返すようにして例外を防止。
  - factor_summary / calc_ic 等で None 値や非有限値を除外することで統計計算時のエラーを回避。
  - calc_score_weights で全銘柄スコアが 0 の場合に等金額配分にフォールバックし警告ログを出力。

### Performance
- DuckDB を分析処理（ファクター計算・ニュース集約等）に使用することで大量データの集計を効率化。SQL ウィンドウ関数を多用して一度のクエリで必要な指標を計算する設計。

### Documentation / Docstrings
- 各モジュールに詳細な docstring を追加し、設計方針・引数・返り値・注意点（例: ルックアヘッドバイアス回避、DuckDB executemany の挙動、lot_size の将来的拡張など）を明示。

### Deprecated
- なし（このリリース時点で明示的な非推奨 API はなし）。

### Removed
- なし。

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を利用する設計。キー未設定時は明示的な ValueError を発生させる（誤設定を早期に検出）。

### Known issues / Notes / TODO
- ai/news_nlp.py のスクリプトは大まかなワークフロー・エラーハンドリングを実装しているが、（提示されたコードは途中で切れているため）完全な実行ルートや DB への書き込み処理の細部が不足している可能性がある。実運用前に end-to-end の検証が必要。
- portfolio.risk_adjustment.apply_sector_cap の価格欠損（price_map に 0.0 等）がある場合、エクスポージャーが過少に見積られる旨の TODO コメントが存在。将来的に前日終値や取得原価をフォールバックとして用いる拡張が想定されている。
- position_sizing は現状 lot_size をグローバル定義（全銘柄共通）としている。将来的には銘柄別 lot_map を受け取る拡張が検討されている旨の TODO。
- process_priority/set_cpu_affinity は権限不足（root 権限等）や一部 OS 非対応の場合に失敗することがあり、その場合は警告を残してスキップする挙動になっている。

---

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノートとして使用する場合は、実装者による確認・追記（マイナー修正・追加された API など）を推奨します。