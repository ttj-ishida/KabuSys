# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはコードベースから推測して作成した概要です。

全般:
- バージョン番号はパッケージ定義 (src/kabusys/__init__.py) に合わせて 0.1.0 としています。
- 日付はこの生成日 (2026-04-23) を使用しています。実際のリリース日が異なる場合は適宜修正してください。

## [0.1.0] - 2026-04-23

### 追加（Added）
- アプリケーション全体の初期基盤を実装。
  - メイン起動スクリプト:
    - run_execution.py: ExecutionEngine の起動ロジック、スレッド実行・停止処理、PID / stop フラグの取り扱いを実装。
    - run_monitoring.py: SystemMonitor のポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。
  - 設定関連:
    - config.py: 環境変数アクセス用 Settings クラスと自動 .env ロード機能（.env / .env.local の読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。
    - validate_config.py: .env と config/*.yaml の起動前検証 CLI を実装（--strict オプションで警告を FAIL 扱い）。
  - ユーティリティ:
    - utils/logging_setup.py: 統一的なロギング設定（コンソール stdout + 日次ローテーションファイル、30日保持）。
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティ（Windows / POSIX を吸収）。
  - データベース関連:
    - run_execution/run_monitoring で sqlite3 と DuckDB を使用する接続処理を追加。監視テーブル初期化関数 init_monitoring_db を呼び出す。
  - Paper Trading 分離:
    - 設定で paper_trading 環境をサポートし、専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用。MockBrokerClient を用いた分離運用を想定（BrokerClientFactory により切替）。
    - PAPER_FILL_MODE: ペーパートレード時の約定挙動を制御するモードを導入（instant, partial, never, reject）。
  - ポートフォリオ構築モジュール:
    - portfolio/portfolio_builder.py: 候補選定（スコア順）、等金額/スコア重み付けを実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: position sizing（risk_based / equal / score）アルゴリズム、単元株（lot_size）丸め、aggregate cap のスケーリングと端数再配分ロジックを実装。
  - リサーチ / ファクター計算:
    - research/factor_research.py: モメンタム等のファクター計算を行う基盤を実装（DuckDB 接続を受ける設計）。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
  - パッケージ初期化:
    - src/kabusys/__init__.py に __version__ と主要サブパッケージを定義。

### 変更（Changed）
- .env 読み込みの仕様を強化（config.py / _load_env_file / _parse_env_line）:
  - export KEY=val 形式への対応。
  - クォートされた値のエスケープ解釈（バックスラッシュ処理）と対応する閉じクォート検索。
  - クォートなしの行でのインラインコメント扱いの改善（'#' の直前が空白/タブの場合のみコメント扱い）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルート検出（.git または pyproject.toml）に基づき安全に探索。
- ロギング:
  - stdout に StreamHandler を出力し、ファイル出力は TimedRotatingFileHandler（日次、30日保持）として統一。
  - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続する堅牢性を追加。
- プロセス優先度設定:
  - Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice 値）を抽象化して set_process_priority を実装。アクセス権限等で失敗する場合は警告でスキップ。
- run_monitoring の動作:
  - MONITOR_POLL_INTERVAL の環境変数検証を強化。整数変換・1 未満の値をデフォルトにフォールバックするロジックを追加。
  - 監視は環境にかかわらず production の sqlite_path を使用する旨を明示。
- run_execution の DB 選択:
  - settings.is_paper によって paper_trading 用の専用 SQLite を使用するように変更（本番 DB と分離）。
- validate_config の検証強化:
  - 必須/任意環境変数チェック、KABUSYS_ENV 値検証、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無い場合はスキップして警告）。
  - 本番環境（live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告等）。

### 修正（Fixed）
- 環境変数の読み込み失敗時に発生しうる例外を警告で扱いプロセスを停止させないよう改善（.env ファイル読み込み失敗で warnings.warn を利用）。
- ログハンドラの二重登録を防止するため、既存ハンドラの flush/close と削除を行うように修正。
- run_execution/run_monitoring の終了時に SQLite / DuckDB コネクションを finally ブロックで確実にクローズするように修正。
- position_sizing のスケーリング処理で端数配分を再現性のある順序で処理するように変更（残差ソートに code を二次キーに使用）。
- paper_verification_report の P95 計算で空データに対する安全な処理を追加。

### ドキュメント / コメント（Documentation）
- 各モジュールに日本語のドキュメンテーション文字列（docstring）を充実させ、アルゴリズムの参照箇所（PortfolioConstruction.md, StrategyModel.md 等）や設計上の注意点（例: price 欠損時の TODO）を明記。
- config_setup の対話ウィザードで生成される .env のテンプレートを明確化（.env を Git にコミットしない旨の注意を追加）。

### 既知の制限 / TODO
- research/factor_research.py の一部（calc_momentum の実装途中で切れている等）や将来の拡張点（銘柄ごとの lot_size の導入、価格フォールバック戦略）はコードコメントで TODO として残されている。
- apply_sector_cap は "unknown" セクターを上限適用対象外とする仕様であり、price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の注記あり（将来的なフォールバック価格導入を検討）。
- process_priority / cpu_affinity は環境依存で権限不足等により効果が無い場合がある（警告でスキップ）。

### セキュリティ（Security）
- 機密トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は .env に保管する想定。config_setup ではそれらを "secret" としてマスク表示。
- .env ファイルは絶対に Git にコミットしない旨をテンプレートに記載。

---

注: 本 CHANGELOG は提示されたソースコードから推測して作成した要約です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。必要があれば、さらに細かいセクション分け（例えば各モジュールごとの変更点や API 互換性の詳細）を追記します。