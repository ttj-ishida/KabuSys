CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に従って記載しています。

Unreleased
----------
（今後のリリースに向けた保留中の変更／メモ）
- 一部モジュールに TODO や改善メモあり（価格欠損時のフォールバックや銘柄別単元対応など）。今後のリファクタ／拡張予定。

v0.1.0 - 2026-04-12
-------------------

Added
- 基本アーキテクチャとコアモジュールを追加。
  - 実行エンジン / 監視プロセス起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading モードの切替（モックブローカー使用）と、paper_trading 用の専用 SQLite DB 分離（デフォルト: data/paper_trading.db）。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用して監視データを一元管理。
  - 設定管理
    - kabusys.config.Settings: 環境変数読み込みとアクセス用プロパティ群を実装。自動 .env 読み込み（プロジェクトルート判定: .git / pyproject.toml）、.env と .env.local の読み込み順序、OS 環境変数の保護（protected）をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 各種設定プロパティを提供: J-Quants / kabu API / LINE トークン、duckdb/sqlite パス、paper trading 関連、監視閾値（CPU/MEM/DISK）や PID/KILL フラグ、ログレベル・環境（development/paper_trading/live）など。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
  - ユーティリティ
    - process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定関数を実装。Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、対応外 OS や権限不足時は安全にスキップして警告ログを出す。
  - ポートフォリオ構築
    - portfolio_builder: シグナル候補選別（スコア降順）と等重・スコア加重の重み計算を実装。スコア全てが 0.0 の場合のフォールバック処理あり。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジーム別の乗数マッピング（bull/neutral/bear）を定義。
    - position_sizing: 各種配分方式（risk_based / equal / score）に基づく株数計算、単元株丸め、per-stock 上限・aggregate cap（利用可能現金）でのスケールダウン、cost_buffer を考慮した保守的見積り、残差に基づく追加配分ロジックを実装。
  - 研究（Research）モジュール
    - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB を用いて実装（prices_daily / raw_financials テーブル参照）。200日移動平均、ATR、前方リターンなどを集計する純関数群。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman rank）計算、ファクター統計サマリー（count/mean/std/min/max/median）を実装。pandas など外部依存なしで実装。
    - research パッケージ再公開（zscore_normalize の再エクスポート等）。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores テーブルへ記録する仕組みを実装。バッチサイズ、トークン肥大化対策（最大記事数・最大文字数）、JSON Mode 想定の厳格なレスポンスバリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフ再試行、部分成功時の既存データ保護（部分的に DELETE/INSERT）等を設計。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成ツールを追加。コマンドライン引数 --from / --to / --db をサポートし、以下指標を算出・表示:
      - 稼働率（system_status から）、総ポーリング数、エラー数
      - 注文成功率（trade_logs: Created / Filled / Sent）
      - シグナル精度（Sent 送信率）、リスク却下数（risk_logs）
      - API レイテンシ（avg/max/P95）
      - Pass/Fail 判定（デフォルト閾値: 稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）
    - DB が無い場合の明確なエラーメッセージ出力、SQL 実行エラー（テーブルなし等）の安全なフォールバックを実装。

Changed
- ロギング・エラーハンドリングの改善
  - 起動スクリプトと各モジュールでのログメッセージを充実。監視ループ内での例外発生時は例外を捕捉して次回ポーリングへ継続させる。
- .env 読み込みの振る舞い
  - .env / .env.local の読み込み順序と「OS 環境変数保護」ロジックを実装。override フラグと protected キー集合により OS 環境を上書かない設計。
- 環境変数のバリデーションを追加
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検査を導入。無効値時は明確な ValueError を送出。

Fixed
- ポーリング間隔の扱いを堅牢化
  - MONITOR_POLL_INTERVAL のパースで 0 以下や不正な値を検出した場合、デフォルト（60 秒）へフォールバックし警告ログを出力。time.sleep へ不正値が渡らないように保護。
- DB 初期化の冪等性を確保
  - init_monitoring_db 呼び出しを起動時に行い、テーブルが存在しない場合でも安全に初期化することで実行時エラーを防止。

Security
- OpenAI API キー取り扱いの安全化
  - ai.news_nlp.score_news は引数 api_key または環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を返して明示的に失敗させる（誤動作の防止）。

Deprecated
- なし

Removed
- なし

Notes / 使い方の補足
- 自動 .env 読み込みはデフォルトで有効。テストから自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 実行時は本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。実運用時は適切にパスを設定してください。
- OpenAI を使ったニューススコアリングを行う場合、OPENAI_API_KEY を設定するか score_news に api_key を渡してください。API 呼び出しは外部ネットワークに依存するため、失敗時はログに残して継続する設計です。
- プロセス優先度の変更や CPU affinity の設定は OS 権限に依存します。権限不足や未対応プラットフォームでは警告を出してスキップします。

今後の予定（想定）
- ai.news_nlp の完全なエラー復旧・部分再試行ロジックの強化、DuckDB への安全な upsert 処理拡張
- position_sizing の銘柄別 lot_size 対応（stocks マスタからの取得）
- 価格欠損時のフォールバック（前日終値等）実装によるエクスポージャー計算の堅牢化
- テストカバレッジ拡充および CI ワークフロー整備

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリース履歴やバージョン管理のコミット履歴と差異がある場合は、該当するコミットメッセージやリリースノートに基づいて更新してください。