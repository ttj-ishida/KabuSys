Keep a Changelog に準拠した変更履歴

すべての変更は semver と Keep a Changelog のスタイルに準拠して記載しています。  
（記載内容は提示されたコードベースの内容から推測してまとめたリリースノートです）

Unreleased
---------
- 今後のリリース計画や未完了のタスクをここに記載します。
  - ai/news_nlp モジュールの一部処理がファイル末尾で切れており（記事集約フェーズ以降の実装が途中）、公開リリース前に完了・テストが必要です。
  - position_sizing の銘柄別単元（lot_size）対応は TODO コメントあり。将来的に銘柄別 lot_map を受け取る拡張を検討。

[0.1.0] - 2026-04-17
-------------------

Added
- プロジェクト初期リリース（バージョン 0.1.0）。
- コア機能
  - 自動売買システムのパッケージ構成を追加（kabusys）。
  - モジュール群を実装:
    - 実行関連: ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - KABUSYS_ENV=paper_trading の場合に MockBroker を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）で本番 DB と分離。
      - PID ファイル管理、停止フラグ（data/stop_requested.flag）に対応。
      - RiskManager, OrderManager, Reconciler 等の組み立てと Engine の起動ループ実装。
    - 監視関連: SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は常に本番 sqlite_path を使用する設計。
      - 停止フラグ検出による安全停止、例外捕捉での次回ポーリング継続。
    - 設定管理: 環境変数 / .env ローダ（src/kabusys/config.py）
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
      - .env / .env.local の読み込みルール（OS 環境変数保護、override 挙動）。
      - 複雑な .env 行パース（export 句、引用符付き文字列、エスケープ、インラインコメント処理）。
      - Settings クラスで多くの設定をプロパティとして提供（DB パス、paper_trading 用パス、PAPER_FILL_MODE 検証、閾値、環境判定等）。
    - ポートフォリオ構築（src/kabusys/portfolio/*）
      - 銘柄選定: select_candidates（スコア降順、signal_rank による tiebreak）
      - 重み算出: calc_equal_weights, calc_score_weights（スコア合計 0 の場合は等配分にフォールバック）
      - リスク調整: apply_sector_cap（既存保有のセクター比率が上限超過のセクターから候補を除外）および calc_regime_multiplier（market regime に基づく投下資金乗数）
      - 取引数量決定: calc_position_sizes（risk_based / equal / score の各配分法、単元株丸め、aggregate cap によるスケーリング、cost_buffer 考慮）
    - リサーチ（src/kabusys/research/*）
      - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL 実装、ウィンドウ関数を活用）
      - 特徴量探索: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank（外部依存なしで統計量・IC 計算を実装）
      - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - AI ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0～1.0）を生成し ai_scores テーブルへ書き込む設計を追加。
      - ニュースの時間ウィンドウ計算（JST ベースで UTC に変換）、記事集約、バッチ処理（最大 20 銘柄）、トークン肥大防止用のトリミング、429/ネットワーク/5xx に対する指数バックオフ retry、レスポンスバリデーション、スコアクリップ（±1.0）等を含む堅牢化方針を実装。
    - ツール（src/kabusys/tools/paper_verification_report.py）
      - Paper Trading 用検証レポート生成ツールを追加。期間指定 (--from / --to) と DB パスオプションをサポート。
      - 指標: 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（avg/max/P95）を算出し、PASS/FAIL 判定を行う。
      - P95 計算ユーティリティ、閾値を定義（稼働率 99%、Fill 90% 等）。
    - ユーティリティ（src/kabusys/utils/process_priority.py）
      - クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを実装。
      - CPU affinity 設定関数（set_cpu_affinity）を追加。権限エラーや未対応 OS では警告を出してスキップする。

Changed
- 各所で堅牢化を実施（入力検証・デフォルトフォールバック・NULL/ゼロ対策）。
  - .env パーサがより現実的なケース（引用符付き値のエスケープやインラインコメント）に対応。
  - Settings の各プロパティで不正値検知（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）時に明確な例外を投げるようにした。
  - run_monitoring のポーリング間隔取得で不正値が指定された場合に警告しデフォルトにフォールバックする処理を追加。
  - calc_score_weights で全スコアが 0 の場合のフォールバックとログ出力を追加。
  - calc_regime_multiplier で未知のレジームに対し警告を出して 1.0 にフォールバック。

Fixed
- 0 除算や None 値による例外が発生しうる箇所にガードを追加。
  - ファクター / リターン / レイテンシ集計系クエリでデータ不足時は None を返すようにして上位処理が扱いやすくした。
  - position_sizing・volume/price 欠損時にスキップして処理を継続するように修正。
- process_priority の未対応 OS や権限エラー時の異常終了を防ぐため例外捕捉と警告ログを追加。

Performance
- DuckDB を活用した SQL 実装により大規模 prices_daily / raw_financials の集計を効率的に実行。
  - ファクター計算や forward_returns のクエリはウィンドウ関数で一括計算する実装になっているため、Python 側ループより高速。

Security
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。OS 環境変数は protected として上書きを防止する仕組みを導入。

Documentation
- 各モジュールに docstring と実装方針を詳細に記載。外部に公開する API（Settings プロパティや各種公開関数）について使用例・注意点を明記。

Known Issues / Notes
- ai/news_nlp.py の実装が提示されているファイル末尾で途中（記事集約フェーズの途中）で切れているため、OpenAI への送信・DB 書き込み周りの実装とユニットテストが未完了です。リリース前に処理の結合テストと失敗時の部分ロールバック（部分成功時の既存スコア保護）を確認する必要があります。
- position_sizing の単元（lot_size）拡張は将来的な拡張予定（TODO コメントあり）。
- run_monitoring は Monitoring 用 DB に常に本番 sqlite_path を使用するため、ローカルでのテスト実行時に注意が必要（別途監視 DB を使いたい場合は環境変数で sqlite_path を切り替える等を推奨）。

その他
- パッケージバージョンは src/kabusys/__init__.py の __version__ にて 0.1.0 を設定。

今後の予定（想定）
- ai/news_nlp の完了と堅牢なエラー処理（部分失敗時の DB 保護）の実装。
- 単体テスト・結合テストの追加（特に DB 周りと OpenAI API のモックを用いたテスト）。
- 銘柄別 lot_size 対応、手数料・スリッページのモデル改善、paper_trading の検証自動化。

----- 
（注）本 CHANGELOG は提示されたソースコードをもとに推測して作成したものであり、実際のコミット履歴や変更日付と異なる可能性があります。必要であれば、実際の git 履歴に基づく正確な CHANGELOG の生成を支援します。