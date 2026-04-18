# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-04-18
初回リリース。KabuSys の基本的な実行・監視・設定・ポートフォリオ構築・解析ツール群を含みます。

### 追加 (Added)
- 基本ライブラリ・エントリポイント
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
- 実行/監視プロセス起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory により環境に応じて MockBrokerClient / 実プロバイダを生成。
    - デーモンスレッドで engine.run_session を実行し、data/stop_requested.flag を検知して安全に停止可能。
    - 起動時に高優先度（"high"）でプロセス優先度を設定。
    - エンジンの PID 管理（data/execution.pid）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは環境に関わらず本番用の sqlite_path を使用して監視テーブルを管理。
    - data/stop_requested.flag によりループを終了。
- 設定管理・ウィザード・検証
  - config.py: 環境変数/`.env` 読み込みロジックを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - `.env` / `.env.local` を OS 環境変数を保護した上で自動読み込み（無効化用に `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意）。
    - 複雑な `.env` 行のパースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - Settings クラスで各種設定値をプロパティとして提供（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path 等）。
    - `paper_fill_mode` のバリデーション（有効値: "instant" / "partial" / "never" / "reject"）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - シークレット項目マスク表示、選択肢サポート、既存 .env 読み込みおよび確認/保存機能。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML があれば中身も検証）。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（daily、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name 引数で設定を制御。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux, macOS, FreeBSD）を吸収して優先度設定を行う。権限不足や未サポート環境では警告を出して安全にスキップ。
    - set_cpu_affinity 関数により先頭 N コアへプロセスをピン留め可能（引数 None で未設定）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（同点時は signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0.0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（'bull'=1.0, 'neutral'=0.7, 'bear'=0.3。未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づき株数を決定。
      - risk_based: risk_pct, stop_loss_pct を用いたリスクベース算出。
      - lot_size 単位で丸め、1 銘柄上限（max_position_pct）を尊重。
      - aggregate cap（available_cash）を超える場合は比率でスケールダウンし、残余を fractional remainder に基づき lot 単位で再配分。
      - cost_buffer によりスリッページ/手数料を保守的に見積もる。
- 解析 / ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出。
    - デフォルト閾値を定義（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - DB パスはコマンドライン引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの順で解決。
    - DB が存在しない場合にエラーメッセージを表示して終了。
- リサーチモジュール（解析基盤）
  - research/factor_research.py: 定量ファクター計算の土台を追加（モメンタム・MA200乖離・ATR・流動性等の算出を想定、DuckDB 経由で時系列データを参照する設計）。
  - DuckDB を分析用データベースとして利用する設計を導入（duckdb_path）。

### 変更 (Changed)
- 設定の自動読み込みの挙動を明確化
  - OS 環境変数は保護され、`.env.local` は `.env` の上書きとして読み込まれる（ただし OS 環境変数が優先）。
- ロギング設定
  - 既存ハンドラが存在する場合は一度クリアしてから再設定することで二重出力を防止。
- エラーハンドリング改善
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループ継続し、例外スタックトレースをログ出力して次ポーリングへフォールバック。
  - 各 CLI/ツールで DB テーブルが未存在の場合は sqlite3.OperationalError を捕捉してデフォルト値で続行。

### 修正 (Fixed)
- .env パーサの堅牢性向上
  - export プレフィックス・クォート内のエスケープ・インラインコメントの扱いを改善し、より多様な .env フォーマットに対応。
- ポジション決定の丸めと上限計算の安定化
  - lot_size 単位での丸め、銘柄ごとの最大株数制約（_max_per_stock）を導入し、不整合な発注量を防止。
- モジュール初期化時の DB 周りの冪等処理
  - init_monitoring_db を呼び出すことで、monitoring テーブルの存在を保証（冪等）。

### セキュリティ (Security)
- .env の取り扱いに関する注意書きと config_setup により `.env` を誤ってコミットしないよう案内を追加。

### 既知の制限 / 将来の改善案 (Known issues / TODO)
- position_sizing の価格欠損時のフォールバック:
  - price_map によるエクスポージャー計算で price が 0.0 の場合、過少見積となる可能性があるため、前日終値や取得原価等のフォールバック価格を検討中。
- market_regime 未知時の扱い:
  - 未知レジームは現状 1.0 でフォールバックし警告を出すのみ。将来的により厳密なデフォルト方針を検討。
- research/factor_research の実装はモジュール骨子を含むが一部関数の未完成箇所（ソース末尾の未完部分）あり。今後詳細実装を追加予定。

---

今後のリリースでは、Strategy 実装、Engine の詳細なテストカバレッジ、さらにモニタリング・アラート（LINE 通知等）の統合を進める予定です。変更履歴はコードの変更に合わせて随時更新します。