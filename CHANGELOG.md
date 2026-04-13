# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
なお、以下はリポジトリの現状のコード内容から推測して作成した変更履歴（要約）です。

## [Unreleased]

- なし（リリース時点のスナップショットに基づく初期リリース想定）

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージとバージョン情報を追加
  - パッケージ初期化: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_execution: src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、engine.run_session() によるセッション実行を実装。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。

  - run_monitoring: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。

- 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
    - .env のパースは引用符・エスケープ・コメント処理に対応。
    - 環境変数読み取りユーティリティ Settings クラスを追加。J-Quants / kabu API / LINE / DB パス /監視関連設定 /しきい値 /実行環境判定（development/paper_trading/live）などをプロパティで提供。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のデフォルトパス処理を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

- ポートフォリオ構成モジュール（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全0 の場合は等金額配分にフォールバックして警告を出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数計算（calc_regime_multiplier）を実装。未知レジームはフォールバック（1.0）し警告を出す。
  - src/kabusys/portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）を実装。allocation_method に応じた "risk_based"/"equal"/"score" の算出、単元株丸め（lot_size）、1銘柄上限・aggregate cap によるスケールダウンと端数再配分ロジックを実装。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - cross-platform のプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows / POSIX（Linux, Darwin, FreeBSD）を考慮し、権限不足等の例外は警告でスキップするフェールセーフ仕様。

- リサーチ・ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value ファクター（calc_momentum, calc_volatility, calc_value）を DuckDB 接続を用いて実装。rolling ウィンドウや欠損データ取り扱いに配慮。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）およびランク変換ユーティリティ（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む仕組みを実装。
    - ニュース収集ウィンドウ（JST基準）計算、記事トリム（最大記事数・最大文字数）、バッチ化（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（部分的に DELETE→INSERT）等の堅牢化を実装。
    - OpenAI API キー未設定時は ValueError。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を実装。期間指定オプション（--from/--to）、DB パスオプション（--db）に対応。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の計算と閾値による PASS/FAIL 判定ロジックを追加（閾値はファイル内定数で管理）。
    - P95（パーセンタイル）計算、DB 存在チェック、テーブル未存在時のフォールバック処理などを実装。

- パッケージエクスポート
  - src/kabusys/portfolio/__init__.py と src/kabusys/research/__init__.py で主要 API をエクスポート。

### Changed
- （初期リリース相当のため変更履歴は主に追加中心）
- ログ出力や警告メッセージを各所に追加し、運用時の観察性を向上。

### Fixed
- 各種フェールセーフを追加
  - .env 読み込み失敗時のワーニング、プロセス優先度/CPU affinity 設定失敗時の警告処理、DuckDB executemany の制約回避（空 params のチェック）など。

### Notes
- 多くの機能は DuckDB / SQLite を前提に実装されているため、運用時は data ディレクトリや DB ファイルの配置・権限、環境変数（API キー、KABUSYS_ENV 等）の設定を確認してください。
- OpenAI を用いる機能は API キー（OPENAI_API_KEY）が必須です。テストや CI では外部呼び出しをモックする運用を推奨します。