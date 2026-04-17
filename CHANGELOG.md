# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
https://keepachangelog.com/ja/

## [Unreleased]

- なし（現時点のコードスナップショットは初回リリース相当の機能群を含みます）

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能を実装しています（コードベースから推測して列挙）。

### Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョン `0.1.0` を設定。

- 設定・環境変数管理（kabusys.config）
  - .env 自動読み込み機構を実装（プロジェクトルートの検出: .git / pyproject.toml）。
  - .env / .env.local の読み込みルール（OS 環境変数を保護する protected 設定、override 動作）。
  - .env 解析器の実装（export 形式、クォート、エスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを提供し、アプリ全体で利用する設定プロパティを定義（J-Quants / Kabu API / LINE / DB パス / PID・KILL フラグパス / 監視しきい値 / 環境種別検証等）。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- ランナー
  - 実行エンジン起動スクリプト（run_execution.py）
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler の組み立て・起動処理。
    - paper_trading モード時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱い、スレッドでのエンジン実行と安全な停止処理。
    - RiskConfig による初期リスクパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - 監視ループ起動スクリプト（run_monitoring.py）
    - SystemMonitor を初期化してポーリングループを実行。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、妥当性チェック）。
    - 監視用途は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の挙動。
    - 停止フラグ検出でループ終了、例外時のロギングと継続動作。

- DB 初期化/監視補助
  - init_monitoring_db 呼び出しによる監視用テーブルの冪等的初期化（run_execution/run_monitoring）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナルの候補選択（select_candidates）、等重み・スコア加重による重み計算（calc_equal_weights, calc_score_weights）。スコア全てが 0 の場合のフォールバックロジックを含む。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier、bull/neutral/bear のマップと未知レジームのフォールバック）。
  - position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の allocation メソッドに対応、単元株（lot_size）丸め、aggregate cap（available_cash に基づくスケーリング）、cost_buffer の考慮、価格欠損時のスキップ等。将来的な拡張点（銘柄別 lot_size 等）に関する TODO コメントを含む。

- 研究用計算（kabusys.research）
  - factor_research: モメンタム（calc_momentum）、ボラティリティ／流動性（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB 上で実行する実装。各種ウィンドウ長・欠損扱いを考慮。
  - feature_exploration: 将来リターン算出（calc_forward_returns）、IC（calc_ic）・ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）。
  - DuckDB を用いた SQL + Python の設計方針、外部 API 非依存。

- ツール
  - paper_verification_report: Paper Trading 向けの検証レポート生成スクリプトを追加。
    - CLI オプション --from / --to / --db を提供。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを計算して人間可読なレポートを標準出力に出力。
    - 判定基準（閾値）を定義して PASS/FAIL を判定。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）に対してバッチでスコアリングし、銘柄別 ai_scores に書き込む処理の設計と実装を追加。
  - 処理フロー設計（ウィンドウ指定、銘柄ごとの記事集約、チャンク送信、リトライ/バックオフ、レスポンス検証、スコアクリップ、部分置換による堅牢な DB 書き込み戦略）を実装。
  - calc_news_window と score_news（API キーチェック、ウィンドウ計算、記事集約呼び出し）を実装。リトライロジック・バッチサイズ・トークン肥大化対策の定数を定義。
  - 注意: 提供されたファイルは末尾が切れているため、記事取得部分の内部実装（_fetch_articles 等）がスナップショットでは未表示（あるいは実装途中）であることを検出。

- プロセス設定ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority により Windows / POSIX の差分を吸収してプロセス優先度を設定（アクセス拒否等をハンドリングして警告を出力）。
  - set_cpu_affinity による CPU affinity 設定（コア数チェック、権限エラーのハンドリング）。

### Changed
- なし（初回リリース相当の追加が中心）

### Fixed
- なし（初期コードに対するバグ修正履歴はなし）

### Notes / Known issues
- news_nlp モジュールがスナップショットの最後で途中切れになっており、記事フェッチや一部の書き込みロジックが未表示／未完になっている可能性があります。実運用前にファイル末尾・関連ヘルパー（_fetch_articles 等）の実装確認が必要です。
- position_sizing 内で価格が欠損（0.0）の場合にエクスポージャーが過少見積りされ、セクター上限チェックで想定外の振る舞いをする可能性がある旨の TODO コメントあり。価格フォールバック戦略（前日終値や取得原価など）の導入を検討してください。
- MONITOR_POLL_INTERVAL の 0 以下や非整数入力に対するフォールバックが実装されていますが、監視要件により最小値制約や上限値の追加検討が推奨されます。
- .env 自動読み込みはデフォルトで有効。テストなどで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用可能。

---

以上は現行コードの内容をもとに推測して作成しています。必要であれば各変更項目に対して該当ソースファイルや行の参照、あるいはリリースノート向けの短い英語要約なども追加できます。どの粒度まで記載するか指示ください。