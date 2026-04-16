Keep a Changelog に準拠した CHANGELOG.md（日本語）
==============================================

すべての変更は意図的にコードから推測して記載しています。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

注記: 以下は今後対応を検討している改善点や既知の TODO です（コード内コメントに基づく推測）。
- 改善: セクターエクスポージャ算出で価格が欠損した場合のフォールバック（前日終値や取得原価など）を導入する。
- 改善: 銘柄ごとの単元株数（lot_size）を銘柄マスタから取得できるように拡張する。
- 改善: news_nlp モジュールの記事フェッチ／API 呼び出し後処理の完成と部分失敗時のロールバック動作の厳密化。
- 改善: DuckDB に対する executemany の空パラメータ回避など、DB 操作周りの堅牢性向上。
- ドキュメント: PortfolioConstruction.md / StrategyModel.md 等の参照部分をリポジトリ内で整備（注釈あり）。
- テスト: edge case（スコア全ゼロ、データ欠損、極端なレジーム等）の単体テストを拡充。

v0.1.0 - 2026-04-16
-------------------

Added
- 初期リリース: KabuSys パッケージの基本機能群を実装。
  - 実行（Execution）関連
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、MockBrokerClient を利用することで本番 DB と完全分離。
      - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
      - ExecutionEngine を別スレッドで実行し、 data/stop_requested.flag による安全停止をサポート。
      - 実行時に process priority を "high" に設定するユーティリティを呼び出す。
  - 監視（Monitoring）
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔調整（デフォルト 60 秒、無効値はフォールバック）。
      - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを更新する設計。
      - data/stop_requested.flag による停止検知、KeyboardInterrupt 対応、DB クローズ処理を実装。
  - 設定（Config）
    - config.py: Settings クラスを実装。
      - .env / .env.local の自動読み込み（環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
      - 複数の環境変数プロパティ（DBパス、API鍵、監視閾値、PAPER_FILL_MODE など）と入力検証を提供。
      - env 値（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。
  - ポートフォリオ構築（Portfolio）
    - portfolio パッケージ:
      - portfolio_builder.py: 候補選定（select_candidates）および配分計算（calc_equal_weights / calc_score_weights）。
      - risk_adjustment.py: セクター集中制限 apply_sector_cap、および市場レジームに基づく乗数 calc_regime_multiplier を実装（既知のレジームに対するフォールバックと警告）。
      - position_sizing.py: 株数決定ロジック calc_position_sizes を実装。
        - risk_based / equal / score の配分方式に対応。
        - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング。
  - リサーチ（Research）
    - research パッケージ:
      - factor_research.py: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB SQL + Python で実装。
      - feature_exploration.py: 将来リターン calc_forward_returns、IC（calc_ic）、ファクター統計 summary（factor_summary）、ランク変換（rank）を実装。スピアマン相関計算で ties の平均ランク対応あり。
      - research/__init__.py で主要関数をエクスポート。
  - AI / NLP
    - ai/news_nlp.py: raw_news から OpenAI（gpt-4o-mini）を利用して銘柄ごとにセンチメントスコアを計算し ai_scores へ保存するための基盤ロジックを追加。
      - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST の変換）を実装。
      - バッチ処理（最大 20 銘柄）・文字数／記事数制限・結果バリデーション・リトライ（指数バックオフ）などの設計を取り込む。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などの指標を集約して標準出力にレポート化。
      - デフォルト閾値（稼働率 99%、成立率 90% 等）を定義。
  - ユーティリティ
    - utils/process_priority.py: プラットフォーム差を吸収するプロセス優先度設定と CPU affinity 設定を実装（Windows / POSIX 対応、権限エラーは警告でスキップ）。
  - パッケージメタ
    - __init__.py: パッケージ名とバージョン __version__ = "0.1.0" を追加。

Changed
- 設計上の注意点（初期リリースで明示）
  - 監視モジュールは KABUSYS_ENV に依らず production sqlite_path を使用するよう明記（監視は環境に依存しない設計）。
  - Paper Trading では本番 DB と完全分離するため paper_sqlite_path を導入し、run_execution が適切な DB を選択するようにした。
  - .env パーサはクォート付き値のバックスラッシュエスケープや inline コメント処理に対応し、export キーワードも許容するなど柔軟性を向上。
  - DuckDB を利用したファクター・リサーチ関数は大きめの単一クエリで計算し、パフォーマンスを考慮したスキャン日数バッファを導入。

Fixed
- 入力バリデーションの強化
  - MONITOR_POLL_INTERVAL の不正値（0 以下・非数）の扱いを明確にしてデフォルトへフォールバックし警告出力するようにした。
  - Settings の enum 的環境値（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）で不正値を検出して ValueError を投げるようにした。
  - feature_exploration.rank で ties を平均ランクで扱う実装によりスピアマン相関の正確性を確保。
- ロバストネス
  - process_priority 周りは AccessDenied 等の例外を捕捉して警告を出すのみとし、プロセス起動失敗でサービス全体が落ちないようにした。
  - DB テーブルが存在しない場合（tools のレポート等）に sqlite3.OperationalError を捕捉して代替値を用いる実装を追加。

Notes / Known limitations
- ai/news_nlp.py は主要ロジックを備えているが、実運用に向けた細部（エラーハンドリングの微調整や部分失敗時の DB マイグレーション戦略）は今後の改善対象。
- position_sizing の価格欠損時の扱いや銘柄別 lot_size のサポートは将来的な拡張予定（コード内に TODO コメントあり）。
- DuckDB に対する一部操作（executemany の空配列渡しなど）に関する互換性注意点があるため、呼び出し側でのガードが実装されている。

Security
- 外部 API キー（OpenAI 等）は Settings または関数引数で取得し、未設定時は ValueError で失敗する安全設計。
- .env 自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

参考
- コード内 docstring に各モジュールの設計意図・参考ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）への言及あり。実装とドキュメントを合わせて運用してください。

---  
（以上）