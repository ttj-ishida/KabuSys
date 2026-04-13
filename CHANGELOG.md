CHANGELOG
=========

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- ドキュメント/補足: 現在のコードベースの最初のリリースノートを作成（自動生成）。
- 小さな内部改善やログ出力の調整、テスト補助のための環境変数制御などが随時追加されています。

[0.1.0] - 2026-04-13
-------------------

Added
- アプリケーション基盤
  - Settings クラスを実装し、.env / .env.local および環境変数から設定値を読み込む自動ロード機能を追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）。
    - .env パーサの実装（シングル/ダブルクォート、エスケープ、export プレフィックス、インラインコメント対応）。
    - OS 環境変数の保護（.env.local の上書き制御）。
  - アプリケーションバージョン (__version__ = 0.1.0) を追加。

- 実行 / 監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。環境に応じた DB 選択（paper_trading 時は paper_trading 用 SQLite を使用）と依存コンポーネントの組み立てを実装。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。
  - いずれのスクリプトも起動時にプロセス優先度を設定するフックを実行。

- DB / 分析基盤
  - DuckDB 接続を利用する研究・NLP・ファクター計算モジュールを追加。
  - 監視・トレードログ用の monitoring DB 初期化ユーティリティ (init_monitoring_db) の利用を組み込み（冪等にテーブル存在を保証）。

- ポートフォリオ構築（portfolio モジュール）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート/上限選出。
    - calc_equal_weights / calc_score_weights: 等比率・スコア加重配分の計算。
  - risk_adjustment:
    - apply_sector_cap: セクター集中の上限チェック（既存ポジション評価・売却予定銘柄の除外対応）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear とフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出、単元株丸め、aggregate cap によるスケーリング、cost_buffer を踏まえた保守的見積りを実装。

- リサーチ / ファクター（research モジュール）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: 財務指標（PER, ROE）を price と組み合わせて算出。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算。
    - calc_ic / rank / factor_summary: スピアマンIC（ランク相関）、順位付けユーティリティ、ファクター統計サマリを実装。
  - research.__init__ で zscore_normalize などのエクスポートを統合。

- ニュースNLP（ai/news_nlp.py）
  - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメントスコアを ai_scores に書き込む処理を実装。
  - 機能:
    - ニュース取得ウィンドウ計算（JST 基準を UTC に変換）。
    - 1銘柄あたりの件数・文字数トリム（上限値）。
    - 最大バッチサイズ、リトライ（429/ネットワーク断/5xx に対する指数バックオフ）と結果バリデーション。
    - スコアを ±1.0 にクリップして保存。
    - API キー未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等の検証レポートを標準出力へ生成。
    - 日付フィルタ (--from / --to) と --db オプションを提供。DB が存在しない場合のエラーメッセージを追加。
    - P95 計算、各種閾値による PASS/FAIL 判定を実装。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を追加（Windows の priority class / POSIX の nice 値対応）。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定する機能を追加。
    - アクセス権や未対応 OS では警告ログを出してスキップするフェイルセーフを備える。

Changed
- 設定関連
  - Settings.env/log_level/paper_fill_mode 等で入力値バリデーションを実装（不正値は ValueError）。
  - paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離。

- Monitoring/Execution
  - run_monitoring は monitoring 用に production sqlite_path を使用する設計（環境に依存せず監視データを一元化する意図）。
  - run_execution は paper_trading 時に paper 用 DB を使うよう明示。

- DB クエリ / 集計
  - latency の P95 計算を paper_verification_report に導入（全値収集による計算）。
  - SQL クエリは欠損データに配慮した NULL ハンドリング／カウント条件を追加。

Fixed
- .env パーサの強化による多くのケース（クォート内のエスケープ、export プレフィックス、インラインコメント、未設定行）の扱いを修正。
- process_priority の未対応環境や権限不足時にプログラムがクラッシュしないよう例外を捕捉して警告ログに変換。
- calc_score_weights: 全スコアが 0.0 の場合は等金額配分にフォールバックして警告を出すように修正。
- calc_position_sizes:
  - 価格欠損時のスキップ処理を明確化。
  - lot_size 単位での丸めや aggregate スケーリング時の端数配分ロジックを追加して過剰発注を防止。
- tools/paper_verification_report:
  - テーブルが存在しない等で sqlite3.OperationalError が発生した場合にデフォルト値（N/A 相当）で処理を継続するよう修正。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得し、未設定時は例外を投げて失敗を明示（誤設定防止）。

Notes / Known limitations
- portfolio.position_sizing は現時点で単元株数 (lot_size) を全銘柄共通で扱う。将来的には銘柄別 lot_size をサポート予定（TODO コメントあり）。
- apply_sector_cap は "unknown" セクターに対してセクター上限を適用しない（仕様）。
- news_nlp の OpenAI 呼び出しはネットワーク/API の挙動に依存するため、外部障害時はスコア取得が部分的に失敗する可能性がある。部分失敗に備えたデータ保護（対象コード絞り込みでの DELETE→INSERT）を実装している。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定可能（テスト用途）。

Breaking Changes
- なし（初回公開リリース）。ただし paper_trading 用 DB を用いる実行フローや Settings の厳密なバリデーションにより、既存環境変数の整合性が求められます。

作者連絡 / 参考
- 各モジュールのソースコメントおよび docstring に設計思想・利用方法が記載されています。実稼働環境へデプロイする際は .env 設定、権限（プロセス優先度設定）および API キーの管理に注意してください。