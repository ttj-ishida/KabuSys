# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
リリースはセマンティックバージョニングを想定しています。

※ 注: この CHANGELOG は与えられたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

- ドキュメント更新やマイナー調整（未リリースの変更点をここに記載してください）。

---

## [0.1.0] - 2026-04-19

初期リリース。自動売買システム KabuSys のコアユーティリティ、実行・監視用スクリプト、ポートフォリオ構築ロジック、設定管理ツール、検証ツール類を提供します。

### 追加 (Added)
- 基本パッケージ定義
  - パッケージバージョンを `__version__ = "0.1.0"` として公開（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラスによる環境変数ラッパーを実装（src/kabusys/config.py）。
    - J-Quants や kabuステーション、データベースパス、監視しきい値などをプロパティ経由で取得可能。
    - 環境種別（KABUSYS_ENV）の検証と補助プロパティ（is_live / is_paper / is_dev）を提供。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）の検証。
    - paper_trading 用 DB パス指定（PAPER_TRADING_SQLITE_PATH）。
  - .env の自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml が基準）。
    - .env と .env.local の読み込み優先度管理、OS 環境変数保護（上書き防止）をサポート。
    - 行パーサは export 形式、クォート文字列、エスケープ、インラインコメントの取り扱いに対応。

- 対話式設定ウィザード
  - .env を対話的に作成/更新する CLI（src/kabusys/config_setup.py）。
    - 項目定義・既存値の読み込み・保存機能を提供。
    - デフォルト値・選択肢・シークレット入力・確認プロンプトをサポート。

- 設定検証 CLI
  - 起動前の設定検証ツール（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの存在チェック（親ディレクトリ）、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギングユーティリティ
  - 統一的なログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーへ設定。
    - LOG_DIR/LOG_LEVEL の優先解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

- プロセス優先度／CPU affinity ユーティリティ
  - Windows/Linux/macOS の差を吸収する set_process_priority / set_cpu_affinity（src/kabusys/utils/process_priority.py）。
    - Windows 用の優先度定数と POSIX の nice 値をマッピング。
    - 設定失敗時は警告を出して安全にスキップ。

- 実行エンジン起動スクリプト
  - ExecutionEngine 起動用スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV により paper_trading の場合は paper 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory を利用したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動ロジック。
    - 停止フラグ（data/stop_requested.flag）検知によるグレースフル停止、PID ファイル管理の想定。
    - RiskManager 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を構成し、初期資金は broker.get_available_cash() による。

- 監視プロセス起動スクリプト
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop_requested.flag による停止、例外発生時のログ出力と次回ポーリング継続。

- ポートフォリオ構築ライブラリ
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates (スコア降順、同点は signal_rank でタイブレーク)
    - calc_equal_weights、calc_score_weights（全スコア0のケースで等分配にフォールバック）
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別比率に基づき新規候補を除外（"unknown" セクターは対象外）
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に基づく乗数（未知値は 1.0 でフォールバックして警告）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" に対応
    - lot_size（単元株）丸め、1銘柄上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を使った保守的見積もり、端数処理の再配分ロジックを実装

- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計してレポート出力。
    - 各種閾値を定義して PASS/FAIL を判定（例: 稼働率 >= 99%、P95 <= 200 ms など）。
    - 日付フィルタ、P95 計算、DB が存在しない場合のエラーメッセージ。

- 研究用ファクター計算の雛形
  - factor_research（src/kabusys/research/factor_research.py）の冒頭実装（モメンタム/MA/ATR/出来高等の計算方針と定数定義）。DuckDB を想定した prices_daily/raw_financials 参照方式。

### 変更 (Changed)
- なし（初期リリース）。ただし各モジュールは堅牢性向上のため入力検証・フォールバックの挙動を整備。

### 修正 (Fixed)
- なし（初期リリース）。コード内に無効な設定値や例外発生時の警告・例外ハンドリングが追加され、実運用時の安全弁が強化されている（例: MONITOR_POLL_INTERVAL の不正値対処、ログディレクトリ作成失敗時のフォールバック、プロセス優先度設定失敗時の警告）。

### セキュリティ (Security)
- 機密トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存する想定で、config_setup はシークレット項目をマスクして表示（保存時も平文のまま .env に書くため .env の取り扱いに注意することを明記）。

---

履歴の解釈についてご要望があれば、例えば「各リリースの細かい差分をコミット履歴ベースで生成する」「日付を変更する」「Unreleased を詳細化する」など対応します。