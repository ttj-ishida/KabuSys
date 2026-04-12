CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （現在のコードベースに対する未リリースの変更は特にありません。）

[0.1.0] - 2026-04-12
-------------------

Added
- 初回公開リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
  - パッケージ基本情報
    - バージョン情報を __init__.py にて 0.1.0 として設定。
  - 設定管理（kabusys.config）
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式や引用符付き値、インラインコメントの扱いに対応する柔軟な .env パーサー。
    - OS 環境変数を保護して .env.local による上書きを制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスで各種環境設定をプロパティとして提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 等）。
    - KABUSYS_ENV, LOG_LEVEL 等の入力検証（不正値は ValueError）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許可）。
  - 実行用スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。
      - BrokerClientFactory によりブローカークライアント生成（Mock を含む想定）。
      - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
      - プロセス優先度を起動時に設定（高優先度）。
  - 監視 DB 初期化
    - init_monitoring_db 呼び出しにより監視テーブルを冪等的に保証（存在チェック／作成）。
  - ユーティリティ（kabusys.utils）
    - process_priority: クロスプラットフォームでプロセス優先度を設定する set_process_priority を追加。
      - Windows 用の優先度クラス、POSIX (Linux/Mac/FreeBSD) の nice 値に対応。
      - 権限不足・未サポート環境では警告を出して安全にスキップ。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を追加（最初の N コアに固定）。
  - ポートフォリオ構築（kabusys.portfolio）
    - portfolio_builder: シグナル選定（select_candidates）、等配分／スコア加重（calc_equal_weights, calc_score_weights）。
      - スコア全零時のフォールバック動作（等配分）と警告ロギング。
    - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
      - unknown セクターの扱い、既存保有の売却予定銘柄を除外するオプション。
      - レジーム乗数は bull/neutral/bear をサポート（未知レジームはフォールバック）。
    - position_sizing: 発注株数計算（calc_position_sizes）。
      - allocation_method に "risk_based", "equal", "score" をサポート。
      - 単元株（lot_size）単位への丸め、max_position_pct / max_utilization による上限適用。
      - aggregate cap（利用可能現金を超える場合のスケールダウン）および残差配分ロジックを実装。
      - cost_buffer による手数料/スリッページの保守的見積りを考慮。
  - リサーチ（kabusys.research）
    - factor_research: モメンタム / ボラティリティ / バリューのファクター計算を追加（DuckDB を使用）。
      - calc_momentum, calc_volatility, calc_value を提供。prices_daily / raw_financials テーブル参照。
      - 各種ウィンドウ長や欠損データ時の振る舞い（不足時は None）を明記。
    - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー。
      - calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマンランク相関）、factor_summary、rank を実装。
      - pandas 等外部依存を使わず標準ライブラリで実装。
  - AI ニューススコアリング（kabusys.ai）
    - news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む機能を追加。
      - ニュース収集ウィンドウ計算（前日15:00 JST〜当日08:30 JST に対応、UTC 変換）。
      - 銘柄ごとに記事を集約し、トークン肥大化対策（最大記事数 / 最大文字数制限）を実施。
      - 最大 20 銘柄ずつのバッチ送信、JSON Mode を期待した厳密なレスポンスバリデーション。
      - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフ再試行、スコアは ±1.0 にクリップ。
      - API キー解決（引数 or OPENAI_API_KEY 環境変数）と未設定時の ValueError。
      - 部分失敗時に他コードの既存スコアを保護するため、更新時は対象コードに限定して置換。
  - ツール（kabusys.tools）
    - paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計。
      - Pass/Fail 判定基準を明確化（稼働率 99%, 注文成功率 90%, 送信率 95%, P95 レイテンシ 200ms）。
      - コマンドライン引数 --from/--to/--db をサポート。P95 はパーセンタイル計算で算出。
  - DB 接続
    - DuckDB と SQLite を用途に応じて併用する設計を採用（DuckDB は時系列・分析、SQLite は稼働ログ/監視等）。
    - monitoring 用 DB 初期化を起動時に行い、冪等で存在を保証。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定などに対応。
- 監視ポーリング設定の安全化
  - MONITOR_POLL_INTERVAL が 0 以下や不正文字列の場合にデフォルトへフォールバックし、time.sleep に渡す不正値を回避。
- 各所でのエラー耐性を向上
  - run_monitoring のポーリングループで check_once() 内の例外を補足して次ポーリングへ継続（ログ出力）。
  - OpenAI API 呼び出しでの失敗は個別チャンクをスキップして全体処理を継続するフェイルセーフ実装。

Security
- 環境変数の自動ロード時、既存の OS 環境変数を protected として上書きから保護（.env.local の override 時も対象）。
- OpenAI API キーは環境変数または明示引数のみで受け付け、未設定時は明示的にエラーとすることで誤った無効な呼び出しを防止。

Notes / Known limitations
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的には前日終値等のフォールバック検討。
- position_sizing: lot_size を銘柄ごとに変動させる拡張（lot_map）について TODO コメントあり。
- news_nlp: ファイルは OpenAI レスポンスの完全性に依存するため、API レスポンス形式の変化に注意。
- run_monitoring は「監視は本番 sqlite_path を使う」と明記しているため、検証環境での使用時は設定に注意。

Acknowledgements
- 本リリースは内部設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に準拠して実装されています。今後のバージョンでユニットテストの追加、ドキュメント拡充、API クライアントの抽象化／テスト用フック追加を予定しています。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴や意図と異なる可能性がありますので、正確な変更履歴が必要な場合は git ログや開発者への確認を推奨します。