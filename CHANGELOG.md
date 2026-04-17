# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお本文は与えられたコードベースから機能・振る舞いを推測して作成しています。

## [Unreleased]
- 追加
  - ニュースNLPモジュールの実装を追加（ai/news_nlp.py）。
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとにセンチメントスコアを ai_scores テーブルへ書き込む処理フローを実装。
    - バッチサイズ、トークン肥大対策、エクスポネンシャルバックオフ等の仕組みを導入。
    - 出力バリデーションとスコアの ±1.0 クリップを実装。
  - 研究・分析機能（research）を追加。
    - ファクター計算: モメンタム・ボラティリティ・バリュー（calc_momentum, calc_volatility, calc_value）。
    - 特徴量探索: 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）。
  - ポートフォリオ構築関連の純粋関数を追加（portfolio パッケージ）。
    - 候補選定/重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - 銘柄ごとの発注株数決定（calc_position_sizes）。risk_based / equal / score の配分方式に対応し、単元株（lot_size）や aggregate cap、cost_buffer による保守的見積もりを実装。
  - 実行・監視用起動スクリプトを追加。
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用して本番 DB と完全分離。Broker クライアント生成、OrderManager／RiskManager／Reconciler 組み立て、スレッドでのエンジン実行と停止フラグ監視を実装。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。停止フラグ検出や例外ハンドリングを含む。
  - ユーティリティを追加 / 強化
    - 環境設定読み込み（config.py）:
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装し、.env / .env.local の自動読み込み（OS 環境変数を保護）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
      - .env パーサは export プレフィックス、クォート（シングル/ダブル）・バックスラッシュエスケープ、行内コメントの扱い等に対応。
      - 各種設定プロパティを用意（DB パス、paper_trading 用パス、PAPER_FILL_MODE、PID/KILL フラグ、閾値等）と入力検証。
    - プロセス優先度・CPU affinity 設定ユーティリティ（utils/process_priority.py）。
      - Windows / POSIX の差分を吸収してカレントプロセスの優先度設定（high/normal/low）と CPU affinity 設定を提供。権限不足や未サポート環境では警告を出してスキップする安全設計。
  - ツールスクリプトを追加
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・API レイテンシ（P95）などを集計し、PASS/FAIL を表示する。閾値は定数で分かりやすく定義。
  - パッケージ初期化
    - kabusys.__init__ にバージョン定義（__version__ = "0.1.0"）とエクスポート宣言を追加。

- 仕様上の注意
  - 実行・監視スクリプトは「停止フラグファイル（data/stop_requested.flag 等）」を監視して安全に停止することを想定。
  - Monitoring は実行環境に関わらず本番 sqlite_path を使用する実装（監視データは常に本番 DB に記録）。
  - Paper Trading は paper_sqlite_path（デフォルト data/paper_trading.db）を使って本番とデータ分離されるよう設計。

## [0.1.0] - 2026-04-17
- 追加
  - 初期リリース相当の機能群を追加（上記 Unreleased の多くを含む）。
    - Execution / Monitoring の起動スクリプト
    - 環境設定自動読み込みと Settings API
    - Portfolio（候補選定、重み付け、位置サイズ、セクター制限、レジーム乗数）
    - Research（ファクター計算、将来リターン、IC、統計サマリ）
    - ツール: Paper Trading 検証レポート
    - ユーティリティ: process_priority（優先度・affinity）
    - AI ニューススコアリング基盤（OpenAI 経由でセンチメント取得）
- 変更
  - なし（初期リリース）
- 修正
  - なし（初期リリース）
- 既知の制限 / TODO
  - position_sizing.calc_position_sizes:
    - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる可能性があり、将来的には前日終値や取得原価によるフォールバックを検討する旨の TODO コメントあり。
  - ai/news_nlp.py:
    - OpenAI 呼び出し周りはリトライやレスポンス検証等を設けているが、実運用での API キー・レート制限、コストやモデル差異に留意すること。
  - DuckDB 関連:
    - executemany 前にパラメータが空でないことを確認する等、DuckDB のバージョン固有制約へ配慮した実装が含まれる。
  - 一部ファイルは実装途中で切れている（与えられたコード断片のため）。実運用前に完了確認を推奨。

## 参考（重要な環境変数）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが設定検証あり）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。不正値は警告してデフォルトにフォールバック。
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB パス（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper トレードの fill モード（instant|partial|never|reject）
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス
- OPENAI_API_KEY: ニュースNLP の OpenAI API キー
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを抑止するために 1 を設定

---

この CHANGELOG はコードベースのコメント・実装内容から推測して作成しています。実際のコミット履歴やリリースポリシーに基づく変更履歴が必要な場合は git の履歴情報を基に追記・修正してください。