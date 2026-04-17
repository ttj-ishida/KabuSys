KEEP A CHANGELOG
=================

すべての重要な変更点をこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠します。  

タグ付け方針: セマンティックバージョニングに準拠します（MAJOR.MINOR.PATCH）。  

Unreleased
---------

- （なし）

[0.1.0] - 2026-04-17
-------------------

初回リリース — コア機能群の実装を含む初版。主な追加内容と挙動は以下の通りです。

added
- 基本構成・環境管理
  - Settings クラスを実装し、.env / .env.local 自動ロード機能を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパーサを強化（export 形式対応、クォート／エスケープ処理、インラインコメントの取り扱い）。
  - 各種環境変数の取得・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを実装。paper_trading 環境では paper 専用の SQLite DB を使用して本番DBと分離（デフォルト: data/paper_trading.db）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグや PID ファイルの扱いを実装。

- 監視・モニタリング
  - init_monitoring_db 呼び出しで監視用テーブルの存在を保証（冪等処理）。
  - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。

- Execution（注文エンジン）周りの骨格
  - ブローカーファクトリ（BrokerClientFactory）を使用したブローカークライアント生成。
  - OrderRepository、OrderManager、RiskManager（RiskConfig 含む）、Reconciler、ExecutionEngine の連携を想定した初期化ロジック。
  - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止する制御。

- ポートフォリオ構築 (純粋関数群)
  - portfolio_builder:
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 重み算出。score 全体が 0 の場合は警告を出して等金額配分へフォールバック。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知のレジームは警告の上 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算。単元株( lot_size ) 丸め、per-position 上限、aggregate cap（利用可能現金でスケーリング）、cost_buffer（手数料・スリッページの見積り）を考慮した安全な計算ロジックを実装。

- 研究（Research）モジュール
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB を用いたファクター計算（momentum, volatility, value）を実装。ウィンドウサイズやデータ不足時の挙動（None返却）を定義。
  - research.feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得する効率的クエリ実装。horizons 引数のバリデーションを実施。
    - calc_ic: スピアマン（ランク）IC を実装。有効レコードが少ない場合は None を返す。
    - rank / factor_summary: 同順位の平均ランク処理や基本統計量（count/mean/std/min/max/median）を実装。外部依存を避け標準ライブラリのみで実装。

- AI ニュース NLP（骨格）
  - ai.news_nlp: raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores に書き込むフローを設計・実装（バッチサイズ、トークン肥大対策、最大文字数・記事数制限、429/ネットワーク/5xx のリトライ、レスポンス検証、スコアクリップなど）。
  - calc_news_window ユーティリティを実装（JST基準ウィンドウ→UTC naive datetime）。

- ユーティリティ
  - utils.process_priority: プロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）と CPU affinity 設定のユーティリティを実装。未対応 OS や権限不足時は警告でスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを実装。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し PASS/FAIL 判定する。閾値はファイル内定数で定義（稼働率 99%、注文成功率 90% など）。

changed
- なし（初回リリース）

fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対するフォールバック処理を run_monitoring 側で実装。無効値のときは警告を出しデフォルト 60 秒を使用。

security
- OpenAI キー未設定時に明確な ValueError を返す（ai.news_nlp.score_news）。

notes / known issues
- ai.news_nlp の実装は堅牢性を考慮した設計になっているが、ソース中で一部の関数（例: _fetch_articles 以降の処理）が途中で切れているように見える箇所があるため、実行前に完全実装を確認してください。
- position_sizing 内で price が欠損（0.0）になる場合のフォールバック価格について TODO コメントあり（前日終値や取得原価を使う等の拡張検討）。
- 将来的に単元株数 lot_size を銘柄別に持たせる設計（stocks マスタに lot_size）へ拡張する旨の TODO が残っている。
- DuckDB に対する executemany の制約に留意（ai.news_nlp の DB 書き込み設計で注意点あり）。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、実行環境での動作確認が必要。

開発者向けメモ
- Settings は起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込みするため、パッケージ配布後も CWD に依存せず環境変数を適切にロードできます。
- paper_trading 環境を明確に分離しているため、バックテストや検証時に本番データを汚染するリスクを低減しています。

----- 

今後の予定（例）
- ai.news_nlp の完全実装とエンドツーエンドテスト。
- 単元株サイズの銘柄別対応、価格フォールバックロジックの追加。
- ExecutionEngine・RiskManager の追加テストと本番監査ログの強化。