# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

全般的な注意
- 本 CHANGELOG は与えられたコードベースの内容から機能追加・振る舞い・修正点を推測して作成しています。
- パッケージバージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [0.1.0] - 2026-04-16

### Added
- 基本アーキテクチャ・実行コンポーネントを追加
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - スレッドでエンジンを起動・監視し、外部 stop フラグファイルで安全に停止可能。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを作成（テスト用 MockBroker 対応想定）。
    - RiskManager / OrderManager / Reconciler を組み立てて ExecutionEngine を実行。
  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - stop フラグファイル検知でループを終了。
    - Monitoring は環境に関わらず本番 sqlite_path を利用する仕様。
  - 環境設定管理モジュール (src/kabusys/config.py)
    - .env / .env.local の自動ロード（OS 環境変数を保護して上書き制御）。
    - .env 行パーサを実装（コメント・export/クォート/エスケープに対応）。
    - 多数のプロパティ（DB パス、PID パス、閾値、env 判定、paper_trading 関連等）を提供。
  - プロセス制御ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）設定を提供。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。
  - ポートフォリオ構築関連 (src/kabusys/portfolio/)
    - portfolio_builder: 候補選定（select_candidates）、等重・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 複数手法（risk_based / equal / score）による株数決定ロジック、単元（lot）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積もりなどを実装。
    - 主要な設計注記（欠損価格の扱い、将来的な lot_size 拡張など）を付記。
  - 研究・リサーチモジュール (src/kabusys/research/)
    - factor_research: momentum / volatility / value ファクター計算（DuckDB を直接使用、prices_daily/raw_financials を参照）。
    - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ関数（標準ライブラリのみで実装）。
    - DuckDB を使った高速 SQL ベースの実装。データ不足時は None を返す等の堅牢な設計。
  - AI ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini 想定）にバッチ送信し、銘柄別センチメント（±1.0）を ai_scores テーブルに保存する処理を実装。
    - バッチサイズ、記事数上限、文字数上限、JSON 出力の厳格検証、スコアクリップ、429/5xx/ネットワークエラーに対する指数バックオフリトライなどを備える。
    - タイムウィンドウ計算（JST を基準に前日 15:00 〜 当日 08:30）を明示的に実装。
  - ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
    - SQLite（paper_trading.db）から集計し、稼働率、注文成功率、送信率、P95 レイテンシなどを計算して標準出力レポートを生成。
    - 日付フィルタ、P95 計算、閾値による PASS/FAIL 判定、欠損テーブルに対する安全なフォールバック（OperationalError 捕捉）を実装。
  - パッケージ初期化情報 (src/kabusys/__init__.py)
    - __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

### Changed
- 環境変数・.env の取り扱いを強化
  - プロジェクトルート探索を .git / pyproject.toml を基準に行い、パッケージ配布後も CWD に依存せずに .env を自動ロードする仕組みを採用。
  - .env.local は .env の上書き（ただし OS 環境変数は保護）として扱う。
- 実行時の優先度設定をデフォルトで高優先度に設定
  - run_monitoring.run と run_execution.main の起動時に set_process_priority("high") を呼び出すようにし、重要プロセスのスケジューリング優先度を確保。
- Paper Trading と本番 DB の明確な分離
  - is_paper 判定により paper_sqlite_path を使用するフローを導入し、paper_trading 時のデータを完全分離してローカル検証可能に。
- レジーム・セクター関連ポリシー明文化
  - calc_regime_multiplier のマッピング（bull/neutral/bear）と、Bear が通常 BUY シグナルを生成しない設計に関する注記を追加。
  - apply_sector_cap で "unknown" セクターは上限判定から除外する挙動を明記。
- position_sizing のスケーリング挙動改善
  - aggregate cap 適用時のスケールダウンと lot_size 単位での残余配分アルゴリズムを実装。cost_buffer を加味して約定コストを保守的に見積もる。

### Fixed
- 環境変数パースの堅牢化
  - export キーワード、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、不正な行や空行を無視するようにした。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 0 以下や数値変換失敗時は警告を出してデフォルト（60 秒）にフォールバックするように。
- run_monitoring / run_execution のリソースクローズを確実化
  - 最終処理で sqlite3 / duckdb のコネクションを確実に close するように保証。
- Paper 検証レポートの堅牢化
  - テーブルが存在しない状況で sqlite3.OperationalError が発生してもレポート生成を継続できるよう try/except を追加（各集計クエリ単位でフォールバック値を使用）。
- AI ニュース処理の安全措置
  - API キー未設定時は明示的な ValueError を送出し、部分失敗時にも既存スコアを保護して書き換える仕組み（対象コードを限定した DELETE/INSERT）を採用。

### Security
- OpenAI API キーの取得は引数優先、その後環境変数 OPENAI_API_KEY を参照する安全なフローを採用。未設定時は明確なエラーで通知。

### Deprecated
- なし

### Removed
- なし

---

注: 上記は現行ソースコードの実装内容に基づく初期リリース向け CHANGELOG です。将来的な変更ではカテゴリ（Added/Changed/Fixed 等）を継続的に追記してください。