CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （今後の変更をここに追加してください）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回リリースを作成。
- 実行系 / 監視系のエントリポイントを追加:
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（MockBrokerClient を含む想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、非正の値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db 等）を使用。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理モジュールを追加:
  - kabusys.config.Settings
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env / .env.local の読み込み順序と上書きルール（OS 環境変数の保護）。
    - export 形式やクォート・インラインコメントを考慮した .env パース実装。
    - 各種設定プロパティ（データベースパス、PID ファイル、監視閾値、PAPER_FILL_MODE 検証、KABUSYS_ENV 検証など）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。

- ポートフォリオ構築関連モジュールを追加:
  - kabusys.portfolio.portfolio_builder
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - kabusys.portfolio.position_sizing
    - 株数決定ロジック calc_position_sizes（risk_based / equal / score の allocation_method、lot_size、コストバッファ、aggregate cap のスケーリング、端数処理）。
  - 上記をまとめてエクスポートするパッケージ kabusys.portfolio。

- リサーチ / ファクター計算モジュールを追加:
  - kabusys.research.factor_research
    - momentum / volatility / value の各ファクター計算（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - MA200, ATR20, 1M/3M/6M リターン等を算出。データ不足時に None を返す安全設計。
  - kabusys.research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ。
    - pandas 等に依存せず標準ライブラリ + DuckDB による実装。
  - 上記をまとめてエクスポートする kabusys.research（zscore_normalize をデータ統計ユーティリティからインポートして公開）。

- AI / ニュース NLP スコアリングを追加:
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini を想定）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ格納。
    - ニュースウィンドウの定義（JST 基準で前日 15:00 〜 当日 08:30 を UTC に変換して使用）。
    - バッチサイズ、最大記事数・文字数制限、JSON Mode の期待出力、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップを実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- 監視・検証用ツールを追加:
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプト（コマンドライン実行可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - PASS/FAIL の閾値を設定（稼働率 >= 99%、fill >= 90% 等）し、期間指定（--from/--to）での集計出力を行う。
    - DB 存在チェックやテーブル未存在時のフェールセーフを実装。

- ユーティリティを追加:
  - kabusys.utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収。権限不足や未対応 OS では警告を出してスキップ。

- パッケージメタデータ:
  - kabusys.__init__.__version__ を "0.1.0" に設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取り扱いは環境変数経由を想定。未設定時は明示的にエラーを返す。

Notes / Implementation details
- DuckDB を分析用データベース（prices_daily, raw_financials 等）として広範に利用。各ファクター・リサーチ関数は DuckDB 接続を引数で受け取り副作用を持たない純粋関数的な設計を目指しています。
- .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントなど多くのケースを扱えるよう実装されています。
- paper_trading モードでは paper_trading 用 DB を使用することで本番データと完全に分離する設計です。
- 一部関数は将来的な拡張（銘柄ごとの lot_size マスタや価格フォールバック等）をコメントで想定しています。

開発者向け/運用メモ
- MONITOR_POLL_INTERVAL に 1 未満（0 や負数）を設定すると警告を出してデフォルト 60 秒にフォールバックします。
- PID / kill flag パスや監視閾値は Settings で環境変数から簡単に上書きできます。
- OpenAI 呼び出しはバッチ処理・リトライを行いますが、API のレート制限やコストに注意してください。

[参照]
- プロジェクトバージョン: kabusys.__version__ = 0.1.0