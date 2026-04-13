# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
バージョン番号はパッケージの src/kabusys/__init__.py にある __version__ を基準にしています。

※この CHANGELOG は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

（現在のリポジトリ状態が初回リリース相当のため、主な追加は以下の 0.1.0 にまとめられています。
今後の変更はここに追記してください。）

---

## [0.1.0] - 2026-04-13

初回リリース。自動売買システム「KabuSys」のコア機能群を実装しています。以下は主要な追加・仕様です。

### Added（追加）
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - 環境変数 KABUSYS_ENV によって paper_trading モードを判定し、paper_trading の場合は専用の SQLite DB（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - DuckDB 接続を渡して ExecutionEngine を起動する。EngineConfig と pid_file の受け渡しを行う。
    - RiskManager に対する初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を実装。
- 監視用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動エントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。不正値時は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定してから DB 接続・モニタを初期化。
- 設定管理
  - config.py
    - .env 自動ロード機能（.env / .env.local）: OS 環境変数を保護する protected 上書きロジックを実装。
    - プロジェクトルート探索（.git または pyproject.toml を基準）によりカレントワーキングディレクトリ非依存で .env を読み込み。
    - 環境変数パースの堅牢化（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行中コメント処理など）。
    - Settings クラスで多数のプロパティを提供（DB パス、PID ファイル、しきい値、PAPER_FILL_MODE 検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークルール）と重み計算（等分配・スコア加重）を実装。
  - portfolio/position_sizing.py
    - 発注株数計算（risk_based / equal / score）を実装。lot_size（単元株）単位で丸め、aggregate cap（利用可能現金）に対するスケーリングロジックを実装。
    - cost_buffer を考慮した保守的見積りと余剰キャッシュを用いた再配分ロジックを実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限: 既存保有のセクター・エクスポージャーに基づき、上限超過セクターの新規候補を除外。
    - レジーム乗数: "bull"/"neutral"/"bear" に応じた投下資金乗数を実装（未定義レジームは警告を出して 1.0 にフォールバック）。
- 監視 DB 初期化ユーティリティ
  - monitoring/monitoring_db.init_monitoring_db を利用して監視テーブルの存在を冪等的に保証。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity 固定機能（set_cpu_affinity）を実装。アクセス権限がない場合は警告でスキップ。
    - psutil の AccessDenied などに対する安全な例外処理と警告ロギング。
- リサーチ（ファクター・特徴量）
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、平均売買代金、出来高比率）、バリュー（PER/ROE）などファクター計算を DuckDB SQL で実装。
    - データ不足時の None ハンドリング、ウィンドウ幅の考慮、効率的なウィンドウ集約を実装。
  - research/feature_exploration.py
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）、ファクター統計サマリ、ランク生成ユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news テーブルから銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - 処理フロー: タイムウィンドウ計算（JST基準 → UTC変換）、記事トリミング（最大記事数・最大文字数）、20 銘柄単位のバッチ送信、リトライ（429/5xx/ネットワーク）と指数バックオフ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の局所的な DB 更新（既存スコア保護）などを実装。
    - OPENAI_API_KEY の未設定検出とエラー報告。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。CLI オプションで期間指定 (--from, --to) と DB パス指定（--db）を受け付け。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）、リスク却下数などを算出・表示。
    - P95 計算、DB 存在チェック、テーブル未存在時は安全に処理（sqlite3.OperationalError をキャッチして N/A とする）、閾値判定（PASS/FAIL）を実装。
- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要モジュールのエクスポート定義を追加。

### Changed（設計上の決定 / 仕様）
- DB 分離
  - paper_trading 環境は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 SQLite DB と完全分離することを明示。
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を参照する仕様。
- 環境変数ロード順序
  - OS 環境 > .env.local > .env の順でロード（ただし OS 環境は上書き保護）。
  - 自動ロードを明示的に無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
- エラー耐性
  - 各種 I/O / API / DB 操作で発生しうる例外を捕捉してログ出力のうえ処理を継続するフェイルセーフ設計（ex. monitoring の check_once() 失敗時に次ポーリングへ継続、OpenAI リトライ/失敗時はスキップして継続等）。

### Fixed（バグ修正・改善）
- .env パーサーの堅牢化
  - export 形式、クォート内のバックスラッシュエスケープ、行内コメントの扱いなどに対応し、不正な行を無視するよう改善。
- モニタ / 実行スクリプトの起動順序
  - プロセス優先度設定を最初に行うことで起動時の優先度反映漏れを防止。
- position_sizing のスケーリングロジック
  - aggregate cap 超過時のスケールダウン処理で端数配分の再割当てを lot_size 単位で行い、一貫性と再現性を確保。

### Documentation（ドキュメント）
- 各モジュールに詳細な docstring と設計方針コメントを追加。外部に依存しない設計意図（例: research や ai モジュールが本番 API にアクセスしない点）を明示。

### Security（セキュリティ関連）
- OpenAI API キーやその他秘密情報は Settings 経由で環境変数から取得し、未設定時には明示的にエラー／例外を発生させることで誤運用を検出しやすくしている。

---

注記:
- 上記はコードから推測した変更履歴・機能一覧です。実際のコミット履歴や作者の意図に基づく項目とは異なる場合があります。
- 今後のリリースでは Unreleased セクションに変更点を追記し、リリースごとにバージョンと日付を付与してください。