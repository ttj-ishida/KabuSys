# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17
初回リリース。プロジェクトの主要な機能群と CLI / ユーティリティ群を実装しました。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 環境設定 / 設定管理
  - Settings クラスを実装し、環境変数から各種設定（DB パス、API トークン、監視閾値、環境種別など）を取得可能に（src/kabusys/config.py）。
  - プロジェクトルート自動検出ロジックを追加（.git または pyproject.toml を探索）。
  - .env ファイルの自動読み込み機能を実装（.env、.env.local、OS 環境変数の保護対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。
  - .env 行パーサーを強化（export プレフィックス、クォート文字のエスケープ、インラインコメント処理に対応）。

- 設定用 CLI / ウィザード
  - 対話式 .env 作成・更新ウィザードを実装（src/kabusys/config_setup.py）。既存値の読み込み、シークレットマスク表示、デフォルト案内、ファイル書き出し機能を提供。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml を検証する `validate_config` 実装（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML がインストールされていない場合は警告）を行う。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行エンジン起動スクリプト
  - ExecutionEngine 起動スクリプトを提供（src/kabusys/run_execution.py）。
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper Trading 用 SQLite（data/paper_trading.db）で本番 DB と完全分離して動作。
  - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager（デフォルト構成値を含む）、Reconciler、ExecutionEngine の組み立てを行う。
  - PID ファイル管理、停止フラグ (data/stop_requested.flag) 検知による安全停止、デーモンスレッドでのエンジン実行をサポート。

- 監視ポーリング起動スクリプト
  - SystemMonitor を定期実行するランナーを実装（src/kabusys/run_monitoring.py）。
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出す。
  - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
  - 起動時にプロセス優先度を High に設定する呼び出しを追加。

- モニタリング DB 初期化
  - 監視用 DB 初期化関数を呼び出してテーブル存在を保証（run_execution と run_monitoring から呼び出し）。

- DuckDB 統合
  - 分析向けに DuckDB 接続を利用（Settings で DUCKDB_PATH 設定、複数モジュールで使用）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等配分 / スコア加重）を実装（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中排除ロジック（apply_sector_cap）、レジームに応じた資金乗数 calc_regime_multiplier を実装（src/kabusys/portfolio/risk_adjustment.py）。
  - 発注株数算出（risk_based / equal / score の allocation_method に対応）、単元株丸め、aggregate cap によるスケーリング、コストバッファ対応を実装（src/kabusys/portfolio/position_sizing.py）。
  - これらをトップレベルでエクスポートする package API を追加（src/kabusys/portfolio/__init__.py）。

- 研究用ファクター計算
  - DuckDB を使ったファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
  - モメンタム（1M/3M/6M リターン、MA200 乖離率）、ボラティリティ（20日 ATR 等）、流動性指標を計算する関数を提供。
  - 大規模データ処理を想定し、ウィンドウ関数を用いた SQL 実装。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（psutil 利用、Windows / POSIX の差分吸収）（src/kabusys/utils/process_priority.py）。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告を出して安全にスキップする。

- Paper Trading 検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - system_status、trade_logs、risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値に対して PASS/FAIL 判定を出力。
  - P95 計算ユーティリティと柔軟な期間フィルタ（--from/--to/--db オプション）を提供。

### 変更
- DB 分離の設計方針を明確化
  - Paper Trading 環境では paper_sqlite_path を使用し、本番監視 DB と分離する設計を採用（run_execution, Settings）。
  - 監視 (run_monitoring) は意図的に本番 sqlite_path を使用（環境に依存しない監視運用を想定）。

- .env 読み込み順序と保護
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護され上書きされない）。

### 修正（バグ修正／堅牢化）
- .env パーサーの堅牢化
  - 引用符あり/なし両方のケースでエスケープやコメントを正しく扱うよう改善（config._parse_env_line）。
  - 無効行や export プレフィックスの処理を明確化。

- 起動時の安全対策
  - run_execution/run_monitoring で停止フラグファイルの検知を行い、既に停止フラグがある場合は起動を中止または適切に停止するようにした。
  - run_monitoring のポーリングループ内で check_once() の例外を捕捉してログ出力し、次ポーリングへ継続するように改良（フォールトトレランス強化）。

- リソースハンドリング
  - run_execution/run_monitoring で使用した sqlite3 / duckdb 接続を finally ブロックで確実にクローズするようにした。

### その他
- ドキュメント的なコードコメントと docstring を充実させ、各関数の引数・戻り値・想定動作を明確化。
- 各モジュールは可能な限り副作用を避ける純粋関数設計（特に portfolio モジュール、research モジュール）を採用。

---

今後の予定（例）
- CLI の追加（インストール後のエントリポイント設定）
- Strategy 実行フローの統合テスト
- 各モジュールに対するユニットテスト、型注釈の厳格化
- 各種設定のドキュメント化（config/*.yaml のテンプレート生成スクリプト整備）

もし特定の変更点を詳細に反映したい（ファイル別のコミット履歴風に記載する等）場合は、追加情報（コミット履歴や差分）を提供してください。コード内容から推測しているため、意図と異なる箇所がある場合はご指示ください。