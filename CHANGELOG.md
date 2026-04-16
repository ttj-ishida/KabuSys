# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
主にソースコードの内容から推測して記載しています。

## [Unreleased]

### 追加 (Added)
- 起動スクリプトを追加 / 拡張
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計注記を追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、paper_trading 専用 DB (data/paper_trading.db) を使用する分離設計。
    - 停止フラグと PID ファイルを用いた安全な起動/停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築関連の純粋関数群を追加
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)、マーケットレジームに応じた乗数 (calc_regime_multiplier) を実装。
  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジック (calc_position_sizes) を実装（risk_based / equal / score の配分方式に対応、lot_size、コストバッファ、aggregate cap のスケールダウン機能を含む）。
  - src/kabusys/portfolio/__init__.py
    - 上記 API をパッケージとして公開。

- 研究・リサーチ関連を追加
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いた SQL ベースの計算）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマン ρ）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク変換 (rank) を実装。
  - src/kabusys/research/__init__.py
    - 研究モジュール API をエクスポート。

- AI ニュース NLP スコアリング基盤を追加
  - src/kabusys/ai/news_nlp.py
    - raw_news から銘柄ごとのニュースを集約し、OpenAI API (gpt-4o-mini) を用いてセンチメントを算出・ai_scores テーブルへ格納する処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、文字数/記事数制限、レスポンスの検証、スコアの ±1.0 クリップ、リトライ（指数バックオフ）戦略などを含む。
    - ニュース収集ウィンドウ（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）を明示的に計算するユーティリティを提供。

- ツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、PASS/FAIL 判定（閾値はソース内定義）を出力。
    - --from/--to/--db のコマンドライン引数対応。

- 設定・環境変数処理の強化
  - src/kabusys/config.py
    - .env ファイル自動読み込み（プロジェクトルート検出ロジック .git / pyproject.toml）。
    - .env のパース強化（export プレフィックス対応、クォート中のエスケープ、インラインコメントの取り扱い）。
    - 設定取得用 Settings クラスを追加。多くの設定プロパティ（DB パス、PID/フラグパス、各種閾値、PAPER_FILL_MODE の検証等）を実装。
    - KABUSYS_ENV / LOG_LEVEL の値検証を追加。

- ユーティリティ改善
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度設定（set_process_priority）を提供。
    - CPU affinity 設定（set_cpu_affinity）を追加。
    - psutil の例外（AccessDenied, AttributeError, NotImplementedError）を捕捉してフォールバックする安全策を実装。

- パッケージ初期化
  - src/kabusys/__init__.py にバージョンとエクスポート一覧を追加（__version__ = "0.1.0"）。

### 変更 (Changed)
- DB 接続動作
  - monitoring の初期化（init_monitoring_db）を起動ルーチン両方で呼び出すようにし、監視テーブルが存在することを冪等に保証するよう変更。
  - run_execution.py は paper_trading 環境では専用の SQLite DB を使用するように分離（本番 DB と完全分離）。

- エラーハンドリング・堅牢化
  - 多くの計算関数で None / データ不足 / 0 値に対するガードを追加（例: ファクター計算・P95 計算・レイテンシ集計・position sizing の価格欠損時ログ）。
  - OpenAI 呼び出しに対するリトライ戦略とレスポンス検証の設計を盛り込み、API エラー時も処理継続するフェイルセーフを設計。

### 修正 (Fixed)
- .env パーサーの不具合対策
  - クォート内のバックスラッシュエスケープやインラインコメントの誤解釈を修正するロジックを導入。
- 端数処理とスケーリングの安定化
  - position_sizing の aggregate cap スケーリングで端数分配を lot 単位で行う際、残余キャッシュで再配分するロジックを実装し、安定性を向上。
- レポート生成の欠損耐性
  - paper_verification_report は対象テーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値で処理を継続するよう修正。

### 既知の制約 / 注意点 (Known issues / Notes)
- run_monitoring は Monitoring 用の DB として常に settings.sqlite_path（本番想定）を参照する設計になっているため、paper_trading 環境で監視を分離したい場合は運用側で注意が必要。
- ai/news_nlp.py のソースはファイル末端で一部切れている（コード断片の終端）。実装上の細部（記事フェッチ関数や最終的な DB 書き込み手順）はコード末尾の続きに依存するため、実行前に未完の部分を補完する必要あり。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の価格フォールバック戦略等）。

## [0.1.0] - 2026-04-11
- 初期リリース
  - 基本的なパッケージ構成とバージョン情報を含む軽量な初期実装。
  - （__version__ = "0.1.0" を設定）

---

参照:
- 各ソースファイルの関数・ドキュメント文字列に基づいて記載。実際のコミット履歴が存在する場合はそちらを優先してください。