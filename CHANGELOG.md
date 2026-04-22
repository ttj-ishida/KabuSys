CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このファイルはプロジェクトの重要な変更点を記録するための要約です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除された機能
- Security: セキュリティ関連の修正や注意点

Unreleased
----------

（なし）

0.1.0 - 2026-04-22
-----------------

初回リリース — KabuSys: 日本株自動売買システムのコア機能群を提供します。主な追加点は以下の通りです。

Added
- 基本パッケージとバージョン情報
  - パッケージメタ: __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV により paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用する仕組みを実装。
    - 実行中の停止制御として data/stop_requested.flag を監視し、安全にエンジンを停止可能。
    - プロセス優先度を起動時に "high" に設定するユーティリティ呼び出しを組み込み。
    - ExecutionEngine 起動前に監視テーブル（監視用 DB）の初期化を行う（冪等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視モードは環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ (data/stop_requested.flag) を検出してループを終了。

- 設定管理・ユーティリティ
  - config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env のパースロジックが堅牢（コメント、クォート、エスケープを考慮）。
    - 環境変数に対する検査および必須鍵取得ユーティリティ（Settings クラス）。
    - 各種設定プロパティ: DB パス (duckdb/sqlite)、paper_trading 用パス、PID/kill flag 関連、閾値設定、環境 (development/paper_trading/live) 等。

  - config_setup.py
    - .env の対話的ウィザードでの作成・更新ツール。
    - デフォルト値と選択肢、シークレット入力（トークン/パスワード）対応。
    - 生成/更新した .env をファイルに保存する機能。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の有無・妥当性を検証する CLI。
    - --strict オプションで警告も失敗として扱う。
    - 本番 (KABUSYS_ENV=live) 向けに追加チェック（LINE 通知設定や Kill Switch の自動クリア設定の警告）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で銘柄選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全0時はフォールバック）。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑制するフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のレジームはフォールバック）。

  - portfolio.position_sizing
    - calc_position_sizes: リスクベース／等分配／スコア配分に基づく株数算出。単元株（lot_size）丸め、max_position / aggregate cap / cost_buffer を考慮したスケーリングロジックを実装。
    - 利用可能現金により正規化し、残余キャッシュを使った再配分アルゴリズムを実装。

- モニタリング・レポート
  - monitoring データベース初期化ユーティリティ（init_monitoring_db を経由して監視テーブルの存在を保証）。
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート出力ツール。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を出力。
    - 日付レンジ指定 (--from / --to) と DB パス指定 (--db) に対応。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数、または data/paper_trading.db。

- リサーチ / ファクター計算（骨格）
  - research.factor_research
    - モメンタム等のファクター計算方針と定数を定義。DuckDB 接続を受けて prices_daily などからファクター算出を行う設計（モメンタム計算の入口が追加）。

- 汎用ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定ユーティリティ。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションされるファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリの自動作成と失敗時のフォールバックをサポート。
    - ログレベル・ログディレクトリの解決順を明記。

  - utils.process_priority
    - cross-platform なプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値を抽象化）。
    - CPU affinity 設定のヘルパーも提供（set_cpu_affinity）。
    - psutil を利用、権限不足や未対応環境では警告ロギングで安全にスキップ。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いに配慮
  - .env 読み込み時に OS 環境変数を保護（自動上書きを制御）。
  - config_setup では .env ファイルにシークレットをプレーンテキストで保存する旨を明示（.env を Git 管理しないよう注意喚起）。

Notes / Implementation details
- DB 分離
  - paper_trading モードでは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番データと明確に分離する設計。
  - 分析用には DuckDB（data/kabusys.duckdb）を利用。

- ログと運用
  - ログは stdout へ出力することでスーパーバイザ／cron でのリダイレクト運用を想定。
  - 日次ログローテーションを 30 日保持で実装。

- 環境変数の自動ロード
  - プロジェクトルート検出が可能な場合、.env を自動で読み込む（.env.local は上書き）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- フェールセーフ
  - process_priority や CPU affinity の設定は権限やプラットフォームにより失敗する可能性があるため、安全に警告を出してスキップする実装。
  - monitoring のポーリング中に例外が発生しても例外ログを出力して次ポーリングへ継続する（監視プロセスの頑健性を確保）。

今後の予定（例示）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の計算ロジック実装完了）
- ExecutionEngine・OrderManager・RiskManager の統合テスト、及び broker 実装の追加（実ブローカーとの接続と統合）
- 単体テスト・CI の整備
- ドキュメントの充実（API ドキュメント、運用手順）

クレジット
- このリリースはリポジトリ内の各モジュール（execution, monitoring, portfolio, utils, research, tools）から構成されています。詳細な使用方法は各モジュールの docstring / CLI ヘルプを参照してください。