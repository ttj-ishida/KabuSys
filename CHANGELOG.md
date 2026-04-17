CHANGELOG
=========

すべての重要な変更点を記録します。
このファイルは Keep a Changelog の形式に準拠しています。
リリース日は本リポジトリの現行状態（src 内の __version__ = 0.1.0）に基づき記載しています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更・挙動改善
- Fixed: バグ修正
- Removed, Security: 必要に応じて記載

[Unreleased]
------------

（現在のリポジトリ状態は 0.1.0 として初回リリースされています。将来の変更はここに記載してください。）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本インフラ・実行スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止フラグファイル data/stop_requested.flag の検知でループを終了。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する仕様を明示。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（data/paper_trading.db）を使用し本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine を別スレッドで実行、停止フラグ検知で安全停止。

- 設定管理・自動 .env 読み込み
  - config.py: プロジェクトルート自動検出（.git または pyproject.toml を基準）と .env / .env.local の安全な読み込み機能を追加。
    - export KEY=val 形式やクォート内エスケープ、行末コメント等のパースに対応。
    - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - Settings クラスでアプリケーション設定をプロパティ化（DBパス、paper_trading 用パス、各種閾値、env/log_level 検証等）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークに signal_rank を採用。
    - calc_equal_weights / calc_score_weights: スコア加重と等金額配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用する関数。既存ポジション・当日売却対象を考慮。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap 減衰・残差配分を実装。

- 研究・リサーチ機能
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算を提供。
    - 各ファクターはデータ不足時に None を返すよう設計。
  - research/feature_exploration.py:
    - calc_forward_returns、calc_ic（Spearman のランク相関）、rank、factor_summary（統計サマリ）を追加。
    - 外部ライブラリ非依存で標準ライブラリのみで実装。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) を追加し、Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピン留め可能。失敗時は警告でスキップ。
    - アクセス権限や未対応 OS の場合に安全にフォールバック。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - DB が存在しない・テーブルが無い場合の例外ハンドリング（sqlite3.OperationalError でフォールバック）を実装。

- AI / ニュース NLP（下流処理の骨格）
  - ai/news_nlp.py:
    - ニュースのタイムウィンドウ計算、OpenAI (gpt-4o-mini) を用いたバッチスコアリングの設計・定数を追加。
    - API キー解決、リトライ方針（指数バックオフ）、スコアクリッピング等の仕様を定義。
    - （注）スクリプトは途中で切れている箇所あり（_fetch_articles 呼び出し以降が未完/省略）。

Changed
- 実行時のプロセス優先度
  - run_monitoring.py / run_execution.py の main() 開始時に set_process_priority("high") を呼び出してプロセス優先度を上げるようにした（重要処理の優先確保）。

- DB 初期化と接続の扱い
  - init_monitoring_db(sqlite_conn) を実行して監視用テーブルの存在を保証（冪等）。
  - run_monitoring は環境に依存せず Settings.sqlite_path（本番想定）を使用する旨を明示。run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。

- .env パースの強化
  - export キーワードや引用文字列内のバックスラッシュエスケープ、行内コメントの扱いをサポートし、より現実的な .env ファイルに対応。

Fixed
- ポーリング間隔の不正値対策
  - MONITOR_POLL_INTERVAL の値を整数化し、1 未満の値や不正な文字列は警告を出してデフォルト（60 秒）にフォールバックするようにした（time.sleep に無効な値を渡さない）。

- DuckDB / SQLite 操作の堅牢化
  - tools/paper_verification_report.py にて、対象テーブルが存在しない場合に sqlite3.OperationalError をキャッチしてレポート生成を継続できるようにした。

Notes / Known issues
- ai/news_nlp.py はスコアリングワークフローの多くを記述しているが、ファイル末尾が途中で切れており記事取得部分（_fetch_articles）以降の実装が欠落／省略されています。実運用前に未実装部分を補完してください。
- position_sizing.calc_position_sizes は現在単元株数を全銘柄共通の lot_size (デフォルト 100) として扱う。将来的に銘柄別 lot_size をサポートするための拡張コメントを残しています。
- config.py の自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後やルートが検出できない環境では自動ロードがスキップされます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御してください。

開発メモ
- 本リリースは初期バージョン（0.1.0）として、システム監視、実行エンジン起動、ポートフォリオ構築ロジック、リサーチ用指標計算、Paper Trading 向け検証ツール、及び OpenAI を用いたニューススコアリングの骨組みを提供します。
- 今後のリリースでは ai/news_nlp の完全実装、追加のテストカバレッジ、エラーハンドリング改善、および性能チューニングを計画しています。