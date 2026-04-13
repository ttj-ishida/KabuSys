# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

---

## [Unreleased]

- ドキュメント化・リファクタ予定:
  - news_nlp.score_news の部分的エラーハンドリングと書き込みロジックの堅牢化（チャンク単位の部分更新戦略の追加を検討）。
  - position sizing の lot_size を銘柄別に扱うための拡張（stocks マスタの導入）検討。
  - テストカバレッジ拡充（.env パーサ、calc_* 系の corner case、paper_verification_report の出力整合性など）。

---

## [0.1.0] - 2026-04-13

初回公開リリース — 自動売買システムのコア機能セットを実装。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
- 実行 / 監視
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、paper_trading 環境時の DB 分離、BrokerClientFactory 経由のブローカクライアント利用、ExecutionEngine セッション起動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、監視用 DB の初期化、プロセス優先度設定を実装。
- 設定管理
  - config.py: 環境変数/.env ロード機能を追加。プロジェクトルート自動検出（.git または pyproject.toml）、.env/.env.local の読み込み順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、キー必須チェックを実装。
  - Settings クラス: 各種設定プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視設定 / システム設定等）。KABUSYS_ENV・LOG_LEVEL 等のバリデーションを実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）を実装。score が全て 0 の場合のフォールバックを警告付きで実装。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に基づく発注株数計算を実装。単元株丸め（lot_size）、max_position_pct／max_utilization／aggregate cap、cost_buffer を考慮したスケーリングと端数処理を実装。
  - portfolio/risk_adjustment.py: セクター集中度制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py: 上記機能をパッケージとしてエクスポート。
- リサーチ / ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value といったファクター計算を DuckDB に対する SQL で実装（ma200, ATR20, PER, ROE 等）。営業日ベースのウィンドウ管理や欠損データハンドリングを考慮。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（スピアマン相関）計算(calc_ic)、ファクターの統計サマリ（factor_summary）、ランク変換ユーティリティ(rank) を実装。外部依存ライブラリを使用せずに実装。
  - research/__init__.py: 主要関数群と zscore_normalize のエクスポートを追加（kabusys.data.stats と連携）。
- AI / ニューススコアリング
  - ai/news_nlp.py: raw_news テーブルから記事を集約し OpenAI (gpt-4o-mini) でセンチメントを算出して ai_scores に格納するモジュールを追加。機能概要:
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）、
    - 銘柄ごと記事集約（記事数・文字数上限でトリム）、
    - バッチ（最大 20 銘柄）で API 呼び出し・JSON Mode を利用、
    - 429/ネットワーク/5xx 等に対する再試行（指数バックオフ）、
    - レスポンス厳密バリデーション（結果キー・型チェック・スコア数値化）、スコアを ±1.0 でクリップ、
    - 部分成功時に既存スコアを保護するための限定的な DELETE/INSERT 戦略（チャンク毎）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定を出力。閾値設定（稼働率 99% 等）と P95 算出ロジックを実装。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定関数を追加。権限不足等の例外は警告に変換してスキップする堅牢な実装。
  - utils パッケージ構成を追加。

### Changed
- 環境変数のデフォルトと振る舞いを明確化
  - DuckDB / SQLite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）、paper_trading 用 DB の分離（data/paper_trading.db）を導入。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を監視用 DB として使用する挙動を明確化。
- run_execution/run_monitoring: 起動時にプロセス優先度を "high" に設定するように変更（最初に実行）。

### Fixed
- env パーサの堅牢性向上（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなどを正しく処理するよう改善。
  - .env 読み込みに失敗した場合は warnings.warn で通知し続行するように実装。
- Settings プロパティに対する入力バリデーションを追加・強化
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の許容値チェックを実装。不正値は ValueError を発生させるようにした。
- MONITOR_POLL_INTERVAL の取り扱い（run_monitoring）
  - 環境変数の値を整数化し、1 未満（0 を含む）や不正な文字列の場合はデフォルト 60 秒にフォールバックして警告を出すように実装。time.sleep に渡せない値によるクラッシュを防止。
- position_sizing の集約スケーリングロジックの端数処理と残余配分を実装し、投資上限を超えた時の安全弁を追加。
- research/feature_exploration.calc_forward_returns の入力検査を追加（horizons のバリデーション）。
- news_nlp: OpenAI API キー未設定時に明確な ValueError を送出するように修正。

### Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テスト・CI 環境向けに OS 環境変数の保護を強化）。

### Notes / Implementation details
- DuckDB を分析用 DB（prices_daily, raw_financials など）に使用し、SQL ウィンドウ関数を多用してファクターを効率的に計算する設計。データ取得は DuckDB 接続を受ける純粋関数群として実装されているため、研究環境と運用ロジックの分離が容易。
- Paper Trading モードでは MockBrokerClient を使用して本番 DB と分離された paper_trading 用 SQLite を利用する設計（run_execution の分離）。
- AI スコアリングの設計はフェイルセーフ志向（API 失敗時の部分スキップ・ロギング・再試行）で、書き込みは影響範囲を限定して行うことで部分失敗時のデータ破壊を抑制する意図。

---

過去リリースや将来の変更についてはこのファイルを継続して更新してください。