CHANGELOG
=========

すべての注目すべき変更を記録します。形式は "Keep a Changelog" に準拠しています。

注: 以下は与えられたコードベースの内容から推測して作成した変更履歴です。実装上の仕様や設計意図に基づき要点を抜粋・整理しています。

保守方針
-------
- 変更履歴はセマンティックバージョニングに従います（現時点のパッケージバージョンは src/kabusys/__init__.py の __version__ を参照）。
- 各リリースでは「Added / Changed / Fixed / Removed / Security」を可能な限り区別して記載します。

## [0.1.0] - 2026-04-16

### Added
- 初期リリースとして以下の主要機能群を追加。
  - ランタイム起動スクリプト
    - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient 経由で完全分離された動作を行う。停止フラグ検知、PID ファイル管理、スレッドでのエンジン実行／停止処理を実装。（src/kabusys/run_execution.py）
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。監視は本番 sqlite_path を用いる実装。（src/kabusys/run_monitoring.py）
  - 設定管理
    - Settings クラスによる環境変数／.env 自動ロード機能を実装。.env / .env.local の読み込み優先度（OS 環境変数を保護）を実装し、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化もサポート。（src/kabusys/config.py）
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどを考慮して堅牢に実装。
    - 各種設定プロパティを提供（DB パス、paper_trading 切替、PID/kill flag パス、閾値設定、ログレベル／環境検証など）。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL のバリデーションを実施。
  - ポートフォリオ構築（純粋関数群）
    - 候補選定と重み付け: select_candidates, calc_equal_weights, calc_score_weights を実装。スコア 0 の場合のフォールバック動作（等金額配分）を考慮。（src/kabusys/portfolio/portfolio_builder.py）
    - セクターキャップ適用: apply_sector_cap 実装。既存ポジションのセクター比率を計算して上限を超えるセクターの新規候補を除外するロジックを提供（unknown セクターは無視）。（src/kabusys/portfolio/risk_adjustment.py）
    - レジーム乗数: calc_regime_multiplier（"bull","neutral","bear" をマップ。未知値はフォールバック 1.0）。（src/kabusys/portfolio/risk_adjustment.py）
    - ポジションサイズ計算: calc_position_sizes を実装。risk_based / equal / score の配分方式に対応。単元株（lot_size）丸め、per-position 上限・aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を用いた保守的コスト見積もり、残差分の lot 単位での追加配分アルゴリズムを実装。（src/kabusys/portfolio/position_sizing.py）
  - 研究（research）モジュール（DuckDB ベース）
    - ファクター計算: calc_momentum, calc_volatility, calc_value を実装（prices_daily, raw_financials を参照）。200 日 MA・ATR20・出来高平均などを計算し、データ不足時は None を返す設計。スキャン範囲やウィンドウバッファを考慮した SQL を生成。（src/kabusys/research/factor_research.py）
    - 特徴量探索: calc_forward_returns（任意 horizon の将来リターン）、calc_ic（Spearman ランク相関による IC 計算、必要レコード数の閾値チェック）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。外部ライブラリに依存せず純粋 Python + DuckDB ベースで実装。（src/kabusys/research/feature_exploration.py, src/kabusys/research/__init__.py）
  - AI ニュース NLP（初期実装）
    - news_nlp モジュールを追加。ニュース集約ウィンドウ計算（JST→UTC 変換）、OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメントスコアリングの設計を実装。バッチ処理、トークン肥大化対策（記事数・文字数制限）、リトライ（指数バックオフ）やレスポンス検証、スコアクリッピング、部分的な DB 更新手順が設計されている。（src/kabusys/ai/news_nlp.py）
    - calc_news_window 等のヘルパーは実装済み。score_news の初期処理（API キー解決・ウィンドウ計算・記事集約フェーズの開始）は実装されているがファイルは途中で切れており、完了処理（API 呼び出し〜DB 書き込み）は未完（後続実装が必要）。
  - ユーティリティ
    - process_priority: プラットフォーム差分を吸収してプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定を提供。アクセス権限不足や未対応 OS の場合は警告を出して安全にスキップする実装。（src/kabusys/utils/process_priority.py）
  - ツール
    - paper_verification_report: Paper Trading 用 SQLite（data/paper_trading.db デフォルト）から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して検証レポートを標準出力する CLI スクリプトを追加。閾値（稼働率99%、成功率90% 等）を定義し PASS/FAIL 判定を行う。SQL の存在チェックや OperationalError のフォールバック処理あり。（src/kabusys/tools/paper_verification_report.py）

