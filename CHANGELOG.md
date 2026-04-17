CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースの内容から推測して作成した変更履歴（日本語）です。

注意: 実際のコミット履歴がないため、ファイル内容から推測した「初期リリース」相当のまとめを記載しています。

[Unreleased]
------------

- 開発中／未リリースの変更はここに記載します。

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージ定義とバージョン (src/kabusys/__init__.py: __version__ = "0.1.0") を追加。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。.env 自動読み込み機能、および環境変数の取得/検証を提供。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export KEY=val 形式、クォート値・エスケープ、行内コメント処理のサポート。
    - 必須環境変数チェック（_require による例外発生）。
    - 各種プロパティ（DB パス、PID ファイルパス、監視閾値、環境種別、ログレベル等）と入力値バリデーション。

- 実行系（Execution）
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskConfig のデフォルト値を設定し、初期ポートフォリオ値に broker.get_available_cash() を使用。
    - paper_trading 環境では paper 用専用 SQLite DB を使用して本番 DB と分離。
    - デーモンスレッドで engine.run_session を実行し、停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 起動時に PID ファイル (data/execution.pid 相当) を扱う設計。
    - 監視テーブルの初期化を冪等に行う処理を含む（init_monitoring_db 呼び出し）。

- 監視（Monitoring）
  - SystemMonitor のポーリング起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を利用する設計。
    - stop flag（data/stop_requested.flag）検知でループ終了。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続管理。

- プロセス制御ユーティリティ
  - set_process_priority, set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収する優先度設定（psutil を利用）。
    - CPU affinity 固定機能。権限不足や未サポート環境では警告ログでスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順 + タイブレーク）、calc_equal_weights、calc_score_weights（スコアがすべて 0 の場合のフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有セクター比率を計算し上限を越えるセクターの新規候補を除外）。
    - calc_regime_multiplier（レジームに応じた投下資金乗数、未知レジームはフォールバックと警告）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score による発注株数算出、lot_size による丸め、per-position および aggregate cap（available_cash）によるスケール調整、cost_buffer を加味した保守的見積り、残余配分ロジック。

- リサーチ / ファクター計算（DuckDB ベース）
  - calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）
    - prices_daily / raw_financials を参照する SQL ウィンドウ関数実装。MA200、ATR20、各モメンタム（1m/3m/6m）等を計算。
    - データ不足時は None を返す設計。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計量）、rank（同順位は平均ランク処理）。
  - research パッケージ公開インターフェースを整備（src/kabusys/research/__init__.py）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI で期間指定（--from, --to）や DB パス指定（--db）が可能。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ生成、安全な OperationalError ハンドリングを実装。

- AI (ニュース NLP)
  - ニュースセンチメントスコアリングの初期実装（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を実装（calc_news_window）。
    - OpenAI (gpt-4o-mini) を用いたバッチスコアリング設計（バッチサイズ、トークン肥大化対策、リトライ／バックオフ、結果検証、スコアクリップ等）。
    - ai_scores テーブルへの部分的な置換（code を限定して DELETE → INSERT）方針を明記。
    - 実行に OPENAI_API_KEY が必要で、未設定時は例外を送出する安全設計。
    - （ファイル末尾で一部実装が未完／切れているため、完全実装は今後の課題）

Changed
- DB 接続方針の明確化
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計に明示。
  - 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading 時に専用 paper_trading DB を使用して本番 DB と分離。

- 設定ロードの挙動
  - .env 読み込み時に OS の既存環境変数を保護する protected 機構を導入（.env.local は override=True だが OS 環境変数は上書きしない）。

Fixed / Improved
- .env パーサの堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、行内コメントの扱い、無効行のスキップ。
  - 誤った MONITOR_POLL_INTERVAL 等の設定値に対して警告を出しデフォルトへフォールバック。

- ポートフォリオ算出の安定化
  - calc_score_weights で全スコアが 0 の場合は等金額配分へフォールバックし警告を出す。
  - position sizing の aggregate scaling と残余配分ロジックにより available_cash を超えた場合でも再配分して安全弁をかける。

- プロセス優先度設定のフェールセーフ
  - 権限不足や未対応 OS の場合は警告を出し処理を継続する。

Security
- 環境変数の必須チェック（API キーやパスワードが未設定の場合は ValueError を投げる）により、認証情報未設定のまま処理を進めるリスクを軽減。

Notes / Migration
- 実行/監視
  - 監視の起動: python -m kabusys.run_monitoring（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可）
  - 実行エンジン起動: python -m kabusys.run_execution（paper_trading 環境では paper DB を使用）
  - 停止制御はプロジェクトルート/data/stop_requested.flag を作成することで行う（両スクリプト共通）。
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- OpenAI 連携
  - news_nlp を利用する場合は OPENAI_API_KEY 環境変数を設定する必要あり。未設定時はエラー。
  - news_nlp は大量トークン発生対策・リトライ等の対策を備えるが、ファイル末尾に未完部分があるため本番利用前に実装完了 & テスト推奨。

Known issues / TODO
- news_nlp モジュールの一部実装（ファイル切断）により完全な end-to-end の動作確認が必要。
- position_sizing の価格欠損（price=0.0）の場合、現状はスキップしており過少見積りになる可能性がある。前日終値などのフォールバック価格導入を検討。
- 将来的な拡張: 銘柄ごとの lot_size を持つ stocks マスタのサポート、より細かな手数料／スリッページモデル、並列処理／監視の拡張など。

--- 

（以上）