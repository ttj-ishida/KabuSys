# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-16
初回リリース — コードベースの初期実装をまとめたリリースです。

### 追加 (Added)
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 実行エントリ / ランタイム
  - run_monitoring.py
    - SystemMonitor を用いた常駐監視ポーリングループを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知によるグレースフルな終了を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - Monitoring は環境に依らず本番 `sqlite_path` を使用する動作を明記。

  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時に MockBrokerClient を使用し、paper_trading 用の SQLite DB（`data/paper_trading.db` をデフォルト）に記録して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等のコンポーネント組み立てと ExecutionEngine 起動を実装。
    - ストップフラグ検知でエンジンを停止する仕組み（スレッド実行とデーモン化）。
    - PID ファイルパスの取り扱い、監視テーブルの初期化を行うための init_monitoring_db 呼び出しを追加。

- 設定管理
  - config.py
    - .env / .env.local 自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml を基準。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサの実装強化:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮したパース処理
    - Settings クラスを導入し、各種環境変数アクセスをラップ（検証ロジックつき）。
      - DB パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH）
      - PAPER_FILL_MODE（有効値検証）
      - KABUSYS_ENV / LOG_LEVEL の検証
      - 各種監視しきい値（CPU/MEM/DISK）や PID／kill flag のパス等をプロパティで提供

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)
    - 等金額配分 (calc_equal_weights)
    - スコア加重配分 (calc_score_weights)（全スコアが 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 (apply_sector_cap)
    - 市場レジームに応じた乗数 (calc_regime_multiplier)（'bull'/'neutral'/'bear' 対応、未知レジームは 1.0 でフォールバック）
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づいた株数計算を実装
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を使った保守的見積りを実装
    - price 欠損時のスキップやログ出力、残差に基づく追加割当ロジックなどを実装

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB 接続を受け、prices_daily/raw_financials を参照）
    - 計算窓・欠損ハンドリング、ウィンドウサイズ等を定義
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)
    - スピアマンランク相関（IC）計算 (calc_ic)、ランク変換ユーティリティ (rank)
    - ファクター列の統計サマリー (factor_summary)

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ等を集計し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ (--from / --to)、DB パス指定オプション (--db) をサポート。

- AI / ニュース NLP（ベータ）
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄単位で記事を集約し、OpenAI（gpt-4o-mini）を用いたセンチメントスコアを ai_scores テーブルへ書き込む処理を設計・実装。
    - バッチ送信、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリップなどの設計を含む。
    - ニュース収集ウィンドウ（JST→UTC 変換）関数 calc_news_window を実装。
    - （注）ファイルは途中で切れている箇所があり、処理本体の一部が未完了。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows と POSIX の差分を吸収）。
    - set_cpu_affinity(cpu_count) でプロセスの CPU affinity 設定をサポート。
    - 実行環境で権限が足りない場合は警告ログを出して安全にスキップ。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env 読み込みの堅牢化:
  - クォート / エスケープ / コメント処理の改善により .env のパースで落ちにくくした。
- 各種関数での None / データ欠損時の安全な取り扱いを強化（DB クエリ結果の None チェックや P95 計算時の空リストハンドリング等）。

### 既知の問題 / 注意点 (Known issues / Notes)
- ai/news_nlp.py が途中で切れている（末尾に処理が未完）。OpenAI API 呼び出し以降の処理（記事抽出の調整、バッチ送信、DB 書き込み等）が未完成の可能性あり。実運用前に該当箇所の完成と十分なテストを推奨。
- position_sizing.calc_position_sizes 内の TODO:
  - 個別銘柄ごとの lot_size を将来的に導入する設計を想定（現在は全銘柄で固定 lot_size）。
- apply_sector_cap の価格欠損時の挙動:
  - price_map に価格が欠損（0.0 等）の場合、エクスポージャーが過小見積りされセクター制約が外れる可能性がある旨の注記あり。必要に応じてフォールバック価格（前日終値等）の導入を検討してください。
- process_priority の設定は OS と実行権限に依存するため、権限不足での警告ログが発生する場合があります（正常動作）。
- DuckDB の executemany に関する注意:
  - ai モジュールの設計文書にある通り、executemany に空 params を渡すとエラーになるため、パラメータ空時の処理回避が必要。

### 破壊的変更 (Breaking Changes)
- なし（初回公開）

### セキュリティ (Security)
- なし（既知の機密漏洩や脆弱性は確認されていないが、OpenAI API キーなど秘密情報は環境変数で管理すること。`.env` ファイルをリポジトリへコミットしないでください。）

--------------------------------
注: 本 CHANGELOG はリポジトリ内の現行ソースコードから推測して作成したものです。実装意図や追加の変更履歴がある場合は適宜更新してください。