# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
このリポジトリの初回リリース相当の状態からコードを解析して推測した変更点を記載しています。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本アプリケーション情報を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動するエントリポイントを追加。  
    - プロセス優先度を "high" に設定。
    - 環境に応じて paper_trading 用 DB を分離（`PAPER_TRADING_SQLITE_PATH` / `settings.paper_sqlite_path`）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - エンジンは別スレッドで動作し、`data/stop_requested.flag` による停止制御をサポート。
    - PID ファイルの取り扱い（`data/execution.pid`）をサポート。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は実行環境に関わらず本番用 sqlite_path を使用する設計。
    - 停止フラグ `data/stop_requested.flag` の検出でループ終了、例外発生時はログ出力して次ループへ継続。

- 設定管理
  - `config.py`：.env 自動読み込み・パースと Settings クラスを実装。  
    - プロジェクトルート検出（`.git` または `pyproject.toml` を基準）により CWD に依存しない .env 読み込み。
    - .env パーサは `export KEY=val` 形式、クォート内のバックスラッシュエスケープ、行内コメントの扱い等に対応。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 各種設定プロパティを提供（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス, PID/Kill flag, 各閾値, PAPER_FILL_MODE 等）とバリデーション。
    - paper_trading 用の DB パス (`paper_sqlite_path`) と fill モード（instant/partial/never/reject）の検証を実装。
    - 環境（development/paper_trading/live）とログレベルの検証ロジックを備える。

- 設定関連 CLI
  - `config_setup.py`：対話式 .env ウィザードを追加。  
    - J-Quants / kabu API 等の必須項目やオプション項目を対話的に入力・保存できる。
    - シークレット項目は表示マスク、既存 .env の読み込み・再利用に対応。
    - 保存前に確認プロンプトを提示。
  - `validate_config.py`：起動前の設定検証 CLI を追加。  
    - 必須環境変数の未設定検出、プレースホルダ値検出、KABUSYS_ENV / LOG_LEVEL / DB パスのチェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）を追加。

- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio/portfolio_builder.py`：候補選定と重み計算を追加。  
    - select_candidates: スコア降順、同点時は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化（合計 0 の場合は等配分へフォールバックし WARNING を出力）。
  - `portfolio/risk_adjustment.py`：セクター集中制限とレジーム係数を実装。  
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックし警告を出力。
  - `portfolio/position_sizing.py`：株数決定ロジックを追加。  
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based: portfolio_value, risk_pct, stop_loss_pct に基づく単銘柄目標株数算出。
    - 等配分系: weights に基づく割当て。lot_size（単元）で丸め。
    - aggregate cap（available_cash）を超える場合のスケーリングと残差処理（lot 単位で再配分）を実装。
    - cost_buffer を導入して手数料/スリッページを保守的に見積もる。

- 監視・実行用 DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db`（起動スクリプトから使用）を用いて監視テーブルの冪等な初期化を行う（存在保証）。

- ログ設定ユーティリティ
  - `utils/logging_setup.py`：統一的なログ初期化関数を追加。  
    - StreamHandler を stdout に設定（cron 等で stdout/stderr を一本化する運用想定）。
    - TimedRotatingFileHandler による日次ローテーション（30 日分保持）をサポート。ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - 引数や環境変数 (`LOG_LEVEL`, `LOG_DIR`) による上書き対応。

- プロセス優先度 / CPU affinity ユーティリティ
  - `utils/process_priority.py`：psutil を用いた抽象化ユーティリティを追加。  
    - set_process_priority(level) で Windows / POSIX の差を吸収して優先度設定。失敗時は警告を出力してスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定（未指定ならスキップ）。失敗時は警告を出力してスキップ。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`：paper_trading の SQLite DB を解析して検証レポートを生成するツールを追加。  
    - uptime, fill rate, send rate, リスク却下数, レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは `data/paper_trading.db`。`--db` オプションや環境変数 `PAPER_TRADING_SQLITE_PATH` により上書き可能。
    - P95 算出、日付フィルタ（--from/--to）対応、閾値はソース中で定義（稼働率 99%、fill 90%、send 95%、P95 200 ms）。

- リサーチ・ファクター計算（基盤）
  - `research/factor_research.py` にて Momentum/Value/Volatility/Liquidity 等のファクター計算の設計を実装（DuckDB 接続を受け、prices_daily/raw_financials のみ参照する設計）。一部実装（calc_momentum 等）について内部ロジックを記載（ファイルの末尾で実装途中）。

### 変更 (Changed)
- .env 読み込みの挙動
  - 自動ロード時は OS 環境変数を保護（protected set）しつつ `.env` と `.env.local` を適切な優先度で読み込むロジックを導入。
- ログの挙動
  - 既存ハンドラを再設定する際に一旦 flush/close して二重設定を防止。

### 修正 (Fixed)
- 環境変数の不正値に対する堅牢性向上
  - MONITOR_POLL_INTERVAL の負や非整数値を検出してデフォルトにフォールバックし、警告を出力するようにした。
  - PAPER_FILL_MODE の不正値は ValueError を発生させて早期に検出。

### 既知の制限 / 注意点 (Known Issues / Notes)
- research/factor_research.py の実装がファイル末尾で途切れている（calc_momentum の続きが未完）。本モジュールは設計方針・定数は整備済みだが、完全な実装はまだ必要。
- position_sizing の価格欠損時の挙動について TODO コメントが存在（price が 0.0 の場合にエクスポージャーを過少見積もる可能性）。
- 一部の機能は psutil や PyYAML に依存する。これらのライブラリが存在しない場合は該当機能の挙動（CPU affinity 設定や YAML 検証など）が限定される旨のフォールバックや警告が入る設計。
- 本リリース相当のコードは運用上の安全装置（Kill Switch / PID 管理 / paper_trading と本番 DB の分離等）を備えているが、本番導入前に設定検証（`python -m kabusys.validate_config`）と .env の適切な保護を行ってください。

---

以上はコードベースの内容から推測して作成した CHANGELOG です。追跡可能なコミット履歴がある場合は、実際のコミットメッセージに基づいて差分を反映することを推奨します。必要であれば、より詳細なセクション分け（内部 API、CLI、ライブラリ等）や未実装タスク一覧を追加できます。