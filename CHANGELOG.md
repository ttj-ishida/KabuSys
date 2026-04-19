# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース: 0.1.0 (初回公開)

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本 CLI/サービス起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient を利用可能にする。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用して起動する仕様。
- 環境設定・管理
  - config.py: Settings クラスを導入。環境変数の読み取り・検証、デフォルトパス（DuckDB / SQLite）や各種閾値、KABUSYS_ENV の妥当性検査を提供。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。OS 環境変数は保護される仕組みを採用。
  - .env パーサー: export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを実装。
- 設定ウィザード
  - config_setup.py: 対話式ウィザードで .env を作成 / 更新する機能を追加。シークレットは表示をマスクして扱う。保存用のテンプレート出力を実装。
- 設定検証 CLI
  - validate_config.py: 起動前に .env や config/*.yaml の設定不備を検出するツールを追加。--strict オプションで警告を失敗扱いにできる。PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ロギングユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定関数を追加。コンソール出力は stdout を使用、日次ローテーション（TimedRotatingFileHandler）でログファイルを保存。LOG_DIR / LOG_LEVEL を尊重し、ログディレクトリ作成に失敗した場合はコンソールのみで継続する。
- プロセス優先度・CPU affinity
  - utils/process_priority.py: Windows と POSIX（Linux/Mac 等）の差分を吸収してプロセス優先度設定（high/normal/low）と CPU affinity を設定するユーティリティを追加。権限不足や未対応プラットフォームでは警告を出してスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）および等配分・スコア加重（calc_equal_weights, calc_score_weights）を実装。スコア全0時は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。未知のセクターやレジームはフォールバック挙動あり。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）で丸め、aggregate cap（available_cash 超過時）のスケーリングアルゴリズムを実装。手数料・スリッページの概算バッファ（cost_buffer）を考慮。
  - portfolio/__init__.py: 上記関数群を公開（API として利用可能）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード専用 DB から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計してレポートを出力する CLI を追加。--from / --to / --db オプションで期間・DB を指定可能。基準値に基づく PASS/FAIL 判定を出力。
- 研究用モジュール（初期実装）
  - research/factor_research.py: DuckDB 接続を受けてファクター（モメンタム等）を計算するための骨格を追加（モメンタム計算関数の実装開始、設計方針・定数を定義）。

### 変更 (Changed)
- 起動時のプロセス優先度設定を各起動スクリプトの最初のステップに統一し、"high" に設定するようデフォルト化。
- ロギングの構成を統一するため、全起動スクリプトから utils.logging_setup.setup_logging を呼び出す設計に統一。

### 修正 (Fixed)
- run_execution.py:
  - ペーパートレード環境では本番 DB と完全分離して paper_sqlite_path（デフォルト data/paper_trading.db）を使用するように明示。
  - 停止フラグ (data/stop_requested.flag) を検知した場合の挙動（起動抑止・実行スレッドの安全停止）を実装。
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）を検出してデフォルトにフォールバックする処理を追加し、警告ログを出力するようにした。
  - 停止フラグ検出時に安全にループを抜けて DB 接続をクローズするようにした。

### 仕様上の注意点
- Settings.require により、J-Quants や kabuAPI の必須環境変数が未設定の場合は起動時に例外を送出する仕様。
- .env の自動ロード順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local は .env を上書き可能。
- logging_setup はログディレクトリ作成に失敗した場合でもコンソール出力は継続するよう耐障害性を確保。
- portfolio モジュールの一部は設計に基づくフォールバックや TODO コメントを含む（例: price 欠損時のフォールバック戦略、将来的な lot_size マスターへの拡張）。

### 既知の制限 / TODO
- research/factor_research.py は実装途中の関数があり、完全なファクター計算ロジックは引き続き実装が必要。
- price 欠損時の扱い（セクターエクスポージャー計算や position sizing の price フォールバック）は暫定実装。将来的に前日終値や取得原価での補完を検討。
- position_sizing の lot_size は現在全銘柄共通固定。将来的に銘柄別単元対応へ拡張予定。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity）
- モニタリング DB schema と init_monitoring_db の公開 & ドキュメント拡充
- テストカバレッジの拡充、CI での静的解析導入

---