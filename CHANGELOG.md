CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （今後の変更をここに記載します）

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース。KabuSys の基本コンポーネントを追加。
  - パッケージ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境/設定管理
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）。
    - 厳密な .env パーサを実装（export 形式、クォート付き値、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを追加し、各種設定値（J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境判定 等）をプロパティで取得可能に。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証を実装。
- 実行系 & 監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、バックグラウンドスレッドでのエンジン実行と停止フラグ監視を実装。
    - プロセス優先度を起動時に "high" に設定。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全に終了。
    - 監視は環境にかかわらず本番 sqlite_path を参照する仕様を採用。
- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等重配分・スコア加重配分ロジックを実装。全スコアが 0 の場合は等配分にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時は警告して 1.0 をフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - 複数の割当方式（risk_based / equal / score）に対応した株数決定ロジックを追加。単元株（lot_size）で丸め、ポジション・総投下上限、コストバッファ、aggregate cap によるスケールダウンと残差処理を実装。
- データ・リサーチ
  - src/kabusys/research/factor_research.py
    - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー）を実装。データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズン）、Spearman ランク相関による IC 計算、ファクター統計サマリー、rank ユーティリティを純粋 Python（外部依存なし）で実装。
  - src/kabusys/research/__init__.py に公開 API をまとめてエクスポート。
- ニュース NLP（AI スコアリング）
  - src/kabusys/ai/news_nlp.py（実装の大半を追加）
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルに書き込む処理の設計と実装（ニュースウィンドウ計算、バッチ処理、最大記事数・文字数制限、JSON レスポンス検証、スコアクリップ、リトライ/バックオフ方針）。
    - OpenAI API キー未設定時は ValueError を送出する安全策を実装。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(): Windows / POSIX の差分吸収実装（nice / HIGH_PRIORITY_CLASS 等）、失敗時の安全なログとスキップ。
    - set_cpu_affinity(): 指定コア数へのピン留め機能を追加（権限・未対応環境で失敗時は警告）。
- 運用ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出し PASS/FAIL 判定を出力。テーブル欠如時は安全に N/A を扱う。
  - src/kabusys/tools/__init__.py を追加（パッケージ化）。
- DB 初期化ヘルパ
  - 複数のエントリポイントで監視テーブル初期化を冪等に行うための init_monitoring_db を参照（run_* で利用）。

Changed
- デフォルトのデータパスを明示
  - duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db、paper_trading: data/paper_trading.db（Settings の既定値）。
- 実行/監視プロセスが起動時にプロセス優先度を高に設定するよう変更。
- Paper Trading 動作を本番 DB と分離（paper_trading 環境で専用 SQLite を使用）。

Fixed
- 環境変数パーサの堅牢化（quoted 値のエスケープ処理、export プレフィックス、コメント処理）。
- calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックするよう修正。
- ファクター / リサーチ系関数はデータ不足時に None を返し上位で N/A 表示されるようにしてクラッシュを回避。
- run_monitoring._get_poll_interval: 0 以下や不正な値を与えた場合にデフォルトへフォールバックし、警告ログを出すよう修正。
- process_priority 系: 権限不足や未対応 OS での例外をキャッチして警告に置き換えるようにして起動失敗を回避。
- paper_verification_report: DB テーブルが存在しないケースで OperationalError を捕捉し N/A を扱うように。

Notes / Known issues
- apply_sector_cap: price_map に価格が欠損（0.0）の場合、エクスポージャーが過少に見積もられてブロック漏れが起こる旨を TODO コメントで記載。将来的にフォールバック価格を導入予定。
- news_nlp.py の score_news の一部がファイル末尾で途切れています（コード断片が未完）。実行前に続きの実装・テストが必要。
- DuckDB executemany の制約（空パラメータの扱い）に注意（news_nlp のコメント参照）。
- 現在の単元株（lot_size）はグローバル固定（デフォルト 100）。将来的に銘柄別単元対応を検討。

Security
- OpenAI API キーや各種秘密情報は Settings 経由で環境変数から取得する設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。

作者注
- 各モジュールは外部 API（ブローカー等）への直接アクセスを最小化する方針で設計されています（Research / Tools / Portfolio はローカル DB と純粋関数で完結するよう配慮）。
- 実稼働前に broker/client 実装、ExecutionEngine の統合テスト、news_nlp の OpenAI 連携テストを推奨します。