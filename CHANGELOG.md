# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回リリース。KabuSys 自動売買フレームワークの基盤機能を追加しました。

### 追加
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合に MockBrokerClient を利用し、Paper Trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用する仕組みをサポート。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority 経由）。
    - duckdb / sqlite の接続確立、監視用テーブルの初期化（init_monitoring_db）を行う。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止。PID ファイル管理（data/execution.pid）。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知時に Engine.stop() を呼んで終了する。

  - システム監視（モニタ）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルにデータを書き込む設計。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - 例外はログに出力して次のポーリングへ継続。

- 設定管理・ウィザード・検証
  - 設定読み込み/管理モジュールを実装（src/kabusys/config.py）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - .env パースは export 形式、クォート・エスケープ、行末コメント処理に対応。
    - Settings クラスを提供し、各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE の検証、paper_sqlite_path 等）を型変換やバリデーション付きで取得可能。
    - 環境（KABUSYS_ENV）やログレベル等の検証を行うプロパティを実装。

  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を初期作成/更新。複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）をサポート。
    - 既存 .env の読み込み、値のマスク表示（シークレット項目）、保存確認、ファイル出力機能を実装。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）を実行。
    - --strict オプションで警告を失敗扱いにできる。

- ログ・プロセスユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順、既存ハンドラのクリアなどを実装。
    - ログディレクトリ作成が失敗した場合はファイル出力をスキップしてコンソールのみで継続。

  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。psutil を利用。アクセス権限が不足する場合は警告でスキップ。
    - CPU affinity を指定コア数に固定する機能を提供（未指定時は何もしない）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレーク条件で候補を上位 N 件に選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック且つ warning ログ）。

  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補の除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear, 未知は 1.0 にフォールバック）。

  - 取付株数算出・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash を超えた場合のスケーリング）による再配分、残差処理を実装。
    - 手数料・スリッページ考慮用 cost_buffer、価格欠損時のスキップ処理、ログによる診断情報。

  - パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- 分析・ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - データベース（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）の trade_logs / system_status / risk_logs から指標を集計。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等。
    - Pass/Fail 基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）し、判定ロジックとレポート出力を実装。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

- 研究用ファクター計算（初期）
  - ファクターモジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - モメンタム / ボラティリティ / 流動性 / バリュー等の指標計算方針と定数を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（詳細実装は継続中）。

- 監視用 DB 初期化（参照）
  - run scripts・execution scripts から監視テーブルの存在を保証するための init_monitoring_db 呼び出しを組み込み（モジュールは別箇所に実装済みと想定）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制約 / 注意点
- .env 自動読み込みはプロジェクトルートが検出できない場合にスキップされる。テスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
- process_priority / cpu_affinity の設定はプラットフォームや実行権限に依存し、失敗した場合はログ警告で継続する設計。
- price が欠損（0.0）の場合、リスク計算やエクスポージャー算出が過少評価される可能性がある旨をログと TODO にて明示（将来の拡張でフォールバック価格を導入予定）。
- research モジュールは DuckDB / テーブルスキーマに依存するため、本番データに合わせた整合が必要。

---

今後の予定例:
- research/factor_research の完全実装（SQL クエリと出力フォーマットの完成）
- ExecutionEngine / BrokerClient の詳細実装と統合テスト
- 単体テスト、CI 設定、型チェック強化
- ドキュメント（アーキテクチャ、運用手順、デプロイ手順）の整備

（以上）