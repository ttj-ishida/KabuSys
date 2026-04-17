CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
本ファイルは Keep a Changelog のフォーマットに準拠します。

フォーマット:
- Unreleased: 次回リリースに向けた保留中の変更
- バージョン付きセクション: リリース済みの変更（リリース日付を併記）

Unreleased
---------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本的な自動売買システム KabuSys を追加
  - パッケージ初期版として以下の主要機能を実装。
- 実行・監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、モックブローカーを利用して本番 DB と分離。
    - スレッドでエンジンを起動し、data/stop_requested.flag による外部停止と実行中の安全な停止処理を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は安全にデフォルトへフォールバック。
    - 監視は本番 sqlite_path を常に使用（環境変数に依らず本番 DB に記録する設計）。
- 設定管理
  - src/kabusys/config.py
    - .env 自動ロード機能（.env、.env.local）を実装。OS 環境変数の保護（上書き防止）に対応。
    - .env の行パーサを独自実装（export 構文、クォート、インラインコメント、エスケープ処理に対応）。
    - 多数の設定プロパティを提供（DB パス、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証、監視しきい値など）。
- ポートフォリオ構築モジュール
  - src/kabusys/portfolio/*
    - 銘柄選定・重み付け（select_candidates、calc_equal_weights、calc_score_weights）。
    - リスク制御（apply_sector_cap、calc_regime_multiplier）。
    - ポジションサイズ計算（calc_position_sizes）：単元株丸め、リスクベース／ウェイトベース配分、aggregate cap スケーリング、コストバッファ考慮。
- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を DuckDB 経由で実装。prices_daily / raw_financials に基づく純粋関数群。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算、IC（Spearman）算出、ランク関数、統計サマリーを標準ライブラリのみで実装。
- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に保存する処理を実装。
    - バッチ送信（最大 20 銘柄）、トークン肥大対策（記事数・文字数制限）、レスポンス検証、スコアクリップ、リトライ（指数バックオフ）などフェイルセーフを考慮した設計。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度（Windows の優先度クラス、POSIX の nice 値）設定。CPU affinity 設定ユーティリティも追加。権限不足等の失敗は警告で安全に無視。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト。期間指定で稼働率、注文成功率、送信率、レイテンシ等を集計し、PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- DB 初期化
  - 監視用テーブルの初期化を行う init_monitoring_db を run 系スクリプトが起動時に呼び出す（冪等に保証）。

Changed
- 初期リリースとして多数の設計決定を明確化
  - 監視（monitoring）は環境に関わらず本番 DB に記録する設計（運用上の注意点）。
  - .env 自動読み込みはデフォルトで有効。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD が利用可能。

Fixed
- 環境変数や外部条件の不備に対して安全にフォールバックする実装
  - MONITOR_POLL_INTERVAL の不正値はログを出してデフォルト値を使用。
  - PAPER_FILL_MODE の不正値は明示的に検証してエラーを投げる（誤設定の早期検出）。
  - process_priority, set_cpu_affinity は権限不足や未サポート環境で失敗しても例外を投げず警告ログでスキップ。

Security
- OpenAI API キーの取り扱い
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合に ValueError を送出し、明示的なキー指定を必須化。

Notes / Breaking changes
- run_monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用するため、テスト・paper_trading 環境で実行する際は DB パスに注意してください。
- PAPER_TRADING_SQLITE_PATH を指定することで paper_trading 用 DB を切り替え可能（run_execution は環境が paper_trading の場合に専用 DB を使用）。

内部設計メモ（参考）
- DuckDB を analytics / research 用の内部テーブル参照に使用。SQL ウェイト処理と Python 結合でファクターやレポートを生成する設計。
- 多くの関数は副作用なし（純粋関数）を心がけ、テスト容易性を重視。
- 単体テストやマイグレーション・運用スクリプトは本リリースには含まれていません。必要に応じて別途追加予定。

--- 
（以上）