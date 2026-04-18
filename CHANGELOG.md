# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠します。

最新更新: 2026-04-18

## [0.1.0] - 2026-04-18

### 追加
- コア初期リリース（基本機能群を追加）。
- 環境・設定管理
  - env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数は保護）。
  - .env パーサーを強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理に対応）。
  - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供（J-Quants トークン、kabu API、DB パス、ログレベル、監視閾値など）。
  - PAPER_FILL_MODE の検証ロジックを追加（有効値チェック）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - プロジェクトルート特定は .git または pyproject.toml を基準に探索（CWD 非依存）。

- 設定ユーティリティ / CLI
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）。既存値の読み込み、シークレット扱い、選択肢・デフォルト、.env 書き出しをサポート。
  - 設定検証 CLI（python -m kabusys.validate_config）を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェック（PyYAML がある場合はパース検証）。
    - --strict オプションで警告を FAIL として扱う。
    - live 環境向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。

- 起動スクリプト
  - 実行エンジン起動スクリプト: run_execution.py を追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離（ドキュメント化）。
    - ブローカークライアント生成（BrokerClientFactory）と ExecutionEngine の組み立て、Thread ベースでの run_session 起動、停止フラグ監視（data/stop_requested.flag）を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト: run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値・0 以下はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - 停止フラグによる安全終了、check_once() 呼び出し時の例外を捕捉してログ出力。

- ロギング / プロセス制御ユーティリティ
  - 統一ログセットアップ関数 setup_logging を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力（30 日分保持）。
    - LOG_DIR / LOG_LEVEL の優先解決、ハンドラ二重設定防止、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）。
    - stdout を利用する理由（タスクスケジューラ等での扱い易さ）を明記。
  - プロセス優先度・CPU affinity ユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - Windows と POSIX を吸収する実装。権限不足や未対応 OS の場合は警告でスキップ。
    - 起動スクリプトで優先度を "high" に設定する呼び出しを追加。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates: スコア降順・タイブレークに signal_rank を利用。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap: 既存ポジションを集計してセクター上限を超える場合に候補を除外（unknown セクターは無視）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは警告して 1.0 にフォールバック。
  - ポジションサイジング（position_sizing）
    - calc_position_sizes: allocation_method による株数計算を実装（"risk_based" / "equal" / "score"）。
    - lot_size（単元株）で丸め、1 銘柄上限（max_position_pct）や投下上限（max_utilization）を考慮。
    - aggregate cap（合計投資額が利用可能現金を超える場合）のスケールダウンと残差処理（lot 単位で追加配分）を実装。
    - price 欠損時のスキップとログ出力、将来的なフォールバック注記を含む。

- リサーチ
  - factor_research モジュール（ファクター計算）を追加（モメンタム / MA / ATR / ボリューム等の定義および calc_momentum の部分実装）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針を採用。
    - （注意）ファイル末尾で calc_momentum の実装途中で切れているため、継続実装が必要。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 期間フィルタ（--from / --to）と --db オプションをサポート。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、リスク却下数、API レイテンシ（avg/max/P95）。
    - 判定基準（しきい値）を定義し、PASS/FAIL を出力するレポートを標準出力に生成。

- パッケージ化
  - パッケージの __version__ を "0.1.0" として定義。

### 変更
- 監視起動動作に関するドキュメント注記
  - run_monitoring.py のドキュメントに「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」旨を明記（運用上の注意）。

### 修正（挙動上の保護・堅牢性向上）
- 環境読み込み時に OS 環境変数を上書きしてしまわないよう保護セットを導入（_load_env_file）。
- .env パーサーの厳密化（引用符内エスケープやコメントの扱い）により実運用時の誤読を低減。
- setup_logging: ログディレクトリ作成失敗時もアプリが継続するようフォールバックを実装。
- process_priority / set_cpu_affinity: 権限不足や未対応プラットフォーム時に例外を握りつぶして警告ログに留めるようにして起動の安定性を改善。
- run_execution/run_monitoring: 停止フラグファイル（data/stop_requested.flag）による安全停止を追加。

### 既知の制限・注意点
- factor_research.calc_momentum の実装が途中で終了しているため、ファクター計算の完全実装は次リリースで対応予定。
- run_monitoring は明示的に本番 sqlite_path を参照するため、開発環境で監視 DB を分離したい場合は運用上の対応が必要。
- paper_trading 環境は発注関連をモックしている前提のため、本番系の API キーやパスワードの取り扱いに注意。

---

今後の予定（例）
- factor_research の完全実装（Momentum の続き、Value/Volatility/Liquidity の集約）。
- 単体テストと CI 設定の追加。
- ExecutionEngine / Broker のドキュメント追記とエンドツーエンドテスト。
- リリースノートの細分化（バグ修正・パフォーマンス改善ごとの記載）。

（この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴に基づく正式な変更履歴は別途生成してください。）