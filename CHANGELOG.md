# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※以下は提供されたコードベースの内容から機能・変更点を推測して作成した変更履歴です。

## [Unreleased]

### Added
- NEWS
  - なし（開発中の作業や未完了のモジュールに関する注記等をここに追加してください）

### Changed
- NEWS
  - なし

### Fixed
- NEWS
  - なし

---

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージ情報
  - パッケージのメタ情報を src/kabusys/__init__.py にてバージョン `0.1.0` として定義。

- 環境設定機能（src/kabusys/config.py）
  - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パースの強化:
    - コメント行 / 空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなし値中のインラインコメント処理を限定的にサポート。
  - 環境変数の保護（既存 OS 環境変数を上書きしない / .env.local で上書き可）。
  - 必須環境変数取得ヘルパー `_require` と各種設定プロパティを提供（DB パス、API トークン、各種閾値、環境判定など）。
  - PAPER_FILL_MODE の検証、PAPER_TRADING 用 SQLite パスの設定等を実装。

- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント取得。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）および実行 PID 管理（data/execution.pid）をサポート。
    - デーモンスレッドで engine.run_session を実行し、停止フラグ検出で安全停止。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境にかかわらず監視は本番 sqlite_path を使用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグを検出してループ終了、例外時のログ出力および接続クローズ処理を実装。

- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルが存在することを保障（冪等性）。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) で Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度を設定。
  - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を最初の N コアに固定できるユーティリティを追加。
  - 権限不足や未対応 OS の場合は警告ログでスキップするフェイルセーフを実装。

- ポートフォリオ構築関連（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank をタイブレークにして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分 / スコア正規化配分。スコア全てが 0 の場合等金額にフォールバックし警告を出す。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超えているセクターの新規候補を除外（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market regime による投下資金乗数を返却（bull/neutral/bear をマッピング、未知レジームは警告の上 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") による発注株数計算、単元株（lot_size）丸め、1 銘柄上限や aggregate cap、手数料バッファ(cost_buffer) を考慮したスケーリング実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER、ROE を算出（最新の report_date を参照）。
    - 各関数はデータ不足時に None を返すなど頑健な実装。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic / rank / factor_summary: スピアマン IC（ランク相関）計算、ランク付け（同順位の平均ランク処理）および統計サマリーを実装。
  - research パッケージのエクスポートを整理。

- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントを -1.0〜1.0 で算出し ai_scores テーブルへ書き込む処理の設計を実装。
  - バッチ処理（最大 20 銘柄/コール）、記事数・文字数のトリム制限、429/5xx/ネットワーク断に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアの上下クリップなどを組み込み。
  - OpenAI API キーの解決ロジックと未設定時のエラー処理を実装。
  - ニュース集計ウィンドウ計算（JST ベースのウィンドウを UTC に変換）を提供。

- ツール類（src/kabusys/tools）
  - paper_verification_report.py:
    - Paper Trading の SQLite DB を読み、システム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを標準出力に出力する CLI ツールを追加。
    - 日付フィルタ（--from / --to）、DB パス指定（--db または 環境変数）をサポート。
    - Pass/Fail 判定基準（稼働率・注文成功率・送信率・P95 レイテンシ）を定義。

### Changed
- ドキュメントコメントや設計ノートを各モジュールに追加し、設計方針（DuckDB を用いた非同期計算・外部 API 参照回避等）を明確化。

### Fixed
- .env 読み込み時のファイル読み込み失敗を警告として扱う（OSError の取り扱い）し、テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を尊重。

### Security
- OpenAI API キーや各種トークンは環境変数から取得する方式を採用（コード中にハードコードしない）。

---

開発者向け注記:
- 一部モジュール（例: ai/news_nlp.py の末尾）は設計途中で切れている可能性があります。実行前に API キーや DB スキーマ、テーブル存在などを確認してください。
- run_monitoring/run_execution はプロセス優先度設定やファイルパス（data 以下の PID/stop フラグ等）に依存します。運用環境での権限・パスを事前に検証してください。

もし特定の変更点をより詳細に反映したい場合（例えばコミット単位・担当者・チケット番号等）、提供された情報を元にさらに細分化した CHANGLEOG を作成します。どの粒度で作成するか指示ください。