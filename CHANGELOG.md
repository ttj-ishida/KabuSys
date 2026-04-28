# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-28

初回リリース。KabuSys のコア CLI / ユーティリティ群を導入します。主な追加点と振る舞いは以下のとおりです。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - プロジェクトルート検出・.env 自動読み込み機構を実装（src/kabusys/config.py）。
    - .git または pyproject.toml を起点にプロジェクトルートを探索し、.env / .env.local を自動ロード。
    - OS 環境変数は保護され、.env.local は .env を上書きする挙動。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスでアプリケーション設定を集中管理（src/kabusys/config.py）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、環境（KABUSYS_ENV）、ログレベル等のプロパティ。
    - PAPER_FILL_MODE（paper trading 用の注文埋まりモード）をサポート（instant/partial/never/reject）。
    - is_live / is_paper / is_dev のヘルパーを提供。

- 実行用 / 監視用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - BrokerClientFactory によるブローカークライアント生成。
    - Paper Trading モードでは paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にブローカーから現金・ポジションを取得して総資産を計算。
    - risk_config.yaml の読み込みと厳格なバリデーションを実装（値範囲チェック、必須キー確認）。
    - 起動時に Reconciler によるリコンシリエーションを実行し、Execution Startup Summary を生成して保存可能。
    - ExecutionEngine をデーモンスレッドで起動し、外部停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - PID ファイル管理（data/execution.pid）に対応。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor を用いたポーリングループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックしてログ出力。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する（監視 DB を常に参照）。
    - プロセス優先度を "high" に設定して実行（set_process_priority）。
    - stop flag（data/stop_requested.flag）検知でループを終了。
  - 各種レポート CLI
    - Signal Queue Confirmation（src/kabusys/run_signal_queue_report.py）
      - DuckDB の signals / portfolio_targets から翌営業日の発注シグナルを収集。JSON / CLI 表示 / ファイル保存に対応。
      - 保存先 artifacts/signal_queue/{date}/ に保存（--save）。
      - 結果ステータスに応じて終了コードを返す（READY → 0 など）。
    - Position Reconciliation View（src/kabusys/run_position_reconciliation_report.py）
      - Broker と OrderRepository を用いて現在スナップショットを収集、差分有無で終了コードを制御。
      - --watch モード（定期ポーリング）およびポーリング間隔指定（--interval）をサポート。
      - SQLite を読み取り専用モードで接続するための URI を使用（file:... ?mode=ro）。
    - Pre-Market Report（src/kabusys/run_pre_market_report.py）
      - DuckDB と SQLite を参照して pre-market の準備状況を評価。BLOCKED 等のステータスに応じて終了コードを返す。
      - 外部停止フラグとタスク名を collector に渡して収集を行う。
  - 設定ユーティリティ
    - 対話式設定ウィザード（src/kabusys/config_setup.py）
      - .env の初期作成・更新を支援。シークレットは入力時にマスク表示、保存前に確認ダンプを表示。
      - デフォルト値や選択肢を用意し、.env を自動生成（.env に保存）。
    - 設定検証 CLI（src/kabusys/validate_config.py）
      - 必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パスの親ディレクトリ存在（警告）・config/*.yaml の存在および YAML パース検証（PyYAML が利用可能な場合）を行う。
      - --strict オプションで警告も FAIL 扱いにできる。
  - ツール
    - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
      - paper_trading 用 SQLite のログからシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を表示。
      - P95 の計算ロジックと閾値（稼働率 99%、fill 90% 等）を組み込み。

- レポート / レンダラー / 保存
  - Signal Queue Confirmation レポートモジュール（src/kabusys/operations/signal_queue_report.py）
    - collect_signals(), build_report(), format_cli_summary(), format_json(), format_markdown(), save_report() を提供。
    - レポートは SignalQueueReport dataclass で表現。save_report は artifacts/signal_queue/{report_date}/ に summary.json / report.md / warnings.json を保存（同一日付は上書き）。
    - レポート生成時に target_size 未設定の BUY シグナル警告等を自動生成。

### Changed
- （初回リリースのため該当なし）

### Fixed / Robustness
- .env パーサーでシングル/ダブルクォートされた値のバックスラッシュエスケープと閉じクォート検出、インラインコメントの扱い等に対応（src/kabusys/config.py: _parse_env_line）。
- .env 読み込み失敗時に警告を出して処理を継続するように改善（読み込み失敗時の warnings.warn）。
- YAML パースが失敗した場合、該当ファイル名と例外情報を含むエラーを返すよう改善（risk_config / validate_config）。
- SQLite / DuckDB の接続は適切に close されるよう try/finally を配置。
- Execution 起動時のポジション評価で current_price が None または非正値の場合の警告とフォールバック処理を追加（_pos_value）。

### Security / Notes
- .env は絶対に Git にコミットしない旨をドキュメント（config_setup の生成ファイルヘッダ）に明記。
- validate_config により本番環境（KABUSYS_ENV=live）での注意喚起（LINE 通知未設定や Kill Flag 自動クリア設定など）を行うチェックを導入。

---

既知の制限・注意点
- monitor の DB 接続は KABUSYS_ENV に関係なく sqlite_path（本番想定）を使います。意図的な設計のため、テスト用に分離が必要な場合は別途 DB パスを指定・環境を調整してください。
- signal_queue_report.save_report() は report_date の形式検証を行い、無効な値の場合は例外を送出します。
- PyYAML 非インストール環境では config/*.yaml の内容検証がスキップされます（警告）。YAML 内容チェックを行うには PyYAML をインストールしてください。

---
（補足）この CHANGELOG はソースコードの内容および動作から推測して作成しています。実際のリリースノート作成時はリリース手順や他ファイル（未掲載のドキュメント・テスト等）を参照のうえ、必要に応じて調整してください。