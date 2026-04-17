CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。
https://keepachangelog.com/ja/

[Unreleased]
------------

- 開発中。次バージョンでの変更はここに記載します。

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アーキテクチャと主要コンポーネントを実装（初回リリース相当）。
  - 実行系
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - エンジンはバックグラウンドスレッドで実行され、data/stop_requested.flag を検知して安全に停止可能。
      - プロセス優先度を起動直後に "high" に設定するユーティリティ呼び出しを組み込み。
      - execution の PID 管理（data/execution.pid）をサポート。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
      - data/stop_requested.flag による外部停止、KeyboardInterrupt のハンドリングと DB クローズ処理を実装。
  - 設定管理
    - config.py: 環境変数 / .env 自動読み込み機能を追加。
      - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
      - .env/.env.local の読み込み順と上書きルール（OS 環境変数の保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - 複数の設定プロパティを提供（DB パス、PID / kill flag パス、paper_trading 用設定、監視閾値、ログレベル、環境判定プロパティ等）。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - ポートフォリオ構築
    - portfolio モジュール（純粋関数群）を追加。
      - portfolio_builder.py: 候補選定 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分にフォールバック）。
      - risk_adjustment.py: セクター集中抑制 apply_sector_cap（"unknown" セクターは適用除外）、レジーム乗数 calc_regime_multiplier（bull/neutral/bear、未知は 1.0 でフォールバック）。
      - position_sizing.py: 発注株数算出 calc_position_sizes（risk_based / equal / score 対応、lot_size 単位丸め、aggregate cap によるスケールダウン、cost_buffer を考慮）。
  - 研究・リサーチ
    - research モジュールを追加（DuckDB を使ったファクター計算・解析）。
      - factor_research.calc_momentum / calc_volatility / calc_value：モメンタム・ボラティリティ・バリュー系ファクターを DuckDB 上で算出。
      - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank：将来リターン計算、IC（Spearman）計算、統計サマリ、ランク処理。
      - duckdb 結合クエリで効率的に集計する設計。
  - AI / ニュース NLP
    - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し ai_scores テーブルへ書き込む設計を追加。
      - ニュース時間窓の計算（JST ベース → UTC 変換）、記事集約（記事数・文字数上限）、バッチ送信（最大 20 銘柄 / 呼び出し）、レスポンスの検証、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライを想定。
      - システムプロンプトと JSON Mode を用いた出力仕様を明確化。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
      - 指定期間内の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）との比較で PASS/FAIL 判定を出力。
      - DB パスは引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの優先順位で解決。
  - ユーティリティ
    - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）と CPU affinity 設定を提供。アクセス権限不足や未対応 OS は警告でフォールバック。

Changed
- （初回リリースのため該当なし）

Fixed
- 各モジュールで次のような実装上のケアを行い堅牢性を向上:
  - config._parse_env_line: クォート付き値（バックスラッシュエスケープ対応）や inline コメントの扱い、export KEY=val 形式対応を実装。
  - portfolio.calc_score_weights: スコア合計が 0 の場合に等金額配分へフォールバックし WARNING ログを出力。
  - research.feature_exploration.rank: 同順位処理は平均ランクを返す実装（浮動小数丸めでの ties 検出対策として round を使用）。
  - tools.paper_verification_report: 各種クエリでデータ欠損時に N/A を返す安全処理を実装（OperationalError をキャッチしてフォールバック）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは必須で、news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を明示的に要求する設計（未設定時は ValueError を送出）。秘密情報の扱いに関する注意喚起を実装。

Notes / Known issues / TODO
- ai/news_nlp.py の実装は設計と多くのロジック（ウィンドウ計算・バッチ処理・リトライ・検証）を含んでいますが、提供コードは途中で切れており記事取得部分（_fetch_articles）などが未定義／未完了となっています。実運用前に _fetch_articles の実装および DB 書き込みロジック（DELETE/INSERT のトランザクション制御等）を完成させる必要があります。
- position_sizing.apply_sector_cap および related 箇所で価格が欠損（0.0）の場合の見積り不足に関する TODO コメントあり。前日終値や取得原価でのフォールバックを検討すること。
- DuckDB に対する executemany の制約を考慮した注意書き（news_nlp）があるため、大量書き込み時のパフォーマンスと部分失敗時の保護戦略を検証すること。
- process_priority.set_cpu_affinity / nice 設定は権限やプラットフォームに依存するため、環境によっては警告でスキップされることがある点に注意。

開発者向けメモ
- 環境変数と .env の自動読み込みはデフォルトで有効。テスト環境や CI で自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境は本番 DB と完全分離するための保護を意図しています。paper_trading 実行時は PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE の設定を確認してください。
- 各モジュールは極力外部サイドエフェクトを避け、DuckDB/SQLite 接続や Broker クライアント等は呼び出し元で注入する設計になっています。

--- 
（本 CHANGELOG はコードベースのコメント・実装から推測して作成しています。実際のコミット履歴が存在する場合はそちらを優先してください。）