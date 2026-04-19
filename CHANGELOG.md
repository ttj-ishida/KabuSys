# Keep a Changelog
すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog を準拠します。  

安定性の目安: 0.1.0 は最初の公開リリース（アルファ/初期安定性）相当のバージョンです。

## 未リリース
- 開発中の改善・リファクタリング、テスト拡張、factor_research の完成などを予定。

---

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーション骨組みを追加。
  - パッケージ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。プロセス優先度を high に設定して起動。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite DB（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全分離。
    - BrokerClientFactory を使ってブローカークライアントを作成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで run_session を実行。data/stop_requested.flag を検知すると安全に停止。
    - 実行時の PID ファイルを data/execution.pid に書き込む想定（設定で上書き可）。
    - デフォルトの RiskManager 設定をコード内に組み込み（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB を別環境に分離しない設計）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 例外はログに残して次ポーリングまで継続する耐障害性を備える。
- 設定管理・ユーティリティ
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートが見つかれば .env → .env.local の順で読み込み。OS 環境変数は保護）。
    - _find_project_root により __file__ を起点にプロジェクトルート（.git または pyproject.toml）を探索するため、CWD に依存しない読み込み。
    - Settings クラスを導入し、各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値, KABUSYS_ENV, LOG_LEVEL 等）をプロパティとして提供。妥当性チェックあり。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）を実装。
  - config_setup.py
    - .env の対話式ウィザードを実装。既存値の読み込み、シークレット入力、選択肢提示、保存機能を提供。
    - .env ファイルへ書き出すテンプレートと説明を生成。
  - validate_config.py
    - 起動前チェック CLI を実装。必須環境変数未設定、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）などを実行。
    - --strict オプションで警告も失敗扱いにする機能を提供。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する setup_logging を実装。
    - LOG_LEVEL の解決順（引数 > 環境変数 > デフォルト）とログディレクトリ解決順（引数 > LOG_DIR > デフォルト "logs/"）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - set_process_priority(level) で Windows/Linux/macOS の差を吸収して現在プロセスの優先度を設定（psutil を利用）。set_cpu_affinity を提供。
    - サポートされない OS やアクセス権限不足時は警告ログを出してスキップする耐障害性を実装。
- ポートフォリオ構築（純関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates（score 降順、同点は signal_rank 昇順でタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして warning）
  - portfolio/risk_adjustment.py
    - apply_sector_cap（同一セクターの既存保有比率が閾値を超える場合、新規候補を除外。unknown セクターは除外しない）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" 対応。未知は 1.0 にフォールバック）
    - デフォルト max_sector_pct は 0.30。
  - portfolio/position_sizing.py
    - calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based のベース計算、等配分・スコア加重での配分、lot_size 単位で丸め、ポートフォリオ全体の aggregate cap によるスケールダウンロジックを実装。
    - デフォルトパラメータ: risk_pct=0.005, stop_loss_pct=0.08, max_position_pct=0.10, max_utilization=0.70, lot_size=100, cost_buffer=0.0。
    - スケールダウン時は小数部の大きい順に lot 単位で追加配分する再現性ある割当ロジックを実装。
- 監視・モニタリング関連
  - monitoring_db/init_monitoring_db（参照される初期化関数を呼び出す実装をスクリプトで利用）
  - run_monitoring/run_execution により監視テーブルの存在を保証する init_monitoring_db の呼び出しを行う（冪等）。
  - duckdb を解析・データ保管用途に利用するため両スクリプトで DuckDB 接続を確立。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計して検証レポートを生成する CLI を実装。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を集計。
    - デフォルト合否基準: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - --from / --to / --db オプションをサポート。
- 研究モジュール（初期実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを実装（Momentum / Value / Volatility / Liquidity）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - 一部定数と関数シグネチャを定義（例: calc_momentum）。（実装途中箇所あり）

### 変更 (Changed)
- なし（初版公開）

### 修正 (Fixed)
- なし（初版公開）

### その他 / 注意事項 (Notes)
- .env 自動ロードはデフォルトで有効。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- config_setup により生成される .env はセキュリティ上、絶対に Git にコミットしないことを README 等で明記する必要あり（ファイルヘッダに注意喚起を含む）。
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（0 や非整数）な場合、デフォルト 60 秒にフォールバックして警告ログを出力する。
- ロギングは stdout を第一に使う設計（cron 等で stdout へリダイレクトしやすくするため）。ログファイル出力が失敗した場合でもアプリは継続動作するようにしている。

### 既知の未実装 / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題に対するフォールバック（前日終値や取得原価など）を未実装。
- position_sizing: 将来的に銘柄ごとの lot_size をサポートする設計拡張を検討中（現状は共通 lot_size）。
- research/factor_research の一部関数が未完（ファイル末尾が途中の状態）。追加実装とユニットテストが必要。
- 一部の外部モジュール（例: PyYAML）が存在しない環境での挙動は validate_config で警告しスキップする設計だが、CI やデプロイ時の依存関係明示が推奨される。

---

連絡・貢献:
- バグ報告や改善提案は issue を立ててください。主要な設計方針（特に本番環境の安全ガード、Kill Switch の扱い）については慎重なレビューをお願いします。