CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
（コードベースの内容から推測してまとめた初期の変更履歴です）

## [Unreleased]

- 今後の変更・修正をここに記載してください。

## [0.1.0] - 2026-04-24
初回リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。スレッドでエンジンを実行し、data/execution.pid に PID を記録（設定での上書き可）。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介して環境に応じたブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - RiskManager / OrderManager / Reconciler を組み立てて ExecutionEngine を起動。停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウン。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する点を明示。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグを検知してループを終了。

- 設定関連
  - config.py
    - 環境変数ラッパー Settings を追加。多くの設定項目（JQUANTS、KABU、DB パス、監視閾値、KABUSYS_ENV/LOG_LEVEL 等）をプロパティとして提供し、入力検証を実施。
    - プロジェクトルート自動検出機能を実装し、.env/.env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパース処理を強化（export 形式、クォート値のエスケープ、インラインコメントの扱い等に対応）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装（不正値は例外を送出）。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。秘密値はマスク表示。生成テンプレートを .env に書き出す機能を提供。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイル存在およびパース検証（PyYAML が無い場合は警告）などを実施。
    - --strict オプションで警告を失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。stdout へ出力する StreamHandler と、日次ローテート（30日保持）の TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加。Windows と POSIX 系（Linux/Mac/FreeBSD）向けに nice/priority を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。権限不足などの失敗は警告としてスキップ。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選択（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）を実装。lot_size（単元）考慮、max_position_pct、max_utilization、コストバッファによる aggregate cap のスケールダウン等を含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）および市場レジームに応じた投資乗数（calc_regime_multiplier）を実装。

- 分析・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を元に検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを算出し、閾値に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）や --db オプションで DB パスを指定可能。

- 研究／ファクター計算
  - research/factor_research.py（骨子）
    - DuckDB の prices_daily / raw_financials を用いたモメンタム／バリュー等のファクター計算を行う関数群の骨子を追加（モメンタム等の定数と calc_momentum の実装開始）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

### Changed
- 起動処理の改善
  - run_execution / run_monitoring 起動時にプロセス優先度を最初に "high" に設定するよう変更（重要な処理の優先実行を確保）。

- DB ハンドリング
  - 監視用テーブルの初期化（init_monitoring_db）を起動時に呼び出し、監視テーブルが存在することを保証（冪等）。

- .env 読み込みルールの明文化
  - OS 環境変数を保護しつつ .env/.env.local を上書き読み込みするロジックを導入（protected set）。

### Fixed
- 環境変数パーサの堅牢性向上
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理等を正しく扱うよう改善。無効行のスキップを明確化。

- 環境変数値の安全なデフォルトフォールバック
  - MONITOR_POLL_INTERVAL の不正（非整数・0 以下など）入力時に警告を出し、デフォルト（60 秒）にフォールバックするよう安全化。

### Security
- シークレットの取り扱い
  - config_setup の対話表示ではシークレット項目（J-Quants トークン、kabu API パスワード、LINE トークン）をマスクして表示し、.env を生成する旨を明記。

### Notes / Known limitations
- research/factor_research.py は一部未完（ファイル末尾が途中で終わる断片あり）。実稼働での利用前にさらなる実装／テストが必要です。
- 一部の処理（プロセス優先度設定、CPU affinity、ログディレクトリ作成）は権限や環境に依存し、失敗した場合は警告を出して処理を継続する設計になっています。
- YAML ファイルの内容検証は PyYAML の有無に依存します。PyYAML 未導入時はパース検証をスキップして警告を出します。

-- 
（以上はソースコードの実装・注釈から推測してまとめた CHANGELOG です。実際のリリースノートとして利用する際は日付・バージョン・詳細を適宜調整してください。）