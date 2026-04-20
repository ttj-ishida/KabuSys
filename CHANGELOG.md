# Changelog

すべての重要な変更をこのファイルに記載します。  
形式は「Keep a Changelog」に準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-20

初回リリース。

### 追加
- 基本的なアプリケーション設定管理を実装（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基に自動で .env を読み込む仕組みを導入。
  - .env / .env.local の読み込み順序をサポート。既存 OS 環境変数の保護オプションあり。
  - Settings クラスを導入し、J-Quants / kabu API / LINE / DB /監視閾値などの設定をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE（ペーパートレード時の約定モード）値検証を実装。
  - 環境値（KABUSYS_ENV）や LOG_LEVEL の妥当性検査を実装。

- 対話式環境設定ウィザードを追加（kabusys.config_setup）
  - .env の初期作成・更新を対話式で行う CLI を提供。
  - シークレット値はマスク表示、生成された .env に書き込む機能あり。
  - .env の書き込みテンプレートに注意書き（Git にコミットしない）を含む。

- 設定検証コマンドを追加（kabusys.validate_config）
  - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース検証（PyYAML が利用可能な場合）を検査。
  - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止処理を実装。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）を使用する制御。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化を行い、SystemMonitor を定期実行して状態を記録。
    - 監視は環境にかかわらず本番 sqlite_path を利用する設計（監視 DB の分離は行っていない点に注意）。
    - 停止フラグを検知してループ終了、KeyboardInterrupt による正常終了処理。

- ロギングユーティリティを追加（kabusys.utils.logging_setup）
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定。
  - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで続行。

- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - Windows / POSIX（Linux, macOS, FreeBSD）を透過的に扱い、nice 値や Windows の優先度クラスを設定。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、権限不足等のエラーは警告でスキップする。

- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件抽出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックし警告を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中リスクを計算し、上限超過セクターの候補を除外（"unknown" セクターは適用外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返却。未知レジームは 1.0 にフォールバックし警告。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer（手数料・スリッページ見積）対応、価格欠損時のスキップなどを実装。
    - スケールダウン時の残差分配アルゴリズムを実装し、再現性を保つため安定ソートを使用。

- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - SQLite（Paper Trading DB）からメトリクスを集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を出力。
  - 閾値に基づき PASS/FAIL 判定を行う。CLI 引数で期間指定（--from / --to）と DB パス指定（--db）をサポート。
  - デフォルトの DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。

- research モジュールにファクター計算の枠組みを追加（kabusys.research.factor_research）
  - Momentum / Value / Volatility / Liquidity を想定した設計と定数を追加。DuckDB 接続を受けて計算する方針を採用。モメンタム計算関数（calc_momentum）の実装開始。

- パッケージメタ情報
  - __version__ を "0.1.0" に設定。

### 変更
- ログ出力先の StreamHandler を stdout に固定（cron / Task Scheduler 等でのリダイレクトを想定）。
- validate_config にて PyYAML 未インストール時は YAML 内容検査をスキップし警告を出すように変更。

### 修正（挙動上の配慮）
- .env 読み込みでファイルが読み込めなかった場合に警告を発し失敗を回避する実装（テスト環境などで安全に動作）。
- process_priority / cpu_affinity の権限不足や未対応 OS への対処は警告ログでスキップする設計にして起動の妨げとならないようにした。
- ポジションサイズ計算における価格欠損時のスキップとログ出力を追加し、不完全データでの誤発注リスクを低減。

### 既知の注意点 / TODO
- monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用監視 DB）を使用する設計になっているため、テスト環境での監視データ分離が必要な場合は手動で SQLITE_PATH を切り替えてください。
- position_sizing の _max_per_stock は price=0 の場合に 0 を返す。価格欠損時のフォールバック（前日終値やマスタ参照）は TODO。
- research.calc_momentum の実装が途中（ファイル末尾で切れている）。ファクター計算の完全実装は今後の課題。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きを追加）。

---

今後のバージョンでは以下を想定しています:
- research のファクター計算完了とテスト追加
- ExecutionEngine / SystemMonitor 周りのユニットテスト強化
- 監視 DB の環境分離オプション追加（development / paper_trading 用）
- 銘柄別単元株サイズのサポート（stocks マスタの導入）