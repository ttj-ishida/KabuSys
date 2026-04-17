# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

なお、この CHANGELOG はソースコードの内容から推測して作成したものであり、実際のリリースノート作成時は必要に応じて適宜修正してください。

## [0.1.0] - 2026-04-17

初回リリース — 基本的な自動売買プラットフォームのコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、設定管理ツール類、および検証レポートツールを含みます。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `__version__ = "0.1.0"` として定義。
- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定（DBパス、APIトークン、監視閾値、環境種別など）を取得可能。
  - 自動 .env ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を読み込み、OS 環境変数を保護する挙動を採用。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パースの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメント処理（スペース前の `#` をコメントとみなす等）
  - 各種プロパティと入力検証（`PAPER_FILL_MODE` の有効値チェック、`KABUSYS_ENV`/`LOG_LEVEL` の妥当性チェック等）を実装。
- 設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式に `.env` を作成/更新するウィザードを提供（`--env-file` オプション対応）。シークレット値はマスク表示。作成テンプレートの書き込みロジックを実装。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須環境変数やパス、config/*.yaml の存在・パース検証、KABUSYS_ENV=live 時の追加ガード等を実行。`--strict` オプションで警告を FAIL 扱いにできる。
  - PyYAML 未導入時は YAML 検証をスキップし警告を出す設計。
- 実行エンジン起動スクリプト
  - `kabusys.run_execution` を追加。以下の要点を含む:
    - プロセス優先度を High に設定する起動フロー。
    - `paper_trading` 環境時は paper 専用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離。
    - `BrokerClientFactory` によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築して起動。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 関連等）を設定例として組み込み。
    - 停止フラグ（data/stop_requested.flag）による安全停止機構。実行中スレッドの監視と停止処理を実装。
- 監視ループ起動スクリプト
  - `kabusys.run_monitoring` を追加。以下の要点を含む:
    - プロセス優先度を High に設定。
    - 監視は環境にかかわらず本番（sqlite_path）を使用して監視情報を記録する旨の動作（環境分離しない設計）。
    - `MONITOR_POLL_INTERVAL` 環境変数によりポーリング間隔を上書き可能。デフォルト 60 秒。無効値はログ出力してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。例外発生時にもログ出力して次のポーリングに遷移する堅牢化。
    - DuckDB 接続を併用している点を明示。
- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用して監視用テーブルの冪等初期化を行う（実行開始時の保証）。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を追加:
    - set_process_priority(level) — Windows と POSIX（Linux/Mac等）で差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) — カレントプロセスを先頭 N コアに固定するユーティリティ。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップする設計。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates (スコア降順選定)
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコアが 0 の場合はフォールバックで等金額配分）
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap（セクター集中制限。既存保有時価を考慮して候補除外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数。bull/neutral/bear のマッピングと未知レジームのフォールバック）
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes（allocation_method に応じた株数計算: risk_based / equal / score）
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap のスケーリング、cost_buffer による保守的見積もり、残余キャッシュを使った端数配分アルゴリズムを実装。
  - これらはすべて副作用のない純粋関数として実装（DB 参照なし）。
- 研究用ファクター計算
  - `kabusys.research.factor_research` を追加:
    - DuckDB を使ったファクター計算（モメンタム: 1M/3M/6M、MA200乖離、ボラティリティ: ATR20、流動性指標等）。
    - 計算用のスキャンウィンドウや NULL/データ欠損時の扱い（十分なウィンドウがない場合は None を返す）を考慮。
- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加:
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力。
    - CLI オプションで期間を指定可能（--from / --to）および --db で DB パス上書き可。
    - 判定基準（閾値）を定義して PASS/FAIL を出力。P95 計算ユーティリティを内蔵。
- その他
  - 各種スクリプトに `if __name__ == "__main__": main()` を整備して CLI 実行をサポート。
  - ロギング出力は基本 INFO レベルで初期化される（スクリプト側で logging.basicConfig を呼び出す）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Known behaviour
- run_monitoring は監視データの記録に settings.env に関わらず本番 sqlite_path を使用する設計となっているため、テストやペーパートレード環境で運用する場合は注意が必要です。
- process_priority の設定は権限やプラットフォームに依存するため、失敗時は警告ログを出して処理を継続する安全設計です。
- .env の自動ロードはプロジェクトルートが特定できない環境（パッケージ配布後など）ではスキップされます。
- Paper Trading 用データベースが存在しない場合、検証レポートはエラーメッセージを出力して終了します。

---
参照: ソース内の docstring・コメントおよび設定項目に基づき作成。必要に応じて各項目の詳細（例: RiskManager のパラメータ説明や SQL スキーマ）を追加してください。