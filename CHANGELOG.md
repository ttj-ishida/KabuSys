# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお下記はコードベース（src/ 以下）を解析して推測した変更点の要約です。

## [Unreleased]
### Added
- 全体
  - DuckDB / SQLite を併用するデータパイプライン周りの整備（prices_daily / raw_financials 等を前提とした分析処理を想定）。
- 実行・監視
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（paper/live 切替を想定）。
    - Engine 起動時に PID ファイルを書き、data/stop_requested.flag による外部停止を監視。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は実行環境にかかわらず本番 sqlite_path を参照する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
- コンフィグ / 環境変数
  - config.py: 高機能な環境変数管理を実装。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）。
    - export KEY=... 形式、シングル・ダブルクォート内のエスケープ、行末コメントの扱いなどを考慮した .env パーサ実装。
    - 必須環境変数取得用の _require() を提供し未設定時は明示的に例外を送出。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）を追加。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH 等の設定プロパティを提供。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: シグナル選定と重み算出関数を追加
    - select_candidates: スコア降順＋タイブレークで上位 N を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化（全スコアが 0 の場合は等配分にフォールバック）
  - portfolio/position_sizing.py: 発注株数算出ロジックを追加
    - risk_based / equal / score の allocation_method をサポート
    - lot_size（単元）に合わせた丸め、max_position_pct・max_utilization・cost_buffer を考慮した集約キャップ処理を実装
    - available_cash に基づくスケーリングと端数配分ロジック（fractional remainders）を実装
  - portfolio/risk_adjustment.py: セクター上限とレジーム乗数
    - apply_sector_cap: 既存保有のセクター露出により新規候補を除外するロジック
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数
- 研究（Research）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200乖離を計算
    - calc_volatility: ATR20 / ATR_pct / 平均売買代金 / 出来高比を計算
    - calc_value: EPS から PER、ROE を計算（raw_financials との結合）
    - 各関数は DuckDB 接続を受け取り、指定日に対する銘柄リストを返す設計
  - research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得
    - calc_ic / rank / factor_summary: IC（スピアマン）計算、ランク化、統計要約を実装
  - research/__init__.py: 公開 API を整理（zscore_normalize の re-export 等）
- AI / ニュースNLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント付与して ai_scores テーブルへ書き込む処理を実装（バッチ送信、スコアクリッピング ±1.0）。
    - タイムウィンドウ算出（JST ベースの前日 15:00 〜 当日 08:30 相当の UTC 範囲）。
    - API 呼び出しに対するリトライ（指数バックオフ）、429/5xx/タイムアウト等のハンドリングを実装。
    - 出力のバリデーションと部分更新（対象コードのみを DELETE → INSERT）で部分失敗に備える。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加（CLI）。
    - システム稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を集計し PASS/FAIL 判定（閾値はソース内定義）。
    - --from / --to / --db オプションをサポート。
- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）。
    - CPU affinity 設定関数 set_cpu_affinity を追加（最初 N コアに固定）。
    - 権限不足や未サポート環境での失敗は警告に留めフォールバック。
- パッケージ
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- DB 初期化
  - monitoring テーブルは init_monitoring_db() で起動時に冪等に初期化されるように統一（monitoring 側・execution 側ともに呼び出す）。
- 実行・監視の振る舞い
  - run_monitoring/run_execution 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
  - run_execution は thread を用いて engine.run_session() をデーモンスレッドとして起動し、外部停止フラグを監視して安全に停止する設計に変更。
- .env 読み込みポリシー
  - OS 環境変数を優先し、.env/.env.local のロード順と上書きポリシーを明確化（.env.local が上書き可能だが OS 環境変数は保護）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- ロギング / エラーハンドリング
  - check_once() 等で例外が発生してもポーリングループが継続するようになり、例外時は logger.exception して次回ポーリングまで待機するように変更。
  - MONITOR_POLL_INTERVAL の不正値に対して警告してデフォルトにフォールバックするロジックを追加。

### Fixed
- 環境変数パーサの強化により、引用符やエスケープシーケンスを含む値、行末コメントなどが誤って切り捨てられる問題を解消。
- position_sizing のスケーリング処理にて小数端数処理（lot 単位丸め）と残余配分の再現性を向上（安定ソートを導入）。
- research モジュールで不足データ時に None を返す設計にして上位処理での例外発生を回避。

### Security
- 必須の機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings 経由で _require() により取得し、未設定時は起動時に明示的に例外を送出して起動を停止するようにした（誤った省略による不正動作を予防）。

---

## [0.1.0] - 2026-04-15
初回リリース相当のスナップショット。
上記 Unreleased に記載の大半の機能（実行エンジン起動、監視ループ、ポートフォリオ構築ユーティリティ、リサーチ/ファクター計算、AI ニューススコアリング、Paper Trading 検証ツール、環境設定ユーティリティ、プロセス優先度設定等）を含む。

- 主要機能（概要）
  - ExecutionEngine / EngineConfig / OrderManager / RiskManager / Reconciler 等の実行系コンポーネントの組み立て及び起動スクリプト（run_execution.py）
  - SystemMonitor と監視ループを起動する run_monitoring.py
  - ポートフォリオ構築（銘柄選定、重み算出、株数計算）、セクター制限、レジーム乗数
  - DuckDB によるファクター計算（モメンタム・ボラティリティ・バリュー）および研究用ユーティリティ（forward returns, IC, summary）
  - OpenAI を用いたニュースセンチメントスコアリング（バッチ処理・リトライ・安全な DB 更新）
  - Paper Trading の検証レポート生成ツール（CLI）
  - .env 自動読み込みと堅牢なパーシング
  - プロセス優先度および CPU affinity 設定ユーティリティ

注: 日付はソース内の使用例・コメントや現在のリリース時点を元に推定しています。

---

保守上の注記・今後の課題（コード内コメントより）
- position_sizing:
  - lot_size を銘柄毎に持たせる設計（将来的な拡張）や価格欠損時のフォールバック価格採用が検討課題。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターに対する取扱いや price が欠損した場合のエクスポージャー過少見積りの改善が必要。
- ai/news_nlp:
  - API 制限や失敗時の部分復旧ポリシー、出力スキーマの厳密検証の継続的な強化が望ましい。

もし特定ファイルや変更点についてより詳細な説明（差分での記載や設計意図の深掘りなど）が必要であれば、対象ファイル名を指定して指示してください。