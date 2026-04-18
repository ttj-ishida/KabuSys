# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは人間が読める形でリリースの要点（追加・変更・修正）をまとめたものです。

リリース日付は 2026-04-18（本リポジトリ内のコードから推測）です。

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージ構成を追加（初期リリース）。
  - パッケージ名: kabusys
  - バージョン定義: src/kabusys/__init__.py にて `__version__ = "0.1.0"`

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止指示はプロジェクトルート/data/stop_requested.flag ファイルを監視して行う。
    - 監視処理は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する想定。
    - 起動時にプロセス優先度を "high" に設定し、SQLite および DuckDB 接続を確立する。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db など）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用して適切なブローカークライアント（Mock を含む）を生成。
    - エンジンは別スレッドで実行され、停止フラグ（data/stop_requested.flag）を監視して安全に停止する。
    - 実行時に PID ファイルを扱う仕組みを持つ。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパースは引用符・エスケープ・コメントなどに柔軟に対応。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、閾値、環境判定メソッド 等）をプロパティで取得できる。
    - `paper_fill_mode` の検証、有効値チェックを実装。
  - config_setup.py
    - .env を対話式に生成・更新するウィザードを追加（項目定義、既存値の読み込み、保存）。
    - 秘匿項目は画面上でマスク表示し、保存用のテンプレートを出力。

- 設定検証ツール
  - validate_config.py
    - .env および config/*.yaml の存在や妥当性を起動前に検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パス親ディレクトリの存在確認、YAML パース検証（PyYAML がある場合）などを実施。
    - `--strict` オプションで警告をエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のログ初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定や CPU affinity 固定のユーティリティを追加。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収。psutil を使って実装。
    - 許可されない環境では安全にスキップし、例外や権限不足は警告で処理。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全銘柄で 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - セクター未定義 ("unknown") の扱い、過剰セクター判定ロジックを明記。
    - レジーム乗数は bull/neutral/bear に対応（デフォルト: unknown は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料等の見積り）を考慮した配分ロジックを実装。
    - スケーリング時の端数処理（lot 単位での再配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計し、検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルト閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義し、Pass/Fail 判定を出力。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。
    - P95 計算、SQL クエリの分離、データ欠損時の N/A ハンドリングを実装。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュール（DuckDB 接続を受ける設計）を追加。Momentum の計算方針や定数が記載されている（実装途中の箇所あり）。

### 変更（設計上の重要点）
- 監視（monitoring）関連は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照する設計になっている点を明記（run_monitoring.py）。
- run_execution は paper_trading モード時に DB を分離し、本番 DB とデータが混じらないようにしている。
- .env 自動読み込みで OS 環境変数を保護するために protected セットを導入。`.env.local` は OS 環境変数を上書き可能にする（ただし protected は除外）。

### 修正 / 安全対策
- 各モジュールで以下のような安全処理を実装:
  - DB ファイル／ディレクトリが存在しない場合は警告（自動作成の可能性を示唆）や N/A を返す。
  - 外部依存（psutil, PyYAML 等）がない場合は機能をスキップして警告メッセージを出力。
  - 不正な環境変数値に対しては例外発生または警告ログを出して既定値にフォールバックする実装（例: MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、LOG_LEVEL、KABUSYS_ENV）。

### ドキュメント（コード内コメント）
- 各モジュールに詳細な docstring と設計ノート（PortfolioConstruction.md 等への参照）を含め、将来的な拡張や注意点（価格欠損時の挙動、単元情報の拡張案等）を明記。

---

今後の予定（想定）
- research/factor_research.py の完全実装（各ファクター計算の SQL 実装）。
- ExecutionEngine / BrokerClient 実装の詳細なテストとドキュメント整備。
- 単体テスト、CI、デプロイ用ドキュメントの追加。

（注）本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートや運用上の注記はリポジトリ管理者の公式情報を参照してください。