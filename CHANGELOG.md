CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリース日はこのドキュメント作成日です。

Unreleased
----------
- （今後のリリースに向けた項目をここに記載してください）

0.1.0 - 2026-04-13
-----------------
Added
- 基本アプリケーション構成とバージョンを追加（パッケージバージョン: 0.1.0）。
  - src/kabusys/__init__.py に __version__ を定義。

- 環境変数/設定管理機能を実装（自動 .env ロード、検証、補助ユーティリティ）。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を読み込む実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。 (src/kabusys/config.py)
  - .env パーサーを実装: export 形式、クォート付き値（バックスラッシュエスケープ対応）、インラインコメント処理などに対応。 (src/kabusys/config.py)
  - OS 環境変数を保護して .env.local の上書きを制御する仕組みを実装。 (src/kabusys/config.py)
  - Settings クラスで多数の設定プロパティを提供（DB パス、paper trading 用パス、PID / kill flag パス、閾値、env / log レベル検証など）。 (src/kabusys/config.py)

- 実行エントリ/デーモン系スクリプト
  - 実行エンジン起動スクリプトを実装（ExecutionEngine 起動、コンポーネント組み立て、paper_trading 用 DB 分離）。 (src/kabusys/run_execution.py)
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離する設計。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
  - システム監視ポーリングループ起動スクリプトを実装（SystemMonitor を定期実行）。 (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示。

- プロセス運用ユーティリティ
  - プロセス優先度設定（Windows / POSIX 差分を吸収）を実装（set_process_priority）。スクリプト開始直後に High 優先度に設定する呼び出しを追加。 (src/kabusys/utils/process_priority.py)
  - CPU affinity 設定ユーティリティを追加（set_cpu_affinity）。許可がない環境では警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定と重み計算: select_candidates, calc_equal_weights, calc_score_weights を実装（スコア降順ソート、スコアゼロ時は等金額にフォールバック）。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限とレジーム乗数: apply_sector_cap（既存保有を考慮してセクター上限を判定）と calc_regime_multiplier（bull/neutral/bear の乗数）を実装。未知レジーム時は警告してフォールバック。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定ロジック（position sizing）を実装: risk_based / equal / score の配分方式、単元株丸め（lot_size）、max_position_pct/max_utilization、aggregate cap のスケーリングおよび残差処理（lot 単位での再配分）。価格欠損時にはスキップする堅牢化。 (src/kabusys/portfolio/position_sizing.py)
  - 上記をまとめてエクスポートするパッケージ API を提供。 (src/kabusys/portfolio/__init__.py)

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（DuckDB を使用した SQL ベースの実装）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離の計算。データ不足時は None を返す。 (src/kabusys/research/factor_research.py)
    - calc_volatility: ATR20、相対 ATR、20 日平均売買代金、出来高比率の計算。 (src/kabusys/research/factor_research.py)
    - calc_value: raw_financials から最新財務データを結合して PER/ROE を計算。 (src/kabusys/research/factor_research.py)
  - 特徴量探索ユーティリティを追加:
    - calc_forward_returns: 将来リターンを一括で取得（horizons バリデーションあり）。 (src/kabusys/research/feature_exploration.py)
    - calc_ic: スピアマンのランク相関（IC）を実装（欠損・非有限値を除外、レコード数が不足する場合は None を返す）。 (src/kabusys/research/feature_exploration.py)
    - factor_summary / rank: 基本統計量と同順位処理（平均ランク）。 (src/kabusys/research/feature_exploration.py)
  - DuckDB を利用する設計で、外部 API に依存せずに prices_daily / raw_financials を参照する方針を採用。

- ニュース NLP（AI）モジュール
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化する機能を実装（バッチ化、トークン肥大化対策、リトライ、レスポンス検証、スコアクリッピング、書き込み戦略）。 (src/kabusys/ai/news_nlp.py)
    - ニュース取得ウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST = UTC で前日 06:00 〜 23:30）を提供（calc_news_window）。
    - 1 銘柄あたりの記事数・文字数上限、チャンクバッチ処理（最大 20 銘柄 / リクエスト）等の実装。
    - API キー未設定時に ValueError を送出する明確なエラーハンドリング。
    - 部分失敗に備え、書き込みは対象コードを限定して差し替える戦略（既存スコア保護）。

- ツール: Paper Trading 検証レポート生成スクリプトを追加。
  - data/paper_trading.db を対象にシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して標準出力レポートを生成。閾値による PASS/FAIL 判定を出力。 (src/kabusys/tools/paper_verification_report.py)
  - P95 の計算を独自実装、期間フィルタ、DB存在チェック、各種 SQL 例外に対するフォールバックを備える。

Changed
- -（初期リリースのため "Changed" 項目はなし）

Fixed
- 環境変数のパースと既存値保護の強化（エスケープ済クォート対応、export フォーマット対応、コメント処理、.env.local の上書きルール）。 (src/kabusys/config.py)
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を行いデフォルトへフォールバック。これにより time.sleep に渡す不正値によるクラッシュを防止。 (src/kabusys/run_monitoring.py)
- DuckDB / SQLite 接続の適切なクローズ処理を起動スクリプトの finally ブロックで保証。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
- 各種関数でデータ不足時に None を返す、あるいはスキップすることで例外発生を抑制（ファクター計算、レイテンシ計算、ポジション算出等）。

Security
- .env の自動ロード時に既存 OS 環境変数を保護する設計とし、意図しない上書きを防止。 (src/kabusys/config.py)

Notes / Known limitations
- position_sizing は現在単元株数 (lot_size) を全銘柄共通で扱う。将来的には銘柄別 lot_map への拡張を予定。 (src/kabusys/portfolio/position_sizing.py)
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" と見なしセクター上限を適用しないため、マスタ未整備の銘柄があると制約が緩くなる可能性がある。TODO コメントあり。 (src/kabusys/portfolio/risk_adjustment.py)
- OpenAI を用いる news_nlp は API レート制限・課金・レスポンス変動に依存する。部分失敗時は他銘柄のスコアを保護する設計だが、運用時には API キー管理とコストに注意。

Acknowledgements
- 本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴（コミットログ等）と差異がある可能性があります。必要であればコミット履歴を参照して差分を確定してください。