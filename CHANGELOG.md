Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従って管理されています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

[Unreleased]
------------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-17
-------------------

Added
- 初回公開リリース (v0.1.0)。
- 環境・設定管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートの .env / .env.local を順に読み込み、OS 環境変数を保護）。
  - .env の行パーサは export プレフィックス、引用符（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - Settings クラスを導入し、環境変数経由でアプリケーション設定を安全に取得（必須項目は _require() で検証）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- 設定ウィザード / 検証 CLI
  - 対話式 .env 生成・更新ウィザード（kabusys.config_setup）。
  - 設定検証 CLI（kabusys.validate_config）：必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば内容を検証）などをチェック。--strict オプションで警告を失敗扱いに可能。
- 実行 / 監視ランナー
  - 実行エントリ: run_execution.py
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して動作。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全なシャットダウン処理。
    - 実行 PID 管理（data/execution.pid を使用）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization 等）を設定。
  - 監視エントリ: run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）。
    - 停止フラグ検知・例外時のログ出力・リソースクローズを実装。
- DB / 分析
  - DuckDB 接続を受け取る設計（duckdb_path 設定）で、分析処理と実行処理を分離。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows と POSIX（Linux/Mac/FreeBSD）間の差分を吸収。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足や未対応 OS の場合は安全にスキップして警告。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等金額配分へフォールバックし警告。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap（売却予定銘柄の除外、"unknown" セクターは上限適用除外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップを提供、未知レジームはフォールバックと警告）。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装。risk_based / equal / score の allocation_method をサポート。単元（lot_size）で丸め、ポートフォリオ上限・銘柄上限・合計キャッシュ制限（aggregate cap）を考慮してスケールダウン・端数配分を行う。cost_buffer を加味して手数料/スリッページを保守的に見積る。
- 研究モジュール（kabusys.research.factor_research）
  - DuckDB を用いたファクター計算実装（モメンタム: 1M/3M/6M/MA200乖離、ボラティリティ: ATR20、流動性指標等）。営業日ベースのウィンドウを想定し、欠損時は None を返す設計。
- ツール
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）。
    - SQLite（paper_trading.db）から稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - PASS/FAIL 判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を規定。
    - 日付レンジ指定（--from/--to）やデータベースパス指定（--db / 環境変数）に対応。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Notes / Implementation details
- .env の自動読み込みは、プロジェクトルートが検出できない場合はスキップされるため、配布後やテスト環境での誤動作を防止。
- Settings.env は KABUSYS_ENV を小文字正規化して検証。無効値は ValueError を送出して早期検出を促す。
- run_execution は paper_trading モードで MockBroker を使用し、paper_trading 用 DB に記録することで本番 DB との完全分離を保証。
- プロセス優先度設定は最初に実行する設計。権限不足時はログで通知して処理は継続。
- position_sizing のスケーリング処理は再現性（安定ソート）を考慮して実装している（端数配分の順序安定化）。

Security
- 本リリースでは特定のセキュリティ修正は無し。環境変数やシークレット（トークン・パスワード）は .env に保存しないこと（README 等で注意喚起することを推奨）。

--- 

今後の予定（例）
- portfolio.position_sizing の銘柄別 lot_size サポート（stocks マスタを導入して lot_map を受け取る）。
- monitor / engine の詳細なテストカバレッジ追加、エラー回復戦略の強化。
- ドキュメント（README、運用手順書、PortfolioConstruction.md など）の拡充。