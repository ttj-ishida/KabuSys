CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初期リリース。自動売買システム KabuSys のコア機能群を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を起動時に "high" に設定（psutil ベース）。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と分離して data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）を使用。
    - BrokerClientFactory によるブローカークライアント生成をサポート（paper/live に応じた切替）。
    - ExecutionEngine の起動（EngineConfig にて target_date を指定して run_session を実行）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）の組み立てと既定設定（RiskConfig のデフォルト値を含む）。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の設計（monitoring 用 DB 初期化を実行）。
    - SystemMonitor を用いた定期チェックを実行。

- 設定管理
  - 環境変数/.env ロード機構を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込む。
    - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 行パーサは export プレフィックス、クォート、エスケープ、インラインコメントを適切に扱う。
    - Settings クラスで各種設定をプロパティとして提供（J-Quants / kabu / LINE / DB パス / pid/kill フラグ /閾値等）。
    - バリデーションを行うプロパティ（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正値は ValueError を送出。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI から期間指定 (--from / --to) と DB パス (--db) を受け付ける。
    - system_status, trade_logs, risk_logs などの集計を行い、稼働率、注文成功率、送信率、レイテンシ（平均／最大／P95）を出力。
    - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - データ不足やテーブル未存在時のフェールセーフ処理を実装。

- ポートフォリオ構築
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0時は等金額へフォールバックして警告を出力。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジーム乗数（calc_regime_multiplier）を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知値は警告して 1.0 でフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - ポジションサイズ計算（risk_based / equal / score）を実装。lot_size（単元）丸め、1 銘柄上限、aggregate cap（available_cash によるスケーリング）、cost_buffer による保守的見積り、端数配分アルゴリズムを備える。
    - price 欠損時のスキップやデバッグログを備える。

- リサーチ（DuckDB ベース）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクターを実装。prices_daily / raw_financials テーブル参照。
    - 長期 MA、ATR、出来高平均などの窓計算を SQL（DuckDB）で実行。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付け（rank）を実装。
    - Pandas 未使用で純粋 Python / DuckDB による処理。

- AI / ニュース NLP
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ（最大 20 銘柄 / コール）で投げてセンチメントスコアを取得し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算ユーティリティ（calc_news_window）。
    - API リトライ（429/ネットワーク断/5xx）用の指数バックオフと上限、レスポンスバリデーション、スコアクリッピング（±1.0）、部分失敗時に既存スコアを保護する DB 操作方針などを実装。
    - OPENAI_API_KEY の未設定時は明示的にエラーを返す。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - クロスプラットフォームなプロセス優先度設定（set_process_priority）を実装。Windows と POSIX（Linux/Mac/FreeBSD）を吸収して動作。アクセス権限不足時は警告してスキップ。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を提供。

Changed
- なし（初版のため該当なし）

Fixed
- なし（初版）

Deprecated
- なし

Removed
- なし

Security
- なし

注意・移行ガイド
- 環境変数自動ロード
  - デフォルトでプロジェクトルートから .env / .env.local を自動読み込みします。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。
  - .env.local は .env を上書きするため、機密値の取り扱いに注意してください（OS 環境変数は上書きされません）。

- 監視（run_monitoring）
  - 監視プロセスは KABUSYS_ENV に関係なく Settings.sqlite_path（本番用 sqlite）を参照します。監視データを分離したい場合は sqlite_path を環境で変更してください。

- Paper Trading
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH により data/paper_trading.db を使用します（本番 DB と完全分離）。PAPER_FILL_MODE の有効値は instant/partial/never/reject のみで、無効値は例外を発生させます。

- OpenAI
  - news_nlp.score_news を利用するには OPENAI_API_KEY （または引数で api_key）を必ず設定してください。未設定だと ValueError を送出します。

- ポジション算出と丸め
  - calc_position_sizes は lot_size（デフォルト 100）に基づき丸めを行います。将来的に銘柄別 lot_size に拡張する予定ですが、現状は全銘柄共通です。

今後の予定（抜粋）
- price 欠損時のフォールバック（前日終値や取得原価）によるエクスポージャー計算の改善。
- stocks マスタを用いた銘柄別 lot_size の導入。
- ai/news_nlp のメタデータ処理やモデル選択オプションの拡張。
- 監視・検証結果の可視化レポート出力（HTML/CSV）やスケジューリング統合。

---
この CHANGELOG はソースコードから推測して記載しています。実際のリリースノートとして公開する場合は、リリース履歴やコミットログと照合して追記・修正してください。