CHANGELOG
=========

すべての利用者へ: この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴と完全に一致しない可能性があります。各項目はソース内の実装・コメント・エクスポート等から抽出した主要変更・機能を要約しています。

フォーマット: Keep a Changelog 準拠（英語版の見出しを日本語に置換）

Unreleased
----------

- （現状なし）新機能や修正があればここに追記してください。

0.1.0 - 2026-04-13
------------------

Added
- パッケージ初期リリース。
- 実行エントリ:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離して動作する設計を採用。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動するワークフローを実装。
    - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
    - 監視は環境に依存せず本番 sqlite_path を使用する設計。
- 設定管理:
  - config.py: 環境変数／.env ファイル読み込みユーティリティを実装。  
    - .git / pyproject.toml を探索してプロジェクトルートを自動検出し、.env, .env.local をロード（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - 複雑な .env パース（export プレフィックス、クォート内のエスケープ、インラインコメント取り扱い）をサポート。
    - Settings クラスで各種設定をプロパティとして提供（DB パス、API トークン、PID ファイルパス、監視しきい値、環境判定など）。入力値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- モニタリング:
  - monitoring_db 初期化の呼び出しを run 系スクリプトで行い、監視テーブルの存在を保証（冪等）。
  - SystemMonitor を利用するポーリングループで例外を捕捉してループ継続する堅牢化。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた資金乗数 calc_regime_multiplier を実装（レジーム未定義時のフォールバックとログ警告）。
  - portfolio/position_sizing.py: position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、個別上限・総投下上限、コストバッファを考慮したスケールダウンロジックを備える。
- 研究・ファクター:
  - research/factor_research.py: モメンタム・ボラティリティ・バリューのファクター計算を DuckDB 上で実装（prices_daily / raw_financials を参照）。MA200, ATR, 各種リターンを算出。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン）、IC（Spearman）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部依存を避け標準ライブラリのみで実装。
  - research __init__ で zscore_normalize を data.stats から公開。
- AI / ニュース:
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）へ送りセンチメントを算出して ai_scores テーブルへ書き込むワークフローを実装（DuckDB を使用）。  
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）と記事集約ロジック。
    - バッチサイズ、記事数・文字数制限、JSON Mode での厳密なレスポンス検証、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライを実装（上限あり）。
    - API キー未設定時は ValueError を送出。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を SQLite の monitoring テーブル群から集計して標準出力へ整形表示。閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。CLI オプションで期間指定 (--from, --to) と DB パス指定 (--db) に対応。
- ユーティリティ:
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加（psutil 使用）。Windows と POSIX（Linux, macOS, FreeBSD）を吸収し、失敗時は警告でスキップする安全設計。
- パッケージ設定:
  - __init__.py によるバージョン設定 (__version__ = "0.1.0") と主要サブパッケージのエクスポート。
- I/O / DB:
  - DuckDB と sqlite3 を組み合わせたデータ処理基盤を採用。DuckDB は主に時系列ファクター計算／AI 集約処理、SQLite は監視／注文履歴／paper_trading 用記録に利用。

Changed
- なし（初回リリースとしての追加が中心）。

Fixed
- 監視ループ等で例外が発生してもプロセスが落ちないよう例外捕捉を追加（run_monitoring の check_once 呼び出し周り）。
- .env 読み込みにおいて OS 環境変数を上書きしない保護ロジックを実装（.env.local は override 可だが protected を尊重）。

Security
- API キー等の機密情報は環境変数経由で取得し、.env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。.env ロード時に OS 環境変数は上書きされないよう保護。

Known issues / Notes
- ai/news_nlp.py の処理は外部 API（OpenAI）に依存するため、API レートや料金に注意が必要。API キー未設定時は明示的にエラーとなる。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を想定しており、将来的に銘柄別単元対応を検討する旨の TODO が残っている。
- sector exposure 計算では価格が欠損（0.0）の場合に過少見積りとなる可能性があり、将来的にフォールバック価格の導入を検討するコメントあり。
- research および portfolio モジュールは DuckDB / prices_daily / raw_financials 等の適切な前処理済みデータを前提としている。
- この CHANGELOG はソースコードからの推測に基づき作成しているため、実際のリリースノートやコミット履歴とは差異が生じる可能性があります。

参考
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/