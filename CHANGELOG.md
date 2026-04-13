# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

なお、本 CHANGELOG は提示されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

## [0.1.0] - 2026-04-13
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開します。各コンポーネントは可能な限り外部依存（取引 API / 本番アカウント等）と分離して設計されています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上デフォルトにフォールバック。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB を使用して本番 DB と完全分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を実行。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

- 環境設定管理
  - config.py
    - .env, .env.local の自動読み込み（プロジェクトルート検出：.git または pyproject.toml を検索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止可能。
    - .env 読み込みは既存の OS 環境変数を保護（protected）する実装。
    - 複数の設定プロパティを公開（DB パス、各種閾値、PID/KILL フラグパス、paper_trading 用設定、PAPER_FILL_MODE の検証など）。
    - 設定検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の入力検査）を実装。

- 監視/モニタリング DB 初期化
  - init_monitoring_db の呼び出し箇所を整備して、監視テーブルの存在を冪等に保証（run_execution/run_monitoring）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプト（コマンドライン実行対応）。
    - 日付フィルタ (--from / --to)、--db オプションをサポート。
    - 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）、リスク却下数などを集計し PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - レポートは DB のテーブルが無ければ安全に N/A を出力する設計。

- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、同点は signal_rank によるタイブレーク）。
    - 等金額配分とスコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター上限適用（既存ポジションのセクター別エクスポージャ算出、sell_codes による除外）。
    - レジームに基づく乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはフォールバックして警告ログ出力）。
  - portfolio/position_sizing.py
    - 発注株数決定（risk_based / equal / score の allocation_method をサポート）。
    - 単元株丸め、個別上限（max_position_pct）・総投下上限（max_utilization）・aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積りと再配分ロジック。

- 研究 / リサーチ機能（DuckDB を用いたオフライン解析）
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials テーブルから計算。
    - 欠損・データ不足時の扱いに注意して None を返す設計。
  - research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman のランク相関）計算、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメント評価を行い、ai_scores テーブルへ書き込み。
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ（UTC 変換）を採用（calc_news_window 実装）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたり最大記事数/文字数の上限、スコアを ±1.0 にクリップ。
    - API への送信は冪等性・フェイルセーフ対応：429・ネットワークエラー・5xx 等は指数バックオフでリトライ、失敗しても他銘柄に影響を与えないよう設計。
    - API キー未設定時は ValueError を送出する明示的エラーハンドリング。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（nice / Windows priority）と CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux/Darwin/FreeBSD）を抽象化して呼び出し元に無理なく利用可能に。
    - 権限不足や未対応 OS の場合は警告ログを出すフェイルソフト実装。
  - utils/__init__.py を追加。

- その他
  - 実行時に DuckDB および SQLite 接続を利用するコンポーネントでの接続確立・クローズ処理を整備（例: run_execution/run_monitoring）。
  - モジュールの __all__ エクスポートやドキュメンテーションストリングを充実化。

### Changed
- 環境変数読み込みの挙動を明確化
  - .env と .env.local のロード順（OS 環境 > .env.local > .env）と protected OS 環境変数の扱いを実装。
- Paper Trading の分離強化
  - paper_trading 環境ではデフォルトで data/paper_trading.db を使用し、本番 monitoring DB と分離する仕様を採用。
- Monitoring の DB 選択ポリシー
  - run_monitoring は環境に依らず本番 sqlite_path を使用する方針（監視データは常時本番 DB に書き込む設計）。

### Fixed
- 環境変数のバリデーションとフォールバックを強化
  - MONITOR_POLL_INTERVAL の不正値（非数値や 0 以下）を検出してログ警告を出しデフォルトにフォールバックする処理を追加。
  - PAPER_FILL_MODE の無効値チェックを追加し、不正値のときは ValueError を発生させるように実装。
- レポートツールの堅牢性向上
  - paper_verification_report は対象テーブルが存在しない場合でも sqlite3.OperationalError を捕捉して N/A を返すようにしている（DB スキーマ未整備時の耐性）。
- DuckDB パラメータ化クエリによる安全な範囲指定（研究モジュールでの SQL パラメータ利用）。

### Security
- 環境変数保護
  - .env 自動ロード時に既存の OS 環境変数を保護（protected set）し、テストや CI で意図せぬ上書きを防止。
- ニュース NLP の設計上の注意
  - score_news は datetime.today()/date.today() を直接参照しない設計でルックアヘッドバイアスを避ける（target_date を明示的に受け取る）。
  - OpenAI API キーの取り扱いは引数または環境変数に限定し、未設定時に明示的エラーを出す。

### Notes / Known limitations
- position_sizing の price が欠損（0.0）の場合、エクスポージャや上限計算が過小評価される可能性がある旨を TODO コメントで記載。将来的に終値や取得原価でフォールバックする設計が検討される。
- 一部の機能（ExecutionEngine の詳細、SystemMonitor の内部実装、init_monitoring_db の正確なスキーマなど）はこのスナップショットから完全には推測できないため、本 CHANGELOG は公開 API と挙動に基づく要約に留まる。
- OpenAI への API コール部分は外部サービス利用を伴うため、実行環境での API キー管理・料金・レート制限に注意が必要。

---

今後の変更として想定される項目（例）
- テストカバレッジの追加、CI/CD の設定
- 銘柄ごとの lot_size をマスタ化して銘柄別単元対応
- execution/risk/engine 各コンポーネントの細かなパラメータ外部化（設定ファイル/管理 UI）
- ai/news_nlp のメタデータ保存・再試行ロジック強化

（以上）