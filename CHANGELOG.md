CHANGELOG
=========

すべての重要な変更はセマンティックバージョニングに従って記載しています。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

Unreleased
----------

注意・未実装／既知の改善点（コード中の TODO/警告に基づく推測）:

- research/factor_research.py が途中で切れているように見えます。ファクター計算（momentum 等）の実装完了および追加ユニットテストが必要です。
- position_sizing や risk_adjustment 内に将来的な拡張案（銘柄別 lot_size のサポート、価格フォールバック等）がコメントとして残っています。これらの拡張は将来の改善項目です。
- ログディレクトリ作成失敗時のフォールバックやファイルハンドラ作成失敗時の挙動は既に配慮されていますが、運用上の監視・アラート（例えばログ書き込み失敗時の外部通知）を追加する余地があります。

0.1.0 - 2026-04-18
------------------

Added
- 基本パッケージ初期実装
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV による paper_trading モードをサポート：paper_trading の場合は専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てとエンジン起動ロジックを実装。
    - 停止制御: data/stop_requested.flag によるグレースフルな停止、実行用 PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定関連 CLI / ユーティリティ
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出 .git / pyproject.toml ベース）。
    - export KEY=val 形式や引用符付き値、行末コメント等に配慮した独自の .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、KABUSYS_ENV 判定、paper_trading 用設定、監視閾値など）。
    - 必須値未設定時は _require() により ValueError を送出する仕様。
  - config_setup.py
    - 対話式 .env 作成ウィザード（.env の初期作成・更新）。
    - 秘匿値のマスク表示、選択肢サポート、既存値の読み込みと上書き保存機能を提供。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML がある場合）パース検証を実施。
    - --strict オプションで警告も FAIL 扱いにできる点をサポート。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する共通ユーティリティ。
    - ログレベル・ログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続する耐障害設計。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX 系）でのプロセス優先度設定（set_process_priority）を提供。
    - CPU affinity 固定用の set_cpu_affinity を実装（psutil 利用）。権限不足や未対応 OS では安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap 実装（売却予定銘柄を除外できる）。
    - 市況レジームに応じた投下資金乗数 calc_regime_multiplier 実装（bull/neutral/bear をマッピング、未知値はフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、単銘柄上限・合計投下上限の考慮、スケールダウン時の端数処理（fractional remainder による優先配分）などを実装。
    - cost_buffer による保守的コスト見積りをサポート。
    - 将来的な拡張点（銘柄別 lot_size 等）をコメントで明示。

- 解析 / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率（uptime）、注文成立率（fill rate）、送信率（send rate）、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。
    - コマンドライン引数で期間（--from, --to）や DB パス（--db）を指定可能。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - P95 計算や各種 N/A ハンドリングを実装。

- DB 初期化 / 監視テーブル
  - monitoring_db 初期化を各起動スクリプトから冪等に呼び出すことで監視テーブルの存在を保証。

Changed
- 設計面での分離
  - paper_trading モード時に本番 DB とデータが混ざらないよう、paper_sqlite_path を明示的に分離して使用するようにした（run_execution.py / Settings）。
- ログ出力の一元化
  - 全起動スクリプトが utils.logging_setup.setup_logging を呼ぶことでログ設定を統一。

Fixed
- .env パーサの強化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行末のコメント扱い等に対応し、より堅牢に .env を読み込めるようにした。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring のポーリング間隔環境変数で不正な値が指定された場合、警告を出してデフォルト値（60 秒）にフォールバックするようにした。

Notes
- セキュリティ
  - .env は Git にコミットしない旨を config_setup.py のヘッダーに明記。
  - 機密値は対話式ウィザードでマスク入力・マスク表示されるが、ファイル保存時は plain-text で .env に記録される点に注意（運用上は適切なファイル保護を推奨）。
- 互換性
  - Settings.env は "development" / "paper_trading" / "live" のみ受け入れる。無効値は起動時にエラーを投げる。
- テスト
  - 各純粋関数は副作用を持たない設計（DB 参照のない関数群）であり、単体テストが容易に書ける構成になっている。

Acknowledgements / References
- 内部ドキュメント参照: PortfolioConstruction.md, StrategyModel.md といった設計メモを参照することを前提とした実装になっています（コメントに言及あり）。

--- 

上記はリポジトリ内の実装内容（ソースコードの関数・コメント・TODO など）から推測して作成した変更履歴案です。実際のリリース履歴やコミットメッセージに合わせて調整してください。必要であれば、各項目をより詳細に（例: 変更された関数のシグネチャやパラメータの説明、影響範囲）書き起こします。