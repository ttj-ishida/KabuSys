CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning に従います。

Unreleased
----------

追加予定 / 今後の改善点（現時点での TODO / 注意点のメモ）:

- 環境変数ロード
  - .env 読み込みの堅牢化（エラー時の通知改善、読み込み順の明示的テスト追加）。
- price フォールバック
  - risk_adjustment.apply_sector_cap 内の price が欠損した場合のフォールバック（前日終値や取得原価）の実装予定（現在は TODO コメントあり）。
- 単元株対応拡張
  - position_sizing.calc_position_sizes を銘柄別 lot_size に対応する設計へ拡張予定（現在は全銘柄共通 lot_size）。
- ai/news_nlp
  - OpenAI API 呼び出しの堅牢化（追加のエラーパターン、ロギングの細分化、部分失敗時のより細かい回復処理）。
- モジュール間の統合テスト追加
  - ExecutionEngine/Monitoring/MockBroker の統合テスト整備（paper_trading と live の振る舞い検証）。

v0.1.0 - 2026-04-13
-------------------

Added
- 基本機能の初期実装（初回リリース相当）。
  - src/kabusys/__init__.py
    - パッケージ初期化、バージョン定義: __version__ = "0.1.0"
  - 環境設定管理
    - src/kabusys/config.py
      - .env 自動読み込み（.env → .env.local、OS 環境変数優先）。
      - 環境変数パース（export 付き、クォート、インラインコメント対応）。
      - Settings クラスで必要な設定（DB パス、API トークン、監視閾値、環境判定など）をプロパティ経由で提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
  - 実行・監視エントリポイント
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - プロセス優先度を高く設定してから各コンポーネントを初期化。
      - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせてセッションを実行。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority, set_cpu_affinity）。
      - 権限エラーや未対応 OS を安全にスキップする設計。
  - ポートフォリオ構築関連（純粋関数）
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates（スコア順選定）、calc_equal_weights、calc_score_weights（スコア正規化、全スコアが 0 の場合は等配分へフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes（risk_based / equal / score の allocation_method をサポート、lot_size 単位で丸め、aggregate cap によるスケールダウン実装、cost_buffer を考慮）。
    - src/kabusys/portfolio/__init__.py
      - 主要関数のエクスポートをまとめたインターフェース。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value の実装（DuckDB 接続を受け、prices_daily / raw_financials を参照）。
      - 各種ウィンドウ長や欠損時の None 扱いなど設計方針に準拠。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマン ρ）、rank、factor_summary（基礎統計量）。
    - src/kabusys/research/__init__.py
      - 研究用 API の公開。
  - AI ニュース NLP
    - src/kabusys/ai/news_nlp.py
      - OpenAI (gpt-4o-mini) を用いたニュースセンチメント評価フローの実装。
      - タイムウィンドウ計算（JST ベース → UTC 変換）、記事集約、チャンクバッチング (最大 20 銘柄)、リトライロジック、レスポンス検証、スコアクリップ、ai_scores テーブルへの置換書き込み方針。
      - OpenAI API キーを引数または OPENAI_API_KEY 環境変数から取得。未設定時は ValueError を送出。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプト。注文成功率、送信率、稼働率、レイテンシ（P95）などを抽出して判定（PASS/FAIL）。
      - DB パス指定オプション（--db）と環境変数 PAPER_TRADING_SQLITE_PATH に対応。
  - DB 初期化ヘルパ
    - src/kabusys/monitoring/monitoring_db.py を起動時に呼び出して監視テーブル存在を保証（冪等）。※ファイル参照 (import) は実装コードで使用（スナペット上は import）。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security
- 環境変数に機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY）を使用する設計。
  - Settings._require により未設定時は ValueError を送出する場所があるため、デプロイ時に .env/環境変数を適切に設定する必要があります。

Notes / Known issues
- 環境読み込み
  - プロジェクトルートの検出は .git または pyproject.toml に依存するため、配布形態によって自動読み込みがスキップされることがあります。その場合は環境変数を明示的に設定してください。
- プロセス優先度 / CPU affinity
  - 管理者権限が無い場合やプラットフォーム非対応時は警告を出してスキップします（例: psutil.AccessDenied）。
- PAPER_FILL_MODE / KABUSYS_ENV の値検証
  - 無効な値が設定されると ValueError を送出します。デプロイ設定時に注意してください。
- DuckDB executemany
  - ai/news_nlp 内のコメントにあるように、DuckDB の executemany に関するバージョン依存の制約を考慮している箇所があります。部分失敗を避けるための実装が組み込まれていますが、運用での確認が必要です。
- price 欠損の扱い
  - apply_sector_cap や position_sizing では price が欠損（0.0）だと露出過少評価やスキップに繋がる可能性がある旨の TODO が残っています。

Contributing
--------------
- Pull requests, issues, and discussions are welcome.
- 大きな変更を加える前に issue を立てて概要を共有してください。

License
-------
- プロジェクトのライセンス表記がこのリポジトリに含まれる場合はそちらを参照してください。