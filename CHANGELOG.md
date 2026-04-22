# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトは現在セマンティックバージョニングを使用しています。

## [Unreleased]

- 表示上の未リリース項目はありません。

## [0.1.0] - 2026-04-22

初回リリース — KabuSys 自動売買フレームワークの基本機能を実装しました。主な追加点と注意点は以下の通りです。

### 追加 (Added)

- 全体
  - パッケージの初期バージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - duckdb / sqlite を用いたデータ保存基盤の統合（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。

- 起動スクリプト / デーモン
  - 実行エンジン起動スクリプト (run_execution.py)
    - ExecutionEngine の起動ロジックを実装。バックグラウンドスレッドでエンジンを実行し、停止フラグ (data/stop_requested.flag) を監視して安全に停止。
    - 環境が `paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル出力の仕組み（data/execution.pid を利用）に対応。
  - 監視ループ起動スクリプト (run_monitoring.py)
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用する設計。
    - 停止フラグ検知による安全終了処理および例外ハンドリングを実装。

- 設定管理・CLI
  - Settings クラス (config.py)
    - 環境変数 / .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 各種設定プロパティ（J-Quants トークン、kabu API 情報、DB パス、Paper Trading 用設定、監視閾値、環境種別検証など）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの妥当性チェック）。
  - 環境設定ウィザード CLI (config_setup.py)
    - 対話式で .env を初期作成 / 更新するウィザードを提供。デフォルト値・選択肢・シークレット入力に対応。
  - 設定検証 CLI (validate_config.py)
    - 起動前に必須環境変数や config/*.yaml の存在・パース検査を実行する CLI。--strict オプションで警告を失敗扱いに可能。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定 (utils/logging_setup.py)
    - stdout に出力する StreamHandler と 日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順とハンドラ再設定による二重出力防止に対応。
  - プロセス優先度・CPU affinity 設定 (utils/process_priority.py)
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority を実装。
    - CPU affinity を固定する set_cpu_affinity を提供（アクセス権限・プラットフォーム非対応時は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算 (portfolio/portfolio_builder.py)
    - select_candidates: スコア降順＋タイブレークによる候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の実装（全スコアが 0 の場合は等金額にフォールバック）。
  - セクター制約・レジーム乗数 (portfolio/risk_adjustment.py)
    - apply_sector_cap: 既存保有を考慮したセクター集中上限チェック（unknown セクターは除外しない）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - 発注株数決定・制約適用 (portfolio/position_sizing.py)
    - calc_position_sizes: risk_based / equal / score 各方式に対応。
    - 単元株（lot_size）での丸め、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと端数配分ロジックを実装。

- 研究・ツール
  - ファクター計算モジュールの骨子 (research/factor_research.py)
    - Momentum, Value, Volatility, Liquidity を想定した設計。DuckDB を用いた計算方針と定数を定義。
    - calc_momentum の実装を開始（ファイル末尾で途中までの状態になっているため後続実装が必要）。
  - Paper Trading 検証レポート (tools/paper_verification_report.py)
    - ペーパートレード用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を出力する CLI。
    - 閾値を定義し（例: 稼働率 >= 99%、P95 <= 200 ms 等）、PASS/FAIL 判定を行う。
    - --from / --to / --db オプションを提供。DB 存在チェックや SQL の存在チェック（テーブル無ければ N/A を扱う）に対応。

### 変更 (Changed)

- 初期リリースのため該当なし。

### 修正 (Fixed)

- 初期リリースのため該当なし。

### 注意事項 / 既知の問題 (Notes / Known issues)

- research/factor_research.py の calc_momentum はファイルの最後で途中（start_da で切れている）になっており、モメンタム計算ロジックの完全実装が未完です。研究機能の完全利用には追加実装が必要です。
- apply_sector_cap 内の価格欠損時の挙動については TODO コメントあり（価格欠損 = 0 の場合エクスポージャー過小見積の可能性）。将来的に前日終値等のフォールバックを導入することを推奨します。
- process_priority.set_cpu_affinity / set_process_priority はプラットフォーム依存のため、権限不足や未対応環境では警告が出て設定をスキップします。期待する優先度適用のためには実行環境の権限確認が必要です。
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml が存在すること）。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- Paper Trading と本番 DB は設計上分離されていますが、運用時は環境変数（KABUSYS_ENV, PAPER_TRADING_SQLITE_PATH 等）を適切に設定してください。

### マイグレーション / 設定ガイド (Migration / Configuration)

- 起動前に .env（または .env.local）を用意してください。config_setup.py にて対話式に作成可能です。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨: validate_config.py を使って設定検証を行ってください。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR 環境変数で変更可能。
- MONITOR_POLL_INTERVAL で監視ポーリング間隔を秒単位で指定できます（正の整数、デフォルト 60）。0 以下や不正値はデフォルトにフォールバックします。

---

脚注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際の設計意図や未公開のモジュール（execution 内の各コンポーネント等）に関しては実装ドキュメントを参照してください。