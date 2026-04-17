CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.

[Unreleased]
------------

- なし

[0.1.0] — Initial release
--------------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を監視して安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の挙動を明示。
    - SQLite / DuckDB 接続を確立し監視 DB テーブルを初期化。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に専用の paper_trading DB を使用（本番 DB と分離）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立て ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
    - data/execution.pid に PID を書き出す運用想定、停止フラグで安全に停止。

- 設定管理
  - src/kabusys/config.py の Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルートの .env / .env.local を読み込み、.env.local が優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パースの強化: export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ処理、インラインコメント処理。
    - 必須環境変数未設定時に明示的に ValueError を送出する _require 関数。
    - 各種設定プロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL, LINE_*（任意）
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PAPER_FILL_MODE（許容値検証）
      - PID ファイル / KILL フラグパス / 監視閾値（CPU / Memory / Disk）
      - KABUSYS_ENV 検証（development / paper_trading / live）
      - LOG_LEVEL 検証

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視用テーブルが存在することを保証（冪等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定、同点時の tie-breaker。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター別上限 (max_sector_pct) の適用（当日売却予定は除外、"unknown" セクターは制限の対象外）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear をマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method("risk_based" | "equal" | "score") に応じた発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap のスケールダウン処理、cost_buffer を加味した保守的見積り、残差を用いた追加配分ロジックを実装。
    - price が欠損・0 の場合はスキップする挙動を採用（ログ出力あり）。
    - 将来の拡張点として銘柄別 lot_size マップの TODO コメントあり。

- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を算出（窓サイズ未満は None を返す）。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE 計算（target_date 以前の最新財務を取得）。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（入力検証、最大ホライズンに基づくスキャン範囲制限）。
    - calc_ic: スピアマンランク相関（IC）計算。有効レコードが 3 未満なら None を返す。
    - rank, factor_summary: ランク化（同順位は平均ランク）・基本統計量計算（count/mean/std/min/max/median）を提供。
  - research パッケージは data.stats.zscore_normalize を再エクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、レイテンシ（avg/max/P95）などを算出・整形して標準出力に表示。
    - デフォルトしきい値（PASS/FAIL 判定）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 計算ユーティリティを実装。DB テーブルが存在しない場合の例外をハンドルして N/A を出力。

- AI ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - ニュース記事を銘柄別に集約し OpenAI API (gpt-4o-mini) でセンチメントスコア（-1.0〜1.0）を生成し ai_scores に書き込むロジックを実装。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの文字数・記事数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功に対する部分置換（DELETE→INSERT）などを設計。
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST を UTC に変換した範囲）を提供。
    - API キー必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装: Windows/Linux/macOS の差分抽象化（psutil 使用）、未対応 OS はスキップ、失敗時は警告して継続。
    - set_cpu_affinity(cpu_count) 実装: 指定コア数にプロセスをピンニング（None は全コア使用）。
    - 無権限エラーや未対応属性に対しては警告ログを出力して安全に続行。

Changed
- .env 読み込みの優先順位を明確化:
  - OS 環境変数 > .env.local > .env（.env.local は override=True）。
  - OS 環境変数は protected として上書き防止。
- Settings の検証ロジックを厳格化:
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の有効値チェックを追加し、不正値は ValueError。
- run_monitoring と run_execution の起動フローを明確化:
  - 起動直後にプロセス優先度を上げ、DB 初期化を行い、停止フラグや PID ファイルのハンドリングを追加。
  - run_execution は paper_trading 環境で mock ブローカーを使用し DB を分離。
- ポジションサイジングの aggregate cap 処理を導入:
  - 合計投資額が利用可能現金を超える場合にスケールダウンし、残余で lot 単位追加配分を行うアルゴリズムを実装。

Fixed
- .env パーサーの不具合修正 / 強化:
  - export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理の改善により .env の柔軟性と安全性を向上。
- DuckDB を使うリサーチ関数群での SQL 実装を安定化:
  - ウィンドウ・ラグ計算やカウント判定（必要行数未満は None）などの SQL 条件を整備。
- tools/paper_verification_report: 空データやテーブル未存在時に安全に N/A を返すハンドリングを追加。

Removed
- なし

Security
- 必須機密情報 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY) が未設定の場合は早期にエラーにして起動失敗（漏れ防止）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の意図しない上書きを防止）。

Notes / Known issues / TODO
- ai/news_nlp.py は大枠の設計と多くの処理を実装しているが、（スニペットの都合で）一部実装が切れている可能性があります。実運用ではエラーハンドリング・トランザクション（部分置換の原子性）・コネクション/バッチの境界条件を再確認してください。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損 (0.0) の場合、エクスポージャーが過少見積もられてブロックが回避される可能性がある旨の TODO コメントあり。必要に応じて前日終値や取得原価をフォールバックする実装を検討してください。
- position_sizing.py:
  - 現状は全銘柄共通の lot_size（既定 100）を使用。将来的には銘柄別 lot_map を受け取る拡張が想定されている。
- run_monitoring は説明どおり「監視は本番 sqlite_path を使用する」ため、開発環境での誤操作に注意してください（意図的な仕様）。

References
- この CHANGELOG はソースコード（src/ 以下のファイル）から推測して記載しています。実際のリリースノート作成時はコミット履歴・実際の変更差分・リリース日・影響範囲を合わせて確認してください。