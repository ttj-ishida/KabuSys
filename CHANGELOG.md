# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内の主要追加・改善点をコードベースから推測して記載したものです。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更 / 改良
- Fixed: バグ修正
- Removed: 削除した機能

## [0.1.0] - 2026-04-21

### Added
- プロジェクト初期リリース相当の基礎機能を追加。
  - パッケージ情報:
    - kabusys.__version__ = "0.1.0"
  - 設定管理:
    - Settings クラスによる環境変数／設定管理モジュールを追加（src/kabusys/config.py）。
      - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - 読み込み順: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
      - 各種プロパティ（J-Quants トークン、kabu API 設定、DB パス、監視パラメータ、環境判定等）を提供。
      - PAPER_FILL_MODE の妥当性検査、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - 環境セットアップ / 検証 CLI:
    - 対話式 .env 作成ウィザード (src/kabusys/config_setup.py) を追加。
      - 各項目のプロンプト、既存 .env の読み込み、シークレット値のマスク、保存機能を提供。
    - 設定検証コマンド (src/kabusys/validate_config.py) を追加。
      - 必須環境変数、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在（及び PyYAML がある場合はパース検証）、本番環境向けガードをチェック。
      - --strict オプションで警告も FAIL 扱いにできる。
  - 実行用スクリプト:
    - run_execution 起動スクリプト (src/kabusys/run_execution.py) を追加。
      - 起動時にプロセス優先度を "high" に設定。
      - paper_trading 環境では paper 専用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行。
      - 停止フラグ（data/stop_requested.flag）と PID ファイルを扱う制御ロジックを提供。
    - run_monitoring 起動スクリプト (src/kabusys/run_monitoring.py) を追加。
      - Monitoring 用に本番 sqlite_path を常に使用（環境に依存せず監視データは本番 DB に保持）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバック。
      - 停止フラグの検知によるループ終了、例外ハンドリング、リソースクローズを実装。
  - 監視用 DB 初期化:
    - init_monitoring_db を用いた監視テーブルの冪等な初期化処理を両起動スクリプトから呼び出す。
  - ロギングユーティリティ:
    - setup_logging (src/kabusys/utils/logging_setup.py) を追加。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
      - 既存ハンドラのクリア、ログレベルの解決順（引数 > 環境変数 > デフォルト）、ログディレクトリ作成のフォールバック処理を実装。
  - プロセス優先度 / CPU affinity:
    - set_process_priority / set_cpu_affinity (src/kabusys/utils/process_priority.py) を追加。
      - Windows / POSIX (Linux, Darwin, FreeBSD) の差分を吸収して優先度設定を簡潔に扱える。
      - 実行権限不足や未対応 OS に対するワーニング処理を実装。
  - ポートフォリオ構築ライブラリ:
    - portfolio モジュールを追加（純粋関数群、DB非依存）。
      - portfolio_builder: 候補選定 select_candidates、等金額／スコア加重の重み計算 calc_equal_weights / calc_score_weights。
      - risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" のマップ）。
      - position_sizing: calc_position_sizes — risk_based / equal / score に対応した株数決定ロジック。単元（lot_size）丸め、max_position_pct・max_utilization・cost_buffer を考慮する aggregate cap スケーリングを実装。
  - Paper Trading 向け検証ツール:
    - tools/paper_verification_report.py を追加。
      - Paper Trading の SQLite DB（デフォルト data/paper_trading.db）を解析して稼働率・注文成功率・送信率・レイテンシ (P95) 等を計算し、PASS/FAIL 判定を出力。
      - P95 計算、日付フィルタ、閾値（稼働率 99%、成立率 90% 等）の定義を含む。
  - 研究／ファクター計算（開始実装）:
    - research/factor_research.py を追加（モメンタム・ボラティリティ等の計算方針、定数の定義。calc_momentum の計算開始まで実装の痕跡あり）。
  - その他ユーティリティ初期実装:
    - パッケージ構造・エクスポート（kabusys/portfolio/__init__.py など）。

### Changed
- （初回リリースのため過去変更なし。設計上の注意点をドキュメント／コード中に明記）
  - .env 読み込み時に OS 環境変数を保護する仕組みを導入（.env/.env.local の上書き制御）。
  - ログ出力は stdout をデフォルトで使用するように設計（cron／タスクスケジューラでの扱いを考慮）。
  - run_execution / run_monitoring は起動直後にプロセス優先度を "high" に設定することでレイテンシ重要処理の優先度を確保。

### Fixed
- 該当なし（初回リリースに含めるべき既知のバグはコード内の TODO コメント等に記載）。

### Removed
- 該当なし。

### Notes / Known limitations
- research/factor_research.py はモジュール実装が途中の可能性があります（calc_momentum の実装がファイル末尾で途中で終わっている痕跡あり）。今後のリリースで完成予定。
- position_sizing の価格欠損時のコメント（TODO）や price のフォールバック未実装など、実運用に向けた堅牢化（価格フォールバック、銘柄毎の lot_size 管理など）が残っています。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダーにも明記）。
- run_monitoring は監視データを「本番 sqlite_path」に常に書き込む設計のため、開発環境での誤運用に注意してください。

---

今後の予定（推測）
- research/factor_research の完成（DuckDB を用いたファクター計算の実装完了）。
- 各コンポーネントの単体テスト・統合テストの追加。
- 価格欠損や手数料モデル等のフォールバックロジックの強化。
- ドキュメントの整備（Usage ガイド、運用手順、デプロイ手順）。