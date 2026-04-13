# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した変更履歴です（実装・設計上の注記や既知の TODO も含みます）。

最新: 0.1.0 — 2026-04-13
----------------------

### Added
- 初期リリース: KabuSys 基本機能を実装
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み合わせてセッションを実行。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority.set_process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（既定 60 秒）。不正な値や 0 以下は警告を出してデフォルトへフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を参照する挙動を採用。
    - duckdb 接続も初期化し、監視用テーブルを整備。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
    - 複雑な .env 行パーサを実装（export 形式、クォート内エスケープ、インラインコメント処理などに対応）。
    - Settings クラスに各種プロパティを実装（DB パス、PID ファイル、監視閾値、ログレベル、env 判定、paper_trading 関連設定等）。
    - `PAPER_FILL_MODE` のバリデーション（有効値："instant"|"partial"|"never"|"reject"）。
- ポートフォリオ構築コンポーネント（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を実装。スコア全て 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャーを計算して上限を超えるセクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）を実装（"bull":1.0, "neutral":0.7, "bear":0.3）。未知のレジームは 1.0 でフォールバックし警告を出す。
    - apply_sector_cap に価格欠損時の注意点（TODO: 前日終値等のフォールバック導入）がコメントとして記載。
  - portfolio.position_sizing
    - allocation_method に応じた株数決定ロジックを実装（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め処理、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer を用いた保守的なコスト見積もりをサポート。スケーリング時の残差処理は lot 単位で安定的に配布するアルゴリズムを実装。
    - 将来の拡張を見越した設計メモ（銘柄毎の lot_size を導入する TODO）。
- 監視・ユーティリティ
  - utils.process_priority
    - Windows と POSIX（Linux/Mac/FreeBSD）での優先度設定を吸収。nice 値や Windows の優先度クラスを使用。
    - CPU affinity 設定関数 set_cpu_affinity を追加（指定コア数でプロセスピン留め）。
    - 権限不足や未対応プラットフォームについては警告を出して安全にスキップする。
- 研究（Research）モジュール（DuckDB を用いたファクター計算 / 特徴量解析）
  - research.factor_research
    - Momentum / Volatility / Value ファクターを DuckDB SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 各関数は prices_daily / raw_financials テーブルを参照し、データ不足時は None を返す仕様。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - 外部依存を避け標準ライブラリのみで実装（pandas 未使用）。
- AI ニュース NLP
  - ai.news_nlp
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄単位のセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込むワークフローを追加。
    - バッチ処理（最大 _BATCH_SIZE=20）、1 銘柄あたりのトークン肥大化対策（最大記事数・最大文字数制限）、レスポンス検証、スコアクリッピング（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（上限 _MAX_RETRIES）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示的に要求。
    - ニュース収集ウィンドウの計算ユーティリティ（calc_news_window）を実装（JST 時刻を基準に UTC に変換）。
    - executemany 前に params が空でないことを確認する注意書き（DuckDB の制約）を実装/記載。
- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプトを実装。CLI から期間指定（--from/--to）や DB パス（--db）を受け取り、システム稼働率・注文成功率・送信率・P95 レイテンシ等を算出して人間向けレポートを出力。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - SQLite のテーブル欠如時に安全に N/A を返すフォールバックを実装。
- パッケージエクスポート
  - portfolio / research の主要ユーティリティを __all__ を通してエクスポート。

### Changed
- 設定の自動ロードはデフォルトで有効。テスト等で無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` フラグを追加（既存環境変数を保護する挙動により、OS 側の設定を上書きしない）。
- run_monitoring におけるポーリング例外処理を強化。monitor.check_once() 内の予期しない例外を捕捉してループ継続（ログ出力して次のポーリングへ）。

### Fixed
- 環境変数読み込みパーサで以下を扱うよう改善
  - export KEY=val 形式のサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォートなし値に対するインラインコメントの厳密判定（直前がスペース/タブの場合のみコメントとする）
- MONITOR_POLL_INTERVAL の不正入力（0 以下や非整数）に対して警告を出し、time.sleep に渡すと ValueError を起こす値を防ぐフォールバック処理を追加。

### Known issues / TODO
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小見積もられてしまい、結果的にブロックが緩くなる恐れあり。将来的に前日終値や取得原価でフォールバックする拡張を検討中（コード内に TODO コメントあり）。
- position_sizing:
  - 現状は全銘柄共通の lot_size（既定 100）で丸めを行う。将来的に銘柄別 lot_size を保持するマスタ導入を検討（TODO コメント）。
- ai.news_nlp:
  - OpenAI レスポンスの検証を厳格に行っているが、部分失敗発生時は成功分のみ ai_scores を置換する挙動（DELETE WHERE date=? AND code=ANY(codes) → INSERT）を採用しており、部分的にロールバックされる可能性に注意。
- DuckDB の executemany による制約に注意（空パラメータでの実行を避ける実装を行っているが、環境差異がある場合の確認を推奨）。

### Security
- .env 自動読み込み時に OS 環境変数は上書きしない（protected set を使用）ことで、デプロイ環境の環境変数が意図せず書き換えられるのを防止。

参考: 主要実装ファイル
- src/kabusys/config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/portfolio/*
- src/kabusys/research/*
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

今後のリリースでは以下を目標に改良予定:
- 銘柄別 lot_size 対応、価格フォールバックの改善、AI バッチの部分失敗に対するより堅牢なトランザクション戦略、単体テストの追加と CI ワークフロー整備。