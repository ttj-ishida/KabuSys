# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。主要リリースはセマンティックバージョニングに準拠しています。

## [0.1.0] - 2026-04-17

初回公開リリース。コア機能（実行エンジン、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ、ツール類）を実装しました。

### Added
- 全体
  - 初期バージョンを定義（kabusys.__init__.__version__ = "0.1.0"）。
  - Settings インスタンスを提供する設定管理モジュールを追加（src/kabusys/config.py）。プロジェクトルート自動検出と .env/.env.local の自動ロード機能を備え、環境変数の保護（OS環境変数の上書き防止）に対応。
- 実行 / エンジン
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBroker を使った完全分離のペーパートレード運用をサポート。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせてエンジンを起動（デーモンスレッド）。停止フラグ・PID 管理に対応。
    - RiskManager 用の初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）を導入。
- 監視
  - SystemMonitor ポーリング起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 監視は実運用の sqlite_path（monitoring DB）を使用する設計。
    - 停止フラグファイル存在検知による安全終了。
- ポートフォリオ構築
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレーク実装
    - calc_equal_weights / calc_score_weights: 等金額・スコア重み算出（スコア合計ゼロ時のフォールバックあり）
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中禁止ロジック apply_sector_cap（現保有と当日売却予定を考慮）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）に対応した株数決定
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装
    - スケールダウン時に端数を lot 単位で再配分するアルゴリズムを導入（残差順に追加配分）
- リサーチ
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB を用いた prices_daily / raw_financials 参照）
    - 200日移動平均、ATR、出来高系・流動性指標、PER/ROE などを計算
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装
    - Pandas など外部ライブラリに依存しない実装
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）
- ニュースNLP（AI）
  - ニュース記事を用いたセンチメントスコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - OpenAI（gpt-4o-mini）をバッチ呼び出しして銘柄ごとのスコア（-1.0〜1.0）を生成し ai_scores テーブルへ書き戻す設計。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行う calc_news_window。
    - バッチサイズ、文字数上限、記事数上限、リトライ（429/ネットワーク/5xx）・指数バックオフ、レスポンス検証、スコアクリッピングを実装。
- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収した set_process_priority（high/normal/low）、set_cpu_affinity を実装。Unsupported OS や権限不足時は警告を出してスキップ。
- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から安定性（稼働率）、注文成功率、送信率、P95 レイテンシなどを計算して PASS/FAIL 判定を行う CLI。
    - 基準値（稼働率 99%、成立率 90% 等）を設定。DB 存在チェックや SQLite の OperationalError に対するフォールバック処理を実装。
- その他
  - packages の __all__ を整備（portfolio / research）。

### Changed
- 環境変数の扱い（src/kabusys/config.py）
  - .env/.env.local のロード順を OS 環境変数 > .env.local > .env として明確化。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など入力値検証を実装し、不正値時に ValueError を投げるようにした。
- 監視と実行の DB の取り扱いを明示
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用（監視データは環境依存にしない方針）。
  - run_execution は paper_trading 環境で専用 paper_sqlite_path を使用するよう変更（本番 DB と完全分離）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値処理（src/kabusys/run_monitoring.py）
  - 0 や負数、非整数の環境変数が指定された場合にデフォルトにフォールバックし、警告ログを出力するように修正（time.sleep での例外回避）。
- .env ファイル読み込み時のエラー取り扱い（src/kabusys/config.py）
  - ファイルオープン失敗時に警告を出力して処理を継続するように改善。
  - .env 行パーサーでクォート内のエスケープ処理やインラインコメントの取り扱いを適切に処理するよう実装。
- calc_score_weights のゼロスコア対処（src/kabusys/portfolio/portfolio_builder.py）
  - 全銘柄のスコア合計が 0 の場合は等金額配分へフォールバックし、警告を出すようにした。
- calc_regime_multiplier の未知レジーム対処（src/kabusys/portfolio/risk_adjustment.py）
  - 未知レジーム文字列が与えられた際に警告を出力しデフォルト 1.0 でフォールバックするよう修正。
- process_priority の例外安全化（src/kabusys/utils/process_priority.py）
  - 権限不足や未実装の API による例外（AccessDenied, AttributeError, NotImplementedError）を捕捉して警告を出し、処理を継続するようにした。
- feature_exploration.rank の同順位処理改善
  - 浮動小数点丸め（round(v, 12)）を導入して ties の検出漏れを防止し、同順位は平均ランクを返す実装にした。
- paper_verification_report の堅牢化（src/kabusys/tools/paper_verification_report.py）
  - データ不足やテーブル欠如時に OperationalError をハンドリングして、レポート生成が致命的に失敗しないように改善。
  - P95 計算、日付フィルタ生成、フォーマット関数を追加。

### Removed
- 該当なし（初回リリース）

### Security
- OpenAI API キーの必須化（src/kabusys/ai/news_nlp.py）
  - score_news 呼び出しで api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合は ValueError を送出して明示的に失敗させる。

---

今後の予定（短期）
- docs/ に API 仕様・運用手順書を追加
- テスト（ユニット / 統合）の整備と CI パイプライン導入
- ニュースNLP の部分実行時の部分的ロールバック・リトライ戦略の拡張
- 銘柄別 lot_size を導入するための stocks マスタ対応

もし特定ファイルの変更点や実装意図について詳細な説明が必要でしたらお知らせください。