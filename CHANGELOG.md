# CHANGELOG

すべての重要な変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム KabuSys の基本機能を実装しました。

### 追加 (Added)
- パッケージ情報
  - パッケージ初期バージョンを設定（__version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) を監視して安全に停止。
    - エンジンの PID を data/execution.pid に記録するための pid_file 指定をサポート。
    - プロセス優先度を起動時に "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）処理は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する。
    - 停止フラグ (data/stop_requested.flag) によるループ終了処理を実装。
    - プロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - 環境変数 / .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順序・上書きルールを実装（OS 環境変数を保護）。
    - .env 内の行パースを robust に実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境指定等）をプロパティで取得可能。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の妥当性検査を実装。
    - paper_trading 用の paper_sqlite_path をサポート。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 入力項目定義（KABUSYS_ENV、J-Quants / kabu API トークン、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込み、入力のマスク表示（シークレット）、確認プロンプト、.env ファイル書き込みを実装。
    - .env のテンプレートコメントと注意書きを出力（.env を Git にコミットしない旨の注意）。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 未インストール時はスキップ）を実装。
    - 本番環境（live）向けのガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を追加。
    - --strict オプションで警告もエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選択（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率による配分（全スコアが 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有・当日売却予定を考慮）で候補をフィルタ。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバックで 1.0 として警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく株数決定。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケール調整、cost_buffer を考慮した保守的見積りを実装。
    - aggregate スケールダウン時の残差処理（lot 単位での追加配分）を実装。
    - 価格欠損時のスキップやログ出力。

- リサーチ／ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取ってファクター（モメンタム、ボラティリティ、流動性等）を計算するモジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。
    - calc_volatility（実装途中まで確認可能）: ATR、相対 ATR、20日平均売買代金、出来高比率などを計算する設計。
    - DuckDB の prices_daily テーブルを使って集計。データ不足時には None を返す設計。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil 依存）。
    - CPU affinity を指定する set_cpu_affinity を追加（最初の N コアに固定）。
    - Windows / POSIX の差分を吸収し、失敗時は警告ログでフォールバック。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等。
    - 閾値（デフォルト）: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - 日付フィルタ (--from / --to) と DB パスの指定 (--db) をサポート。
    - DB が存在しない場合やテーブルが無い場合に対するフォールバック処理を実装。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を利用して監視用テーブルの存在を保証（冪等的に初期化）。

### 変更 (Changed)
- （初回リリースのため適用なし）

### 修正 (Fixed)
- （初回リリースのため適用なし）

### 削除 (Removed)
- （初回リリースのため適用なし）

### セキュリティ (Security)
- 環境変数を .env に保存する際の注意喚起を config_setup に記載（.env を絶対に Git にコミットしない旨）。

---

注記:
- 一部モジュール（ExecutionEngine / SystemMonitor / BrokerClient 等）の詳細実装は本差分一覧で省略していますが、起動フローや依存関係（DB 接続、ブローカー選択、各種マネージャ組立て、停止フラグ監視など）は上記の通りです。
- config.py の自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後は CWD に依存せず動作するよう設計されています。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。