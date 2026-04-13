# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重要度に応じて分類しています。日付は本リビジョンのコードベースから推測して設定しています。

全般的な方針：
- 安全性（フェイルセーフ）と再現性を重視した設計。
- 実運用を想定したデフォルト設定と環境変数による上書き。
- DuckDB / SQLite を用いたデータ処理・永続化。
- 本番（live）・ペーパー（paper_trading）環境の明確な分離。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-13
### Added
- プロジェクト基盤と初期リリース相当の主要機能を追加。
  - パッケージメタ
    - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - 設定管理（kabusys.config）
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env および .env.local の読み込み順序と OS 環境変数の保護機構。
    - export 構文、クォート文字列、インラインコメント等に対応した .env パーサ実装。
    - 必須環境変数チェック（_require）と各種設定プロパティ（DBパス、API トークン、閾値、環境種別など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 実行スクリプト
    - run_execution.py：ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成。
      - OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせて ExecutionEngine を起動。
      - PID ファイル・DuckDB 接続管理を含むライフサイクル処理。
    - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。
  - 監視 DB 初期化
    - init_monitoring_db（監視用テーブルの冪等な作成保証）を実行開始時に呼び出し、監視テーブルの存在を確保。
  - プロセス制御ユーティリティ（kabusys.utils.process_priority）
    - set_process_priority(level): Windows / POSIX（Linux, macOS, FreeBSD）を吸収して優先度設定を行う。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity 固定機能（アクセス権限や未対応環境では安全にスキップ）。
    - 権限不足や未対応 API に対する警告ログを出力して安全にフォールバック。
  - ポートフォリオ構築（kabusys.portfolio）
    - portfolio_builder: シグナル選定（select_candidates）、等配分・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
      - スコア全0 の場合は等配分にフォールバックし警告。
    - position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap に基づくスケールダウンロジック、コストバッファ対応。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。
      - セクター不明コードの扱いや、レジーム不明時のフォールバックを規定。
  - 研究（research）
    - factor_research: DuckDB を用いるファクター計算（momentum, volatility, value）。
      - mom_1m/3m/6m、MA200乖離、ATR20、20日平均売買代金などを計算。
      - データ不足に対する None 処理を明確化。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマン）計算、ファクター統計要約（factor_summary）、ランク関数。
      - horizons の検証、単一クエリでのリード計算、欠損値除外等を実装。
    - research パッケージからのエクスポート（zscore_normalize を含む）。
  - AI ニュース NLP（kabusys.ai.news_nlp）
    - OpenAI API（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
      - ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ（calc_news_window）。
      - 記事を銘柄別に集約してバッチ（最大 20 銘柄）で API に送信。
      - JSON Mode の期待レスポンスを明確に定義（厳密な JSON のみ受け入れ）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを想定（リトライ上限・初期待機秒数定義）。
      - スコアを ±1.0 でクリップし、取得成功コードのみ ai_scores テーブルを差し替え（部分失敗時の保護）。
      - API キー未設定時は ValueError を送出。
  - ユーティリティ・ツール
    - tools/paper_verification_report.py：Paper Trading 向け検証レポート生成スクリプトを追加。
      - CLI（--from/--to/--db）を通じてレポート期間を指定可能。
      - system_status / trade_logs / risk_logs から各種指標を集計（稼働率、注文成功率、送信率、レイテンシ P95 など）。
      - 閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
      - p95 計算、NULL 値やテーブル欠如時のフェイルセーフ処理を実装。
  - DB 周り
    - DuckDB / SQLite 両方を利用する設計。各モジュールは接続を受け取り副作用を限定。

### Changed
- 設計上の明確化と安全性向上。
  - 環境依存の動作を減らすため Settings はプロパティ経由で値を取得し、検証を実行（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
  - run_monitoring と run_execution は起動直後にプロセス優先度を "high" に設定するよう統一。
  - Paper Trading の DB は本番 DB と完全分離する方針を明記（settings.is_paper によるパス切替）。
  - DuckDB を用いる分析処理は SQL 内で窓関数等を活用しパフォーマンスを考慮した設計に変更。
  - .env パーサにおいてクォート内のバックスラッシュエスケープやインラインコメント処理を追加し柔軟性を向上。
  - ログ出力の詳細化（起動環境、ポーリング間隔、チャンク処理数などの情報ログ追加）。

### Fixed
- フェイルセーフ処理を追加して運用上の致命的障害を低減。
  - MONITOR_POLL_INTERVAL が不正な値（0 以下や文字列等）の場合にデフォルトへフォールバックし、警告ログを出すように修正。
  - open prices / price が取得できない場合のスキップ処理（position_sizing, apply_sector_cap）を追加し、計算エラーを防止。
  - DuckDB executemany/insert 前にパラメータ空チェック等、部分失敗によるテーブル破壊を防ぐ設計を導入（news_nlp に関する注記）。
  - research / factor モジュールでデータ不足時に None を返すなど、NULL 伝播・カウント不足による誤計算を回避。
  - process_priority の未対応 OS / 権限不足時に例外を投げず警告してスキップするよう改善。

### Security
- 機密情報の取り扱いに関する基本方針を追加（環境変数経由での API キー取得、OS 環境変数保護）。
- OpenAI API キーが未設定の場合は明示的にエラーを発生させ、誤動作で鍵をロギングしないよう配慮。

---

注:
- 上記はコードベースの内容から機能・変更点を推測してまとめた CHANGELOG です。実際のコミット履歴やリリースノートが存在する場合は、それに合わせて更新してください。