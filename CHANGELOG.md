CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
別途リリースノートやタグを作成する際はここを更新してください。

Unreleased
----------
- なし（初回公開）

0.1.0 - 2026-04-13
-----------------
初回公開リリース。主な追加機能・実装内容は以下の通りです。

Added
- 基本パッケージとエントリポイント
  - パッケージ初期化 (kabusys.__init__) によるバージョン管理 (__version__ = 0.1.0)。
  - 実行用スクリプト:
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV=paper_trading の際は paper_trading 用 SQLite を使用し MockBroker を利用する仕組みを提供。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 環境設定・読み込み
  - config.Settings: 環境変数 / .env(.local) を扱う設定クラスを実装。
  - .env 自動読み込み: プロジェクトルートの検出（.git または pyproject.toml ベース）、.env と .env.local の読み込み順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - 環境変数パーサを強化: export プレフィックス対応、クォート文字・バックスラッシュエスケープ、行内コメントの扱いなどを実装。
  - Settings に各種プロパティを実装（データベースパス、PID/KILL ファイルパス、しきい値、PAPER_FILL_MODE 検証、KABUSYS_ENV / LOG_LEVEL 検証等）。
- 実行・監視周りユーティリティ
  - process_priority：プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度設定・CPU affinity 設定を行うユーティリティを実装。権限がない場合は警告を出して安全にスキップ。
- Execution コンポーネント（簡易構成）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の組み立てと実行フローを run_execution で実現。RiskManager にデフォルト RiskConfig 値を設定。
  - Paper Trading 用の DB 分離（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。
- 監視（Monitoring）
  - monitoring DB 初期化（init_monitoring_db）を実行開始時に行い、SystemMonitor を用いた定期チェックループを実装。例外時のログ出力とリトライ（次ループまで待機）を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、スコアが全て 0 の場合のフォールバック警告）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier、未知レジームは 1.0 でフォールバック）。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め（lot_size）、単銘柄上限や aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。
- リサーチ（DuckDB ベース）
  - research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、出来高指標）、バリュー（PER、ROE）を DuckDB の SQL とウィンドウ関数で実装。
  - research.feature_exploration: 将来リターン（複数ホライズン）、IC（スピアマンランク相関）計算、ランク関数（同順位は平均ランク）、ファクター統計サマリーを実装。標準ライブラリのみで完結。
  - DuckDB 接続を前提とし、外部 API や本番トレード API にはアクセスしない設計。
- AI / ニュース NLP
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメントを ai_scores テーブルに書き込む機能を実装。
  - 特徴:
    - タイムウィンドウ計算（JST の前日 15:00 ～ 当日 08:30 を UTC に変換）
    - 銘柄ごとの記事トリミング（件数・文字数上限）と 20 銘柄単位のバッチ送信
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - レスポンスバリデーションとスコアの ±1.0 クリッピング
    - 部分失敗に備えた安全な DB 更新（対象コードのみ置換）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定し標準出力にレポートを出力。DB が存在しない・テーブル欠損時のフォールバック処理（OperationalError を捕捉）を実装。
  - レポートの判定基準（しきい値）を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。

Changed
- なし（初回公開）。

Fixed
- 環境変数・入力値の堅牢化
  - MONITOR_POLL_INTERVAL: 0 以下や不正な値が与えられた場合は警告を出してデフォルトにフォールバックするように実装（run_monitoring）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL: 許容値チェックを実装し、不正値の場合は ValueError を投げて早期検出。
- ツールの堅牢化
  - paper_verification_report: テーブル欠損時に OperationalError を捕捉してレポート生成を継続するようにし、データ不足時には N/A 表示で明確化。

Security
- なし

Compatibility / Breaking Changes
- なし（初回リリース）。環境変数や DB パスは Settings を経由しており、既存の設定運用と互換性を保つ設計。ただし Settings が必須環境変数をチェックするので、未設定の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は起動時にエラーになります。

Notes / 今後の改善案（参考）
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の使用）や、銘柄別 lot_size のサポートを改善予定（TODO コメントあり）。
- ai.news_nlp の部分失敗リカバリや詳細なメトリクス記録の強化。
- DuckDB の executemany に関する注意点（空パラメータ回避）は現実装でケア済みだが、大量データ処理時のパフォーマンス改善余地あり。

署名
----
この CHANGELOG はコードベースの内容（モジュール構成・ドキュメンテーション文字列・実装コメント）に基づいて推測して作成しています。実際のリリースノート作成時は、コミットログやリリース管理情報を元に適宜調整してください。