CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の書式に準拠しています。  
コードベースの内容から推測して作成しています（実装意図・仕様はソースを参照してください）。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 基本バージョンを v0.1.0 としてリリース。
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading 時は専用 MockBroker を利用）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 設定管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）。.env/.env.local の優先順位や OS 環境変数保護（上書き禁止）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを提供し、各種環境変数（DB パス、API トークン、PID/KILL フラグ、閾値など）をプロパティとして取得できるようにした。KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE のバリデーションを実装。
- 監視用 DB 初期化
  - init_monitoring_db 呼び出しをエントリポイントに追加し、監視テーブルの存在を保証（冪等）。
- ポートフォリオ構築（純粋関数ライブラリ）
  - portfolio.portfolio_builder: シグナル選定（score 降順）と等配分・スコア配分の重み計算を実装。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）を実装。単元株丸め、最大ポジション上限、aggregate cap によるスケールダウン、cost_buffer の考慮等を行う。
- リサーチ機能（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB SQL で実装（prices_daily / raw_financials を参照）。MA200、ATR20、10・21・63 等の計算に対応。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニュース NLP
  - ai.news_nlp: raw_news / news_symbols からニュースを集約し OpenAI API（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出する機能を追加。バッチ（最大 20 銘柄）、文字数・記事数のトリム、リトライ（指数バックオフ）、レスポンスバリデーション、スコアクリップ、部分更新戦略（DELETE→INSERT）を実装。
  - calc_news_window: JST ベースのニュースウィンドウ計算ユーティリティを追加（前日 15:00 JST ～ 当日 08:30 JST）。
- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 set_process_priority を実装。CPU affinity 設定用の set_cpu_affinity を追加（権限がない場合は警告してスキップ）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを計算し PASS/FAIL 判定する。P95 計算や日付フィルタ、DB 存在チェックを実装。
- パッケージ初期化
  - __init__.py に __version__="0.1.0" を設定し、主要サブモジュールのエクスポートを定義。

Changed
- run_monitoring/run_execution: 起動時にまずプロセス優先度を "high" に設定するように変更（set_process_priority を呼び出し）。これにより監視／実行プロセスの実行優先度を上げる試みを行う。
- run_execution: paper_trading 環境の場合、SQLite は settings.paper_sqlite_path を使用して本番 DB と完全に分離する仕様にした（安全設計）。
- monitoring 動作: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の記述（設計上の注意）。
- .env パーサ: export KEY=val 形式や引用符内のバックスラッシュエスケープ、行内コメントの扱い等を考慮したより堅牢なパーサを実装。存在しない .env ファイルや読み取りエラーは警告として扱う。

Fixed
- 環境変数パースの堅牢性向上: 空行やコメント行、export プレフィックス、クォートの扱い、不正行のスキップなどの処理を改善。
- MONITOR_POLL_INTERVAL の不正値対策: 0 以下や非整数が設定された場合にデフォルト（60 秒）にフォールバックし、警告を出すようにした（time.sleep に渡す不正値対策）。
- DuckDB / SQLite の使用上の注意: tools や ai モジュールでテーブルが存在しない場合に sqlite3.OperationalError を捕捉してフォールバックする処理を追加（レポート生成やスコア計算の堅牢性確保）。
- OpenAI API の未設定検出: API キー未設定時に明確な ValueError を投げるようにした。

Security
- 環境変数（OS 環境）の保護: .env の自動ロード時に既存の OS 環境変数を上書きしない（デフォルト）。必要な場合は .env.local で上書きを許可するが、OS 環境を protected として扱う設計にしている。

Notes / Known limitations
- ai.news_nlp の OpenAI 呼び出し処理は外部依存（API キー・ネットワーク）に左右されるため、障害発生時はログ出力・部分スキップでフェイルセーフに設計されているが、完全な再送・永続化戦略は未実装。
- position_sizing の単元丸めや price の欠損時の扱い等に関しては TODO コメントが残っている（将来的に銘柄別 lot_size や価格フォールバックを導入予定）。
- calc_regime_multiplier は未知レジームに対して 1.0 でフォールバックする（警告を出す）。
- DuckDB の executemany 等のバージョン制約に注意（ai モジュール内に注記あり）。

--- 

その他、細かなログメッセージやデバッグ出力を通じて運用時の可観測性を高める実装が多く含まれています。詳細な挙動・API 仕様は各モジュールのドキュメント／コメントを参照してください。