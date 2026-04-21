# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [0.1.0] - 2026-04-21

初回リリース。KabuSys の基盤となる以下の機能群を実装しました（監視・実行ランナー、設定管理、ポートフォリオ構築、ユーティリティ、分析ツール等）。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル (data/stop_requested.flag) を検知して優雅に終了。monitor.check_once() の例外を捕捉して次ポーリングへ継続。
    - File: src/kabusys/run_monitoring.py
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して paper_trading 専用 SQLite（data/paper_trading.db）に記録し、本番 DB と分離。PID ファイル管理、停止フラグ検知で実行スレッドを停止。
    - File: src/kabusys/run_execution.py

- 設定管理
  - Settings クラスを実装し、環境変数からアプリ設定を一元化（DB パス、API トークン、監視閾値、環境種別等）。値のバリデーションや既定値を提供。
    - File: src/kabusys/config.py
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。OS 環境変数を保護して .env/.env.local を読み込む挙動。
    - File: src/kabusys/config.py
  - .env パーサの強化: export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理に対応。

- 設定ユーティリティ・CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレットはマスク表示し、保存前に確認プロンプトを表示。デフォルト値や選択肢を定義。
    - File: src/kabusys/config_setup.py
  - validate_config: .env や config/*.yaml の設定妥当性を起動前に検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML の存在とパース（PyYAML があれば内容検証）を行う。--strict オプションで警告を FAIL 扱いにできる。
    - File: src/kabusys/validate_config.py

- ポートフォリオ構築モジュール
  - 銘柄選定・重み計算:
    - select_candidates: スコア降順・タイブレークに signal_rank を採用して候補を選出。
    - calc_equal_weights / calc_score_weights: 等額配分およびスコア加重配分を実装。スコア合計が 0 の場合に等配分へフォールバックし警告を出力。
    - Files: src/kabusys/portfolio/portfolio_builder.py, src/kabusys/portfolio/__init__.py
  - リスク調整:
    - apply_sector_cap: セクターごとの既存保有比率が上限を超える場合は当該セクターの新規候補を除外（unknown セクターは除外しない）。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバック 1.0 として警告を出力。
    - File: src/kabusys/portfolio/risk_adjustment.py
  - ポジションサイジング:
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。lot_size 単位で丸め、最大ポジション比・投下資金上限を考慮。合計コストが利用可能現金を超える場合はスケーリングし、端数は再優先度で lot 単位を追加配分するロジックを実装。コストのバッファ（手数料・スリッページ見積り）も考慮。
    - File: src/kabusys/portfolio/position_sizing.py

- ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを実装。コンソール出力は stdout、日次ローテート (TimedRotatingFileHandler) を用いてログファイルへ出力。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - File: src/kabusys/utils/logging_setup.py
  - process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度 (nice / HIGH_PRIORITY_CLASS) と CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS の場合は警告を出してスキップ。
    - File: src/kabusys/utils/process_priority.py

- 分析・検証ツール
  - paper_verification_report: Paper Trading 用 SQLite データベースから検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。日付フィルタ (--from / --to) および DB パス指定 (--db) に対応。DB が存在しない場合はエラーメッセージを出力。
    - File: src/kabusys/tools/paper_verification_report.py

- DuckDB 統合
  - 実行・監視で DuckDB 接続を作成し分析用データを扱えるようにした（Settings でパス管理）。
    - Files: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py, src/kabusys/config.py, src/kabusys/research/factor_research.py

- パッケージメタ情報
  - パッケージ初期バージョンを設定。
    - File: src/kabusys/__init__.py (__version__ = "0.1.0")

### 変更 (Changed)
- ロギング挙動
  - StreamHandler を stdout に統一（stderr ではない）: タスクスケジューラ / cron などでログを一括リダイレクトする運用を想定。
  - 既存ハンドラは起動時に flush/close してから削除し、重複ハンドラ登録を防止。
    - File: src/kabusys/utils/logging_setup.py

- .env 読み込み順序明確化
  - 自動読み込み順: OS 環境 > .env.local > .env。プロジェクトルートが特定できない場合は自動ロードをスキップして安全化。
    - File: src/kabusys/config.py

- DB 接続の振る舞い
  - run_monitoring は環境に関わらず本番 sqlite_path を監視 DB として使用する設計（監視データは本番 DB に記録する前提）。
  - run_execution は paper_trading 時に paper_sqlite_path（分離された DB）を使用することで検証と本番を完全に分離。
    - Files: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py

### 修正 (Fixed)
- 環境変数パーシングでの不具合回避
  - _parse_env_line にてクォート内のバックスラッシュエスケープやインラインコメント処理を実装し、より多くの .env フォーマットに耐性を持たせた。
    - File: src/kabusys/config.py

- ロギングハンドラ作成失敗時のフォールバック
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合に、プロセスを停止せずコンソールログのみで継続するように修正。
    - File: src/kabusys/utils/logging_setup.py

- ポートフォリオ / サイジングの安全弁
  - price が欠損（0 または None）であれば該当銘柄を安全にスキップする挙動を各所に追加し、ゼロ除算や不正なキャッシュ算出を回避。
    - Files: src/kabusys/portfolio/position_sizing.py, src/kabusys/portfolio/risk_adjustment.py

- Paper verification の堅牢性
  - テーブルが存在しない（OperationalError）場合にデフォルト値にフォールバックすることで、部分的な DB でもレポート出力が可能になった。
    - File: src/kabusys/tools/paper_verification_report.py

### ドキュメント (Documentation)
- 各モジュールに docstring と使用例・設計方針を追加（monitoring/ execution/ portfolio/ utils/ research 等）。CLI 用のヘルプ文字列も整備。
  - Files: 多数（各モジュール）

### 既知の制限・注意点 (Known issues / Notes)
- research/factor_research.py は一部実装（モメンタム計算の冒頭など）で切れ目があり、完全実装が必要。DuckDB 接続を受け取る設計だが、実運用前に追加の検証とテストが推奨される。
- process_priority の優先度変更や CPU affinity はプラットフォーム依存かつ権限が必要な場合があり、設定に失敗すると警告ログにフォールバックする。運用環境の権限設定を事前に確認してください。
- PAPER_FILL_MODE の設定値検証を行うが、MockBrokerClient 側での挙動検証が必要（fill_mode の振る舞いにより検証結果が変化します）。

---

今後の予定（例）
- research モジュールのファクター計算を完成させ、DuckDB ベースのパイプラインを追加。
- 単体テスト・統合テストの整備（特に position sizing / risk logic / execution engine）。
- ドキュメントと運用手順の充実（デプロイ手順・監視アラート設定等）。

もし特定の変更点をより詳細に記載してほしい箇所があれば（ファイル単位、関数単位など）、対象を指定して伝えてください。