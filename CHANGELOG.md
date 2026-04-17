CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（日本語）。

Unreleased
----------

### Added
- 全体
  - プロジェクトの初期機能群を実装（監視・実行エンジン・ポートフォリオ構築・リサーチ・AI ニューススコアリング等の主要コンポーネント）。
- 環境設定
  - .env / .env.local の自動読み込み機能を追加。プロジェクトルートは .git または pyproject.toml を探索して決定する実装に（src/kabusys/config.py）。
  - 環境変数読み込みの挙動制御: KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを強化し、export 構文、クォート文字列（バックスラッシュによるエスケープ）の取り扱い、インラインコメントのルールを実装（src/kabusys/config.py）。
- 実行／監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と完全分離する挙動を実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用することを明示。
  - 実行エンジンは停止フラグ（data/stop_requested.flag）および PID ファイルを扱う仕組みを備え、スレッドでセッションを起動・停止する処理を実装。
  - 監視・実行の起動時にプロセス優先度を設定するユーティリティを呼び出すように（高優先度で起動を試みる）。
- モニタリング DB 初期化
  - 監視用テーブルの冪等な初期化処理を提供（init_monitoring_db を各起動処理で呼び出す）。
- 実行関連コンポーネント
  - BrokerClientFactory によるブローカークライアント生成を統合（paper/live を抽象化）。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine 等の組み立て例を run_execution に実装。RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定し、initial_portfolio_value を broker.get_available_cash() から取得するフローを追加。
- Paper 検証ツール
  - paper_trading 用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。期間指定でシステム稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL 判定を出力。閾値は定数で明示（稼働率 99%、注文成功率 90% 等）。
- ポートフォリオ構築
  - 候補選定、重み計算、株数決定、セクター制限、レジーム乗数等の純関数群を実装（src/kabusys/portfolio/*）。
    - select_candidates: スコア降順かつ signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合のフォールバック実装あり。
    - calc_position_sizes: risk_based / equal / score の配分方式、lot_size（単元）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全側推定をサポート。
    - apply_sector_cap: 既存保有を基にセクター上限を判定し、上限超過セクターの新規候補を除外（売却予定銘柄はエクスポージャー計算から除外可能）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）。
- リサーチ
  - DuckDB 接続を前提としたファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - モメンタム、ボラティリティ、バリューの各計算関数（calc_momentum, calc_volatility, calc_value）を提供。長期移動平均や ATR、過去データスキャン範囲のバッファ等を考慮した SQL を使用。
  - 特徴量探索モジュールを実装（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、各種統計サマリー（factor_summary）、rank ユーティリティ等を提供。外部ライブラリ非依存の実装。
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。
- AI ニュース NLP
  - raw_news を OpenAI API（gpt-4o-mini を想定）でスコアリングし、結果を ai_scores テーブルへ書き込む基盤を実装（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算、銘柄ごとの記事集約、バッチ送信、リトライロジック（429/ネットワーク/5xx に対する指数バックオフ）等を設計。
    - 出力バリデーションとスコアクリップ（±1.0）を行い、部分的な失敗時でも既存スコアを保護するために対象コードで限定的に置換を行う方針を採用。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。Windows（psutil の HIGH_PRIORITY_CLASS 等）と POSIX 系（nice 値）を吸収し、サポート外 OS はスキップするフォールバックを用意。set_cpu_affinity によるコア固定もサポート。

### Changed
- 環境変数取り扱い
  - .env ロードの優先順位を OS 環境変数 > .env.local > .env に明確化（既存 OS 環境は保護）。
- 実行・監視起動
  - run_monitoring は監視専用に本番 sqlite_path を常に使用するように変更（環境に依存しない監視 DB を想定）。
  - run_execution は paper_trading モードで専用 DB を選択するように（settings.paper_sqlite_path を使用）。

### Fixed
- 環境変数パーサ
  - クォート内のバックスラッシュエスケープ処理やインラインコメントの誤認識を改善し、より堅牢な .env パースを実装（src/kabusys/config.py）。
- position sizing
  - aggregate cap 適用時に残余キャッシュで lot_size 単位の再配分を行うことで、より効率的に利用可能現金を配分するロジックを追加（src/kabusys/portfolio/position_sizing.py）。
- モニタリングの堅牢性
  - run_monitoring のポーリングループで例外発生時にループ継続するよう例外捕捉を追加（ログを残して次のポーリングへ）。

0.1.0 - 2026-04-17
------------------
- 初回公開リリース
  - 上記の主要機能群（監視・実行・ポートフォリオ構築・リサーチ・AI ニュース・ユーティリティ・ツール）をまとめてリリース。
  - パッケージ初期バージョンを 0.1.0 として設定（src/kabusys/__init__.py）。

注意事項 / 既知の制約
--------------------
- OpenAI API キーは必須（news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を要求）。未設定時は ValueError を送出。
- 一部の機能は DuckDB / SQLite 上の特定テーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / trade_logs / system_status / risk_logs 等）を前提とするため、該当テーブル・スキーマが存在しない場合は OperationalError を捕捉してフェイルセーフとして扱う実装が含まれている（paper_verification_report 等）。
- process_priority や cpu_affinity の設定は権限や OS に依存し、失敗した場合は警告を出してスキップするフォールバックを行う。
- news_nlp モジュールは API 呼び出し関連の実装が中心で、実データ集約の最後の部分で未完（提供されたコードは途中で切れている）。完全実装のためには記事取得関数や DB への書き込みロジックの続き実装が必要。

ライセンス / 貢献
----------------
- この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートはリポジトリの Git 履歴に基づいて修正・追記してください。