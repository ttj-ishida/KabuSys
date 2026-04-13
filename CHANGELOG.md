CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日はコードベースから推測して設定しています。

[Unreleased]
------------

- （現時点のコードベースでは未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 初期リリース。以下の主要機能・モジュールを追加。
  - 実行・監視関連
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading 用 DB を分離して利用する（KABUSYS_ENV=paper_trading の場合は専用 MockBrokerClient を対象）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用。
    - プロセス優先度設定ユーティリティを起動時に呼び出し（高優先度に設定を試みる）。
  - 設定管理
    - config.Settings クラスを実装。.env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。環境変数の検証・取得用ユーティリティを提供（必須変数チェック、列挙型検証、パスの展開等）。
    - .env パーサで export 形式、クォート文字、エスケープ、インラインコメントの取り扱いを実装。既存 OS 環境変数を保護する仕組みを導入。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順、タイブレーク）、等重み・スコア重みの計算。
    - portfolio.position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケール調整、手数料/スリッページ用バッファ考慮。
    - portfolio.risk_adjustment: セクター集中上限チェック（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier）。
  - 研究・ファクター
    - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け、prices_daily / raw_financials を参照）。MA200 や ATR、各種リターン等を算出。
    - research.feature_exploration: 将来リターン計算（horizons 指定可）、IC（スピアマンランク相関）計算、ランク付けユーティリティ、ファクター統計サマリー。
    - research パッケージの公開 API を整備（zscore_normalize の再エクスポート等）。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄別センチメントスコアを ai_scores テーブルに書き込む処理を実装。時間窓の計算、チューニング（記事数・文字数上限）、バッチサイズ、429/ネットワーク/5xx に対する指数バックオフでのリトライ、レスポンスバリデーション、スコアクリップなどを実装。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。期間指定 (--from/--to) や DB パス指定 (--db) に対応。稼働率・注文成功率・送信率・レイテンシ（P95）等を算出し、PASS/FAIL 判定を出力する。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。権限不足や未対応 OS の場合は警告を出してスキップする安全策を実装。
  - DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を起動時に呼び、監視用テーブルが存在することを冪等に保証（run_execution/run_monitoring に統合）。
  - パッケージ管理
    - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため過去変更なし）

Fixed
- 設定・運用上の堅牢化を実施（実装上の注意点・フォールバック処理を導入）。
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出し、デフォルト値にフォールバックする処理を追加。
  - PAPER_FILL_MODE の検証を追加（有効値のみ許容し、不正値は ValueError を送出）。
  - KABUSYS_ENV / LOG_LEVEL の検証を追加（不正な値は ValueError）。
  - .env の読み込みで OS 環境変数を保護する protected 機構を導入し、.env.local での上書きをサポート。
  - DuckDB/SQLite 接続の明示的クローズを常に行うようにしてリソースリークを防止。
  - news_nlp: OpenAI API キー未指定時は明確な ValueError を出す処理を追加。
  - paper_verification_report: DB ファイルが存在しない場合のメッセージと早期リターンを実装。テーブル欠如（OperationalError）に対するフォールバックを実装して壊れにくくした。

Security
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。OS 環境変数は上書き保護される設計を採用。
- OpenAI API キーは環境変数 OPENAI_API_KEY を期待（news_nlp で未設定の場合は明示的なエラー）。API キーの扱いは外部に依存するため、さらに安全に扱う運用を推奨。

Notes / Implementation details
- 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計（監視は本番 DB を監視する意図）。
- 実行（run_execution）は paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全に分離。
- research モジュールは DuckDB を用いて SQL + Python のハイブリッドで大規模データ集約処理を行う設計。外部 API に依存しない純粋分析処理を意図。
- position_sizing の aggregate cap 処理は lot_size（単元株）単位で切り下げ・残余配分を行い、再現性のため安定ソートを用いる。
- ai.news_nlp は出力 JSON の厳密性を前提としており、不正応答や部分失敗時のデータ保護（DELETE→INSERT の範囲限定）を考慮している。
- Paper Trading 検証ツールは閾値（稼働率 99%、注文成功率 90% 等）をコード内定義し、簡易的な PASS/FAIL 判定を行う。

今後の見込み（推測）
- 単体テスト・統合テストの追加、CI パイプライン統合。
- 銘柄別単元情報（lot_size）や複数手数料モデルへの対応（position_sizing 拡張）。
- OpenAI 呼び出しのより細かなエラーハンドリング・メトリクス収集。
- DuckDB スキーマ（prices_daily, raw_financials, raw_news, ai_scores 等）のドキュメント整備。

----------------------------------------
この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートに合わせて調整してください。