# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルではパッケージの主要な追加・変更点を日本語でまとめています。

なお、ここに記載した内容は提供されたソースコードから推測して記載したものであり、実際のコミット履歴ではありません。

## [Unreleased]

該当なし。

## [0.1.0] - 2026-04-21

初回リリース。以下の主要コンポーネントを追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__version__ = "0.1.0"
  - 共通設定管理モジュール `kabusys.config`
    - .env/.env.local 自動読み込み（OS 環境変数を優先）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート
    - .env のパース機能（export プレフィックス、シングル/ダブルクォート、インラインコメント対応）
    - 環境変数取得ヘルパー（必須チェック、バリデーション）
    - 各種設定プロパティ（DB パス、PID ファイルパス、Kill/threshold 等）
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）
- 起動スクリプト / 実行系
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）に記録して本番 DB と分離
    - プロセス優先度設定・PID ファイル管理・停止フラグ監視を実装
    - RiskManager のデフォルト設定（max_position_pct 等）を組み立てて ExecutionEngine に注入
    - DuckDB 接続サポート（分析用）
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）
    - 停止フラグ（data/stop_requested.flag）検知でループ終了
    - 監視用 DB 接続（monitoring は環境にかかわらず sqlite_path を使用する旨の設計）
- 設定・検証 CLI
  - `kabusys.config_setup`
    - 対話式ウィザードで .env を新規作成 / 更新
    - J-Quants / kabuAPI / DB パス / LINE 設定など主要項目をサポート。シークレット項目はマスク表示
  - `kabusys.validate_config`
    - .env と config/*.yaml の事前検証 CLI
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認
    - PyYAML が無ければ YAML 検証をスキップして警告を表示
    - `--strict` フラグで警告を FAIL 扱いにできる
- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の検証レポート生成スクリプト
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計
    - 日付レンジフィルタ（--from / --to）および DB パス指定（--db）対応
    - 結果は標準出力に読みやすく整形して出力。しきい値判定（PASS/FAIL）を実装
- ポートフォリオ構築
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: スコア降順＋signal_rank ブレークで上位 N を選択
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中上限に基づく候補除外（unknown セクターは除外対象外）
    - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear、未定義は警告して 1.0 フォールバック）
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method に応じた株数決定（risk_based / equal / score）
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケーリングと余剰分の分配ロジックを実装
    - cost_buffer による保守的コスト見積もりを考慮
- ユーティリティ
  - `kabusys.utils.logging_setup`
    - 一貫したログ設定ユーティリティ（StreamHandler を stdout に、TimedRotatingFileHandler を日次ローテートで設定）
    - LOG_LEVEL / LOG_DIR による設定、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装
    - 30 日分のローテーション保存 (backupCount=30)
  - `kabusys.utils.process_priority`
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX）
    - CPU affinity 設定ヘルパー（最初の N コアに固定）
    - psutil を用いた実装で権限不足等は警告して安全にスキップ

- 研究モジュール（骨格）
  - `kabusys.research.factor_research`
    - ファクター計算方針とモメンタム等の計算関数（calc_momentum 等）の実装開始（DuckDB の prices_daily / raw_financials を参照する設計）
    - 定数・ウィンドウ設定（21/63/126/200 等）を定義

### 変更 (Changed)
- ログ出力
  - 標準出力を stdout に統一（cron / Task Scheduler のリダイレクトを想定）
- DB 利用方針
  - ExecutionEngine と Monitoring で DuckDB を分析用途として接続する設計を採用
  - Paper Trading と本番の SQLite を明確に分離（paper_trading 用 DB パスをサポート）

### 修正 (Fixed)
- 設定読み込みの堅牢化
  - .env パースでクォート内のエスケープ処理やインラインコメントの扱いを改善
  - MONITOR_POLL_INTERVAL が不正値のときは警告ログを出力してデフォルトへフォールバックする安全策を追加
- 起動停止フラグ / PID 管理
  - 起動スクリプトで停止フラグを検知した場合の安全な停止処理を追加（monitoring / execution 両方で実装）

### 注意点 / 移行案内 (Notes)
- .env
  - .env は絶対にリポジトリへコミットしないでください（config_setup から生成されるファイルにもその旨のコメントを出力）
  - 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用可能）
- 本番稼働時の注意
  - KABUSYS_ENV=live の場合、設定ミスや未設定のままだと警告・エラーを発するチェックを導入しています（validate_config を起動前に実行してください）
  - KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します（1 にすると Kill Switch が自動クリアされるため危険）
- 依存関係
  - 一部機能（YAML パース）は PyYAML に依存します。PyYAML がない場合は validate_config の YAML 検証がスキップされ警告が出ます。
  - プロセス優先度 / CPU affinity は psutil を使用します。権限不足や未対応 OS の場合は警告して処理をスキップします。

---

今後の予定（推測）
- factor_research の各ファクター実装完了（Momentum / Value / Volatility / Liquidity）
- ExecutionEngine / SystemMonitor の詳細ユニットテスト追加
- ストラテジー連携 API とシグナル生成モジュールの統合

――以上。