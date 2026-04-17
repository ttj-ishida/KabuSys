# Changelog

すべての重要な変更点は Keep a Changelog の方針に従って記録します。慣例によりセマンティックバージョニングを採用しています。

履歴はコードベース（src/ 以下）の内容から推測して作成しています。実装上の注記や既知の制約も併せて記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17
最初の公開リリース（コードベースから推測）。以下の主要機能・モジュールを追加。

### Added
- 全体
  - パッケージ初期化。バージョンを `__version__ = "0.1.0"` として定義。
  - DuckDB/SQLite を利用したデータ処理基盤の採用（設定でパス指定可能）。

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 環境（KABUSYS_ENV）に応じて paper_trading モード用 DB を分離使用（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory を通じたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskConfig のデフォルト値を設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, 等）。
    - スレッドでエンジンを実行し、data/stop_requested.flag による外部停止制御と data/execution.pid による PID 管理をサポート。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）を行い、環境にかかわらず本番 sqlite_path を使用する仕様。
    - プロセス優先度を起動時に "high" に設定（utils/process_priority を使用）。
    - data/stop_requested.flag の検出による安全な終了。

- 設定 / 環境読み込み
  - config.py: 環境変数と .env/.env.local の自動ロード機能を追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env ファイルのパースはクォート・エスケープ・コメント等に対応する堅牢な実装。
    - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定（is_live / is_paper / is_dev）などをプロパティで取得可能。
    - PAPER_FILL_MODE の検証ロジック（instant, partial, never, reject のみ有効）を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順に選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率による配分。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を検出して当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ。未知のレジームは 1.0 でフォールバックし警告）。
    - 既知の注意点: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり（TODO コメントあり）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を計算する汎用関数を追加。
      - allocation_method に "risk_based", "equal", "score" をサポート。
      - lot_size（単元）、cost_buffer（手数料/slippage 見積り）を考慮した aggregate cap（available_cash に基づくスケーリング）実装。
      - スケーリング後に lot_size 単位で端数調整を行い、残余キャッシュで fractional 残差順に追加配分するロジックを搭載。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を prices_daily から計算。
    - calc_volatility: ATR20, 相対 ATR, 20日平均出来高, 出来高比率等を計算。
    - calc_value: raw_financials と prices_daily から PER/ROE を計算（target_date 以前の最新財務を取得）。
    - DuckDB を使ったウィンドウ関数中心の実装で、データ不足時は None を返す挙動。
  - research/feature_exploration.py:
    - calc_forward_returns: 指定日から将来の複数ホライズン（デフォルト: 1,5,21）までのリターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 未満の場合は None を返す。
    - rank / factor_summary: ランク計算（同順位は平均ランク）・基本統計量集計を提供。
  - research/__init__.py: 主要 API を再エクスポート（zscore_normalize を data.stats からインポート）。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）に送って銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルに書き込む処理の実装。
    - バッチ処理（1回あたり最大 20 銘柄）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を追加。
    - 設計方針としてルックアヘッドバイアス防止（datetime.today() を参照しない）などを明記。
    - API キー未設定時に ValueError を送出。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）を透過してプロセス優先度（high/normal/low）を設定。psutil を使用。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定するヘルパー。
    - 権限不足・未対応プラットフォーム時は警告ログを出力してスキップ。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して CLI 出力。
    - デフォルト閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - --from / --to / --db の CLI オプションをサポート。DB ファイルがない場合の案内を表示。

### Changed
- 設計/堅牢性の向上
  - 多くの集計関数は入力データ不足時に None やデフォルト値でフォールバックし、例外を最小限に抑える設計になっている（運用での堅牢性重視）。
  - .env パース機能は quoted values / escape / inline comment などに対応し、OS 環境変数を保護するための protected オプションを導入。

### Fixed
- ロバストネス向上
  - MONITOR_POLL_INTERVAL が不正な値（文字列や 0 以下等）のときにデフォルトへフォールバックし、警告を出す処理を実装（run_monitoring）。
  - 各種 SQL クエリはデータ欠如時の sqlite3.OperationalError を扱う箇所を用意（tools/paper_verification_report）し、ツールが異常終了しないようにしている。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キーは明示的に引数または環境変数（OPENAI_API_KEY）で渡す必要があることを明記。キー管理は運用者の責任。

---

補足（実装上の注記 / 既知の制約）
- run_monitoring.py は「監視」は環境に依存せず本番用 sqlite_path を参照する仕様になっています。テスト/開発環境での監視データ分離が必要な場合は注意してください。
- position_sizing.calc_position_sizes 内で price が欠損（0.0）の場合、エクスポージャーの過少見積りにつながる可能性がある旨の TODO コメントがあります（将来的なフォールバック価格の導入を検討）。
- ai/news_nlp.py は堅牢化のため多数のバリデーション・リトライ機構を持ちますが、API 使用料やレート制限に注意してください。処理は部分的に失敗しても他銘柄の結果を保護する（原子置換の工夫）設計になっています。
- DuckDB 側で executemany に関するバージョン依存の制約がコメントに記載されています（DuckDB 0.10 の制約を参照）。

もし特定ファイルや関数に対する詳細な変更点（例: 行単位の差分や理由の深堀り）が必要であれば、対象箇所を指定してください。さらに正確な日付やリリース番号を指定いただければ、CHANGELOG の日付・ヘッダを調整します。