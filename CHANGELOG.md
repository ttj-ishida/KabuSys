# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
主なバージョンは package の __version__ (src/kabusys/__init__.py) に合わせて 0.1.0 としています。

## [Unreleased]

- ドキュメント・マイナー修正やテスト追加などの未リリース変更をここに記載してください。

## [0.1.0] - 2026-04-17

初回公開リリース。自動売買システム KabuSys のコア機能群を収録しています。主な追加内容は以下の通りです。

### Added
- コアパッケージ
  - 基本情報: パッケージバージョンを __version__ = "0.1.0" として追加。
- 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（OS 環境変数を保護する protected 機構を含む）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ: コメント、export キーワード、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / paper trading / 監視閾値 / ログレベル / 環境判定 等）。
  - PAPER_FILL_MODE の入力検証（valid 値: instant/partial/never/reject）。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading 環境では専用の paper_trading DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live 切替対応）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - デーモン化されたスレッドでセッションを実行し、data/stop_requested.flag による安全停止処理を実装。execution.pid 管理。
    - RiskManager のデフォルト設定を定義（max_position_pct 等）し、初期ポートフォリオ値に broker.get_available_cash() を使用。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は環境に依らず本番 sqlite_path を使用。
    - data/stop_requested.flag による停止検知と安全終了。
- 監視 DB 初期化ユーティリティ (monitoring_db.init_monitoring_db の利用)
  - run_execution / run_monitoring 起動時に監視テーブルの存在を冪等に保証。
- プロセス優先度と CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) : Windows / POSIX に対応した優先度設定。失敗時は警告ログでスキップ。
  - set_cpu_affinity(cpu_count) : 最初の N コアにプロセスを固定する機能を追加（引数検証あり）。
- ポートフォリオ構築（純関数群） (src/kabusys/portfolio/)
  - portfolio_builder: シグナル選択 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights。
    - スコア全ゼロ時は等金額にフォールバックして警告を出力。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear を実装、未知レジームはフォールバック）。
  - position_sizing: 株数算出 calc_position_sizes（risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケーリング、残差処理による lot 単位での追加割当）。
  - 上記はすべて DB 参照無しの純粋関数として設計（メモリ内計算）。
- リサーチ機能 (src/kabusys/research/)
  - factor_research: momentum / volatility / value ファクター計算（DuckDB の prices_daily / raw_financials テーブルを参照）。
    - mom_1m/3m/6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等を計算。
    - データ不足時は None を返す設計。
  - feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic（Spearman ランク相関）、統計サマリー factor_summary、rank ユーティリティ。
    - horizons バリデーション、ランクの同値処理（平均ランク）などを実装。
  - research パッケージのエクスポートを整備。
- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI API (gpt-4o-mini) でセンチメントスコア化し ai_scores テーブルへ書き込む処理を実装（バッチ化・リトライ・レスポンス検証・スコアクリップ）。
  - ニュースウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST を UTC に変換) を提供する calc_news_window。
  - API キー解決、リトライ（429/ネットワーク/5xx）ロジック、銘柄毎にトリム（記事数・文字数）してトークン爆発を抑制。
  - フェイルセーフ: API 失敗時は該当処理をスキップして継続。部分失敗時に既存スコアを保護する DB 書き込み戦略（限定 DELETE→INSERT）。
- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading の検証レポート生成ツールを追加。
    - --from / --to / --db オプション対応。
    - system_status, trade_logs, risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して判定（PASS/FAIL）。
    - P95 計算、各種 N/A の扱い、閾値（稼働率 99% 等）を定義。
- DuckDB / SQLite 両対応
  - DuckDB を利用して時系列・財務データを高速に集計。SQLite は監視 / paper_trading 用 DB に使用。
- モジュールエクスポート
  - portfolio, research パッケージの __all__ を整理し、主要関数を外部からインポートしやすくした。

### Changed
- 設計/運用ポリシー
  - run_monitoring は常に本番 sqlite_path を使用するように明示（監視観点からの分離不要）。
  - run_execution は paper_trading 環境で DB を完全分離（data/paper_trading.db デフォルト）。
- エラーハンドリング
  - 各種長時間処理（monitoring loop、OpenAI 呼び出し、ExecutionEngine スレッド）での例外をログに出しつつフェイルセーフに継続する実装に統一。
- .env 読み込みルール
  - OS 環境変数はデフォルトで保護され、.env.local は override=True で上書き可能（ただし既存 OS 環境は保護）。

### Fixed
- 不正な MONITOR_POLL_INTERVAL の取り扱いで time.sleep に渡す前に検証を追加し、0 以下や非数値はデフォルトへフォールバック（警告ログ出力）。
- calc_score_weights: 全スコアが 0 の場合に division-by-zero を避けるため等金額配分へフォールバック（警告ログ）。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY でのみ解決。未設定時には ValueError を送出して明示的に失敗する（キー漏洩を避けるため環境変数取扱いの注意喚起が必要）。

---

備考:
- 多くのモジュールは「DB にアクセスしない純関数」「DuckDB を使った分析 SQL」「実行/監視の起動スクリプト」等、役割単位で分離しています。将来的な拡張（銘柄別 lot_size、価格フォールバック、外部 API の追加）を想定した拡張ポイントがコード内にコメントとして残されています。