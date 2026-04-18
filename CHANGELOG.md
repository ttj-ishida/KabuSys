# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の書式に準拠します。  
バージョン番号は semver 準拠を想定しています。

※ 以下はリポジトリ内のコードから機能追加・動作仕様・修正点を推測して作成した変更履歴です。

## [Unreleased]

（次回リリースに向けた未確定の変更はここに記載します）

---

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV に応じて paper_trading モードでは MockBroker を使用し、paper_trading 用の専用 SQLite（data/paper_trading.db）を利用する分離設計を採用。
    - エンジンはスレッドで実行され、data/stop_requested.flag を検知すると安全に停止する機構を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
    - PID 管理（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 監視は環境設定にかかわらず本番用 sqlite_path を使用する設計。
- 設定管理と初期化ツール
  - config.py: 環境変数 / .env 自動読み込み機構を実装。  
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
    - export KEY=val 形式やクォート・エスケープ・インラインコメントに対応する堅牢なパーサを実装。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視しきい値等）をプロパティ経由で取得。値の検証（列挙値チェックや float 変換など）を行う。
  - config_setup.py: 対話式 .env ウィザードを実装。既存 .env 読み込み、入力補助、保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を実装。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化ユーティリティを追加。  
    - StreamHandler（stdout） + TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルは引数 > 環境変数 > デフォルト の順で解決。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加。  
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応。`set_process_priority("high"|"normal"|"low")` を提供。  
    - CPU affinity を設定する set_cpu_affinity() を実装（権限や未対応環境では警告を出してスキップ）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア・ランク順）、等金額配分、スコア加重配分を実装。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限の適用と市場レジームに応じた乗数（regime multiplier）を実装。  
    - apply_sector_cap(): 当日売却予定銘柄を除外して既存セクターエクスポージャを算出し、上限超過セクターの候補除外を行う。unknown セクターは制限対象外として扱う。  
    - calc_regime_multiplier(): "bull"/"neutral"/"bear" をサポート。未知レジームは 1.0 でフォールバック（警告を出力）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。  
    - risk_based / equal / score の配分方式をサポート。lot_size（単元株）丸め、per-stock 上限、aggregate キャップ（利用可能現金に基づくスケールダウン）、cost_buffer による保守的見積り、残差の公平配分ロジックなどを実装。
- research/factor_research.py（ファクター計算）
  - DuckDB 接続を受け取り、価格・財務データを基にモメンタム・ボラティリティ等のファクターを計算する設計を導入（モジュールの冒頭・定数・関数枠組みを実装、モメンタム計算関数の実装開始）。
- 管理用ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを集計し閾値判定（PASS/FAIL）を出力。  
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB パス指定可能。
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- ログ出力先について標準出力を stdout に統一（stderr ではなく stdout を使用）して、外部スケジューラからのログリダイレクトをしやすくした（logging_setup）。
- .env 自動読み込みの優先順位を明確化（OS 環境変数 > .env.local > .env）。既存 OS 環境変数を保護するため protected セットを導入。

### Fixed / Robustness
- .env パーサの改善:
  - export プレフィックス対応、クォート文字とバックスラッシュエスケープの正しい扱い、インラインコメント判定の改善により .env の解析がより堅牢に。
- 設定検証（validate_config）:
  - PyYAML が未インストールでもスクリプトが致命的に失敗しないようにし、パース検証をスキップして警告を出すようにした。
  - DB パスの親ディレクトリが存在しない場合に警告を出力（起動時に自動作成されることを注記）。
- run_execution / run_monitoring:
  - 停止フラグ（data/stop_requested.flag）の検出により安全に停止するハンドリングを追加。
  - run_execution では paper_trading モードと本番 DB の分離を確実化。
- process_priority:
  - 非対応 OS や権限不足時に例外で停止せず警告を出して続行するように改善。

### Documentation / Developer experience
- config_setup の対話ウィザードにより .env の初期作成や既存値の編集が容易になった（シークレットはマスク表示、確認プロンプトあり）。
- validate_config CLI による起動前チェックを用意し、問題の早期検出を支援。

### Notes / Known limitations
- research/factor_research.py はモジュールのフレームワークとモメンタム計算用の定数が実装されているものの、ファイル末尾付近に未完成箇所（実装途中で切れている箇所）が見られます。完全なファクター計算ロジックの実装は今後の課題です。
- position_sizing や apply_sector_cap の一部ロジックでは価格欠損（価格が 0 または None）に対するフォールバックが限定的であり、将来的に前日終値等のフォールバック価格を導入することが推奨されています（TODO コメントあり）。
- process_priority や set_cpu_affinity は権限や OS に依存するため、環境によっては期待通りに設定できない場合があります（警告でスキップ）。

---

今後の予定（例）
- research/factor_research の完全実装とユニットテスト追加
- ExecutionEngine / Broker クライアントの統合テスト追加
- モニタリング・アラート（LINE 連携）実装強化
- 単体テスト・CI の整備

---

過去の変更履歴（旧バージョン）はここに順次追記していきます。