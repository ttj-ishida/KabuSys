# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリースポリシー: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

初回リリース。本リポジトリは日本株向け自動売買システム「KabuSys」のコアユーティリティ群・実行・監視・ポートフォリオ構築・検証ツールを含みます。

### Added
- 全体
  - パッケージ初期バージョン (kabusys) を追加。バージョンは `__version__ = "0.1.0"`。
  - モジュール構成を整備（execution, monitoring, portfolio, research, utils, tools, config 等）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を使ったブローカー選択、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、および ExecutionEngine のバックグラウンドスレッド実行と停止フラグ検出を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視 DB の一貫性確保）。
    - 停止フラグ `data/stop_requested.flag` を検知してループを終了。
    - 例外発生時にログで捕捉して次ポーリングに継続。

- 設定・CLI
  - config.py
    - 環境変数と .env ファイルの読み込み機能を提供。
    - プロジェクトルート検出ロジック（.git または pyproject.toml）を実装し、CWD に依存しない自動 .env ロードを実現。
    - .env パースの強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
    - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - Settings クラスで各種設定をプロパティ提供（J-Quants / kabu API / DB パス / paper_trading 設定 / 監視閾値 / 実行環境判定 等）。
    - PAPER_FILL_MODE の入力検証と有効値の列挙。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI ツールを追加。
    - シークレット項目はマスク表示、選択肢サポート、保存前の確認を実装。
    - .env の読み込み／書き込みロジックを提供（既存値を保持した上で更新可能）。
  - validate_config.py
    - 起動前の設定検証ツールを追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAMLがインストールされている場合）を検査。
    - `--strict` オプションで警告を失敗扱いに可能。
    - 本番環境（live）向けの追加警告（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。

- 監視・検証ツール
  - monitoring.monitoring_db による監視テーブルの初期化呼び出し（init_monitoring_db）を各起動スクリプトで実行し、冪等的にテーブル存在を保証。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加（DB 参照、期間フィルタ対応）。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ (avg/max/P95) を算出して総合判定（PASS/FAIL）を出力。
    - P95 計算、データ存在チェック、SQL クエリ分離ロジックを実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等重み (calc_equal_weights)、スコア重み (calc_score_weights) を実装。スコア全ゼロ時は等重みにフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)：既存ポジションのセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - レジームに応じた資金乗数 (calc_regime_multiplier)：bull/neutral/bear のマッピングを実装。未知レジームは警告後フォールバック 1.0。
  - portfolio/position_sizing.py
    - position size 計算 (calc_position_sizes)：
      - allocation_method に応じた計算（"risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer を考慮した保守的見積り。
      - aggregate スケーリング後の端数処理（残余キャッシュで lot 単位追加）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバック。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
    - stdout を使用することでタスクスケジューラ/cron の出力捕捉を想定。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（Windows: priority class、POSIX: nice 値）を実装。
    - CPU affinity 設定ユーティリティ (set_cpu_affinity) を追加。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップする安全ハンドリング。

- research
  - research/factor_research.py（部分実装）
    - DuckDB を用いたファクター計算フレームワーク（Momentum, Value, Volatility, Liquidity）を設計。モメンタム計算のための定数と関数の枠組みを追加（calc_momentum 等）。（実装は途中の可能性あり）

### Changed
- ログ出力
  - デフォルトで stdout に出力するように変更（stderr ではなく）。これは外部ジョブ管理環境での出力収集を考慮した決定。

- 環境変数ロードの既定挙動
  - OS 環境変数を保護しつつ .env.local が .env を上書きする挙動を採用（.env の自動ロード順を明確化）。
  - 自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。

- run_monitoring の DB 接続
  - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を用いる仕様に変更（監視の一貫性を重視）。

### Fixed
- .env パーサ
  - export プレフィックス付き行やクォート内のバックスラッシュエスケープ、インラインコメント取り扱いの不整合を修正（より一般的な .env 構文に対応）。

- DB ハンドルのクリーンアップ
  - run_*.py 内で finally ブロックにより sqlite/duckdb コネクションを確実にクローズするように改善。

- 監視・Execution の堅牢性
  - monitor.check_once() の例外はキャッチしてログ出力し、次ポーリングへ継続するように変更（監視ループの安定化）。
  - ExecutionEngine のスレッドを監視し、停止フラグ検出時に安全に engine.stop() を呼ぶ実装を追加。

### Deprecated
- 特になし

### Removed
- 特になし

### Security
- config_setup にて .env ファイル作成時に注意書きを追加（.env を Git にコミットしないことを明示）。
- シークレット入力時はウィザードでマスク表示。

### Known issues / Notes
- research/factor_research.py はモジュール骨格と一部実装を含むが、calc_momentum の実装が途中で切れている（ファイル末尾が未完）。実行時に該当機能を利用する場合は追加実装が必要。
- position_sizing の price フォールバックが未実装: price が欠損（0.0）の場合にエクスポージャーやポジション計算が過少評価される可能性がある旨 TODO コメントあり。将来的に前日終値や取得原価のフォールバックを検討。
- PAPER_FILL_MODE 等の環境変数値の不正入力は ValueError を発生させるため、運用環境では validate_config や config_setup を用いて正しい値を設定することを推奨。
- run_monitoring では監視 DB に本番 sqlite_path を直接使用するため、検証環境で監視を分離したい場合は設定の調整が必要。

---

将来的なリリースでは、research の完全実装、ExecutionEngine/Reconciler の動作検証、テストカバレッジの追加、及び運用向けの監視アラート設定（LINE 通知等）の拡充を計画しています。