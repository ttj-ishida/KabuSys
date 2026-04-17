CHANGELOG
=========

すべての変更は "Keep a Changelog" のフォーマットに準拠して記載しています。  
（コードベースの内容から推測して作成しています。実際の変更履歴やリリース日付は適宜調整してください。）

Unreleased
----------

- なし

0.1.0 - 初期リリース
-------------------

Added
- 基本機能・アーキテクチャ
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - DuckDB と SQLite を併用するデータレイヤーを導入。duckdb を解析用途、SQLite を監視／実行ログ用に使用。
  - Settings クラスを導入し、環境変数からの設定取得を集中管理。
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出ロジック付き、OS環境変数を保護する override ロジックを採用）。
  - パッケージのエクスポートを整理（portfolio, research, tools などの公開 API を定義）。

- 実行系
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使い、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアントの抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動前および実行中に data/stop_requested.flag を監視し、フラグ検知で安全に停止。
    - 実行用 PID ファイルをサポート。

  - run_monitoring.py：SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルに書き込み（設計上の注意）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 監視・データ初期化
  - init_monitoring_db 呼び出しにより監視用テーブルの冪等的初期化を実行。

- process / OS ユーティリティ
  - utils/process_priority.py を追加。
    - set_process_priority(level) で Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定を実装。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity を固定するユーティリティを実装。
    - 権限不足やサポートされない環境では警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコア合計が 0 の場合に等配分へフォールバックする警告処理を含む。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジックを実装（売却予定銘柄の除外対応、"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear）を提供。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 等配分・スコア加重・リスクベースの株数決定ロジックを実装。
    - 単元株丸め（lot_size）、per-position 上限・aggregate cap のスケールダウン、自動的な残差処理（fractional remainder に基づく追加配分）を実装。
    - cost_buffer を考慮した保守的なコスト見積りをサポート。

- リサーチ（ファクター・特徴探索）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルのみ参照。
    - 各ファクターは欠損・データ不足を考慮して None を返す仕様。
  - research/feature_exploration.py
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計）、rank（同順位は平均ランク）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで処理。

- AI / ニュース NLP
  - ai/news_nlp.py を追加（OpenAI を利用したニュースセンチメントスコアリング）。
    - target_date に対するニュースウィンドウ計算（JST ベース → UTC 変換）を実装（calc_news_window）。
    - ニュース記事を銘柄ごとに集約してバッチ（最大 20 銘柄）で OpenAI に送信、JSON 形式の厳密な出力を期待。
    - レート制限・ネットワーク障害・5xx 等に対する指数バックオフのリトライ、レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - 部分失敗時のデータ保護のため、更新対象 code を限定して ai_scores テーブルを置換。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、PASS/FAIL を判定する閾値を持つ。
    - --from / --to / --db オプションを提供。

Changed
- 環境変数読み込み
  - .env 読み込みのパーサを強化：
    - export KEY=val 形式に対応。
    - クォート付き値のバックスラッシュエスケープを正しく処理。
    - クォートなし値のインラインコメント処理を改善（'#' の直前が空白/タブの場合にコメントとして扱う）。
  - 自動ロード順序: OS 環境 > .env.local（override）> .env（初期設定）。プロジェクトルートが検出できない場合は自動読み込みをスキップ。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- Settings のバリデーション強化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値を検証し、不正な場合は ValueError を送出して早期検知。

- 実行／監視プロセスの優先度設定
  - Main 起動時に最初に set_process_priority("high") を呼び出すように変更し、重要プロセスの優先度を高める。

Fixed
- 環境変数のパースやポーリング間隔関連の堅牢化
  - MONITOR_POLL_INTERVAL が不正（整数でない、0 以下など）の場合に警告してデフォルト値（60 秒）へフォールバックする処理を追加。
  - .env を開けなかった場合に警告を出して安全に続行する挙動を追加。

- エラー耐性の向上
  - run_monitoring の監視ループ内で monitor.check_once() が例外を投げてもログ出力して継続するように変更（監視の高可用性を優先）。
  - process_priority / cpu_affinity 設定で権限不足や未実装の API に対して警告ログを出して処理継続するように改善。

Removed
- なし

Deprecated
- なし

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得する設計。未設定時は ValueError を投げて処理を中断（誤操作で公開キーを使うリスクを低減）。

Notes / Known limitations / TODO（コード中の注記に基づく）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価を使うフォールバックを検討中。
- position_sizing:
  - lot_size は現状全銘柄共通の想定（100）。将来的に銘柄別 lot_map を受け取る設計に拡張予定。
- ai/news_nlp:
  - OpenAI 呼び出しの完全実装（_fetch_articles 以降の処理）が大きな処理フローとなるため、実運用では API レートやコスト、エラーハンドリングの調整・監視が必要。
- monitoring:
  - 監視は説明文の通り「環境にかかわらず本番 sqlite_path を使用」するため、開発環境で意図せず本番 DB に書き込まないよう環境設定に注意が必要。

作者注
- この CHANGELOG は提示されたソースコードの内容から推測して作成した要約です。実際のコミット履歴や意図したリリースノートが存在する場合は、それに合わせて適宜更新してください。