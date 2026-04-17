CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
重要なバージョンや機能追加・修正について日本語で要約しています。

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Security: セキュリティに関する注意

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース。以下の主要コンポーネントを追加。
  - 実行系起動スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、スレッド実行と停止フラグ監視を実装。
    - Paper Trading（KABUSYS_ENV=paper_trading）時は専用の paper_trading DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
  - 監視系起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを用いた優雅な終了処理、例外発生時のログ保護を実装。
  - 設定管理
    - config.py: .env/.env.local の自動読み込み機能（OS 環境変数を保護）、.env パースの堅牢化（クォート・エスケープ・コメント処理対応）、設定取得用 Settings クラスを追加。各種環境変数（DB パス、PID/kill フラグパス、しきい値、Paper Trading 設定等）をプロパティとして提供。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック挙動を定義。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - portfolio.position_sizing: 複数配分方式（risk_based / equal / score）に対応した株数決定ロジックを実装。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮。
  - リサーチ / ファクター計算
    - research.factor_research: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB 上の prices_daily / raw_financials テーブルを参照して純粋関数として計算。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を追加。外部依存を避け標準ライブラリのみで実装。
    - research パッケージは zscore_normalize を外部モジュール（kabusys.data.stats）からエクスポート。
  - ニュース NLP（AI）モジュール
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングする基盤を追加。タイムウィンドウ計算（calc_news_window）、バッチ送信設計（1 API call あたり最大銘柄数）、API キー解決、リトライ（指数バックオフ）・応答バリデーション・スコアクリッピングの方針を実装。部分的に実装中の関数あり（score_news は途中まで実装）。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX の対応、権限不足時のフォールバックログ処理を実装。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（P95）等を計算し、閾値（稼働率 99%、注文成功率 90% 等）に基づく PASS/FAIL 判定を標準出力に出力。
  - パッケージ初期化
    - __init__.py: パッケージバージョン（0.1.0）とエクスポート一覧を追加。

Changed
- プロジェクト自動環境読み込みの仕様を定義
  - .env 自動読み込みはデフォルトで有効。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=True で .env を上書き）。
  - OS の環境変数は protected として上書きされないよう保護。

Fixed
- 各モジュールでの入力検証とフォールバックを強化
  - config.Settings.paper_fill_mode: 有効値チェックを追加し、無効な場合は ValueError を発生させる。
  - run_monitoring._get_poll_interval: 環境変数が不正（0 以下や非整数）の場合にデフォルトへフォールバックし、警告ログを出すよう改善。
  - position_sizing のスケーリングロジック: lot_size 単位での丸めと残差の再配分を明確化し、再現性のために安定ソート（code 二次キー）を使用。
  - factor / forward return 計算: horizons の検証（正の整数かつ <= 252）を追加。

Security
- ai.news_nlp.score_news は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須とし、未設定時は ValueError を送出。API キーの取り扱いは環境変数経由を想定。

Notes / Implementation details
- DB 関連
  - DuckDB は分析用（prices_daily, raw_financials 等）、SQLite は監視・実行（monitoring / paper_trading）用に想定。run_monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視専用）。
  - init_monitoring_db が呼び出され監視用テーブル存在を保証（冪等）。
- プロセス制御
  - 起動スクリプトは最初に set_process_priority("high") を呼び出して優先度を上げるようにしている（権限がない場合は警告で継続）。
  - 停止はプロジェクトルート/data/stop_requested.flag（または設定されたパス）で検知して優雅に終了。
- CLI / ツール
  - tools.paper_verification_report は日付フィルタ（--from / --to）と --db オプションを備え、期間フィルタを ISO8601 形式の UTC タイムスタンプに変換してクエリに渡す。
- 開発上の注意
  - ai.news_nlp モジュールは API 送信・レスポンス検証を行う設計だが、実装の一部（記事集約からの続き処理）がファイル内で途中となっているため、本格運用前に完成実装と単体テストが必要。

Acknowledgments
- 本リリースはプロジェクト初期実装の集合であり、ポートフォリオ構築・リサーチ・実行・監視・AI 評価の主要機能を中心に揃えています。運用・拡張（例: lot_size の銘柄別対応、ニュース NLP の完全実装、テストカバレッジ強化）を今後の課題としています。