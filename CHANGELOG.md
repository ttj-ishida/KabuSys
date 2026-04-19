# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。  
リリース日付はコードベースに含まれる日付や本環境の想定日付に合わせて記載しています。

## [Unreleased]

- 既知の未実装 / 要改善点
  - research/factor_research.py の実装が途中（ファイル終端が切れている / `start_da` で途切れ）ため、ファクター計算機能は現時点で未完成。今後のリリースで実装・テストを追加予定。
  - position_sizing.calc_position_sizes の将来的な拡張（銘柄別 lot_size サポート）や、risk_adjustment.apply_sector_cap における price のフォールバック処理（前日終値等）の実装は TODO コメントとして残っている。大規模運用前にこれらの改善を推奨。
  - cross-platform のプロセス優先度・CPU affinity 周りは権限や OS に依存するため、環境によっては設定がスキップされる可能性がある（既知の挙動）。

---

## [0.1.0] - 2026-04-19

初期リリース。本リリースでは自動売買システム「KabuSys」のコアユーティリティ、実行・監視ランナー、設定管理、ポートフォリオ構築ロジック、いくつかの CLI ツールを提供します。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB から完全分離。
    - 停止フラグ（data/stop_requested.flag）検知や PID 管理（data/execution.pid）に対応。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - リスク管理（RiskManager）・OrderManager・Reconciler を組み合わせて実行セッションを起動。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - モニタリングは環境にかかわらず本番の sqlite_path を使用（監視データは共通で保存される想定）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。

- 設定管理
  - config.py
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）を実装。.env と .env.local の読み込み順を実装し、OS 環境変数は保護。
    - 環境変数パースの堅牢化（クォート、エスケープ、インラインコメント処理、export 句対応）。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、閾値、環境判定など）へプロパティ経由でアクセス可能。
    - PAPER_FILL_MODE（paper_trading の動作モード）といった紙取引専用設定、ログレベル・しきい値などのデフォルトとバリデーションを実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。秘密値はマスク表示、既存値の再利用、確認後にファイル書き込み。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml（存在する場合）を起動前に検査するツール。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無確認、YAML パース検査（PyYAML がインストールされている場合）を実施。
    - --strict オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
    - スコアが全て 0 の場合に等配分へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が上限を超えている場合の候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull / neutral / bear → 1.0 / 0.7 / 0.3、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック。allocation_method（risk_based / equal / score）に対応。
    - 単元株丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守見積り、残差処理（lot 単位での追加配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティ。
    - LOG_DIR / LOG_LEVEL を尊重し、ファイル作成失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS 等）差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。権限不足や未対応 OS では安全にスキップし警告を出力。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて監視用テーブルの存在を保証する仕組みを run スクリプトから呼び出し（冪等）。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から集計を行い、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出して検証レポートを標準出力に出力。
    - PASS/FAIL 判定用の閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- パッケージメタ
  - __init__.py にてパッケージバージョンを "0.1.0" に設定。

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- ログ設定や環境ファイル読み込みに関する堅牢性改善
  - .env のパースでクォートとエスケープ、インラインコメントの扱いを明確化。
  - ログディレクトリ作成に失敗した場合のフォールバック（コンソール出力のみ）を実装。

### 既知の問題 / 注意点 (Known issues & Notes)
- monitoring は明示的に「環境にかかわらず」Settings.sqlite_path（本番監視 DB）を使用する仕様。開発用に分離したい場合は SQLite_PATH 等の環境変数を変更するか設計を見直す必要あり。
- run_execution は paper_trading 環境で paper_sqlite_path を使用することで本番 DB と分離するが、設定ミスにより同じ DB を参照しないよう注意が必要。
- process_priority / set_cpu_affinity は実行権限（root など）や OS に依存して実際に効果が出ない場合がある。警告はログに出力される。
- research/factor_research.py の実装が途中で終わっている（ファイル末尾が欠損）。ファクター計算機能は現状で未完成。
- 複数箇所に TODO コメント（例: price フォールバック、銘柄別 lot_size）の記載あり。運用前に確認・実装を推奨。

### セキュリティ (Security)
- なし（このリリースでのセキュリティ修正は無し）。ただし API トークン等の扱いは .env を利用し、.env を決してリポジトリにコミットしない旨をツールとドキュメントで強調。

---

上記は現在のコードベース（src/ 以下）から推測できる機能・仕様をもとに作成した CHANGELOG です。実際の変更履歴やコミット履歴があれば、それに基づいてより正確なエントリへ更新してください。