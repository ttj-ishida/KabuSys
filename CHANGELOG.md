# Changelog

すべての変更は Keep a Changelog の形式（https://keepachangelog.com/ja/1.0.0/）に準拠しています。  
このファイルは、与えられたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- なし（現時点で未リリースの変更はありません）。

## [0.1.0] - 2026-04-17
初回公開リリース。システム全体の起動スクリプト、設定管理、ポートフォリオ構築、ポジションサイズ計算、リスク調整、リサーチ用ファクター計算・解析、ニュースNLP連携、監視・実行エンジン周りのユーティリティ等を含むフルスタックな自動売買・検証ツール群を追加。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理。
    - 監視用 DB は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨を明示。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し、本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH により上書き可能）。
    - MockBrokerClient の利用（paper_trading）や PID / 停止フラグ管理を実装。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml ベース）。
    - .env / .env.local の読み込み順制御、OS 環境変数保護（上書きガード）。
    - 複数の設定プロパティを提供（DB パス、PID パス、監視閾値、PAPER_FILL_MODE など）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（スコア降順、signal_rank によるタイブレーク）。
    - 等重み・スコア加重の重み計算（スコア合計が 0 の場合は等重みへ警告付きフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier、未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数決定ロジック。
    - 単元株丸め、per-position 上限、aggregate cap によるスケールダウン（cost_buffer 考慮）。
    - lot_size 固定（将来的な拡張を想定した TODO コメントあり）。

- リサーチ / ファクター計算
  - research/factor_research.py
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、流動性）、Value（PER/ROE）等の DuckDB ベース計算関数を追加。
    - 不足データに対する None ハンドリングを実装。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）。
    - IC（スピアマンランク相関）計算（calc_ic）とランク関数（rank）。
    - ファクター統計サマリー（factor_summary）。
    - 標準ライブラリのみでの実装、外部依存を避ける設計。
  - research/__init__.py
    - 主要関数と zscore_normalize の公開。

- ニュース NLP / AI
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント付与し、ai_scores テーブルへ書き込むスコアリング機能を追加（バッチ処理、スコアクリップ、レスポンス検証、リトライ戦略）。
    - タイムウィンドウ計算（JST→UTC変換）や記事トリム（最大記事数・最大文字数）等のトークン対策を実装。
    - API キー未設定時は ValueError を送出する明示的なチェックを実装。
    - フェイルセーフ: API 失敗時は部分スキップで継続し、既存スコアを保護する書き換え戦略（DELETE→INSERT を絞った条件で実行）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を表示。
    - P95 計算や日付フィルタ機構、DB パス指定オプション（--db / PAPER_TRADING_SQLITE_PATH）を提供。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows と POSIX を吸収）。
    - CPU affinity 設定関数（set_cpu_affinity）を追加。
    - 権限不足や未対応 OS の場合は警告してスキップする堅牢性を実装。

- パッケージ管理
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースにおける新規追加が中心）。

### Fixed
- .env パーサーの堅牢化（config._parse_env_line）
  - export プレフィックス対応、クォート文字内のバックスラッシュエスケープ対応、インラインコメント処理、クォートなし時のコメント識別の改善。
- monitoring_db 初期化（init_monitoring_db の呼び出し）を起動時に行い、監視テーブル存在を保証（冪等）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- ai/news_nlp の利用に OpenAI API キーが必要である旨を明記。未設定の場合は明示的にエラーを出す設計により誤操作を防止。

### Breaking Changes / 注意事項
- run_monitoring.py は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明記されているため、開発環境で監視を実行すると本番の monitoring DB を参照／書き込みする可能性があります。開発運用時は sqlite_path を適切に設定するかコードを変更してください。
- run_execution.py は paper_trading モード時に専用 DB（PAPER_TRADING_SQLITE_PATH）を使うことで本番 DB との分離を図っています。paper_trading を使う場合は DB パスの確認を推奨します。
- set_process_priority はプラットフォームや権限に依存するため、期待した優先度変更が行えない場合はログの警告を確認してください。
- news_nlp の外部 API 呼び出しはレート制限やコストが発生します。バッチサイズやリトライ設定は定義済み（_BATCH_SIZE, _MAX_RETRIES 等）ですが、運用環境に合わせた調整を推奨します。

---

今後のリリースでは以下のような改善が想定されます（例）:
- ニュース NLP の部分的失敗に対するより詳細なロールバック/リトライ戦略の拡充
- position_sizing の銘柄別 lot_size 対応（stocks マスタとの連携）
- duckdb クエリのパフォーマンス最適化・インデックス/マテリアライズの導入
- 単体テスト・統合テストの追加と CI ワークフローの整備

（この CHANGELOG はコード内容から推測して作成したため、実際のコミット履歴とは差異がある可能性があります。）