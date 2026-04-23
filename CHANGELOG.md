CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。
次の基準に従っています: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-23
-------------------

初回公開リリース — KabuSys の基本コンポーネントを追加しました。
以下はコードベースから推測した主な機能と修正の一覧です。

Added
- 基本アプリケーション情報
  - パッケージのバージョンを __version__ = "0.1.0" として定義。

- 起動スクリプト / 実行制御
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（Mock/実ブローカー切替対応）。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による外部停止検知を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行 PID を data/execution.pid に書き込む想定（pid_file 指定）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）で監視ループを終了。

- 設定管理
  - config.py: 環境変数／.env 読み込みと Settings クラスを追加。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により .env 自動ロードを実行（無効化フラグあり）。
    - .env のパースは quoting / export 形式 / インラインコメント / エスケープに対応。
    - 各種設定プロパティを提供（DB パス、API トークン、PID/kill フラグパス、モニタ閾値、環境判定など）。
    - PAPER_FILL_MODE に対するバリデーション実装。

- 設定関連 CLI
  - config_setup.py: 対話式 .env 作成／更新ウィザードを追加。
    - デフォルト値・選択肢・シークレット入力に対応し .env を安全に生成。
    - .env を生成するテンプレート書き込みロジックを提供（.env を Git にコミットしないよう注意喚起）。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の確認、KABUSYS_ENV の妥当性、ログレベル、DB パス（親ディレクトリ）の存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML があれば）。
    - 本番環境（live）時の追加ガード（LINE 設定や Kill Flag の自動クリア設定など）を警告。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア順で候補選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコアが 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限。既存保有のセクターエクスポージャーに基づき新規候補を除外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数。'bull','neutral','bear' を実装し、未知レジームは 1.0 でフォールバック）
  - portfolio/position_sizing.py:
    - calc_position_sizes（等比／スコア比／リスクベース配分に基づく株数計算）
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer による保守的見積り、スケーリングと端数配分ロジックを実装

- 監視・モニタリング
  - monitoring 用 DB 初期化呼び出しポイント（init_monitoring_db の利用）を run_execution と run_monitoring で保証。
  - SystemMonitor のチェック呼び出しチェックポイント（monitor.check_once）をポーリングで実行（例外はログに捕捉してループ継続）。

- ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を組み合わせる共通ロギングセットアップ。
    - ログディレクトリ作成に失敗した場合はコンソールのみで継続するフェイルセーフ。
    - ログレベル決定ロジック（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS など）を設定。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を提供。
    - 権限不足や未対応 OS での安全ハンドリング（警告ログ）を実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計。
    - PASS/FAIL 判定の閾値を定義（稼働率 99% 等）。
    - --from / --to / --db オプションで期間と DB を指定可能。
    - DB が存在しない・テーブル欠損時に N/A を扱う耐障害性を実装。

- リサーチ（未完/追加予定）
  - research/factor_research.py: ファクター計算（Momentum / Value / Volatility / Liquidity）の設計と一部実装を追加（DuckDB 接続を用いる方針）。（ファイルの末尾に未完の箇所あり）

Changed
- ログ出力の統一化:
  - 全起動スクリプト／コンポーネントから setup_logging を呼ぶことでログ出力の挙動を統一。
  - StreamHandler を stdout に設定（cron 等の運用で stdout/stderr を統合しやすくするため）。

Fixed / Robustness improvements
- .env 読み込みの堅牢化:
  - export 形式 / シングル／ダブルクォートのエスケープ / インラインコメント等に対応し、不正行は無視する設計。
  - プロジェクトルートが特定できない場合は自動ロードをスキップする安全化。
- MONITOR_POLL_INTERVAL の取り扱い:
  - 整数でない・0 以下の値が設定された場合は警告を出してデフォルト（60 秒）にフォールバック。
- プロセス優先度・CPU affinity 設定:
  - 権限不足や未対応環境で例外を捕捉し、警告ログを出力してスキップするようにした。
- ログディレクトリ作成失敗時のフォールバック:
  - ファイルハンドラ作成に失敗してもコンソール出力は維持する。

Security
- .env 生成テンプレートに「.env を絶対に Git にコミットしないこと」を明記。
- シークレット項目は config_setup の確認表示時にマスク表示。

Notes / Migration / Operational details
- DB 分離:
  - paper_trading モードでは paper 用 SQLite（data/paper_trading.db）を使用して本番データと完全に分離します。運用時は環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
- 監視データ:
  - monitoring 用 SQLite は Settings.sqlite_path（デフォルト data/monitoring.db）を使用。run_monitoring は環境に関係なく本番 sqlite_path を参照して監視テーブルを初期化します。
- 起動／停止:
  - data/stop_requested.flag の配置で監視 / 実行ループを外部から停止できます。KILL フラグ周りの動作は設定で制御（KILL_FLAG_CLEAR_ON_START）。
- CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from yyyy-mm-dd --to yyyy-mm-dd --db PATH]
  - 起動スクリプトはそれぞれ直接実行可能（run_execution.py, run_monitoring.py）。

Known issues / TODO（コードから推測）
- research/factor_research.py の calc_momentum 以降が途中で切れており、実装が未完の箇所があります（今後完成が必要）。
- apply_sector_cap の価格欠損（price が 0.0）の扱いに TODO コメントあり：前日終値等のフォールバック価格を使う検討が示唆されています。
- position_sizing の lot_size 将来的拡張（銘柄別単元対応）が計画されています。

以上が現行コードベースから推測できる初期リリースの変更履歴です。必要であれば、各ファイルごとのより詳細な変更点（関数単位の説明や使用例、既知の問題箇所の抜粋）も追記します。どのレベルの詳細を希望しますか？