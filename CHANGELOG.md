# CHANGELOG

すべての notable な変更は Keep a Changelog の慣例に従って記録します。  
フォーマット: https://keepachangelog.com/ja/ より。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。KabuSys の基本コンポーネントを追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory 経由）を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
      - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
      - 停止は data/stop_requested.flag によるファイルフラグで制御。実行中は execution.pid を作成して PID 管理。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用は KABUSYS_ENV に関わらず本番 sqlite_path（data/monitoring.db デフォルト）を使用して監視 DB を初期化。
      - 停止は data/stop_requested.flag を検知してループを終了。
  - 設定管理
    - config.py: Settings クラスを追加し、環境変数経由でアプリ設定を提供。
      - .env 自動読み込み機能（プロジェクトルートを自動検出: .git または pyproject.toml）を実装。
      - 読み込み優先順: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
      - 設定項目: J-Quants / kabuAPI / LINE / DuckDB/SQLite パス / Paper Trading 関連 / 監視閾値 等。
      - env 値・LOG_LEVEL のバリデーションを実装（許容値チェック）。
    - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の初期化・更新支援）。
      - シークレット入力のマスク表示、デフォルト値・選択肢の提示、保存確認を実装。
    - validate_config.py: 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML がなければパース検証をスキップして警告）。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log）、30 日分保持の設定。
      - LOG_DIR / LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを追加。
      - Windows / POSIX（Linux, macOS 等）差分を吸収し、"high"/"normal"/"low" をサポート。アクセス権限不足時は警告を出してスキップ。
      - set_cpu_affinity により最初の N コアにプロセスをピン留め可能。
  - ポートフォリオ構築モジュール（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順で候補を選択（同点は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額・スコア加重によるウェイト計算。全スコア 0 の場合は等配分にフォールバックして警告。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジックを実装（売却予定銘柄を除外して既存エクスポージャーを計算、"unknown" セクターは制限の対象外）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知のレジームはフォールバックで 1.0。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各 allocation_method に対応した株数決定ロジックを実装。
      - 単元株（lot_size）丸め、最大ポジション上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積）に対応。
      - スケールダウン時に端数（fractional）を考慮して残余キャッシュで単元単位追加配分するアルゴリズムを実装。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
      - データベース（PAPER_TRADING_SQLITE_PATH）から system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ等を算出。
      - P95 レイテンシ計算、閾値比較による PASS/FAIL 判定（デフォルト閾値をスクリプト内に定義: 稼働率 99%、成行成功率 90% など）。
      - --from / --to / --db オプションをサポート。
  - 研究用モジュール（部分実装）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity 設計に基づく）。モメンタム計算等の関数骨子を実装（prices_daily / raw_financials を参照）。

### Changed
- ログ・プロセス設定を統一
  - 起動スクリプトは共通の setup_logging() と set_process_priority() を呼び出すようにして起動時の挙動を整備。
- DB の扱い
  - 監視（monitoring）は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視データを一元化する設計に変更（監視の信頼性確保のため）。

### Fixed
- .env パースの堅牢化
  - export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理、空行・コメント行スキップなどのパーサーを改善して .env の安全な読み込みを実現。
- validate_config における YAML 未インストール時の挙動を改善して、PyYAML が無ければパース検証をスキップして警告出力するように変更。

### Security
- .env の生成ウィザードで生成されたファイルに関して「.env は絶対に Git にコミットしないこと」を明記（config_setup.py に注意コメントを追加）。

### Known limitations / Notes
- research/factor_research.py はファクター計算ロジックの骨子を含むが、内部の一部実装が途中（ファイル末尾が切れている）であり、追加実装・テストが必要。
- process_priority/set_cpu_affinity は権限不足やプラットフォーム差分で動作が制約されるため、環境依存の動作には注意が必要（警告出力してスキップする実装）。
- position_sizing の価格欠損時（price=0.0）に関する TODO が残っており、将来的にフォールバック価格を導入する想定。
- Paper Trading と本番 DB は分離されているが、運用時には環境変数やパス設定の確認（validate_config の実行）を推奨。

---

今後の予定（未実装 / 検討中）
- factor_research の完全実装と単体テスト
- Strategy 実装（シグナル生成）と統合テスト
- モニタリングのアラート（LINE 通知）実装の拡充
- 単体テスト・CI の追加

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）