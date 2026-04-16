# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

なお、この CHANGELOG はリポジトリ内のソースコードから推測して作成したものであり、
実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]


## [0.1.0] - 2026-04-15

初回リリース相当（ソースコードから推測）。

### Added
- 基本パッケージ・モジュールを追加
  - kabusys.__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 実行エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用する処理を導入。
    - ブローカークライアント生成のための BrokerClientFactory を利用。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立ておよびスレッド実行制御を実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - プロセス優先度を起動時に High に設定する仕組みを組み込む。
  - run_monitoring.py
    - SystemMonitor のポーリングループ実行スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続の確立を行う。
    - 停止フラグ検知によるループ終了処理を実装。
    - プロセス優先度を起動時に High に設定する仕組みを組み込む。
- 設定管理
  - config.py
    - .env ファイル自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
    - `.env` / `.env.local` の読み込み順と上書きルール（OS 環境変数保護）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止対応。
    - 各種環境変数ラッパーを提供（DB パス、API トークン、監視閾値、環境切替など）。
    - PAPER_FILL_MODE に対する検証ロジックを追加（有効値チェック）。
- ポートフォリオ構築関連の純粋関数群
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）ロジックを実装。lot_size、cost_buffer、aggregate cap によるスケールダウンを実装。
  - portfolio/risk_adjustment.py
    - セクター上限適用 (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
- 監視関連ユーティリティ
  - monitoring/monitoring_db.py（参照される初期化関数をコード上で呼び出しているため、監視 DB 初期化ロジックが存在）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ等を集計して標準出力へレポート出力。
    - CLI オプション --from / --to / --db を提供。PAPER_TRADING_SQLITE_PATH 環境変数もサポート。
    - 判定基準（閾値）をファイル内定数として定義 (稼働率 99%、注文成功率 90% など)。
- リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials テーブルを参照する設計。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク付けユーティリティ (rank) を実装。
  - research.__init__.py で zscore_normalize を含めたエクスポートを整理。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む仕組みを実装（スコアの切り取り、チャンク送信、バッチ処理、リトライ等の設計を含む）。
    - calc_news_window(target_date) を実装（JST ウィンドウ → UTC 変換）。
    - API キー解決、スコアクリップ、最大記事数・最大文字数制限などを実装。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows / POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告ログでスキップするフェイルセーフを実装。

### Changed
- DuckDB と SQLite の併用設計を導入
  - 実行系およびリサーチ系で DuckDB を analytical store として利用し、SQLite をトランザクション/監視ログ用に併設する形に統一。
- 環境変数ロードの動作
  - OS 環境変数を優先しつつ .env/.env.local を安全にロードする方式に変更。テスト等で自動ロードを抑止可能。

### Fixed
- （初期公開相当のため明示的な修正履歴は無し。コード内に多数の安全弁 (try/except、Input validation、ログ出力) を追加しているため堅牢性が向上していることを反映。）

### Known issues / Notes
- ai/news_nlp.score_news の実装が途中（ソースが切れている）:
  - provided code の終端が途中で切れており、記事取得フェーズや OpenAI 呼び出し後の DB 書き込み処理が完全に含まれていないため、現状はモジュールが部分実装の状態です。実運用前に残りの実装と統合テストが必要です。
- Monitoring の挙動に注意:
  - run_monitoring は KABUSYS_ENV に関わらず production 用 sqlite_path（settings.sqlite_path）を使用する設計になっているため、paper_trading と監視 DB が分離されていない点に注意してください（意図的な設計に見えるが環境ごとに別 DB を期待する運用では注意が必要）。
- .env のパースは柔軟だが完全なシェル互換ではない:
  - シングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントへの対応を含むが、あらゆる .env フォーマットの微妙な差異を保証するものではありません。極端に複雑な .env の場合は手動確認推奨。
- position_sizing の価格欠損に関する TODO:
  - price_map / open_prices に欠損（0.0）がある場合、現状はスキップしてしまいエクスポージャーが過少見積りされる可能性がある旨の注釈あり。将来的には前日終値等をフォールバックする改善が想定されている。
- 実行時権限や環境依存の処理:
  - set_process_priority / set_cpu_affinity は環境や権限によって失敗し得る（警告ログでスキップされる）。CI や限られたコンテナ環境では期待通りに動作しない可能性あり。

### Security
- OpenAI API キーの扱い:
  - ai/news_nlp.score_news は API キーを引数または環境変数 OPENAI_API_KEY で受け取る仕様。キーの管理は運用上の注意（秘密管理）を要する。

---

もし CHANGELOG に追記してほしい点（リリース日を正確なコミット日付に合わせる、Unreleased の差分を自動生成する等）があれば教えてください。コード差分（git のコミットログ等）を渡していただければ、より正確な履歴を生成できます。