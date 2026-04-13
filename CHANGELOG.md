# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]
（未リリース — 将来の変更をここに記載します）

---

## [0.1.0] - 2026-04-13

初回公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコア機能群を含み、以下の主要機能・改善点を実装しています。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数／.env ファイル読み込み・検証機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序を実装（OS 環境変数を保護）。
    - export KEY=val 形式、引用符付き値（バックスラッシュエスケープ対応）、インラインコメント処理をサポート。
    - 必須項目取得時に未設定なら ValueError を送出する _require() を提供。
    - 各種設定プロパティ（DB パス・PID/KILLフラグパス・閾値・環境モード等）を提供し、入力値の妥当性チェックを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 実行／監視スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを提供。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - DuckDB 接続を受け取り、engine に渡す実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を設定、例外発生時もループ継続するフェイルセーフ実装。
- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を run スクリプトから呼び出し、監視用テーブルの存在を冪等に保証。
- portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio_builder:
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を提供。
    - calc_score_weights: スコア加重配分を提供。全銘柄のスコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を制限するフィルタリング（sell_codes を除外して計算）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは警告して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じた発注株数計算を実装。
    - lot_size による丸め、単銘柄上限・総合キャップ（available_cash）によるスケールダウン、cost_buffer を使った保守的コスト見積り、端数処理の再配分ロジックを実装。
- research（ファクター計算・探索）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクター（mom, MA200乖離, ATR20, avg_turnover, PER, ROE 等）を計算。
    - データ不足時の None 処理およびウィンドウ計算を考慮。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括クエリで計算。
    - calc_ic, rank, factor_summary: IC（Spearman ρ）計算、ランク付け（同順位は平均ランク）、基本統計量サマリーを実装。外部ライブラリに依存せず標準ライブラリで実装。
- ai（ニュース NLP）
  - news_nlp:
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）を正しく UTC に変換する calc_news_window。
    - バッチサイズ（最大 20 銘柄）、記事/文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）を実装。
    - API キーが未設定の場合は ValueError を送出。
    - 部分失敗時に既存の他コードスコアを保護するため、対象コードで絞って DELETE→INSERT を行う更新戦略を採用。
- tools
  - paper_verification_report:
    - Paper Trading の検証レポート生成ツール（CLI）を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - 集計クエリ、P95 算出、閾値判定（デフォルト閾値を定義）および PASS/FAIL 判定を出力。
    - CLI オプション --from / --to / --db を提供。DB がない場合は明示エラーメッセージ。
- utils
  - process_priority:
    - set_process_priority(level) 実装（Windows / POSIX(Linux, Darwin, FreeBSD) を吸収）。権限不足や未対応 OS では警告してスキップ。
    - set_cpu_affinity(cpu_count) を追加（None で設定しない、1未満は ValueError）。
  - その他ユーティリティはパッケージ構成に統合。

### Changed
- 設計上の方針（ドキュメント・コード内コメント）
  - ファクター・ポートフォリオ構築・ポジションサイズ計算はすべて純粋関数（副作用なし、DB 参照なし）という方針を明確化。
  - DuckDB を中心とした分析ワークフローを前提に SQL + Python の組合せで実装。
  - 実行スクリプトは起動時にプロセス優先度を上げることで運用上の優先度を確保する設計。

### Fixed
- 環境変数処理
  - .env パーサーの挙動を堅牢化（空行・コメント・export 形式・引用符付き文字列のエスケープ・インラインコメント処理）。
- ポジションサイズ計算
  - 合算コストが available_cash を超える場合のスケーリングと端数処理により、lot_size 単位で再配分するロジックを実装し、余剰キャッシュの活用を改善。

### Security / Reliability
- 外部 API 呼び出し（OpenAI）に対してリトライ・バックオフ・バリデーションを導入し、フェイルセーフで継続できるように実装。
- プロセス優先度や CPU affinity の設定は権限不足や未サポート環境で安全にスキップするように警告ログで処理。
- 実行スクリプトは try/finally で DB コネクションを確実にクローズするように実装。

### Notes / Limitations
- NEWS NLP: OpenAI API キーが未設定の場合は処理が失敗する（ValueError）。運用時は OPENAI_API_KEY を設定してください。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（テストやパッケージ配布を考慮）。
- calc_regime_multiplier の bear=0.3 はリスク低減用の追加ガード。Strategy 層で Bear 時はそもそも BUY シグナルを生成しない設計（コメント参照）。
- position_sizing は現状 lot_size が全銘柄共通（将来的に銘柄別 lot_map へ拡張予定）。
- monitoring/run_monitoring は監視用 DB に本番 sqlite_path を使うため、環境分離ポリシーに注意。

---

今後の予定（例）
- ユニットテストの充実（research・portfolio・ai モジュールの境界テスト）
- ブローカークライアントのモック/インターフェース改善とテストツールの整備
- 銘柄別 lot_size 対応、コスト見積り（手数料・スリッページ）モデルの拡張
- ai スコア取得の並列化・プロンプト改善と応答フォーマットの厳格化

もし特定の変更点（ファイル単位や挙動）について詳細な説明や別の書き方（英語版やより細かいリリースノート形式）を希望される場合はお知らせください。