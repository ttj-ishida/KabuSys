# Changelog

すべての重要な変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本リポジトリの現行バージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としてリリースしています。

## [Unreleased]

- ドキュメント化されているが実装が途中の箇所、未解決の TODO、及び既知の注意点をこの欄に列挙します。
  - ai/news_nlp.py において score_news() の途中でファイルが切れているため、OpenAI 呼び出し周り・書き込み処理・後続のエラーハンドリングが未完です。実運用前に残りの実装とテストが必要です。
  - portfolio/risk_adjustment.py の apply_sector_cap(): price が欠損（0.0）の場合のエクスポージャー過少見積りに関する TODO が残っています（前日終値等のフォールバック導入を検討）。
  - portfolio/position_sizing.py の lot_size は全銘柄共通を想定しており将来的に銘柄別単元対応の拡張 TODO が記載されています。
  - utils/process_priority.py の set_process_priority / set_cpu_affinity は権限不足や未対応プラットフォーム時にスキップする設計です。運用環境での動作確認を推奨します。

---

## [0.1.0] - 2026-04-17

最初の公開リリース。主な追加点と実装概要は以下の通りです。

### Added
- 基本構成・エントリポイント
  - パッケージ初期版を追加（src/kabusys）。
  - __version__ = "0.1.0" を設定。

- 実行 / 監視用スクリプト
  - run_execution.py
    - ExecutionEngine を立ち上げるエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使い本番 DB と分離して MockBroker を利用する想定（BrokerClientFactory を利用）。
    - プロセス優先度を高く設定し、PID ファイル管理・停止フラグ (data/stop_requested.flag) による安全停止をサポート。
    - RiskManager、OrderManager、Reconciler を組み立ててスレッドでエンジンを実行。停止フラグ検知で安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計（監視データは共通で記録）。

- 設定管理
  - config.py
    - .env / .env.local の自動ロード機能（プロジェクトルート自動検出）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサーはコメント・クォート・export 形式対応の堅牢な実装。
    - Settings クラスで環境変数値の取得・バリデーションを一元化（J-Quants / kabuAPI / DB パス / PID/kill フラグ /監視閾値 / env/log_level など）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の許容値検証を実装。

- 監視・DB 初期化ユーティリティ（参照）
  - monitoring.monitoring_db の init_monitoring_db を起動時に呼び出すように両エントリポイントで統一（監視テーブルが存在することを保証）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 日付レンジ指定 (--from / --to)、DB パス指定 (--db) をサポート。既定は data/paper_trading.db。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - 判定のしきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）をソース中で明示。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順かつ signal_rank を用いたタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有の時価を元に除外処理）。"unknown" セクターは上限適用しない挙動。
    - calc_regime_multiplier: 市場レジームごとの乗数（bull/neutral/bear → 1.0/0.7/0.3）と不明レジームのフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の allocation_method を実装。単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリングロジックを含む。cost_buffer（スリッページ等）を考慮した投下金額保守見積り。

- 研究（research）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各ファクターを計算。
    - 各関数はデータ不足時に None を返すなど安全な設計。
    - パフォーマンス考慮でスキャン範囲にバッファを持たせたクエリ実装。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）の一括取得クエリ実装。
    - calc_ic / rank: スピアマンランク相関（IC）計算、ランク付けユーティリティを実装（ties は平均ランクで処理）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
  - research/__init__.py で主要関数をエクスポート。

- AI ニュース NLP（基盤実装）
  - ai/news_nlp.py
    - タイムウィンドウ計算 (calc_news_window)、OpenAI API を用いたニュースセンチメントスコアリングの設計を実装。
    - バッチサイズ、モデル（gpt-4o-mini）、リトライ/バックオフ方針、スコアのクリップなどの運用ルールを実装。
    - DB（raw_news / news_symbols / ai_scores）との連携方針、レスポンスバリデーション、部分更新（DELETE→INSERT の範囲限定）方針をコメントとして明示。
    - ※ 実装途中（score_news がファイル途中で切れているため未完）。（Unreleased に詳細あり）

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows/Linux/macOS 等の差分を吸収するラッパー。
    - 権限不足や未対応 OS では警告を出して安全にスキップする設計。

### Changed
- （初リリースのため変更履歴はありません）

### Fixed
- （初リリースのため修正履歴はありません）

### Known issues / Notes
- run_monitoring は Monitoring 用 DB に常に settings.sqlite_path（本番想定）を使います。開発環境で監視 DB を分離したい場合は設定の見直しが必要です。
- .env ローダーは自動でプロジェクトルートを探索しますが、ルート検出に失敗した場合は自動ロードをスキップします。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能です。
- ai/news_nlp.py は現状で未完のため、実運用時は該当機能の完成と十分なバリデーションが必要です。
- 一部モジュール中に TODO コメントが存在します（価格フォールバック、lot_size の銘柄別対応等）。将来の機能追加候補。

---

## 今後の予定（提案）
- ai/news_nlp.py の残実装（API 呼び出し、レスポンス処理、DB 書き込み、異常時の部分ロールバック）と総合テスト。
- portfolio の lot_size を銘柄別に扱える設計への拡張。
- apply_sector_cap の価格欠損対策（前日終値や取得原価でのフォールバック）実装。
- CI で DuckDB / SQLite を使った統合テスト導入（factor calc / forward returns の正当性検証）。
- ドキュメント（README、運用ガイド、.env.example）の整備。

---

以上。必要であれば各ファイルごとのより詳細な変更説明（関数シグネチャ、引数説明、例）や、リリースノート英訳を作成します。どの粒度がよいか指示してください。