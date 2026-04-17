# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ 以下はリポジトリ内のコード内容から推測して作成した変更履歴です。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-17

初回リリース。本バージョンで導入された主な機能・改善点・修正は以下のとおりです。

### Added
- 実行エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて本番/ペーパートレード用の SQLite を使い分け、BrokerClientFactory を介してブローカークライアントを生成。スレッドでエンジンを起動し停止フラグで安全に終了できる仕組みを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能、停止フラグ検知でループ終了。
- 設定管理
  - config.py: .env / .env.local の自動ロード（OS 環境変数優先、.env.local は上書き）と、厳密なパース・バリデーションを実装。必須環境変数取得用のヘルパーと各種設定プロパティを提供（DB パス、PAPER_FILL_MODE、KABUSYS_ENV など）。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア順ソート）、等金額・スコア加重の重み計算を実装。スコアが全て 0 の場合は等金額フォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告の上フォールバック。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数計算（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position と aggregate の上限、投下資金スケーリング、cost_buffer を用いた保守的コスト見積りをサポート。
- リサーチ／ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB 上の prices_daily/raw_financials テーブルから実行する関数を実装（MA200, ATR20, PER/ROE 等）。
  - research/feature_exploration.py: 将来リターン算出、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを実装。標準ライブラリのみで完結する設計。
  - research/__init__.py: 利便性のためのエクスポートを追加。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を元に OpenAI API（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込むロジックを実装。処理ウィンドウ計算、記事トリム、バッチング、リトライ（429/5xx/ネットワーク）や JSON バリデーション、スコアクリッピングを備える設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL 判定を出力。CLI オプションで期間指定と DB パス指定が可能。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定のユーティリティを追加。未対応 OS や権限不足時は警告を出して安全にスキップする実装。

### Changed
- 実行／監視の DB ポリシー
  - 監視(run_monitoring)は KABUSYS_ENV に関係なく本番 sqlite_path を使用するよう明示（監視データは本番 DB に格納する方針）。
  - 実行(run_execution)は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
- .env の取り扱い
  - config.py の自動ロード順は OS 環境変数 > .env.local > .env。環境変数で自動ロード無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）が可能。
  - .env パーサーは export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントの扱いに対応し堅牢性を向上。
- ロバスト性向上
  - 多くの処理でデータ欠損時のフォールバック（例: ファクター計算で行数不足時は None を返す、position sizing で価格が欠損する銘柄はスキップ）を追加。
  - AI ニューススコア処理は API キー未設定時に ValueError を投げ、API エラーはリトライのうえフェイルセーフで継続する設計。

### Fixed
- スコア重み計算
  - calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出すよう修正（数値ゼロ割回避）。
- ポジションサイズ調整
  - aggregate cap スケールダウン時の丸め・残差配分ロジックを実装して単元株制約（lot_size）を満たす分配を行うよう改善。
- プロセス優先度設定の失敗安全化
  - set_process_priority / set_cpu_affinity で権限不足や未実装例外をハンドルし、ワーニングでスキップするように修正。

### Documentation / Misc
- パッケージメタ
  - __init__.py によるバージョン定義 (__version__ = "0.1.0") と主要モジュールのエクスポートを追加。
- モジュール内ドキュメント
  - 各モジュールに設計方針・使用上の注意・参照ドキュメント（PortfolioConstruction.md 等）を記載して可読性を向上。

### Known issues / TODO
- ai/news_nlp.py は複雑なワークフローを実装しているが、実際の API 呼び出し周りや執筆時点でのマイナーな未実装・例外ケースの追加テストが必要。  
- position_sizing の price 欠損時のフォールバック（前日終値等）について注記があり将来的対応を予定。  
- DuckDB 側のテーブル存在チェック／スキーマ変化に対する追加の堅牢化テストが望まれる。

---

（以上）