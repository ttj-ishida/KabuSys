# Changelog

すべての変更は「Keep a Changelog」形式に従っています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-18

初回リリース — KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証・セットアップツール、監視/実行エンジンの骨組みを追加しました。

### 追加 (Added)
- 全体
  - パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を起点に探索）（src/kabusys/config.py）。
  - .env ファイルの自動ロード機能を実装（.env/.env.local、OS 環境変数保護対応、無効化フラグあり）。

- 設定管理
  - Settings クラスを実装（環境変数ラッパー、検証、デフォルト値の解決）（src/kabusys/config.py）。
    - J-Quants、kabuステーション、LINE、DB（DuckDB/SQLite）などの設定プロパティを提供。
    - KABUSYS_ENV の有効値検証（development / paper_trading / live）。
    - PAPER_FILL_MODE（paper trading 用の fill モード）等、いくつかの専用設定を追加。
  - 設定ウィザード CLI: .env を対話的に作成・更新するツールを追加（src/kabusys/config_setup.py）。
    - 入力候補、シークレット入力、既存 .env の読み込み・再利用、保存確認などの対話式 UX。
  - 設定検証 CLI: 起動前に環境変数や config/*.yaml の存在/基本妥当性を検査するツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML による YAML パース検証（PyYAML 未導入時は警告）、本番環境時の追加注意喚起。
    - --strict オプションで警告を失敗扱いにする機能。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組立てと起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱い。
    - スレッドで Engine を実行し、停止フラグ検知で安全に停止する制御。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを集約（設計上の注意）。
    - 停止フラグ検知でループを終了、例外発生時はロギングして次のポーリングに継続。

- ロギング / プロセス制御ユーティリティ
  - 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール（stdout）出力と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成のフォールバック、LOG_LEVEL / LOG_DIR の解決順を明示。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX(Linux/Mac/FreeBSD) の差分吸収（nice / psutil の優先度定数）、権限不足時は警告・スキップ。
    - set_cpu_affinity でプロセスを最初の N コアに固定する機能。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み（全スコアが 0 の場合は警告して等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有比率が閾値を超えるセクターの新規候補除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - 株数決定・投資上限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した発注株数計算、lot_size（単元）で丸め、per-stock 上限 / aggregate cap（available_cash）でのスケーリング処理、cost_buffer による保守的見積り、残余キャッシュによる端数配分ロジックを実装。

- 研究用 / ツール
  - ファクター計算モジュールの追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA / ATR / Liquidity 等の計算方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（関数群は実装中）。
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - DB（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の注意点 / Migration
- run_monitoring は「監視用の SQLite（monitoring.db）」について、KABUSYS_ENV に関係なく Settings.sqlite_path を使用する設計になっています。テスト・paper_trading と監視 DB を完全に分離したい場合は注意してください。
- .env の自動ロードはデフォルトで有効です。テスト実行等で自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING 環境では発注・注文のログが data/paper_trading.db に書き込まれ、本番の monitoring.db と分離されます（run_execution の挙動）。
- process_priority / cpu_affinity の設定は権限に依存します。権限不足時は警告が出て処理は続行されます。

### セキュリティ
- .env ファイルは生成時に「絶対に Git にコミットしないこと」を明記しています（config_setup の出力）。シークレット値は対話中にマスク表示されますが、ファイルにはプレーンテキストで保存されます。運用時はファイル権限に注意してください。

---

今後の予定（例）
- research/factor_research の各ファクター関数の実装完了・テスト追加
- ExecutionEngine / BrokerClient 周りのモック実装と統合テスト
- ロギングの細かなフォーマット・Structured Logging 対応検討
- ポートフォリオ計算のユニットテスト強化およびパフォーマンス改善

（以上）