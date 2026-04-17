# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

なお、本ログは提示されたソースコードの内容から機能追加・修正点を推測して作成したものです。

## [Unreleased]

### Added
- - （開発中）今後のリリース向けの変更点をここに記載します。

## [0.1.0] - 2026-04-17

初回リリース想定。以下の主要機能を実装しています。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 実行開始時にプロセス優先度を設定し、監視用 SQLite（monitoring DB）を初期化、DuckDB 接続を確立して定期的に monitor.check_once() を実行する。
    - 停止はプロジェクト配下 data/stop_requested.flag によるファイルフラグ方式を採用。
    - 監視は環境 (KABUSYS_ENV) にかかわらず本番 sqlite_path を使用する仕様を明示。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグおよび PID ファイルの扱いに対応。

- 設定・環境読み込み
  - config.py
    - Settings クラスを導入。環境変数経由で各種設定（DB パス、API トークン、閾値、各種フラグ等）を取得するプロパティを提供。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env / .env.local の自動読み込み機能を実装（OS 環境変数を保護するための上書き制御あり）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）や PID/kill フラグパス等のプロパティを提供。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。コマンドライン引数 --from/--to/--db をサポート。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) などを集計し、定義済み閾値に基づいて PASS/FAIL 判定を出力。
    - DB テーブル欠如や OperationalError 発生時のフォールバック処理を実装。

- ポートフォリオ構築
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates（スコア降順選定、タイブレークルール）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバックし警告出力）を実装。
    - risk_adjustment.py
      - apply_sector_cap（既存保有からセクター別エクスポージャを算出し、上限超過セクターの候補銘柄を除外）、calc_regime_multiplier（Bull/Neutral/Bear の乗数マップ、未知のレジームは警告とともに 1.0 にフォールバック）を実装。
    - position_sizing.py
      - calc_position_sizes を実装。allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）丸め、銘柄ごとの上限（max_position_pct）・ポートフォリオ総上限（max_utilization）適用、コストバッファを考慮した aggregate cap スケーリングおよび残差に対する lot 単位での再配分ロジックを実装。

- 研究用/因子計算
  - kabusys.research
    - factor_research.py にてモメンタム（1M/3M/6M）、MA200 乖離、ATR20、平均出来高等の計算関数（DuckDB 接続利用）を追加。
    - feature_exploration.py にて将来リターン（複数ホライズン対応）、IC（Spearman）計算、ファクター統計サマリ、ランク関数を実装。
    - research パッケージの __all__ を整備。

- AI / ニュース NLP
  - ai/news_nlp.py（初期実装）
    - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）でニュースセンチメント（-1.0〜1.0）をバッチでスコアリング、ai_scores テーブルへ書き込む処理を設計。
    - バッチサイズ、最大記事数／文字数トリム、リトライ（429/5xx/ネットワーク）等の基本動作／定数を定義。
    - calc_news_window（JST ベースのニュースウィンドウ計算）と score_news（API キー検証を含む）を実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority（Windows/POSIX の差分を吸収して優先度設定）、set_cpu_affinity（プロセスを最初 N コアに固定）を追加。権限不足や未対応 OS の場合は警告を出して処理をスキップする堅牢化を実装。

### Changed
- 環境変数読み込みポリシー
  - .env と .env.local の読み込み順と上書きポリシーを明確化（OS 環境変数を保護、.env.local は override=True で上書き）。
- 監視プロセス
  - run_monitoring の監視データは開発・paper_trading 等にかかわらず本番 sqlite_path を使用する仕様に固定（設計上の意図を明示）。
- 実行エンジン
  - run_execution が paper_trading モード時に専用 DB を使うようにし、本番データと完全分離する動作に変更（安全性向上）。
- position_sizing
  - aggregate cap のスケーリングロジックと残差配分アルゴリズムを導入し、available_cash 超過時の分配をより安定／再現性を持たせて処理。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL の扱い
  - 環境変数から読み取った値が不正（非整数、0 以下等）の場合は警告を出してデフォルト（60 秒）にフォールバックするように修正（time.sleep に与える不正値対策）。
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメントの扱いなどを取り扱うように実装し、より .env ファイルの多様な表記に対応。
- calc_score_weights
  - 全銘柄スコア合計が 0.0 の場合に等金額配分へフォールバックし logger.warning を出す安全弁を追加。
- process_priority / cpu_affinity
  - 未対応プラットフォームや権限不足時に例外を投げず警告でスキップするよう堅牢化。
- research / feature_exploration
  - calc_forward_returns の horizons 引数検証を追加（正の整数かつ 252 以下）。
- tools/paper_verification_report.py
  - DB テーブルが存在しない／OperationalError が発生した場合に個別指標ごとにフォールバックしてレポートを生成するようにして、欠損テーブルでもレポートが出力されるように改善。
- ai/news_nlp.py
  - score_news で API キーが未設定の場合に ValueError を発生させる（明示的なエラーとフェイルセーフ）。

### Documentation / Comments
- 各モジュールに詳細な docstring コメントを追加（設計方針、入力/出力、注意点、TODO など）。これにより API 利用者／開発者が意図を把握しやすくなっています。

---

注記
- 上記は提供されたソースコードを元に推測した変更点・実装内容です。実際のコミット履歴や差分とは異なる場合があります。
- セキュリティ面（API キーの取り扱い、DB ファイル権限等）や運用手順（PID/stop フラグの管理）は別途運用ドキュメントで整理することを推奨します。