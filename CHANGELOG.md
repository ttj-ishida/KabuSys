CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（以下の変更点は提示されたソースコードから推測して作成しています）

Unreleased
----------

（なし）

0.1.0 - 2026-04-20
------------------

Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離して動作。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に停止する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
- 設定関連 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を作成／更新するツール（シークレットのマスク表示、選択肢サポート、保存確認等）。
  - validate_config.py: .env と config/*.yaml の起動前検証ツール（必須環境変数チェック、パスチェック、YAML パース検証（PyYAML がない場合はスキップ）、KABUSYS_ENV=live 時のガードチェック）。--strict オプションで警告を FAIL 扱いにできる。
- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py: Paper Trading の SQLite DB からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力する CLI。閾値はソース内定義（例: 稼働率 >= 99% 等）。
- 設定管理・自動読み込み改良
  - config.py: .env 自動ロード機構を導入（プロジェクトルートを .git や pyproject.toml から探索）。読み込み順は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースを強化（export プレフィックス対応、クォート文字のエスケープ処理、行内コメントの扱い向上）。
  - Settings クラスを導入し、各種設定（DB パス、API トークン、環境判定、紙トレードモードの設定など）をプロパティ経由で取得可能にした。PAPER_FILL_MODE に対するバリデーションを実装。
- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークルール）と等配分・スコア加重配分のユーティリティを実装。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは制限適用外、未知レジームは警告とフォールバック。
  - portfolio/position_sizing.py: risk_based / equal / score ベースの株数決定ロジックを実装。単元株（lot_size）で丸め、ポジション上限・総投資上限（aggregate cap）を考慮したスケーリングと端数処理を行う。
- ユーティリティの整備
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティ。stdout 出力（StreamHandler）と日次ローテートファイルハンドラ（TimedRotatingFileHandler、デフォルト logs/、30日保持）を設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定（Windows の優先度クラス／POSIX の nice）と CPU affinity 設定関数を実装。権限不足等の失敗は警告ログでフォールバック。

Changed
- DB の取り扱いポリシーを明示
  - 監視（Monitoring）は実行環境に依らず本番の sqlite_path を使用するように設計（run_monitoring.py）。
  - 実行エンジン（Execution）は paper_trading 環境時に専用の paper_sqlite_path を使用することで発注履歴等を本番 DB と完全分離する（run_execution.py）。
- ログの既定動作を統一
  - 全スクリプトで setup_logging(app_name=...) を呼ぶことを想定しており、stdout とローテートファイルの二系統でログを収集する設計に統一。

Fixed
- .env 読み込みの堅牢性向上
  - _load_env_file の挙動を整理し、既存の OS 環境変数を保護する protected 引数を導入（OS 環境を上書きしない）。override パラメータで .env.local などの上書きを可能にしている（config.py）。
- 停止フラグチェックの追加と安全停止処理
  - run_execution/run_monitoring に停止フラグ（data/stop_requested.flag）検出ロジックを導入。停止検知時に Engine.stop() を呼ぶ、またはループを終了して接続をクローズするようにしている。

Security
- 機密値の取り扱いに配慮
  - config_setup の対話表示ではシークレット項目をマスクして表示。README 等への誤コミット防止のため .env の注意書きを出力している。

Notes / Implementation details（実装上の注意）
- .env パーサーはクォート内のバックスラッシュエスケープを処理し、クォート無しの場合は「#」の直前が空白/タブであるときのみコメントとみなすなど、現実的な .env 記述に耐えるようになっている。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみを許容。無効値は ValueError を発生させる。
- Position sizing は単元株（lot_size）で丸めるため小口株の扱いに注意。open_prices 欄が欠損している銘柄はスキップする実装。
- paper_verification_report の P95 算出は単純パーセンタイル（ソートしてインデックス選択）を使用している。データ不足時は N/A を出力する。

今後の改善提案（推奨）
- prices/financials 等の外部データフォールバック（例: 価格欠損時の前日終値）を実装し、position sizing と sector exposure の欠損影響を低減する。
- logging_setup のテスト可能性向上のため、ハンドラの注入インタフェースを追加する。
- validate_config の YAML 検証は PyYAML が必須であるため、依存を明文化してインストール時に警告を出すか、オプション機能化する。
- ExecutionEngine と Monitoring のライフサイクル管理を systemd やコンテナ向けに調整（PID ファイル・終了シグナルのハンドリング改善等）。

--- 
（この CHANGELOG は提供されたソースコードの挙動から推測して作成しています。実際の変更履歴やリリースノートを作成する場合はコミット履歴・リリース方針に基づいて調整してください。）