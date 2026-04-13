# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本 CHANGELOG は与えられたコード内容から機能追加・修正点を推測して作成しています。

## [0.1.0] - 2026-04-13

初回リリース — コア機能を実装しました。以下は主な追加・設計方針・品質改善点の一覧です。

### 追加 (Added)
- プロセス起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。Paper Trading 環境では MockBroker を用い専用 SQLite DB（data/paper_trading.db）に完全分離して記録する仕組みを提供。
  - run_monitoring.py: SystemMonitor ポーリングループを起動するスクリプトを実装。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き機能を追加（デフォルト 60 秒）。
  - 両スクリプトとも起動時にプロセス優先度を設定する処理を含む。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml に基づく）。
  - .env / .env.local の読み込み順序と OS 環境変数保護（上書き禁止）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 複雑な .env 行のパース（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）を実装。
  - 各種設定プロパティ（DB パス、API トークン、PID・kill-flag パス、閾値、環境種別判定 etc.）を提供。
  - PAPER_FILL_MODE の検証（有効値チェック）を実装。

- モニタリング / 監視関連
  - 監視用 DB 初期化ユーティリティ init_monitoring_db の呼び出しを run_* スクリプトで行い、監視テーブルが存在することを保証（冪等）。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視は本番データを対象にするため）。

- Portfolio コンポーネント (src/kabusys/portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア合計が 0 の場合は警告して等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用して候補をフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear のマッピング、未知レジームはフォールバックして 1.0）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の割当方式を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap のスケールダウン（残差処理で lot 単位の追加配分）などを実装。
    - cost_buffer による保守的コスト見積り考慮。

- リサーチ機能 (src/kabusys/research)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（horizons のバリデーション、効率的な一括クエリ）。
    - calc_ic: スピアマンランク相関による IC 計算（結合・欠損除外・最小サンプル数チェック）。
    - rank / factor_summary: ランク化と基本統計量サマリを提供。
  - research パッケージの __all__ を整備して zscore_normalize 等と統合。

- AI / ニュース NLU (src/kabusys/ai/news_nlp.py)
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎のセンチメントスコアを ai_scores に書き込む処理を実装。
  - バッチ処理（1回あたり最大 20 銘柄）、1銘柄当たり記事数・文字数上限、スコアを ±1.0 にクリップする設計。
  - API エラー (429・ネットワーク・タイムアウト・5xx) を対象に指数バックオフでリトライするロジック（上限回数あり）。
  - JSON Mode の検証、部分失敗時の DB 保護（対象コードに限定した DELETE→INSERT の置換）などを仕様として明記。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
  - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）と詳細出力を実装。
  - 日付フィルタ (--from/--to) および DB パス (--db / 環境変数) をサポート。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装し Windows / POSIX (Linux, Darwin, FreeBSD) を吸収。アクセス権限不足等の失敗を警告ログで扱う。
  - set_cpu_affinity(cpu_count) を実装（必要時にプロセスを先頭 N コアに固定）。

- パッケージ初期値
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更 (Changed)
- DB ハンドリングと安全性
  - run_* スクリプトで finally ブロックにより sqlite/duckdb 接続を確実にクローズするように構成。
  - init_monitoring_db をエンジン開始時に呼び出し、監視テーブルの存在を保証（冪等処理）。

- ロギング / フェイルセーフ
  - run_monitoring のポーリングループは monitor.check_once() の例外をキャッチしてログに記録し、次のポーリングへ継続（サービス継続性の向上）。
  - main() で KeyboardInterrupt をハンドルして graceful shutdown ログを出力。

- 環境変数の取り扱い
  - .env の複雑な行（export、引用符内エスケープ、インラインコメント）を正しく扱うようパーサを改善。
  - 環境ごとの DB パス選択: 実行エンジンは paper_trading の場合に paper_sqlite_path を使用するように変更（監視は本番 DB を使用）。

### 修正 (Fixed)
- 整数/閾値の検証
  - run_monitoring の _get_poll_interval で MONITOR_POLL_INTERVAL が 0 以下・非数の場合に警告を出し、デフォルトにフォールバックするよう修正（time.sleep に不正値が入るのを防止）。

- スコア重み計算のフォールバック
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合、等金額配分へフォールバックして警告ログ出力（ゼロ除算防止）。

- DuckDB / SQL 実装上の頑健性
  - 各種 research モジュールでウィンドウ／行数チェック（例: MA200 の行数チェック・ATR の行数チェック等）を行い、データ不足時に None を返すようハンドリング（NULL 伝播の扱いに注意）。
  - feature_exploration.calc_forward_returns で horizons のバリデーションを行い、不正な入力を弾く。

- OpenAI API ハンドリング
  - news_nlp の API 呼び出しでリトライやエラー（429, RateLimit, Timeout, 5xx, ネットワーク断）を想定し処理の安定性を向上。

### 注意事項 / 既知の制約 (Known issues)
- news_nlp の実装では OpenAI API キーが未設定の場合に ValueError を発生させる（利用前に OPENAI_API_KEY の設定が必要）。
- position_sizing の price フォールバックは未実装: price が欠損 (0.0) の場合にエクスポージャー過小評価によるブロック漏れのリスクがあり、将来的に前日終値や取得原価をフォールバックとして導入することを想定している（TODO を記載）。
- set_cpu_affinity / set_process_priority は権限不足や未サポート OS の場合にスキップされるが、その旨を警告ログで通知するのみで処理は継続する。
- DuckDB の executemany 要件（空パラメータ不可）に注意した実装方針。部分失敗時に既存スコアを保護するため、INSERT 前に削除の対象コードを限定する設計を採用しているが、運用時にトランザクション設計や部分ロールバックの要件がある場合は追加検討が必要。

### ドキュメント / 参考
- コード内コメントに設計方針や参照ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）への言及あり。実運用前にこれらの外部ドキュメントも参照してください。

---

今後のリリースで予定している改善（例）
- position_sizing の銘柄別 lot_size 対応（stocks マスタへの lot_size 属性導入）
- news_nlp の結果バリデーション強化とメトリクス出力
- monitoring 周りのアラート送信（LINE 等）の統合
- より詳細なテストカバレッジと CI ワークフローの整備

以上。もし特定ファイルや変更項目についてより詳細な説明が必要であれば指示してください。