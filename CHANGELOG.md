# Changelog

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従います。
比較的高レベルな要約はソースコードの実装から推測して作成しています。

※ 日付はコードの現状を元に推定しています。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-16

初回公開リリース。自動売買システムのコア機能群を実装／統合しました。主な追加点は以下の通りです。

### Added
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
  - ExecutionEngine をスレッドで起動する CLI エントリポイントを提供。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用し、本番 DB と完全に分離する仕組みを実装。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、EngineConfig により当日の取引セッションを管理。
  - 停止フラグ (data/stop_requested.flag) と pid ファイル管理をサポート。停止フラグ検知で安全にシャットダウンする制御を実装。
  - RiskManager のデフォルトパラメータ（ポジション上限・利用率・レート制限・サーキットブレーカー等）を設定。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動するエントリポイントを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
  - 監視は環境にかかわらず（paper/live/dev に関係なく）本番 sqlite_path を使用して監視データを記録する旨の設計。
  - プロセス優先度を上げるユーティリティ呼び出し（set_process_priority("high")）を起動時に実行。

- 設定管理
  - src/kabusys/config.py
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。OS 環境変数上書きを保護する実装。
  - .env のパースはクォート・エスケープ・コメント処理を細かく扱う実装。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - Settings クラスで各種設定（DB パス、OpenAI や API トークン、監視閾値、環境種別など）をプロパティで提供し、妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。

- ポートフォリオ構築ユーティリティ
  - src/kabusys/portfolio/*
  - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクターエクスポージャー計算、除外ロジック、unknown セクターの扱い等）。
  - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。
  - position_sizing モジュールで allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。cost_buffer による保守的見積もりにも対応。
  - 一部に将来的な拡張点（個別銘柄の lot_size 管理や価格フォールバックの TODO コメント）を明記。

- 研究（Research）モジュール
  - src/kabusys/research/*
  - ファクター計算: calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け取り prices_daily / raw_financials テーブルに基づいて計算。
  - 特徴量探索: 将来リターン計算 calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計 summary を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - 実装はパフォーマンスに配慮し、ウィンドウの走査範囲や SQL の一括取得で効率化。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
  - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを -1.0〜1.0 で算出して ai_scores テーブルへ書き込む処理を提供。
  - バッチサイズ（デフォルト 20 銘柄）、記事数・文字数のトリム、429/ネットワーク/5xx に対する指数バックオフによるリトライ等を実装。
  - レスポンス検証（JSON 形式、results キー、型チェック）とスコアのクリップ（±1.0）を行うことで堅牢性を確保。
  - タイムウィンドウの計算は JST ベースで定義され、ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
  - Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。権限不足や未対応環境時は警告を出してスキップするフェイルセーフを備える。

- ツール
  - src/kabusys/tools/paper_verification_report.py
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）に対する検証レポート生成ツールを実装。期間指定 --from / --to、および --db オプションをサポート。
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を行うための閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）を定義。
  - p95 の計算、欠損テーブルに対する安全ハンドリング（OperationalError のフォールバック）を実装。

- パッケージ基本情報
  - src/kabusys/__init__.py にてパッケージ名とバージョン (0.1.0) を定義。

### Changed
- 監視（monitoring）設計上の決定: 監視用 polling は環境に依存せず常に本番用 sqlite_path に書き込む仕様（run_monitoring の実装より）。paper_trading の隔離は run_execution 側で取り扱う。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス対応、クォート中のバックスラッシュエスケープ対応、インラインコメント処理（クォートなしの場合の '#' 扱い）などを実装し、より現実的な .env 設定ファイルに対応。

### Known limitations / Notes
- position_sizing の一部処理において price が欠損（0.0）の場合にエクスポージャー過少見積りとなる可能性があり、将来の拡張として前日終値や取得原価を用いたフォールバック案がコメントとして残されています。
- ニュース NLP の実装は外部 API（OpenAI）依存のため API キー必須。失敗時は部分スコア保護およびフェイルセーフで継続する設計だが、運用時の API エラー・コスト管理が必要です。
- src/kabusys/ai/news_nlp.py は内部で記事取得の続き処理（_fetch_articles 等）が存在する前提で設計されており、環境に応じたテーブル定義（raw_news, news_symbols, ai_scores）が必要です。

### Security
- 外部 API キーは環境変数から読み込む設計（OPENAI_API_KEY 等）。.env 読み込みはデフォルトで有効だが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

---

この CHANGELOG はソースコードの現在実装内容から推測して作成しています。実際のリリースノート作成時には、コミット履歴・ PR の説明・リリース方針に基づいてより詳細にカテゴリ分け（Fixed / Changed / Deprecated / Removed / Security 等）してください。