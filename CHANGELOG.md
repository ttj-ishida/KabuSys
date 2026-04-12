# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。
このファイルはコードベース（src/ 以下）の内容から推測して作成しています。

※日付は推定です。正確なリリース日は必要に応じて調整してください。

## [Unreleased]

### Added
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境変数 KABUSYS_ENV により paper_trading 時は専用の MockBrokerClient を使用し、データベースを分離（PAPER_TRADING_SQLITE_PATH）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は本番 sqlite_path を使用して記録。

- 設定管理
  - config.py:
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env/.env.local の自動読込を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の柔軟なパース実装（export プレフィックス、クォート、エスケープ、インラインコメント処理対応）。
    - Settings クラスを導入し、各種環境変数（DB パス、OpenAI/API トークン、PID/kill フラグ、閾値設定、ログレベル、環境種別など）をプロパティで取得・検証する API を提供。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差分を吸収する set_process_priority(level) を追加（Windows と POSIX（Linux/Mac/FreeBSD）に対応）。
    - set_cpu_affinity(cpu_count) を追加（最初の N コアにプロセスをピン留め）。
    - 権限不足や未対応環境では安全にスキップし、ログで警告する実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全てが0の際のフォールバック警告を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックして警告を出す。
  - portfolio/position_sizing.py:
    - ポジションサイズ計算（calc_position_sizes）を追加。risk_based / equal / score の配分方式をサポートし、lot_size 単位で丸め、aggregate cap（available_cash）に基づくスケーリングと端数配分処理を実装。cost_buffer による保守的コスト見積りも考慮。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（ATR20・出来高指標）、バリュー（PER・ROE）などの定量ファクター計算関数を追加。DuckDB を用いた SQL ベースの高速処理を想定。
    - データ不足時は None を返すなどの堅牢性対応。
  - research/feature_exploration.py:
    - forward returns、IC（Spearman の ρ）計算、rank、factor_summary（count/mean/std/min/max/median）等の統計ユーティリティを追加。外部ライブラリに依存せず実装。
  - research/__init__.py で主要関数を公開。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores に書き込む機能を追加。
    - 処理フロー：ウィンドウ計算（JST→UTC 変換）、記事トリム（最大記事数・文字数制限）、チャンク（最大20銘柄）送信、429/5xx/タイムアウト等の再試行（指数バックオフ）、レスポンス検証、スコア ±1 にクリップ、部分失敗時のデータ保護（対象コードのみ置換）等を実装。
    - API キー未設定時の明示的エラーと、安全なフォールバック（失敗はスキップ）を考慮。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。期間指定（--from/--to）や DB 指定（--db）をサポート。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を出力する。P95 計算や各種フォールバック（テーブル未存在時）を実装。

- DB/分析基盤
  - DuckDB 統合: 多くのリサーチ・AI モジュールが duckdb 接続を受け取り、prices_daily / raw_financials / raw_news 等のテーブルを参照する設計を採用。
  - monitoring_db 初期化呼び出しを run_* スクリプトで行い、監視テーブルの存在を保証（冪等）。

### Changed
- なし（初期導入想定）

### Fixed
- なし（初期導入想定）

### Security
- 環境変数の取り扱いに注意する旨（OPENAI_API_KEY など必須キーは未設定時に明示的にエラー）を実装。

---

## [0.1.0] - 2026-04-11

初回公開リリース（推定） — 上記「Added」に列挙した主要機能を含む最初の安定的な機能セット。

### Added
- パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
- 実行（実運用）コンポーネント
  - ExecutionEngine 起動スクリプト（run_execution.py）、Paper Trading モードと本番モードの DB 分離、RiskManager/OrderManager/Reconciler 等の組み立て。
  - SystemMonitor ポーリングループ（run_monitoring.py）と MONITOR_POLL_INTERVAL による設定。
- 設定/環境読み込み機構（config.py）と Settings API。
- プロセス優先度・CPU affinity 設定ユーティリティ（utils/process_priority.py）。
- ポートフォリオ構築ライブラリ（select/calc weights/position sizing/risk adjustment）。
- リサーチ（factor 計算、forward returns、IC、統計サマリー）。
- AI ニューススコアリング（OpenAI 経由、バッチ/リトライ/検証/テーブル更新）。
- 検証用ツール（paper_verification_report）。
- DuckDB と SQLite を併用する分析/監視基盤。

### Changed / Fixed / Security
- 初回リリースのため該当なし。

---

注記（運用上の注意）
- .env の自動ロードはプロジェクトルート検出に依存します。配布後に自動ロードされない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動で設定するなどの対応を検討してください。
- process_priority/set_cpu_affinity は権限や OS に依存して失敗する可能性があるため、ログでの警告を確認してください。
- news_nlp の OpenAI 利用は API キーと利用料金に注意してください。API のレート制限やエラーは指数バックオフでリトライしますが、完全成功を保証するものではありません。
- Paper Trading と Live 環境で DB を厳密に分離することにより、検証データと本番データの混在を防いでいます。DB パスの設定は Settings 経由で制御してください。

（必要であれば、この CHANGELOG を各コミットや PR に対応させた詳細な履歴に更新します。）