CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（注: 本ファイルはリポジトリ内のコード内容から機能追加・設計意図を推測して作成しています。）

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

追加 (Added)
- 基本アプリケーション構成を実装
  - kabusys.__version__ を "0.1.0" に設定。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - 環境変数 KABUSYS_ENV が paper_trading の場合は paper_trading 専用の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient を利用することで本番 DB と分離。
    - 実行前にプロセス優先度を設定する機能を導入（utils.process_priority.set_process_priority）。
    - ExecutionEngine の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）とセッション実行処理を含む。
- 監視用スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - DuckDB 接続を併用している。
- 設定・環境変数管理を実装
  - config.Settings クラスを追加し、各種設定をプロパティで提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / システム設定等）。
  - .env 自動読み込み機能を導入（プロジェクトルート検出：.git または pyproject.toml を基準）。.env → .env.local の順で読み込む。OS 環境変数を保護するための上書き制御・protected 機構を実装。
  - .env のパースを強化（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings 内で環境変数値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定と等重／スコア重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.position_sizing: 株数決定ロジックを実装（calc_position_sizes）。  
    - allocation_method に応じた算出（risk_based / equal / score）。
    - lot_size（単元）丸め、per-position 上限や aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的見積り、端数配分ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対する乗数を返し、未知レジームは警告のうえ 1.0 をフォールバック。
- リサーチ / ファクター計算
  - research.factor_research: Momentum / Volatility / Value ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。DuckDB を用いた SQL ベースの高速集計。
    - MA/ATR/volume 等のウィンドウ集計、データ不足時の None 処理、ログ出力を実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - calc_forward_returns は horizons の入力検証（正の整数かつ <= 252）や効率的な単一クエリ実行を行う。
    - calc_ic はスピアマン相関（ランク相関）を実装。データ不足時は None。
- AI / ニュース NLP モジュール
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むロジックを実装（score_news）。主な機能:
    - ニュース収集ウィンドウの算出（JST 基準を UTC に変換）、記事トリミング（最大記事数・文字数制限）、銘柄単位の集約。
    - チャンク処理（最大 20 銘柄/コール）、JSON Mode 出力の検証、スコアの ±1.0 クリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、部分成功時の部分更新（該当コードだけ入れ替える戦略）などフェイルセーフ設計。
    - API キー未設定時は ValueError を送出。OPENAI_API_KEY からの解決もサポート。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームのプロセス優先度・CPU affinity 設定関数を追加（set_process_priority, set_cpu_affinity）。  
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収し、アクセス権限や未対応 OS の場合は警告でスキップする堅牢設計。

追加（ツール）
- tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。CLI（python -m kabusys.tools.paper_verification_report）で利用可能。
  - システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを集計して標準出力にレポート表示。
  - 閾値定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）と Pass/Fail 判定を実装。
  - 日付フィルタ（--from / --to / --db）に対応。DB が存在しない場合はユーザ向けエラーメッセージを出力。

変更 (Changed)
- DB 周りの扱いを明確化
  - 監視（run_monitoring）は環境（KABUSYS_ENV）に関係なく本番 sqlite_path を使用する方針を明記。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して DB を分離。
- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で適用されるように変更（自動ロード時）。
- DuckDB を分析用途で積極的に利用
  - prices_daily / raw_financials 等の大規模集計処理は DuckDB 接続を受け取って SQL で実行する設計に統一。

修正 (Fixed)
- .env パーサの堅牢性を向上
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、行内コメントの取り扱いなどを改善。
- 環境変数の未設定時の明示的エラー
  - Settings._require が未設定環境変数時に分かりやすい ValueError を投げるように実装。
- process_priority / cpu_affinity の失敗時の挙動を穏やかに
  - 権限不足や未対応 API での例外を捕捉して警告を出すようにし、プロセスがクラッシュしないように変更。

既知の制限・注意点 (Known issues / Notes)
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、_max_per_stock の評価でエクスポージャーが過少見積りされる可能性がある旨をコメントで明記（将来的に前日終値などのフォールバックを検討）。
- ai.news_nlp:
  - OpenAI API のレスポンス形式に強く依存（厳密な JSON の "results" 配列を期待）。API の出力仕様に変化があった場合はエラーとなる可能性あり。
- research モジュールは DuckDB 環境（prices_daily / raw_financials の整備）が前提。
- calc_forward_returns の horizons は最大 252 日に制限（入力検証あり）。

セキュリティ (Security)
- 環境変数の自動ロード時に OS 環境変数を保護する設計（protected set）を導入。テストや CI で .env の上書きを制御可能。

その他
- 各モジュールにデバッグログや情報ログを適切に追加しており、運用時の観測性を意識した設計になっています。
- 多くの関数は「純粋関数」または副作用を限定した実装になっており、テストや再利用を想定しています。

今後の予定（提案）
- position_sizing: 銘柄別 lot_size を銘柄マスタから取得する設計への拡張。
- ai.news_nlp: 応答のバリデーションやスキーマ検証をさらに厳格化、及び失敗時のロールバック戦略の強化。
- monitoring: SystemMonitor の詳細なメトリクス（メモリ / CPU / ディスク使用量の履歴）やアラート出力を充実化。

-------------------------------------------------------------------------------
参考:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。