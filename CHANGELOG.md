# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
詳細な貢献者情報はリポジトリのコミット履歴を参照してください。

なお、本 CHANGELOG はリポジトリ内のソースコードから実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`.
- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite DB（`data/paper_trading.db` をデフォルト）を使用し、本番 DB と完全に分離。
    - エンジン起動時にプロセス優先度を "high" に設定。
    - 停止制御用のフラグファイル（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）を利用してデーモン化（スレッド）実行／停止を制御。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを実行するスクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。無効値時はデフォルトにフォールバックし、警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用（監視データは常に本番 DB に集約）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ検知でループを終了する挙動を実装。
- 設定管理
  - `config.py`
    - `.env` 自動読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` のパース機能強化（export 構文、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどをサポート）。
    - 設定を表す `Settings` クラスを実装。J-Quants / kabu API / DB パス / 監視しきい値 / 環境（development/paper_trading/live）など多数のプロパティを提供。
    - `PAPER_FILL_MODE` 等の入力検証（有効値チェック）を実装。
- 設定ユーティリティ CLI
  - `config_setup.py`
    - 対話式ウィザードで `.env` の初期作成・更新を支援する CLI を追加。
    - デフォルト値・選択肢・説明文を表示し、シークレット項目はマスクして扱う。
    - 生成される `.env` に注意書きを付与（.env をコミットしないよう明記）。
  - `validate_config.py`
    - 起動前に環境変数や config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース確認、KABUSYS_ENV=live 時の追加ガード（LINE 通知や Kill Switch 周り）などを実装。
    - `--strict` オプションで警告をエラー扱いにできる。
- ロギングユーティリティ
  - `utils/logging_setup.py`
    - 全起動スクリプトで共通利用する logging セットアップ関数を追加。
    - stdout へ StreamHandler（標準出力）を設定し、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を `logs/<app_name>.log` に設定（30日分保持）。
    - ログレベルとログディレクトリの解決順を実装。ファイルハンドラ作成に失敗してもコンソール出力は維持。
- プロセス優先度 / CPU アフィニティユーティリティ
  - `utils/process_priority.py`
    - Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定する機能を追加。
    - CPU アフィニティを最初の N コアに固定する `set_cpu_affinity` を実装。
    - 権限や未対応 OS の場合は警告を出してスキップ。
- Portfolio 構築モジュール
  - `portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等分にフォールバック）を実装。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート）。
  - `portfolio/position_sizing.py`
    - position sizing（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケールダウン）および残差処理（lot_size 単位で再配分）を含む。
  - `portfolio/__init__.py` でエクスポートを統一。
- Research（ファクター計算）モジュールの骨組み
  - `research/factor_research.py`
    - モメンタムなど複数のファクターを計算する設計を追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照する想定の関数群（例: calc_momentum）が実装開始（ドキュメントと定数を含む）。
- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL を出力。
    - P95 計算ロジック、期間フィルタリング、DB 存在チェック、デフォルト DB パス解決（環境変数 `PAPER_TRADING_SQLITE_PATH`）を実装。

### 変更 (Changed)
- なし（初期リリースとして新規実装中心）。

### 修正 (Fixed)
- なし（初期リリースとして新規実装中心）。

### ドキュメント (Documentation)
- 各モジュールに日本語のドキュメンテーション文字列（docstring）を豊富に追加。設計意図、使用例、引数・戻り値、注意点（TODO 含む）を明記。
- config_setup と validate_config に使い方を CLI ヘルプとして実装。

### 注意点 / 実装上の留意
- Monitoring は環境にかかわらず本番用 sqlite_path を利用する振る舞いに設計されているため、意図的に監視データを一元化しています。Paper トレードの監視データを完全に分離したい場合は設定見直しが必要です。
- `.env` 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後や特殊な配置では自動ロードがスキップされる可能性があります。必要であれば `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で管理してください。
- 権限や実行環境によってはプロセス優先度や CPU affinity の設定が失敗することがあるため、失敗時は警告を出して処理を継続する実装です。
- position sizing / risk adjustment 周りでは価格欠損時のフォールバック等、将来の改善点（TODO コメント）を残しています。
- Research モジュールはファクター計算の骨組みを実装していますが、実運用時は DuckDB のスキーマとデータ投入（prices_daily / raw_financials）が前提になります。

---

参照: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/