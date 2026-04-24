CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （現時点で未リリースの変更はありません）

0.1.0 - 2026-04-24
-----------------
Added
- 初回公開：KabuSys 自動売買フレームワークのコアユーティリティ群と CLI を実装。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient による分離されたペーパートレードが可能。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 設定・検証・ウィザード
    - config.py: 環境変数管理クラス Settings を実装。自動 .env ロード（.env, .env.local の順）、値取得ユーティリティ、各種デフォルトパス、PAPER_FILL_MODE の値検証等を提供。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。シークレット項目のマスク表示、既存値の再利用、ファイル書き出し機能を提供。
    - validate_config.py: 起動前に .env と config/*.yaml の状況をチェックする検証 CLI を追加。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）・等金額配分・スコア加重配分を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear マップ）を実装。
    - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファを考慮した配分ロジックを実装。
    - portfolio/__init__.py: 上記機能をまとめて公開。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を行う。CLI で期間指定・DB 指定可能。
  - utils
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテーションのファイル出力（TimedRotatingFileHandler）をサポート。LOG_LEVEL / LOG_DIR による設定、既存ハンドラのクリアを行う。
    - utils/process_priority.py: psutil を利用したプラットフォーム非依存のプロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows / POSIX に対応し、未対応 OS や権限不足時は警告を出して安全にスキップする。
  - モニタリング DB 初期化フック（monitoring.monitoring_db の init 関数を利用）や DuckDB 接続サポートを主要スクリプトに追加。
  - research/factor_research.py: ファクター計算モジュール（モメンタム・ボラティリティ等）を追加（DuckDB 接続を受けて prices_daily/raw_financials を参照する設計、モジュールは部分実装）。

Changed
- なし（初回リリース）。ただし実装全体で以下の設計方針を明文化・適用：
  - データベースの分離：ペーパートレードは paper_trading 専用 SQLite を使用し、本番データと分離。
  - 環境設定の自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に基づき行うため、作業ディレクトリに依存しない。
  - ログは stdout に出力することで外部スケジューラとのリダイレクト運用を容易にした。

Fixed
- なし（初回リリース）。下記の堅牢性考慮を導入：
  - .env パーサは export プレフィックス、クォートされた値内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく扱えるように実装。
  - logging_setup はログディレクトリ作成に失敗した場合にファイル出力を安全にスキップし、既存ハンドラを正しく flush/close して二重登録を防止。
  - process_priority と set_cpu_affinity は権限やプラットフォームの制約で失敗しても警告を出して処理を継続するよう例外ハンドリングを追加。

Security
- なし（初回リリース）。ただし機密値（トークン・パスワード）は .env にて管理し、config_setup の出力にも「.env を Git にコミットしない」旨の注記を追加。

Notes / Usage tips
- MONITOR_POLL_INTERVAL 環境変数で監視ループのポーリング間隔を秒単位で設定可能。不正な値（0 以下や非整数）はデフォルト（60 秒）にフォールバックして警告が出る。
- 停止フラグのファイル（data/stop_requested.flag）を置くことで run_execution/run_monitoring の安全な停止が可能。
- validate_config と config_setup を組み合わせて .env を作成 → 検証するワークフローを推奨。
- PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等は Settings で厳密に検証され、不正値は ValueError を発生させる（起動前に validate_config を使うと良い）。

今後の計画（例）
- research/factor_research の完全実装（全ファクター計算の完成とテスト）。
- ExecutionEngine / OrderManager 周りの E2E テスト整備、BrokerClient の抽象化強化。
- 銘柄ごとの lot_size などマスタ参照による position sizing の拡張。
- モニタリング指標のダッシュボード化（DuckDB を用いた集計・可視化）。