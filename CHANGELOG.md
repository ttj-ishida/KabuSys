CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-13
--------------------

初回リリース（初期実装）。以下の主要機能とユーティリティを追加しました。

Added
- コマンドライン起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 SQLite（monitoring DB）と DuckDB に接続し、監視 DB の初期化を行う（init_monitoring_db）。
    - check_once() 実行中の例外は捕捉してログに出力し、ループを継続する。
    - KeyboardInterrupt を考慮したグレースフルな終了処理を実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離（MockBrokerClient 想定）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動する。
    - 例外や終了時に DB 接続をクローズする処理を実装。

- 設定・環境変数管理
  - config.py に Settings クラスを追加。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - export KEY=val 形式やクォート・エスケープ、インラインコメントの扱いに対応する .env パーサを実装。
    - 各種プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / PID/KILL フラグパス / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証を実装。

- 監視関連
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を呼び出す利用箇所を追加（監視・実行両方で冪等に実行）。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加（--from / --to / --db オプション対応）。
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ 等を集計して PASS/FAIL 判定（閾値はソース内定義）。
    - P95 の算出、日付フィルタ生成、テーブル存在エラー時のフォールバック等を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順／タイブレークに基づく候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコア 0 の場合は警告して等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用。既存ポジションからセクター別エクスポージャを計算して過剰セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のマップと未知レジームのフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）へのスケーリング、cost_buffer を考慮した保守的見積り、残余配分ロジックを実装。
    - 入力欠損（価格等）時のスキップやログ出力を実装。

  - package エクスポートを追加（kabusys.portfolio の __init__）。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。アクセス権限や未サポート OS の場合は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 設定（安全なバリデーションとエラーハンドリング）。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB の SQL ウィンドウ関数を活用して各種ファクター（モメンタム、ATR、流動性、PER/ROE 等）を計算。
    - データ不足時に None を返す等、安全な実装。

  - research/feature_exploration.py
    - calc_forward_returns: 将来リターンをホライズン毎に一括取得。
    - calc_ic: スピアマン（ランク）相関による IC 計算（欠損・非有限値処理、3 件未満で None）。
    - factor_summary / rank: 基本統計量とランク付けユーティリティを実装。
    - research パッケージからのエクスポートを整備。

- ニュース NLP（AI）モジュール
  - ai/news_nlp.py
    - raw_news を集約して OpenAI API（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算 (calc_news_window)、銘柄ごとの記事トリム（最大記事数・最大文字数）、バッチ処理（最大 20 銘柄/回）、バックオフとリトライ、レスポンスバリデーション、スコアクリップ（±1.0）、部分成功時の安全な DB 更新戦略（対象コードのみ置換）を設計。
    - OpenAI API キーの解決と未設定時のエラーを実装。
    - （注）ファイルは大きな処理フローを含み、API エラー処理やログ出力が詳細に実装されている（ソースの一部は表示を省略）。

- パッケージメタデータ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初期リリースのため特記事項なし）。

Fixed
- なし（初期リリース）。

Security
- .env 自動ロード時、既存の OS 環境変数は protected として上書きされないよう設計（protected 引数）。
- OpenAI API キーが未設定の場合に明確なエラーメッセージを出力する処理を追加。

Notes / Requirements
- DuckDB, psutil, openai ライブラリ等の外部依存があるため、実行環境にそれらがインストールされている必要があります。
- 一部の振る舞い（例: MockBrokerClient の使用や BrokerClientFactory の具象実装）は設定（KABUSYS_ENV）と外部実装に依存します。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別拡張を想定した TODO を含む）。
- config.py のプロジェクトルート判定は .git / pyproject.toml を基準とするため、配布後の環境で期待通りに動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動ロードを無効化し、環境変数を明示的に設定してください。