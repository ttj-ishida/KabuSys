CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
この CHANGELOG はコードベースの現行ファイル内容から推測して作成したもので、実装の意図・設計注釈・未実装の注意点なども含みます。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 全体
  - 初回リリース相当の機能群を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を導入。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が "paper_trading" の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成。
    - ExecutionEngine をバックグラウンドスレッドで起動し、data/stop_requested.flag を検知すると安全に停止。
    - エンジン用 PID ファイル path を data/execution.pid 等から参照可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告しデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データの共通保存）。
    - data/stop_requested.flag による外部停止検知、KeyboardInterrupt による終了処理をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を最初に実行。

- 設定管理
  - config.py: Settings クラスを追加し、アプリケーション設定（環境変数）をプロパティで提供。
    - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env / .env.local の読み込み順を実装（OS 環境変数を保護して上書き制御可能）。
    - 複雑な .env パースを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
    - 必須変数未設定時に _require() が ValueError を投げることで早期検出。
    - PAPER_FILL_MODE の妥当性チェック（instant|partial|never|reject）、KABUSYS_ENV と LOG_LEVEL の値検証を実装。
    - デフォルト経路やフラグ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH等）を提供。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合等は等金額配分にフォールバックし警告出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 (apply_sector_cap) を実装。既存保有のセクター比率が閾値を超える場合に同セクターの新規候補を除外。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
    - 設計注記（unknown セクターは上限を適用しない等）。
  - portfolio/position_sizing.py:
    - position sizing ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、per-position / aggregate の上限判定、コストバッファの導入、利用可能現金に応じたスケールダウン（端数処理で残差順に追加配分）を実装。
    - price 欠損や 0 の場合はスキップする安全措置を実装。

- 研究 (Research)
  - research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー系ファクター計算を追加。DuckDB 接続を受け取り prices_daily / raw_financials 等を参照して結果を返す。
    - 計算は営業日ベースの窓を用い、データ不足時は None を返すように設計。
  - research/feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)、IC（ランク相関）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク化ユーティリティ (rank) を追加。
    - 外部依存を避け、標準ライブラリのみで実装。
  - research/__init__.py:
    - 研究用 API をエクスポート（zscore_normalize を外部からインポートして統合）。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）に送信して銘柄別センチメント ai_scores を作成するモジュールを追加。
    - タイムウィンドウの算出（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）や、記事集約、1 銘柄あたりのトークン肥大対策（記事数・文字数上限）、バッチ送信（最大 20 銘柄）、スコアの ±1.0 クリップ、429/5xx/ネットワークエラーに対する指数バックオフリトライ等の設計を含む。
    - API キー未設定時に ValueError を投げる安全チェックを実装。
    - （注）ファイル末尾で実装途中で切れている箇所があるため、実行時に補完が必要な可能性あり。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して nice 値や HIGH_PRIORITY_CLASS を設定。権限不足や未サポート環境では警告を出してスキップ。
    - CPU affinity は利用可能コア数を越える指定に対するフォールバック処理を実装。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加（コマンドラインから実行可能）。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを算出し、閾値と比較して PASS/FAIL 判定を出力。
    - DB が存在しない場合やテーブルがない場合に graceful に N/A を返す防御的実装を採用。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし特記事項（ただし OpenAI API キーの取り扱いは env 経由で行い、未設定時の早期エラーを導入）。

Notes / Known issues / TODOs
- portfolio/position_sizing.py
  - price が欠損（0.0）の場合、エクスポージャーや発注量が過少に見積もられる旨の TODO コメントあり。前日終値や取得原価でのフォールバックが将来検討対象。
  - lot_size の銘柄別対応は現状未実装（将来的な拡張予定）。
- ai/news_nlp.py
  - ファイル末尾が途中で切れている（_fetch_articles 呼び出し以降が未完）。実際に動かすには未実装箇所の実装が必要。
- config._load_env_file
  - .env 読み込み時にファイル読み込み失敗で warnings.warn を出す実装だが、運用上 .env 障害の扱い方を設計ドキュメントで合意しておくことを推奨。
- run_monitoring
  - 監視は常に本番 sqlite_path を使う設計になっている。テスト環境で監視データの分離が必要な場合は設定の拡張が必要。

開発者向け補足
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストでの制御に有用）。
- paper_trading 環境では DB を物理的に分離しているため、paper 環境での検証は本番 DB に影響を与えない設計。
- DuckDB を利用した研究モジュールは依存ライブラリを増やさず SQL と純粋 Python で計算する設計方針。

履歴の作成にあたっての注記
- 本 CHANGELOG は提供されたソースコードの内容から機能追加・設計意図・TODO を推測してまとめたものです。実際のコミット履歴や過去リリースノートに基づくものではありません。ソースに明記されている TODO や途中実装箇所は運用上の注意点として列挙しています。