CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.
（日付はリポジトリのコードベースを元に推定して作成しています）

Unreleased
----------
- （現時点なし）

0.1.0 - 2026-04-12
------------------
Added
- プロジェクト初期リリース。以下の主要コンポーネントを実装。
  - 実行 / 監視ランチャー
    - run_execution.py: 実取引/ペーパートレード双方に対応する ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、data/paper_trading.db にデータを分離して記録。
      - プロセス起動時にプロセス優先度を "high" に設定。
      - SQLite / DuckDB 両方への接続を確立し、終了時にクローズ。
    - run_monitoring.py: SystemMonitor のポーリングループを起動する監視スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用して起動（監視テーブルを初期化）。
  - 設定・環境管理
    - kabusys.config.Settings: .env 自動ロード（.env, .env.local の順、OS 環境変数を保護）と各種設定プロパティを実装。
      - .git または pyproject.toml からプロジェクトルートを検出して .env を探索。
      - 必須環境変数未設定時は明示的に ValueError を送出する _require を提供。
      - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの値検証を実装。
  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder:
      - select_candidates: スコア降順で上位 N を選定（タイブレークに signal_rank を使用）。
      - calc_equal_weights / calc_score_weights: 等重・スコア加重の重み計算（全スコア 0 の場合にフォールバック）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限を評価して候補を除外（"unknown" セクターは無制限で除外対象外）。
      - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear を実装、未知は警告のうえ 1.0 をフォールバック）。
    - portfolio.position_sizing:
      - calc_position_sizes: weight / candidates / risk_based に基づく発注株数計算。単元株（lot_size）で切り下げ、aggregate cap によりスケールダウンと残差処理を行う。
      - cost_buffer による手数料・スリッページ見積りを考慮。
  - リサーチ（DuckDB を用いる分析モジュール）
    - research.factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 欠損制御付き。
      - calc_volatility: 20 日 ATR、相対 ATR、出来高関連指標。
      - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（report_date <= target_date の最新レコードを使用）。
    - research.feature_exploration:
      - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
      - calc_ic / rank / factor_summary: スピアマンランク相関（IC）、ランク付け、基本統計量計算。
    - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
  - AI ニュース NLP（OpenAI 統合）
    - ai.news_nlp:
      - raw_news を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を取得する機能を実装。
      - バッチサイズ・チャンク処理（デフォルト 20 銘柄）、1銘柄当たり文字数/記事数制限、JSON Mode 出力バリデーション、スコアクリッピングを実装。
      - レートリミット（429）・ネットワーク/5xx に対して指数バックオフでリトライ。
      - 書き込み戦略: 成功したコードのみ ai_scores テーブルで差し替え（DELETE + INSERT）して部分失敗時に他銘柄データを保護。
  - ユーティリティ
    - utils.process_priority:
      - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX に対応）。アクセス拒否等は警告でスキップ。
      - set_cpu_affinity: 指定コア数分の CPU affinity を設定（対応できない環境では警告）。
  - ツール
    - tools.paper_verification_report:
      - ペーパートレード用 SQLite DB から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、CLI で検証レポートを出力。
      - 合格基準の閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）とし、PASS/FAIL 判定を出力。
      - P95 は全値を取得して percentile を計算。DB が存在しない場合やテーブル欠損に対してフォールバックしてレポートを生成。

Changed
- プロジェクト構成をパッケージ化し、主要 API をモジュール単位で分割して公開（__all__ によるエクスポート整理）。
- 環境変数ロードの既定動作:
  - OS 環境変数を保護したうえで .env を読み込み（.env.local は上書き）、自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- DB の取り扱い:
  - 監視（monitoring）は常に本番用 sqlite_path を使うように明示（環境に依存しない設計）。
  - 実行（execution）は paper_trading 環境では paper_sqlite_path を使用し本番 DB と分離。
- 入力検証の強化:
  - MONITOR_POLL_INTERVAL が無効な値のときは警告を出してデフォルト（60 秒）へフォールバック。
  - PAPER_FILL_MODE の値検証を追加（instant|partial|never|reject のみ許容）。

Fixed
- 環境ファイルパーサーの堅牢化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント検出ロジック、空行/コメント行スキップなどを実装。
  - OS 環境変数上書きを防ぐ protected 機能を導入。
- process_priority / cpu_affinity 実行時の権限や非対応 OS に対する例外捕捉と警告化（AccessDenied 等をハンドリング）。
- 複数モジュールで DB の存在やテーブル欠損時に sqlite3.OperationalError をハンドリングしてレポートや処理継続ができるようにした。

Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる問題をコメントで指摘（将来的に前日終値や取得原価でフォールバックする検討が必要）。
- position_sizing:
  - lot_size は全銘柄共通固定（将来的に銘柄別 lot_map の導入を想定）。
- ai.news_nlp:
  - API 呼び出し結果の書き込み以降や一部エラーパスの詳細実装は運用での調整が必要（部分失敗時の取り扱いは既設計で保護するが運用テスト推奨）。
- ExecutionEngine の細部（EngineConfig の振る舞いやリコンシリエーションの詳細）は上位設計（StrategyModel.md / PortfolioConstruction.md）依存で、追加のテスト・チューニングが必要。
- DuckDB / SQLite のスキーマバージョン管理やマイグレーション機構は現状で明示されていないため、スキーマ変更時の対応計画が必要。

その他
- パッケージバージョンは kabusys.__version__ = "0.1.0" を設定済み。
- ロギングは各スクリプトで basicConfig(level=INFO) をデフォルト起動時に使用。

Contributing
- バグ修正・機能追加は issue を立て、Pull Request は機能ごとに分けて提出してください。
- .env 自動ロードの挙動はテストや CI で影響するため、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が利用できます。

ライセンス
- 各ファイルにライセンスヘッダはありません（リポジトリの LICENSE を参照してください）。