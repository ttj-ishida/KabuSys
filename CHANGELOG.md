CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （現時点で未リリースの変更はありません。）

0.1.0 - 2026-04-13
------------------

初期リリース — コードベースから推測した主要機能・実装をまとめています。

Added
- 基本構成
  - パッケージ初期バージョンを定義（kabusys.__version__ == "0.1.0"）。
  - Settings クラスによる環境変数ベースの設定管理を追加。.env / .env.local の自動ロード機能を持ち、OS 環境変数を保護する設計（上書き制御）。
  - .env ファイルパーサの実装（クォート対応、エクスポート形式対応、インラインコメント処理）。

- 実行系 / 監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskConfig の既定パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring: SystemMonitor 用のポーリング起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視はデフォルトで本番 sqlite_path を使用する挙動を明記。
    - プロセス優先度を起動時に "high" に設定する仕組みを導入。

- データベース / 分析基盤
  - DuckDB 接続を用いたリサーチ・AI 処理基盤を追加（prices_daily / raw_financials / raw_news 等のテーブル参照を想定）。
  - monitoring 用 SQLite 初期化ユーティリティ（init_monitoring_db）。

- ポートフォリオ構築
  - portfolio_builder: シグナル選定（select_candidates）・重み計算（calc_equal_weights / calc_score_weights）を追加。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier を実装。
  - position_sizing: position サイズ計算 calc_position_sizes（risk_based / equal / score 対応、lot_size 丸め、aggregate cap スケーリング、cost_buffer 考慮）。

- リサーチ / 特徴量
  - factor_research: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算を実装。各関数は DuckDB 接続を受け取り SQL ベースで計算。
  - feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic、rank/統計 summary（factor_summary）を追加。外部ライブラリに依存せず純 Python 実装。

- AI / ニュース NLP
  - ai.news_nlp: OpenAI (gpt-4o-mini) を用いたニュースのセンチメントスコアリング機能を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ計算（UTC 変換）。
    - 銘柄ごとに記事を集約し、バッチ（最大 20 銘柄）で API に送信。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護して更新する戦略（DELETE → INSERT の局所更新）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ処理。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などの指標算出と基準値判定（PASS/FAIL）を出力。
    - DB が存在しない場合のユーザ向けメッセージ、テーブル欠落時のフォールバック（OperationalError を捕捉）を実装。

Changed
- 設計上の決定（実装により明示）
  - Paper Trading と本番 DB を明確に分離（settings.paper_sqlite_path を利用）。
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を探索して行うため、CWD に依存しない設計。
  - 環境変数の優先順位: OS 環境変数 > .env.local > .env。
  - 多くのモジュールで外部リソース（ブローカー API など）へ直接アクセスしないよう分離（研究／AI モジュールは DuckDB のみに依存）。

Fixed / Robustness improvements
- 環境・入力バリデーションの強化
  - MONITOR_POLL_INTERVAL のパースで非正数や不正文字列を検出した場合に警告を出してデフォルトへフォールバック。
  - Settings.env / LOG_LEVEL / PAPER_FILL_MODE 等のプロパティで不正値を検出すると早期に ValueError を発生させ、誤設定の早期発見を容易に。
  - _parse_env_line の改善により引用符付き値、エスケープ、export プレフィックス、インラインコメントなどを正しく扱うようにした。

- フォールバック・例外処理
  - process_priority 設定（set_process_priority / set_cpu_affinity）で権限不足や未対応プラットフォームを捕捉して警告を出すようにして安定性を向上。
  - calc_score_weights: 全銘柄スコアが 0 の場合は等分配へフォールバックして警告を出す。
  - 各種計算でデータ不足（NULL・行不足）時に None を返す等、安全な動作を担保（ファクター計算・ボラティリティ・P95 等）。
  - ai.news_nlp: API キー未設定時に ValueError を送出して明確化。API 呼び出しで失敗してもフェイルセーフで処理を継続する設計。
  - paper_verification_report: テーブルが存在しない・OperationalError が発生した場合は指標をデフォルト値（N/A 等）にフォールバック。

- 数値/丸め・キャップ処理の改善
  - calc_position_sizes: lot_size（単元株）での丸め処理、per-stock 上限・aggregate cap のスケーリング、残余キャッシュによる補正（fractional remainder に基づく追加配分）を実装し、投資額調整の再現性を担保。
  - apply_sector_cap: "unknown" セクターの扱いを明示し、既存ポジションの売却予定銘柄をエクスポージャー計算から除外。

Security
- .env ロード時に既存 OS 環境変数を保護する protected 引数を使った上書き制御を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化も可能）。
- J-Quants / Kabu API トークン等の必須変数は Settings のプロパティで require され、未設定時に明示的なエラーを出すことで誤配布のリスクを低減。

Notes / Known limitations（コードから推測）
- 一部の処理（例: price が欠損しているケース）については TODO コメントや将来的なフォールバックの検討が残っている（前日終値や取得原価のフォールバック等）。
- 単元株サイズは現状全銘柄で共通 lot_size=100 を想定しているが、将来的に銘柄別拡張が検討されている。
- ai.news_nlp の処理ログや部分失敗時の永続化ポリシーは基本設計に従っているが、運用時の監視・再実行ロジックは別途必要。

作者注
- 本 CHANGELOG は提供されたコード内容から実装意図・動作を推測して作成しています。実際のリリースノートや運用ドキュメントを作成する際は、コミット履歴・チケット等の一次情報を参照してください。