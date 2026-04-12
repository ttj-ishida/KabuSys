# CHANGELOG

すべての重要な変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、項目はソースコードの内容から推測して記載しています。実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- 次回リリースに向けた変更はここに記載されます。

## [0.1.0] - 2026-04-12
初回公開リリース（推定）。自動売買システムのコア機能、監視、研究・ポートフォリオ構築、Paper Trading 向けツール、AI ニューススコアリング等を含む。

### Added
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の SQLite DB を使用し、MockBrokerClient と分離して実行できる実装を含む。起動時にプロセス優先度を設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きに対応（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する旨を実装。
- 設定管理
  - kabusys.config.Settings: 環境変数読み込みを中心にした設定モジュールを実装。`.env` / `.env.local` の自動読み込み機能を備え、OS 環境変数を保護する仕組み（protected set）を採用。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって無効化可能。
  - .env パーサー: クォート、エスケープ、export プレフィックス、インラインコメントなどに対応した堅牢なパーサーを実装。
  - 多数の設定プロパティを追加（DB パス、PID/KILL フラグパス、閾値、ログレベル、env 判定、Paper Trading 関連設定など）。
  - PAPER_FILL_MODE の入力検証を実装（許容値: "instant", "partial", "never", "reject"）。
- モニタリング DB 初期化
  - init_monitoring_db を起動スクリプトから呼び出して監視用テーブルの存在を保証（冪等）。
- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder: BUY シグナルの候補選定（score 降順／signal_rank タイブレーク）、等重配分、スコア加重配分を実装。スコア全てが 0 の場合は等金額配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有を考慮して候補を除外）、市場レジームに応じた投入倍率（bull/neutral/bear）を実装。
  - portfolio.position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）、単元株丸め、個別・合算上限（max_position_pct / max_utilization）、コストバッファを考慮したスケーリングと残差処理を実装。
- 研究（Research）モジュール
  - research.factor_research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）。200日移動平均や ATR20、価格/財務データ結合による PER/ROE などを計算。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを実装。標準ライブラリのみで実装し、horizons の検証を行う。
  - research パッケージ内で zscore_normalize を外部モジュール（kabusys.data.stats）から再エクスポート。
- AI ニュース NLP スコアリング
  - ai.news_nlp: raw_news を元に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む仕組みを実装。
    - 前日 15:00 JST 〜 当日 08:30 JST のタイムウィンドウを正しく計算。
    - 銘柄ごとに記事を集約、トークン肥大化対策（記事数・文字数上限）を実装。
    - 最大 20 銘柄/チャンクでバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの JSON バリデーション、スコアの ±1.0 クリップ、部分的失敗時のテーブル更新保護（対象コードのみ DELETE→INSERT）などの堅牢化を導入。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、PASS/FAIL 判定（閾値あり）で結果を標準出力に出力する。
  - P95 計算、DB 存在チェック、テーブル欠損時の安全ハンドリング（OperationalError 捕捉）を実装。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定（Windows / POSIX の差分吸収）、CPU affinity 設定関数を追加。対応 OS 以外では警告を出してスキップし、権限不足等の例外を安全にハンドリング。

### Changed
- DB 分離の方針を明確化
  - Paper Trading 実行時は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）を使用し、本番監視 DB と完全分離する設計に変更。
  - 監視用スクリプトは環境にかかわらず本番用 sqlite_path を使用する明確な挙動を追加（監視データは本番 DB に保存）。
- 環境変数読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込み。`.env.local` は既存の OS 環境を上書き可能だが、protected set により OS のキーは上書きされない。
- run_* スクリプトで起動直後にプロセス優先度を設定するように統一。
- 多くの関数で入力検証や None 値処理、境界条件（データ不足時の None 応答）を厳格化。これにより上位呼び出しは例外ではなく None や空集合で扱えるように安定化。

### Fixed
- 環境変数パースの不備対応
  - export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等を正しく扱うよう修正し、.env の誤読による設定不整合を防止。
- MONITOR_POLL_INTERVAL の処理を堅牢化
  - 0 以下や整数以外の値を与えた場合にデフォルト（60 秒）にフォールバックし、警告ログを出力するように変更（time.sleep に渡す不正値による ValueError 回避）。
- process_priority の例外処理
  - psutil による優先度/affinity 設定で権限不足や未サポート機能が発生しても警告ログを出して処理を継続するように変更。
- report ツールの堅牢性
  - paper_verification_report は DB ファイルが見つからない場合やテーブル欠損時にエラーを出力／回避して安全に終了するようにした。
- research モジュールの SQL 実装でデータ不足時に None を返すようにして上位処理の例外発生を防止。
- portfolio.position_sizing のスケーリングロジックで合計コストが available_cash を超えた場合の丸め/残差処理を追加し、単元株（lot_size）に基づく再配分ロジックを改善。

### Security
- OpenAI API キーの取り扱い
  - ai.news_nlp.score_news は引数 api_key または環境変数 OPENAI_API_KEY の両方をサポート。未設定時は明確な ValueError を発生させる（誤動作を防止）。

### Notes / Known limitations
- portfolio.position_sizing のコメントで示したように、価格が欠損（0.0）の場合にエクスポージャーや発注量が過少評価される可能性がある。将来的に前日終値や取得原価をフォールバック価格として扱う改善を予定。
- ai.news_nlp は OpenAI レスポンスのフォーマットに依存（厳密な JSON を要求）。外部 API の仕様変更により破壊的影響を受ける可能性あり。
- process_priority の機能は OS と実行権限に依存するため、すべての環境で同一の効果を保証するものではない。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。差異や追加のリリース情報がある場合は、実際のコミットログ／リリースノートを参照してください。