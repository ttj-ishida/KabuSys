CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。

## [0.1.0] - 2026-04-17

Added
-----
- 基本パッケージ初期リリース。
- 実行用スクリプト:
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB から完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) によるプロセス制御をサポート。
    - プロセス優先度を高優先度へ設定し、スレッドで engine.run_session を実行する実装。
- 監視用スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負値や 0 はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示。
    - 停止フラグ (data/stop_requested.flag) により安全にループを終了。
- 設定 / 環境読み込み:
  - config.py
    - .env/.env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込みの優先度: OS環境変数 > .env.local > .env。OS側の環境変数は保護される（上書き禁止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパース機能を充実（export 形式対応、クォートやエスケープ対応、インラインコメント処理）。
    - Settings クラスを導入し、各種環境変数をプロパティとして公開。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須変数検証。
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（ペーパートレード DB）、PID_FILE_PATH 等のパス取得。
      - PAPER_FILL_MODE（instant|partial|never|reject）の検証。
      - KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL の検証。
      - 監視用しきい値（CPU/MEM/DISK）など。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合に等金額フォールバックと警告を出す挙動を実装。
  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 (apply_sector_cap)、市場レジームに応じた資金乗数 (calc_regime_multiplier) を実装。
    - "unknown" セクターの取り扱いやログ出力などの挙動を明記。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - risk_based / equal / score の allocation_method をサポート。
    - lot_size（単元）丸め、max_position_pct／max_utilization による単銘柄・総投下額上限、cost_buffer を用いた保守的見積もり、利用可能現金を超えた場合のスケーリング（端数処理：lot 単位での残差配分）を実装。
- 研究 (research) 機能:
  - research/factor_research.py
    - モメンタム、ボラティリティ（ATR, turnover 等）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials テーブルから計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - 大規模データを想定したウィンドウ・スキャン設計を採用。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、スピアマンランク相関による IC 計算（calc_ic）、ファクター統計要約（factor_summary）、ランク付けユーティリティ（rank）を追加。
    - 外部ライブラリ非依存の純 Python 実装。
  - research パッケージ __all__ を整備し、zscore 正規化などを公開。
- AI ニュース NLP:
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチで投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ、文字数上限、記事数上限を設計（_BATCH_SIZE=20、1銘柄あたり最大記事数/文字数制限）。
    - 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ（最大リトライ回数指定）。
    - 出力の厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分的な書き換え（対象コードのみ DELETE→INSERT）による部分失敗耐性。
    - calc_news_window による JST ベースのニュース対象ウィンドウ計算を提供。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - CLI オプション --from / --to / --db を提供し、SQLite の paper_trading DB から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を算出して標準出力へレポートを出力。
    - 合否判定の閾値を定義（稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 <= 200 ms）。
    - データ欠損時のフォールバック（テーブルがない場合でも処理継続）を実装。
- ユーティリティ:
  - utils/process_priority.py
    - set_process_priority(level) を追加（Windows と POSIX（Linux/macOS/FreeBSD）の差異を吸収）。
    - set_cpu_affinity(cpu_count) を追加（指定コア数への固定、エラー時は警告スキップ）。
    - 権限不足や未対応プラットフォーム時に警告し安全にスキップする実装。

Changed
-------
- 初期リリースのため該当なし（新規実装群）。

Fixed
-----
- 初期リリースのため該当なし。

Notes / Breaking changes / Migration
-----------------------------------
- 監視 (run_monitoring) はコード上で「常に本番 sqlite_path を使用する」実装になっています。テストや開発環境で別の監視 DB を使いたい場合は注意してください。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB を選択します（本番 DB と分離）。ペーパートレード運用時は PAPER_TRADING_SQLITE_PATH を設定して下さい。
- .env 自動ロードはデフォルトで有効。CI／テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を用いる ai/news_nlp.score_news は API キーが必須です（api_key 引数または環境変数 OPENAI_API_KEY）。API 失敗時はフェイルセーフでスキップする設計ですが、キー未提供時は例外を送出します。
- position_sizing の出力および内部ロジックは単元（lot_size）丸めなどのルールに依存します。将来的に銘柄別の lot_size を導入する余地を残しています（TODO 記載あり）。

Security
--------
- 現時点で特記事項なし。

Authors
-------
- コードベースから推測して生成された初期リリース記録です。詳細実装や追加の変更点は各モジュール内の docstring / ログ出力を参照してください。