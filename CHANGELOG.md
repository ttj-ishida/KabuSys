# Changelog

すべての変更は Keep a Changelog の形式に従っています。慣例により重要度順（Added / Changed / Fixed / …）で記載しています。

## [Unreleased]

- 小さな改善・ドキュメント補強等を予定。

---

## [0.1.0] - 2026-04-19

Initial release — KabuSys の基本モジュール群を実装しました。以下はコードベースから推測してまとめた主要な機能・設計上のポイントです。

### Added
- 全体
  - パッケージ初期リリース (package version = 0.1.0)。
  - メインモジュール群を実装：実行エンジン、監視、設定管理、ポートフォリオ構築、調査ツール、ユーティリティなど。

- 実行 / 起動関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカー切替（Mock vs 実ブローカー）を想定。
    - engine.run_session を別スレッドで起動し、data/stop_requested.flag による外部停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。
    - 実行中の PID を data/execution.pid に書く仕組み（pid_file の渡し込み）をサポート。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き対応（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視 DB は本番 DB を想定）。
    - data/stop_requested.flag による監視ループ終了制御を実装。
    - duckdb 接続と monitoring DB 初期化処理を統合。

- 設定 / ユーティリティ
  - config.py: 環境変数・設定管理を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env 自動読み込み機能（優先順位: OS 環境 > .env.local > .env）。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは quoted 値、export プレフィックス、インラインコメントルール等に対応。
    - Settings クラスで各種設定値（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定、監視しきい値など）をプロパティとして提供。入力検証を行い不正値は例外を送出。
    - paper_fill_mode の有効値チェック（instant/partial/never/reject）。

  - config_setup.py: .env 初期作成 / 対話式ウィザードを実装。
    - 対話式プロンプトで主要な環境変数を入力・既存値の再利用が可能。
    - .env ファイルの読み書き機能を提供し、書式・注意文を含めて出力。
    - 秘匿値はマスクして表示。

  - validate_config.py: 起動前の設定検証 CLI を実装。
    - 必須環境変数の有無確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）。
    - --strict オプションで警告を失敗扱いにできる。
    - 本番環境向けのガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を追加。

  - utils/logging_setup.py: ロギング設定ユーティリティを追加。
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - ログディレクトリを自動作成し、作成失敗時はファイル出力をスキップして stdout のみで継続するフェールセーフを実装。
    - 既存ハンドラを再設定して二重出力を防止。
    - ログレベル解決は (引数 > 環境変数 > デフォルト) の順。

  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して nice/priority を設定。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留め可能（未指定なら全コア）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレーク（signal_rank）で候補選定。
    - calc_equal_weights, calc_score_weights: 等重・スコア加重の重み計算。全スコアが 0 の場合は等重にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を既存保有の時価ベースで評価し、超過セクターの新規候補を除外。unknown セクターは上限適用をスキップ。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を算出。
      - リスクベースでは risk_pct, stop_loss_pct を用いてポジションサイズを計算。
      - lot_size（単元）丸め処理を実装。
      - aggregate cap（available_cash）を超過した場合はスケールダウンし、残余キャッシュを使って再配分（fractional remainder に基づくロット単位での追加配分）を行う。
      - cost_buffer によりスリッページ等を考慮した保守的見積りをサポート。
      - TODO コメントとして将来的な銘柄別 lot_size 対応、価格フォールバックの必要性を記載。

- 調査 / レポートツール
  - tools/paper_verification_report.py
    - Paper trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、閾値（Uptime 99%、Fill 90%、Send 95%、P95 200 ms）で PASS/FAIL を判定。
    - 日付フィルタ、DB パスのオーバーライド (--db) をサポート。
    - DB にテーブルが存在しない場合の安全なフォールバックを実装（OperationalError を捕捉して N/A を扱う）。

- 研究モジュール（着手）
  - research/factor_research.py
    - ファクター計算基盤の追加（モメンタム・MA200・ATR 等の定数と calc_momentum の枠組みを実装）。DuckDB 接続を受ける設計。 ※ファイル末尾に実装途中の箇所あり（calc_momentum の続きが未完）。

### Changed
- なし（初回リリースに伴い変更履歴は Added に集約）。

### Fixed
- なし（現行コードではフェールセーフ処理や例外ハンドリングを追加して堅牢化）。

### Notes / Design decisions
- 監視 (monitoring) は意図的に環境に依存せず本番 sqlite_path を参照する設計（監視対象は本番の稼働状況を監視するため）。
- run_execution は paper_trading 環境を DB レベルで完全に分離することで、本番データ誤操作のリスクを低減。
- ログは stdout と日次ローテーションファイルの両方に出力し、ログディレクトリ作成に失敗した場合でもプロセスを停止させない設計。
- 環境変数の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後も動作するよう __file__ 起点で探索する実装。

### Known issues / TODO
- research/factor_research.calc_momentum の実装途中（ファイル末尾が切れている／続き実装が必要）。
- position_sizing と apply_sector_cap で価格欠損時のフォールバックロジックが TODO コメントで指摘されている（現状は price=0 の場合はスキップする挙動）。
- 将来的な拡張として銘柄ごとの lot_size 情報を導入する設計拡張がコメントとして残っている。

---

変更点の詳細や誤りの指摘があれば、該当箇所（ファイル/関数名）を教えてください。コードから推測して記載していますので、実際の履歴やコミットメッセージと差分がある場合は差し替え可能です。