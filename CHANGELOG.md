# Changelog

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠します。

リリース日はコードから推測して記載しています。実際の公開日と異なる場合があります。

## [Unreleased]

（現在のコードベースは初回リリース相当の機能セットに見えます。未反映の小修正やドキュメント追記がある場合はここに追加してください。）

## [0.1.0] - 2026-04-13

### Added
- 実行／監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の際は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。  
    - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

- 設定管理モジュールを追加（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順序をサポートし、OS 環境変数を保護する（上書き禁止）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env の行パーサは export プレフィックス、引用符（',"）およびバックスラッシュエスケープ、インラインコメントなどに対応。
  - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、paper_trading 関連、監視閾値、PID/KILL フラグ、KABUSYS_ENV/LOG_LEVEL 等）。PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の値検証を実装。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全ゼロ時は等金額へフォールバックし警告を出す。
  - risk_adjustment: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、ログ出力、未知レジーム時のフォールバックを明示。
  - position_sizing: 発注株数算出（calc_position_sizes）。allocation_method="risk_based" / "equal" / "score" をサポート。ロット丸め（lot_size）、単一銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を用いた保守的コスト見積り、スケール時の残差処理による再配分ロジックを実装。

- 研究モジュール（kabusys.research）
  - factor_research: DuckDB を用いたファクター計算を実装（モメンタム、ボラティリティ、バリュー等）。それぞれの関数は prices_daily / raw_financials テーブルを参照し、欠損データ時の挙動を明示。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、基本統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。
  - バッチ処理（最大 20 銘柄／回）、1 銘柄あたりの記事数上限（デフォルト 10）と文字数上限（デフォルト 3000）でトークン肥大化へ対処。
  - レスポンス検証、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライ、部分失敗時に既存スコアを保護するトランザクション設計（対象コードを絞った削除→挿入）などフェイルセーフな設計を採用。
  - OpenAI API キーの未設定時には ValueError を送出。

- ユーティリティ（kabusys.utils）
  - process_priority: プラットフォーム（Windows / POSIX）差分を吸収してプロセス優先度を設定する set_process_priority(level) を実装。set_cpu_affinity(cpu_count) で CPU affinity の固定も可能。アクセス権限不足や未対応環境では警告を出して安全にスキップする。

- ツール（kabusys.tools）
  - paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH を参照し、期間フィルタ（--from/--to）で system_status / trade_logs / risk_logs を集計。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づく PASS/FAIL を出力する。DB が存在しない、またはテーブルがない場合に対するフォールバック（N/A）を実装。

- パッケージメタ情報
  - kabusys.__init__.py に __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため、既存挙動の変更は特になし）

### Fixed
- 監視ループ系での堅牢性強化
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループを継続するように例外をキャッチしてログ出力する設計（サービスの自動復旧性を向上）。
  - init_monitoring_db 呼び出しは冪等であり、DB スキーマが既に存在していても問題なく起動可能。

- .env パーサの堅牢化
  - クォート中のバックスラッシュエスケープやインラインコメント処理、export プレフィックス対応により .env の柔軟性を向上。

### Security
- OpenAI API キーの取り扱い
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY の設定を必須化。未設定時は明示的に例外を送出して誤動作を防止。
- OS 環境変数の保護
  - .env 自動ロード時に既存の OS 環境変数を保護（protected set）し、意図しない上書きを避ける設計。

### Notes / 非機能的な設計判断
- DuckDB を分析用データストアとして積極的に利用（research、ai、その他集計処理での高性能 SQL）。SQLite は監視・トレードログなど軽量ストレージに使用。
- Paper Trading と Live の DB を明確に分離し、シミュレーションが本番環境に影響しない設計を採用。
- 多くの関数は「副作用なし（純粋関数）」を意識して設計され、テスト容易性を高めている（特に portfolio / research モジュール）。
- 既存処理はロギングに依存しており、運用時のログレベル設定（LOG_LEVEL）で挙動を調整可能。

---

参考: 主要ファイル一覧（実装済み・注目点）
- src/kabusys/config.py — 環境変数管理、自動 .env ロード、設定プロパティ
- src/kabusys/run_monitoring.py — 監視ループ起動スクリプト（MONITOR_POLL_INTERVAL）
- src/kabusys/run_execution.py — 実行エンジン起動スクリプト（paper_trading 分離）
- src/kabusys/portfolio/* — 候補選定・重み付け・リスク調整・株数決定
- src/kabusys/research/* — ファクター計算・IC・統計サマリー
- src/kabusys/ai/news_nlp.py — ニュースセンチメントの OpenAI スコアリング
- src/kabusys/tools/paper_verification_report.py — Paper Trading 検証レポート CLI
- src/kabusys/utils/process_priority.py — プロセス優先度 / CPU affinity 設定

もしリリース日やバージョン、カテゴリの分け方を別途指定したい場合はお知らせください。必要に応じて各項目を詳細化（関連する関数や環境変数のリスト添付など）します。