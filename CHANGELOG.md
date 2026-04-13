# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。以下はリポジトリ内のソースコードから推測して作成した変更履歴です（コードの実装内容に基づく要約）。

注意: バージョン番号は src/kabusys/__init__.py の __version__ を参照しています。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションパッケージを追加（kabusys 初期リリース）。
  - バージョン情報: __version__ = "0.1.0"（src/kabusys/__init__.py）
- 設定管理機能（環境変数 / .env 読み込み）を実装
  - プロジェクトルート検出による自動 .env ロード（.git / pyproject.toml ベース）を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。（src/kabusys/config.py）
  - .env パーサは export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。（src/kabusys/config.py）
  - Settings クラスに各種プロパティを実装（DBパス、API トークン、Paper Trading 切替、監視閾値、PID/KILL ファイルパス、環境判定等）。（src/kabusys/config.py）
- 実行用スクリプトを提供
  - 実行エンジン起動スクリプト（ExecutionEngine エントリ）: 環境に応じた DB 分離（paper_trading は専用 DB を使用）、ブローカークライアントファクトリ、Order 管理・リスク管理・Reconciler 組立て、Engine 実行フローを実装。（src/kabusys/run_execution.py）
  - 監視ポーリング起動スクリプト（SystemMonitor エントリ）: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き、監視用 DB 初期化、PID ファイル使用、例外ハンドリング付きの永続ループを実装。（src/kabusys/run_monitoring.py）
- 監視 DB 初期化ユーティリティ（init_monitoring_db）を使用する統合ポイントを作成（実行・監視スクリプトで呼び出し）。
- Paper Trading 検証レポート生成ツールを追加
  - SQLite の paper_trading DB を元に稼働率・注文成功率・送信率・レイテンシなどを集計してレポートを標準出力へ出力する CLI ツール。（src/kabusys/tools/paper_verification_report.py）
  - P95 計算、期間フィルタ、閾値（稼働率99%、成功率90% 等）を定義し PASS/FAIL 判定を行う実装。
- ポートフォリオ構築関連モジュールを追加（純粋関数群）
  - 候補選定と重み計算（score / equal）: select_candidates, calc_equal_weights, calc_score_weights を実装。（src/kabusys/portfolio/portfolio_builder.py）
    - calc_score_weights は全銘柄スコアが 0 の場合に等配分へフォールバックして警告を出す。
  - セクター集中制限とレジーム乗数: apply_sector_cap（セクター別エクスポージャ判定で候補除外）と calc_regime_multiplier（bull/neutral/bear マップ、未知レジームはフォールバック）を実装。（src/kabusys/portfolio/risk_adjustment.py）
  - 株数決定・投下資金制御・単元丸め: calc_position_sizes を実装。risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap によるスケールダウン、cost_buffer を用いた保守的推定をサポート。（src/kabusys/portfolio/position_sizing.py）
- 研究（research）モジュールを追加
  - ファクター計算: モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を実装。（src/kabusys/research/factor_research.py）
  - 特徴量探索: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク付けユーティリティ、ファクター統計要約を実装（外部ライブラリに依存せず標準ライブラリのみで実装）。（src/kabusys/research/feature_exploration.py）
  - research パッケージのエクスポート設定を追加。（src/kabusys/research/__init__.py）
- AI ニュース NLP スコアリングモジュールを追加
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を実装。（src/kabusys/ai/news_nlp.py）
  - バッチサイズ、トークン肥大化対策（記事数/文字数制限）、スコアクリッピング、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、部分成功時の DB 保護（対象コードで削除→挿入）などを設計に含む。
  - ニュース収集ウィンドウ（JST基準）を calc_news_window として実装し、DB クエリで UTC ナイーブ datetime を利用する設計。
- プロセス優先度 / CPU affinity ユーティリティを実装（クロスプラットフォーム対応）
  - set_process_priority(level) は Windows / POSIX（Linux/Mac/FreeBSD）の差を吸収し優先度を設定、アクセス権限不足時は警告を出してスキップ。（src/kabusys/utils/process_priority.py）
  - set_cpu_affinity(cpu_count) によるコア固定機能を実装（引数チェック・権限失敗時の警告）。
- DuckDB と連携する設計
  - research / ai / run_* スクリプトで duckdb 接続を使用する実装（データ分析向け）。
- パッケージ化上の細部
  - tools パッケージ（__init__.py）を追加して CLI ツールを整理。

### Changed
- （初期リリースのため過去の変更履歴はありません）

### Fixed
- 入力値と環境値検証を強化
  - MONITOR_POLL_INTERVAL の値が不正（非正整数等）の場合にログを出しデフォルトへフォールバックするようにした。（src/kabusys/run_monitoring.py）
  - Settings の列挙型的な環境値（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）に対するバリデーションを実装し、不正値は例外で通知する。（src/kabusys/config.py）
  - 各種集計関数（report 生成等）でテーブルが存在しない場合の sqlite3.OperationalError をキャッチしてデフォルト値で継続するようにした。（src/kabusys/tools/paper_verification_report.py）
  - calc_position_sizes 等で価格が欠損している場合はスキップしてデバッグログを出す扱いを採用。（src/kabusys/portfolio/position_sizing.py）
  - process_priority の未対応 OS / 権限エラーをログでハンドリング。（src/kabusys/utils/process_priority.py）

### Security
- OpenAI API キーは関数引数で渡すか環境変数 OPENAI_API_KEY を参照する実装とし、未設定時は明示的に例外を送出。環境変数の取り扱いは .env 自動読込を任意で無効化できる。（src/kabusys/ai/news_nlp.py, src/kabusys/config.py）

---

もしこの CHANGELOG をリポジトリの実際の変更履歴として使う場合は、実際のコミット履歴やリリース日付に合わせて日付・セクションの調整を行ってください。必要であれば、より細かい機能ごとの抜粋や該当ソースコード行への参照を追加します。