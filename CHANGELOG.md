# Changelog

すべての注目すべき変更点をここに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  

※内容は与えられたコードベースから推測して作成しています。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-11

### Added
- パッケージ初期リリース。以下の主要機能を実装。
- 実行／監視用スクリプト
  - `run_execution.py`
    - ExecutionEngine を組み立て・起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、専用の paper_trading SQLite DB を使用（デフォルト: data/paper_trading.db）し、Mock ブローカー利用を想定して本番 DB と完全分離する挙動を提供。
    - DuckDB 接続との組み合わせで ExecutionEngine を起動（pid ファイルの利用）。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用する設計。

- 設定管理
  - `kabusys.config.Settings`
    - .env および .env.local の自動読み込み（プロジェクトルートが特定できる場合）。OS 環境変数を保護する仕組みあり。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値など）。
    - 環境変数値のバリデーションを実施（例: `KABUSYS_ENV` は `development|paper_trading|live`、`LOG_LEVEL` は標準的なログレベル、`PAPER_FILL_MODE` は `instant|partial|never|reject`）。

- ポートフォリオ構築 (純粋関数群)
  - `kabusys.portfolio.portfolio_builder`
    - `select_candidates`：BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - `calc_equal_weights`：等金額配分。
    - `calc_score_weights`：スコアで加重配分（全てのスコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - `kabusys.portfolio.risk_adjustment`
    - `apply_sector_cap`：セクター集中制限（既存ポジションの時価ベースで判定、当日売却予定銘柄は除外可）。"unknown" セクターは上限適用対象外。
    - `calc_regime_multiplier`：市場レジーム（"bull" / "neutral" / "bear"）に応じた投下資金乗数を提供。未知レジームは 1.0 でフォールバック（警告）。
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes`：リスクベース／等配分／スコア配分に基づく発注株数計算。単元株（lot_size）丸め、1 銘柄上限、投下資金の aggregate cap、コストバッファ（手数料・スリッページ見積り）を考慮したスケーリングと残余配分ロジックを実装。

- リサーチ機能（DuckDB ベース）
  - `kabusys.research.factor_research`
    - `calc_momentum`：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - `calc_volatility`：20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。欠損データの取り扱いに注意。
    - `calc_value`：raw_financials から直近財務データを取得し PER／ROE を計算。
    - いずれも DuckDB の SQL ウィンドウ関数を活用した実装。
  - `kabusys.research.feature_exploration`
    - `calc_forward_returns`：各ホライズンに対する将来リターン（horizons のバリデーションあり）。
    - `calc_ic`：ファクターと将来リターンのスピアマンランク相関（IC）を計算（データ不足時は None）。
    - `rank`, `factor_summary`：ランク付け（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）を提供。
  - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照する設計（ルックアヘッドバイアス対策が考慮されている）。

- AI（LLM）連携
  - `kabusys.ai.news_nlp`
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む。
    - タイムウィンドウは JST を基準に前日 15:00 ～ 当日 08:30 を UTC に変換して判定（calc_news_window）。
    - バッチサイズ、文字数上限、記事数上限、JSON mode を想定した厳格なバリデーション、スコア ±1.0 でクリップ、exponential backoff によるリトライ（429 / 接続断 / タイムアウト / 5xx）。
    - 部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT する冪等的な書き込みを行う（DuckDB の executemany の制約に配慮して空配列チェックあり）。
  - `kabusys.ai.regime_detector`
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - LLM 呼び出し失敗時は macro_sentiment を 0.0 として安全に継続するフェイルセーフ。
    - 結果は market_regime テーブルへ冪等書き込み。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する機能（設定なしは全コア使用）。
    - アクセス権限不足や未対応 OS に対する警告ログとフォールバック処理を実装。

- パッケージ情報
  - `kabusys.__init__.__version__` を "0.1.0" として追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数または環境変数 `OPENAI_API_KEY` から読み取る設計。未設定時はエラーを返す（AI 機能呼び出し時）。

### Notes / Usage / 環境変数（主要）
- .env 自動ロード:
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主な環境変数（デフォルトや制約を明示）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - SQLITE_PATH: 本番監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）。1未満や非整数はデフォルトにフォールバックして警告出力。
  - OPENAI_API_KEY: OpenAI 呼び出しに必須（AI 機能を使う場合）。
  - PAPER_FILL_MODE: instant | partial | never | reject（不正値は ValueError）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等の監視用設定。

### Limitations / Known behaviors
- monitoring（run_monitoring）は KABUSYS_ENV にかかわらず sqlite_path（本番）を使う設計のため、テスト時に注意が必要。
- DuckDB の executemany が空リストを受け付けない制約に配慮した実装になっている（空チェックを行う）。
- AI への出力は厳密な JSON を期待するが、実際には余分なテキストが混ざる可能性があるため復元ロジックを備える（最外の {} を抽出して JSON 解析を試みる）。
- テスト容易性のため、OpenAI 呼び出し関数をモック可能な設計（例: news_nlp._call_openai_api のパッチ）。

---

（以降のバージョンはここに追加）