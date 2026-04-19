# Changelog

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべてのリリースは安定版でない可能性があるため、互換性保証は明示していません。

## [0.1.0] - 2026-04-19

初回リリース

### 追加 (Added)
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag ファイルで検知。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Mock ブローカ（paper_trading DB）で本番 DB と分離。
    - スレッドでエンジンを実行し、停止フラグで安全に停止する制御を実装。
    - 起動時に実行用 PID ファイルを扱う（data/execution.pid）。

- 設定関連 CLI / ユーティリティ
  - config.py
    - .env の自動ロード機能（.env / .env.local、OS 環境変数保護）を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複雑な .env パースをサポート（export 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント）。  
    - Settings クラスを追加し、アプリケーションから統一的に環境設定を参照可能に。J-Quants / kabu / DB / 監視閾値等のプロパティを提供。
    - PAPER_FILL_MODE（paper trading の fill 動作）や PAPER_TRADING_SQLITE_PATH など paper_trading 向け設定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを作成・更新するツールを追加。
    - 複数の設定項目のデフォルト・選択肢・シークレット入力をサポートし、最終的に .env を出力。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（config/*.yaml、必須環境変数、パス、ログレベル等のチェック）。
    - --strict オプションで警告を FAIL 扱いにできる。PyYAML がない場合は YAML チェックをスキップして警告を出力する。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と日次ローテーションする TimedRotatingFileHandler をルートロガーへ設定する共通ユーティリティを追加。
    - 出力先ディレクトリの自動作成、既存ハンドラのクリア、ログレベルの解決順（引数 > 環境変数 > デフォルト）を実装。ログは 30 日分保持。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU アフィニティを最初の N コアに固定する set_cpu_affinity() を追加。
    - 権限不足や未対応 OS で安全にフォールバックする実装。

- ポートフォリオ構築関連モジュール（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選択（score 降順、signal_rank でのタイブレーク）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコアが全て 0 の場合は等配分にフォールバックして警告を出す実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限（apply_sector_cap）を実装。既存保有のセクター露出を計算し、上限超過セクターの新規候補を除外する。
    - market レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method="risk_based" / "equal" / "score"）。
    - lot_size（単元株）での丸め、per-position 上限、aggregate cap（総投資金が available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積）をサポート。
    - 価格欠損時はスキップする安全処理を実装。

- 研究／分析モジュール（部分実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などのファクター計算方針と計算関数群のスケルトンを追加（DuckDB 接続の想定、prices_daily/raw_financials を参照）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ指標（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。P95 算出やデータ無しケースの扱いに配慮。

- パッケージ情報
  - __init__.py にて __version__ を "0.1.0" に設定。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 注意事項 (Notes)
- デフォルトファイル・パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/, 各アプリケーションは logs/<app_name>.log を出力
- セキュリティ:
  - .env は生成スクリプトから「絶対に Git にコミットしないこと」と注記しています。シークレット（トークン・パスワード）は .env に格納する想定です。
- 実行関連:
  - run_execution / run_monitoring は stop flag（data/stop_requested.flag）で停止制御を行います。運用時の Kill Switch 周りの設定は validate_config のガードチェックを参照してください（KILL_FLAG_CLEAR_ON_START は本番で 1 にしないことを推奨）。
- 不足・将来の拡張点（ソース内 TODO の抜粋）:
  - position_sizing: 銘柄別の lot_size を将来的にサポートする拡張設計がコメントに記載されています。
  - risk_adjustment: price 欠損時のフォールバック（前日終値等）の扱い改善が検討課題として残っています。
  - research/factor_research は全実装が完了しているわけではなく、DuckDB クエリと整合する実装の完成が必要です。

---

今後のリリースでは以下を計画しています（未実装・要検討）:
- research モジュールの完全実装（すべてのファクター計算）
- モックブローカの詳細実装と execution 系ユニットテスト
- 監視・ロギングのさらに細かなメトリクス出力とアラート連携（LINE など）
- ユニットテスト／CI の整備

（以上）