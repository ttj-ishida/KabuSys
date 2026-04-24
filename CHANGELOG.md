CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
主要なリリース情報はセマンティックバージョニングに基づき記載しています。

[Unreleased]
------------

- （現時点のコードベースは初期リリース相当のため、未リリースの変更はありません）

[0.1.0] - 2026-04-24
-------------------

Added
- プロジェクト初期実装を追加。
  - 全体のパッケージ情報:
    - src/kabusys/__init__.py: パッケージ名とバージョン定義（0.1.0）。
  - 起動スクリプト:
    - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行う。
      - Monitoring は環境に関係なく本番用 sqlite_path を使用する設計。
    - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 専用 DB（data/paper_trading.db）を使うことで本番 DB と分離。
      - 停止フラグ検知で実行エンジンを安全に停止可能（data/stop_requested.flag）。
      - 実行 PID を data/execution.pid に記録する仕組み（設定によりパス変更可）。
  - 設定管理 / ユーティリティ:
    - src/kabusys/config.py: 環境変数/.env 自動ロードと Settings クラスを実装。
      - プロジェクトルート検出は .git または pyproject.toml を探索して行う（CWD 非依存）。
      - .env/.env.local の優先順位と OS 環境変数保護機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env のパースは引用符とバックスラッシュエスケープ、インラインコメント処理に対応。
      - 各種設定プロパティ（DB パス、PID/kill flag パス、しきい値、PAPER_FILL_MODE の厳密チェックなど）を提供。
    - src/kabusys/config_setup.py: .env 初期作成・更新の対話式ウィザードを追加（CLI）。
      - 使用例をヘルプに明記、既存 .env のロード・編集・保存をサポート。
    - src/kabusys/validate_config.py: 起動前設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML があれば内容も検証）などを行う。
      - --strict オプションで警告も失敗扱いにできる。
  - ポートフォリオ構築ロジック（純粋関数群、DB 参照無し）:
    - src/kabusys/portfolio/portfolio_builder.py:
      - シグナルの選定（select_candidates）、等金額・スコア加重配分（calc_equal_weights, calc_score_weights）を実装。
      - スコア全てが 0 の場合は等金額配分にフォールバックして警告を出す。
    - src/kabusys/portfolio/risk_adjustment.py:
      - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
    - src/kabusys/portfolio/position_sizing.py:
      - position sizing 実装（risk_based / equal / score の各方式）。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer（スリッページ・手数料見積）を考慮したスケーリング処理を実装。
  - ロギング・プロセス管理ユーティリティ:
    - src/kabusys/utils/logging_setup.py:
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30世代保持）を設定する共通ユーティリティ。
      - LOG_LEVEL/LOG_DIR の解決順と、ログディレクトリ作成失敗時のフォールバック動作を実装。
    - src/kabusys/utils/process_priority.py:
      - プロセス優先度（high/normal/low）設定と CPU affinity 固定のユーティリティを実装。Windows/Linux（POSIX）差分を吸収し、権限不足等は警告でスキップ。
  - Paper Trading 検証ツール:
    - src/kabusys/tools/paper_verification_report.py:
      - Paper Trading 用 SQLite DB を解析して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計するレポート生成スクリプトを追加。
      - デフォルト閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200 ms）に基づいて PASS/FAIL を判定する。
      - --from/--to/--db オプションに対応。
  - 研究用ファクター計算（骨格実装; prices_daily/raw_financials を使う設計）:
    - src/kabusys/research/factor_research.py: Momentum 等のファクター計算モジュールの開始実装（DuckDB 接続を利用、関数群の設計方針と定数を定義）。

Changed
- （初期リリースのため変更履歴はありません）

Fixed
- （初期リリースのため修正履歴はありません）

Notes / 実装上の重要点
- DB の分離:
  - monitoring（run_monitoring）は環境にかかわらず Settings.sqlite_path（monitoring DB）を使用する設計。実行 (Execution) は KABUSYS_ENV が paper_trading の場合に専用の paper_sqlite_path を使用して本番 DB と分離する。
- .env 自動ロード:
  - プロジェクトルートが検出できる場合に .env/.env.local を自動ロードする。OS 環境変数は保護され、.env.local は上書き可能（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できる）。
  - .env のパースは引用符やバックスラッシュ、インラインコメント処理を考慮しており、export キーワードにも対応。
- 排他・停止制御:
  - run_monitoring/run_execution ともにプロジェクトルートの data/stop_requested.flag を監視して安全に停止する仕組みを備える。
- ロギング:
  - コンソール出力は stdout を使用（cron などでの出力統一を想定）。ログファイルは日次ローテーションで保管。
- 安全設計:
  - process_priority の適用は権限不足等の環境で失敗しても警告でスキップし、起動を阻害しない。
  - config.validate にて本番環境（KABUSYS_ENV=live）での危険設定（LINE 未設定や KILL_FLAG_CLEAR_ON_START=1 など）を警告するチェックを追加。

今後の予定（例）
- research/factor_research の完全実装。
- Strategy / Execution の詳細なユニットテストと耐障害性向上。
- 銘柄ごとの lot_size や価格フォールバック処理の拡張（TODO コメントあり）。
- より詳細なドキュメント（PortfolioConstruction.md 等の参照実装を含む）。

---
注: 本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。