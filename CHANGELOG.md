# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

注: リリース日はパッケージの __version__ が "0.1.0" のため初回リリースとしてまとめています。

## [Unreleased]

（現在の開発中の変更はここに記載してください）

---

## [0.1.0] - 2026-04-19

初回公開リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

### 追加 (Added)
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite DB（data/paper_trading.db）に記録し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理。
    - 起動時にプロセス優先度を設定（High）。
  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境に関わらず本番 sqlite_path を使用。
    - 停止フラグ検知による終了処理。
- 設定・環境管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出を行い .env / .env.local を環境変数に反映）。
    - 必須/任意設定の取得ヘルパー（Settings クラス）。
    - env 値・ログレベル・PAPER_FILL_MODE 等の入力検証とデフォルト設定。
  - config_setup.py
    - .env 作成・更新のための対話型ウィザード CLI を追加。
    - J-Quants / kabu API 等の必須項目やログ設定、DB パスなどを対話的に設定・保存。
  - validate_config.py
    - .env と config/*.yaml の起動前チェック CLI。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、YAML の存在およびパース確認（PyYAML が無ければパースチェックはスキップ）。
    - --strict オプションで警告を失敗扱いにできる。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを提供。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（30 日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログ保存先を制御。ディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを追加。psutil を利用しアクセス権エラーは警告でスキップ。
- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、レジームに応じた資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）を実装。lot 単位丸め、per-stock 上限、aggregate cap によるスケーリング、手数料・スリッページ見積り用 cost_buffer などを考慮。
- モニタリング DB 初期化補助
  - monitoring/monitoring_db.py （内部参照用、init_monitoring_db を各起動スクリプトから呼び出す）
- tools
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99% 等）。
    - 日付フィルタ（--from/--to）、DB パス指定（--db）に対応。
- 研究用モジュール
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB 接続を受け取り prices_daily / raw_financials から各種ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計を追加（関数群の骨子を実装）。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### 変更 (Changed)
- 監視・実行ロジックの設計方針
  - 監視 (run_monitoring) は実行環境に関係なく「本番の監視 DB（sqlite_path）」を使用する旨を明示。実行エンジン（run_execution）は paper_trading 時に専用 DB を使用して本番 DB と分離する設計。
- .env の自動ロード順序を明確化
  - OS 環境変数 > .env.local > .env の優先順位で読み込み。テスト用に自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。

### 修正 (Fixed)
- 設定値の堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）に対し警告を出してデフォルトへフォールバックするように修正。
  - PAPER_FILL_MODE の有効値チェックを追加し、不正値時に ValueError を送出するようにした。
  - Settings.env / log_level の検証を強化して不正値を早期検出するようにした。
- ログ設定の堅牢化
  - ログディレクトリ作成失敗時にファイルハンドラ作成で例外が出ても動作を継続するよう改善（StreamHandler のみで継続）。
- DB 初期化の冪等性確保
  - Execution 起動時にも monitoring の初期化（init_monitoring_db）を呼び出し、監視テーブルが存在することを保証（冪等操作）。

### ドキュメント・使用上の注意 (Notes)
- 停止フラグ
  - 起動スクリプトはプロジェクトの data/stop_requested.flag（または Settings 経由で決まるパス）を監視し、存在を検知すると安全に停止します。運用時に手動でフラグを作成/削除して制御可能です。
- Kill Switch
  - Settings で KILL_FLAG_CLEAR_ON_START を設定すると起動時に kill フラグを自動クリアできますが、本番では 0（無効）を推奨します。validate_config.py は本番向けのガードチェックを行います。
- ログ
  - デフォルトでは logs/ ディレクトリにアプリケーションごとの日次ローテートログ（30 日保持）を保存します。環境変数 LOG_DIR や引数で変更可能。ディレクトリ作成に失敗した場合はコンソール出力のみになります。
- Paper Trading の DB 分離
  - ペーパートレードを行う場合、発注履歴・トレードログ等は data/paper_trading.db （または環境変数 PAPER_TRADING_SQLITE_PATH 指定）に保存され、本番の monitoring.db と分離されます。
- 依存
  - 一部の検証機能（config/*.yaml のパース）やプロセス管理は外部パッケージを利用（例: PyYAML, psutil）。未インストール時は該当機能が限定的になります（validate_config は PyYAML 非インストール時に YAML 内容検証をスキップ、process_priority は psutil のエラーを警告でスキップ）。

---

今後の予定:
- research/factor_research の完全実装（各因子の SQL 実装・正規化処理）
- テストカバレッジ拡充（特にポートフォリオ構築・ポジションサイズのロジック）
- 運用向けドキュメント（デプロイ手順、監視ダッシュボード、運用 runbook）の追加

もし特定のファイルや機能についてより詳細な変更点（関数単位の差分や設計意図）を記載したい場合は、その対象を指定してください。