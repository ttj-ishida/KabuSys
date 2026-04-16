CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティック・バージョニングに従います。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
(現時点で未リリースの変更はありません。)

[0.1.0] - 2026-04-16
-------------------

Added
- 基本プロジェクト情報
  - パッケージの初期バージョンを設定: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) を検知してループを終了。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して初期化。
    - 起動時にプロセス優先度を設定するフックを組み込み。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory により実行環境に応じたブローカークライアントを生成。
    - PID ファイル管理（data/execution.pid）と停止フラグ監視を実装。
    - エンジンを別スレッドで起動し、安全に停止するためのループを提供。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートに基づき .env/.env.local を順序付けてロード）。
    - export プレフィックス対応やクォート付き値（エスケープ処理対応）、インラインコメントの扱いなどを考慮した堅牢な .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - Settings クラスを追加し、環境変数の取得・検証を集中管理（例: KABUSYS_ENV の検証、PAPER_FILL_MODE の許容値チェック）。
    - データベースやログ関連のパス／閾値等をプロパティ経由で提供。

- モニタリング／DB 初期化
  - monitoring_db 初期化関数を利用して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順・タイブレークロジック）。
    - 等金額配分・スコア加重配分ユーティリティを実装（スコア全0時は等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有時価をもとに上限超過セクターの新規追加をブロック。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をマップ、未知レジームは警告の上でフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジック実装（risk_based / equal / score の各方式）。
    - 単元株（lot_size）での丸め、銘柄単位上限・ポートフォリオ合計のスケール調整、手数料・スリッページ見積り用 cost_buffer 対応。
    - aggregate cap 超過時のスケーリングと端数配分アルゴリズムを実装。

  - package エクスポートを整備（__all__ に主要関数を列挙）。

- 研究（Research）モジュール
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装。DuckDB 接続を受け取り SQL で計算。
    - MA200, ATR20 等の指標、データ不足時の None 戻しに対応。

  - research/feature_exploration.py
    - 将来リターン計算（複数ホライズン対応）。
    - スピアマン（ランク）に基づく IC 計算、ランク付けユーティリティ、ファクターの統計サマリーを実装。
    - 標準ライブラリのみで動作する設計（pandas 等の外部依存を避ける）。

  - research/__init__.py で主要 API を外部公開（zscore_normalize は data.stats から参照）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news テーブルを元に OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリング機能を実装。
    - 処理フロー: 時間ウィンドウ算出 → 記事集約（記事数・文字数トリム）→ バッチ（最大 20 銘柄）で API 呼び出し → レスポンス検証 → ai_scores テーブルへ安全に書き込み。
    - 再試行（429/ネットワーク/5xx 等）に対する指数バックオフ、スコアの ±1.0 クリップ、部分失敗時の既存データ保護方針などを採用。
    - API キー未指定時は明示的なエラーを返す設計。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを実装（Windows / POSIX をサポート）。
    - CPU affinity を固定する set_cpu_affinity を実装（権限不足や未対応環境では警告を出してスキップ）。
    - psutil が投げる例外に対するフォールバック（警告）を通じて安全に動作。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（CLI）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to) と DB パス指定オプション (--db) をサポート。

- DB 統合
  - DuckDB / SQLite を併用する設計を採用。DuckDB は主に時系列・研究向けデータ集計、SQLite は監視／取引ログ保存に使用。

Quality / Safety
- ロギングと例外処理を各所で強化（予期しない例外発生時のログ出力・処理継続）。
- 環境変数の検証や入力値チェックを導入し、誤設定に対する早期エラーを提供。

Changed
- 初期リリースのため変更履歴は無し。

Fixed
- 初期リリースのため修正履歴は無し。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー等の機密情報は環境変数経由で管理するよう明記。自動ロード機能は必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

注記
- ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）参照の旨がソース内に記載されており、アルゴリズム設計の根拠が補足されています。  
- 今後のリリースで、テストカバレッジ、より詳細な運用ドキュメント、エッジケース（価格欠損時のフォールバックなど）に関する改善が予定されます。