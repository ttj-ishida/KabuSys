CHANGELOG.md
=============

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------

- 実装途中 / 注意事項
  - kabusys.ai.news_nlp モジュールがほぼ完成しているものの、取得した記事集約処理の直前でファイルが途切れており（コード末尾が途中で切れている）、一部処理が未完です。OpenAI API 呼び出し周り・DB書き込みの最終ロジックは存在しますが、実運用前に残りの実装および統合テストが必要です。
  - portfolio.risk_adjustment.apply_sector_cap にて price が欠損した場合のフォールバック（前日終値や取得原価など）は TODO コメントあり。価格欠損時の挙動に注意してください。

0.1.0 - 2026-04-16
-----------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __init__.py に __version__ = "0.1.0" として収録。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動ロード実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサを独自実装し、export KEY=val、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - OS 環境変数を保護するための protected オプションを用意し、上書き制御を実現。
  - Settings クラスを実装し、アプリケーション設定（DBパス、APIトークン、監視閾値、環境判定など）をプロパティ経由で取得可能に。

- 実行・監視プロセス起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の独立した SQLite DB（data/paper_trading.db デフォルト）を使用する分離設計。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせたエンジン組立。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理、スレッド実行・グレースフル停止処理を実装。
    - RiskManager の初期設定（max_position_pct 等）を明示的に設定。初期ポートフォリオ値は broker.get_available_cash() で取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。無効な値はデフォルト 60 秒へフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度設定（High）を最初に行う。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - Windows / POSIX（Linux, macOS, FreeBSD）を吸収する set_process_priority 実装。
  - set_cpu_affinity 実装（最初の N コアに固定）。
  - 失敗時は警告ログでスキップするフェイルセーフ実装。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder:
    - BUY シグナルの候補選定（スコア降順、signal_rank によるタイブレーク）と等金額・スコア加重の重み計算。
    - スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - risk_adjustment:
    - セクター集中制限 (apply_sector_cap)：既存保有からセクターごとのエクスポージャを計算し、上限超過セクターの新規候補を除外。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマップ）と未知レジームのフォールバック（1.0）実装。
  - position_sizing:
    - allocation_method 別（risk_based / equal / score）による発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、残余キャッシュでの再配分アルゴリズムを実装。
    - cost_buffer を加味して保守的なコスト見積りを行う。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - モメンタム、ボラティリティ、バリューの計算関数を実装（DuckDB 接続を受け prices_daily, raw_financials を参照）。
    - ma200, atr_20 等を必要な行数チェック付きで算出。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン対応）。
    - スピアマンランク相関による IC 計算 calc_ic、ランク計算 util rank、ファクターサマリー factor_summary。
  - research パッケージの __all__ に主要関数をエクスポート。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading の検証レポート生成スクリプトを追加。
  - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
  - P95 計算、期間フィルタ、テーブル存在に対する堅牢なフォールバック処理を備える。
  - デフォルト DB は data/paper_trading.db を参照。CLI オプションで期間・DB パスを指定可能。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) を用いた銘柄別センチメントスコアリング処理を設計・実装。
  - バッチサイズ制御、1銘柄あたりの最大記事数・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、書き込みの部分置換（DELETE→INSERT）を考慮した安全な DB 更新方式など、実運用を想定した堅牢な設計。
  - OpenAI API キー未設定時に明確な例外を送出。

Changed
- 環境変数パース挙動の強化
  - .env の parse 処理がより柔軟になり、クォート内エスケープや export プレフィックス、インラインコメント扱いの規則を実装。
  - 自動ロード順を OS 環境 > .env.local > .env と明示。

Fixed
- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL に不正な値が設定された場合にデフォルトへフォールバックし、time.sleep に渡して発生する ValueError を防止。
  - monitor.check_once() 実行時の例外を捕捉してログ出力し、次ポーリングを続行するフェイルセーフを実装。

Notes / Known issues
- kabusys.ai.news_nlp モジュールの末尾が途中で切れており、記事取得 → API 呼び出し → DB 書き込みのうち記事集約フェーズ直後で途切れています。リポジトリに残る未完了部分は完成させる必要があります。
- price 欠損時のエクスポージャ算出（apply_sector_cap）では将来的に前日終値や取得原価でのフォールバック対応が望ましい（現在は TODO）。
- その他 async/並列化や外部 API に依存する箇所（OpenAI、各ブローカー）はモック/テストを用いた統合試験推奨。

Security
- なし（既知のセキュリティ問題はコード上では検出されていませんが、外部 API キーの取り扱い・ログ出力に注意してください）。