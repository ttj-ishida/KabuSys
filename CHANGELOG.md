# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のフォーマットに準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

### [Unreleased]
- 今後のリリースで取り込み予定の小改良・リファクタはここに記載します。

---

### [0.1.0] - 2026-04-13
初回公開リリース。以下の主要機能・モジュールを含みます。

Added
- 全体
  - プロジェクト初期実装。自動売買システム KabuSys のコア機能群を含む。
  - 環境変数読み込み・管理用 Settings クラスを実装（src/kabusys/config.py）。
    - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式・クォート・インラインコメントの扱いを考慮したパーサ実装。
    - 必須環境変数取得用の _require 関数を提供。
    - KABUSYS_ENV / LOG_LEVEL 等の妥当性チェック実装。
- 実行系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を分離して使用する実装（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager 初期設定のデフォルト値（最大保有率、利用率、レートリミット、サーキットブレーカー閾値、ドローダウン等）。
    - duckdb 結合（duckdb_path）。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - プロセス優先度を最初に "high" に設定する処理組み込み。
- 監視 / ツール
  - 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db の利用を起動時に保証）。
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（P95 等）などを算出し CLI 出力。
    - 日付フィルタ対応（--from / --to）、PAPER_TRADING_SQLITE_PATH の指定サポート。
    - 明確な合格/不合格基準（閾値）を実装。
- ポートフォリオ構築
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順ソート、等金額配分、スコア加重配分（スコア全てが 0 の場合は等金額にフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - セクターごとの既存エクスポージャーを計算して新規候補を除外する apply_sector_cap。
    - market regime に応じた乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）でスケーリングするロジックを実装。
    - cost_buffer を考慮した保守的見積りおよび残余キャッシュを用いた端数配分アルゴリズム。
- リサーチ（DuckDB ベース）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（ATR20、相対 ATR、出来高系）、Value（PER, ROE）を実装。
    - データ不足時は None を返す堅牢な設計。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（horizons 対応）、IC（Spearman の ρ）計算、ファクター統計サマリ、ランク付けユーティリティを実装。
    - 外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージ向けのエクスポート（src/kabusys/research/__init__.py）。
- AI / NLP
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）。
    - raw_news を OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores に書き込む設計。
    - バッチ処理（最大 20 銘柄）、1 銘柄あたりの記事数・文字数制限、JSON Mode 期待の厳密なレスポンス仕様。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装方針。
    - API キー解決（引数優先、環境変数 OPENAI_API_KEY を参照）、未設定時は ValueError。
- ユーティリティ
  - プロセス優先度 & CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 間の差分吸収（psutil ベース）。
    - nice 値 / HIGH_PRIORITY_CLASS 等のマッピング、失敗時のフォールバック（警告ログ）。
    - CPU affinity を N コアにピン留めする機能（安全な入力チェックと例外ハンドリング）。
- パッケージ情報
  - __version__ = "0.1.0" を設定（src/kabusys/__init__.py）。

Fixed
- 環境変数読み込み
  - .env のパースを堅牢化（export プレフィックス、クォート内エスケープ、インラインコメント扱い、空行/コメント行スキップ）。
  - .env.local を .env より優先して上書き可能に（OS 環境変数は保護）。
- ポートフォリオ / position sizing
  - 0/欠損価格・0 以下の値に対する安全なスキップ処理を追加し、異常データによるゼロ除算や不正発注を回避。
- リサーチ / ファクター
  - DuckDB クエリ内で NULL 伝播やカウント不足時の None 返却を明示的に処理（信頼性向上）。
- 実行 / 監視
  - モニタリングループ内の例外を捕捉してログ出力後に次のポーリングへ継続するフェイルセーフを追加（run_monitoring.py）。

Security
- OpenAI API キーは明示的に引数または環境変数で供給する設計。未設定の場合は実行側でエラーを投げて処理を停止するため、誤ってキーなしで API 呼び出しするリスクを低減。

Notes / Known issues
- news_nlp.score_news は堅牢な設計（バッチ、リトライ、レスポンス検証）を持つが、外部 API の仕様変更やレスポンス形式が異なる場合に備えた運用が必要。
- apply_sector_cap のエクスポージャー計算は price_map に 0.0（欠損値）がある場合に過小評価する可能性があり、将来的にフォールバック価格（前日終値や取得原価）を導入することを注記している。
- position_sizing の将来拡張: 銘柄ごとの lot_size を導入するための設計余地を残している（TODO コメントあり）。
- 自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布先での動作や CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD による制御を推奨。

---

将来リリースでは以下の点を検討しています（予定）
- OpenAI API のレスポンス検証とエラー時の部分ロールバック／リトライ戦略の強化
- 銘柄ごとの lot_size マスタ導入、手数料モデルの拡張
- モニタリングのメトリクス可視化エクスポート（CSV/JSON）実装
- ユニットテストの充実（特に数値アルゴリズム・SQL クエリ周り）

--- 

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や設計仕様に基づく正式なリリースノート作成時には、差分コミットメッセージや設計ドキュメントを参照してください。