# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys のバージョンを 0.1.0 として定義。
- 実行用スクリプトを追加:
  - run_execution: ExecutionEngine 起動スクリプトを実装。プロセス優先度設定、ブローカーファクトリ経由の BrokerClient 作成、ExecutionEngine の起動/停止制御（stop フラグ / PID ファイル）をサポート。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用して本番 DB と完全分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。モニタリングは環境にかかわらず本番 sqlite_path を使用する仕様。
- ツールを追加:
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツール（コマンドライン）。稼働率・注文成功率・送信率・レイテンシ等の集計と PASS/FAIL 判定を出力。期間フィルタ、DB パスの引数指定に対応。
- 設定管理（config）機能を追加:
  - Settings クラスによる環境変数アクセスラッパを提供（J-Quants / kabu API / LINE / DB / 監視閾値 等）。
  - .env/.env.local の自動読み込みを実装（OS 環境変数を保護して上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証（許容値チェック）を追加。
- ポートフォリオ構築関連モジュールの実装（純粋関数群、DB 参照なし）:
  - portfolio.portfolio_builder: 候補選定（score 降順）、等金額 / スコア加重の重み計算を実装。スコア全0 時のフォールバックログあり。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用除外、未知レジームはフォールバックで警告。
  - portfolio.position_sizing: 発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。単元株丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、lot 単位での再分配ロジックを含む。
- 研究（research）モジュールを実装:
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL + Python 実装）。MA200、ATR20、各種リターンなどを計算。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリ、ランク変換ユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの公開 API に zscore_normalize（data.stats 経由）と上記ファンクション群を追加。
- AI ニュース NLP （ai.news_nlp）機能を追加（OpenAI 連携の設計および主要ロジックを実装）:
  - ニュース収集ウィンドウ計算（calc_news_window）、OpenAI へのバッチ送信戦略、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、DuckDB への書き込み方針（部分置換）などを設計・実装。
  - score_news は API キー未設定時に ValueError を送出して明示的に失敗する設計。
- ユーティリティを追加:
  - utils.process_priority: Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。psutil を利用し、権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフあり。

### Changed
- DB/分析基盤:
  - DuckDB をデフォルトで利用する設計に。research / ai などの分析処理は DuckDB 接続を受け取り SQL を主体に計算する設計へ統一。
- 実行フロー:
  - 実行・監視プロセスで起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを追加）。
- .env 自動読み込みの挙動:
  - 読み込み順序を OS 環境 > .env.local（上書き）> .env（既存未設定時のみ）に固定し、OS 環境変数は protected として上書きしないようにした。

### Fixed
- レポートツールの堅牢化:
  - paper_verification_report は対象テーブルが存在しない場合に sqlite3.OperationalError を補足してデフォルト値を使うようにし、DB スキーマ未構築でもクラッシュせずにレポートを出力可能にした。
  - P95 計算のインデックス算出ロジックを修正して空リスト時は None を返すようにした。
- run_monitoring のポーリング間隔取得ロジックを堅牢化:
  - 環境変数 MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）に対して警告を出しデフォルト（60 秒）にフォールバックするように修正。
- 設定取得のエラーメッセージを明確化:
  - _require 関数は未設定の必須環境変数を検出した際に明示的な ValueError を送出し、.env.example を参照する旨を案内。

### Security
- OpenAI API キーの取り扱い:
  - score_news は API キーを引数または環境変数 OPENAI_API_KEY から取得。未設定時は明示的にエラーを返すため、誤設定による無限リトライや不正なアクセスを抑止。

### Notes / Breaking changes / Migration
- 監視（run_monitoring）は「環境にかかわらず」settings.sqlite_path（本番用 sqlite_path）を使用します。開発や paper_trading 環境で監視データを分離したい場合は sqlite_path を明示的に変更してください。
- ExecutionEngine（run_execution）は paper_trading モード時に paper_sqlite_path（既定: data/paper_trading.db）を使用します。paper_trading と本番 DB は完全に分離されます。
- .env 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してアプリ内で手動ロードしてください。

---

今後の予定（TODO）
- ai.news_nlp の記事フェッチ部分（_fetch_articles 等）の実装/テストを完了して完全なパイプラインにする。
- 銘柄ごとの lot_size の外部化（stocks マスタ）と銘柄別単元対応。
- position_sizing の価格フォールバック（前日終値 / 取得原価）実装により price が欠損するケースを改善。