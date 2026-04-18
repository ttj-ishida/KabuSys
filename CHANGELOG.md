CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

フォーマット:
- Unreleased: 現在進行中の変更
- バージョン見出しは [x.y.z] - YYYY-MM-DD

Unreleased
----------
- なし

[0.1.0] - 2026-04-18
-------------------
Added
- 基本アーキテクチャと主要コンポーネントを実装し、初期リリースとしました。
  - 実行系 / 監視系起動スクリプト
    - run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合に専用の Paper Trading 用 SQLite（data/paper_trading.db）を使用するよう分離。
      - BrokerClientFactory を用いたブローカークライアント生成を追加（環境に応じて Mock 実装を使用）。
      - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止を監視。
      - 起動時にプロセス優先度を "high" に設定する処理を追加。
      - 起動時に監視テーブルが存在することを保証するため init_monitoring_db を呼び出す。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
      - 監視は実行環境にかかわらず本番 sqlite_path を使用する設計。
      - stop フラグ（data/stop_requested.flag）でループを安全に終了。
      - monitor.check_once() の例外をハンドルして次サイクルへフォールバック。
  - 設定管理
    - config.py
      - 環境変数/`.env` の自動ロード（.env, .env.local の優先度ルール）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可。
      - .env パースの強化（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
      - Settings クラスを導入し、各種設定値（DB パス、LINE トークン、KABUSYS_ENV 等）をプロパティとして提供。入力検証を行う（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
      - paper_trading 用の PAPER_TRADING_SQLITE_PATH および PAPER_FILL_MODE サポート。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI を追加。既存 .env 読み込み、シークレットマスク表示、保存前確認などを実装。
    - validate_config.py
      - 起動前に必須環境変数や path、config/*.yaml の存在を検証する CLI を追加。
      - --strict モードで警告を失敗扱いにできる。
      - PyYAML 未導入時は YAML 検証をスキップし警告を出す設計。
  - ロギング／プロセス制御ユーティリティ
    - utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定する共通ユーティリティを追加。
      - 既存ハンドラのクリア処理を行い二重設定を防止。
      - LOG_DIR / LOG_LEVEL の解決ロジックを提供。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - utils/process_priority.py
      - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限や未対応プラットフォームは警告でスキップ）。
  - ポートフォリオ構築モジュール
    - portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等加重 (calc_equal_weights)、スコア加重 (calc_score_weights; スコア合計が 0 の場合は等配分へフォールバック) を実装。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap と市場レジームに応じた資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバック）。
    - portfolio/position_sizing.py
      - risk_based / equal / score の配分方式に対応した株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を用いた保守的コスト見積りを実装。
  - 研究用 / ユーティリティ
    - research/factor_research.py（ファクター計算基盤）
      - Momentum, Value, Volatility, Liquidity 等のファクター計算を行うためのモジュール骨格を追加（DuckDB を利用して prices_daily / raw_financials を参照する方針）。
    - tools/paper_verification_report.py
      - Paper Trading の検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を出力する。
      - デフォルト DB パスは data/paper_trading.db。--db, 環境変数で上書き可能。
  - パッケージ管理
    - __init__.py にバージョン (__version__ = "0.1.0") と主要サブパッケージの __all__ を設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues
- research/factor_research.py がソース途中で切れている箇所があり（ファイル末尾に未完のコード断片を検出）、ファクター計算の一部実装は継続作業が必要です。
- 一部モジュールは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。環境にない場合は該当機能の一部が制限される点に注意してください（validate_config は PyYAML 未導入時に YAML 検証をスキップ）。
- PAPER_FILL_MODE 等の設定値や KABUSYS_ENV の設定ミスは起動時に例外を投げるため、config_setup や validate_config の活用を推奨します。

開発者向けメモ
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。パッケージ配布後も CWD に依存せず動作するよう設計されています。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合は標準出力のみになります。
- run_monitoring は常に本番用 sqlite_path を使用する設計（監視データは実環境の状態を反映するため）。
- run_execution は paper_trading 時に本番 DB と完全分離された紙芝居用 DB を使用します。

---
この変更履歴はコードベースの現状から推測して作成しています。実際のコミット単位や追加の変更点がある場合は適宜更新してください。