### Changed
- パッケージ初期化
  - __init__.py にパッケージメタデータ（__version__="0.1.0"）と主要サブパッケージのエクスポートリストを追加。（src/kabusys/__init__.py）
- 設計指針の明確化
  - research / portfolio モジュールは「DB 参照は限定し、計算は可能な限り純粋関数で行う」方針を明確にして実装（副作用を持たない関数群として提供）。

### Fixed
- .env 読み込みの堅牢化
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどをサポートし、.env 読み込みでの誤認識を低減。（src/kabusys/config.py）

### Notes / Implementation details / Observations
- run_execution は paper_trading 環境で本番 DB と完全分離する設計（settings.is_paper による sqlite パス切替）。監視テーブルの初期化（init_monitoring_db）を冪等に呼んでいるため、本番／ペーパートレード両方で監視テーブルが保証される。
- RiskManager の初期設定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）などは実運用想定のデフォルトを設定している（src/kabusys/run_execution.py）。
- calc_position_sizes の aggregate cap ロジックは cost_buffer を用いて手数料等を保守的に見積もり、スケールダウンと残差配分まで考慮した実装になっている。単元株数（lot_size）に依存する丸め処理も実装済み。
- research モジュールは DuckDB を活用して SQL で大規模テーブルを効率的に処理する設計。DataFrame 等の外部依存を避ける方針。
- news_nlp モジュールは OpenAI との連携設計が詳細に書かれているが、ファイルが途中で切れているため最終的な API 呼び出し・DB 書き込み実装は未完。API キー解決やウィンドウ計算、定数類、エラーハンドリング方針は既に定義されている。

### Known limitations / TODO
- news_nlp.score_news の実装が途中で終わっており、OpenAI 呼び出し→レスポンス検証→ai_scores 書き込みの完成が必要。
- position_sizing の価格欠損（price が 0.0）時のフォールバック戦略について TODO コメントあり（前日終値や取得原価でのフォールバック実装が検討対象）。
- 一部の操作はプラットフォーム依存（プロセス優先度、CPU affinity）。権限不足や未対応環境へのフォールバックが必要（既に警告で回避する実装あり）。
- DuckDB での executemany 周りの制約（params が空だと失敗する等）に対する注意書きがあるため、部分失敗時の安全な DB 更新ロジック（ai_scores の code 絞り込み削除→挿入等）を設計に取り入れている。

未リリース / 将来の変更候補
------------------------
- news_nlp の完全実装（API 呼び出しと DB 反映、バックオフ／再試行の詳細実装）。
- ポートフォリオ構築における銘柄ごとの lot_size を stocks マスタで持つ拡張。
- position_sizing における価格欠損時のフォールバック価格ロジック。
- テストカバレッジ強化（特に重み付け・スケーリング・IC 計算・rank の同順位扱い等の境界ケース）。
- ドキュメント（PortfolioConstruction.md / StrategyModel.md 等参照の実装箇所）と実装の整合性チェック。

---

参考:
- 主なファイル群:
  - src/kabusys/config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/portfolio/*
  - src/kabusys/research/*
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/utils/process_priority.py

（この CHANGELOG は与えられたソースコードの状態に基づく推測的なまとめです。追加のコミット履歴やプロジェクトのリリースノートがあれば、より正確に更新できます。）