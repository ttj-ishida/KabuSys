Keep a Changelog に準拠した CHANGELOG.md（日本語）
※この変更履歴は提示されたコードベースの内容から推測して作成しています。

Changelog
=========

全般的な注記
-------------
- 本プロジェクトは日本株自動売買システム (KabuSys) です。
- 各項では該当するモジュール/スクリプト名や主な挙動を明記しています。
- バージョン番号はパッケージ定義 (kabusys.__version__) に合わせています。

[Unreleased]
-------------

- （現時点の提示コードでは未確定の追加・修正があるため未記載）

[0.1.0] - 2026-04-12
--------------------

Added
-----
- 実行用エントリスクリプトを追加/実装
  - run_execution.py: 実行エンジン（ExecutionEngine）を組み立ててセッションを実行する起動スクリプトを追加。起動時にプロセス優先度を上げ、SQLite / DuckDB に接続して各種コンポーネント（BrokerClient、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を初期化する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロセス優先度を高く設定して監視を行う。

- 設定管理・.env 自動読み込み
  - config.py: .env / .env.local の自動ロード機能を導入（プロジェクトルートは .git または pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パース機能を実装（export 形式、クォート文字列、エスケープ、インラインコメントの考慮など）。

- 環境設定クラス
  - Settings クラスを導入し、環境変数の取得・検証を集約。KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等のバリデーションを行うプロパティを提供。
  - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH / paper_sqlite_path）サポート。

- 監視・モニタリング
  - monitoring_db 初期化ユーティリティの呼び出しを各起動スクリプトに追加し、監視用テーブルの存在を保証（冪等）。
  - run_monitoring が本番 sqlite_path を監視に使用する方針（KABUSYS_ENV に関わらず本番 DB パスを使用する旨を明記）。

- 実装済みのポートフォリオ構築機能（純粋関数）
  - portfolio/portfolio_builder.py: シグナルの選別（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株（lot_size）で丸め、aggregate cap によるスケーリング、コストバッファ対応。
  - portfolio/risk_adjustment.py: セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数 calc_regime_multiplier。

- 研究（Research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB を使った SQL で実装（calc_momentum, calc_volatility, calc_value）。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）や統計サマリー（factor_summary）、rank ユーティリティを実装。
  - research パッケージで zscore_normalize を外部に公開。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper_trading の SQLite DB を読み取り、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して CLI レポートを生成するツールを追加。閾値（稼働率99%、成功率90% 等）による PASS/FAIL 判定を出力。--from / --to / --db オプションをサポート。

- ニュース NLP（AI）モジュール
  - ai/news_nlp.py: raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) を用いた銘柄別センチメントスコアリングを実装。バッチ処理、最大記事数・文字数トリム、429/5xx/タイムアウト時の指数バックオフ再試行、レスポンス検証、スコアクリップ（±1.0）、結果の ai_scores テーブルへの安全な置換ロジックを備える。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足時は警告ログでスキップ。

Changed
-------
- 設計上の分離
  - Paper Trading 実行時は本番 DB と完全に分離するため、run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用するように実装。これにより paper_trading と本番データが混在しない。

- DB 接続方式
  - 多くのコンポーネントで SQLite に加えて DuckDB 接続を併用する設計に（分析・ファクター計算向けに duckdb を明示的に接続）。

- .env 読み込みの優先度
  - 読み込み順を OS 環境変数 > .env.local > .env として実装。.env.local は .env の値を上書き可能（ただし既存 OS 環境変数は保護）。

- モニタリングのポーリング間隔
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。値が不正（0以下や非数）の場合はデフォルト 60 秒へフォールバックし、警告を出す。

Fixed / Improved
---------------
- .env パーサの堅牢化
  - export KEY=val 形式をサポート、クォート文字列内のバックスラッシュエスケープに対応、インラインコメントの扱いを改善（クォート外の # を適切にコメントとして扱うルール）。
  - 読み込みに失敗した .env ファイルは警告を出して安全にスキップ。

- Research / ファクター計算の安定性向上
  - 欠損データ（例: 移動平均に必要な行数が不足）の場合は明示的に None を返す実装で downstream の誤計算を防止。
  - calc_forward_returns や calc_momentum でのスキャン範囲にバッファ（カレンダー日ベース）を設け、週末や祝日の影響を低減。

- ニュース NLP のフェイルセーフ
  - OpenAI API キー未設定時には明確な ValueError を投げ、API 呼び出し失敗時は部分失敗を許容して他銘柄への影響を最小化する安全策を導入。

- position_sizing のスケーリングロジック改善
  - aggregate cap におけるスケールダウン後の残余キャッシュを用いた lot_size 単位での再配分ロジックを追加し、再現性のために安定ソート（code を二次キー）を採用。

Security
--------
- 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。テストや CI 環境で不要/危険な自動読み込みを回避可能。

Deprecated
----------
- なし（このリリースでは既存 API の後方互換性を損なう変更は行っていない想定）。

Removed
-------
- なし

Notes / Known limitations
-------------------------
- ai/news_nlp の OpenAI 呼び出しは外部ネットワークに依存するため、オフライン環境では動作しない。
- apply_sector_cap の現行実装は price_map に欠損（0.0）があるとエクスポージャーが過小見積となる可能性があり、将来的に前日終値や原価でのフォールバックを検討する旨がコメントとして残っている。
- position_sizing は現状 lot_size を全銘柄共通で扱っている（銘柄別単元対応は将来の拡張案）。

パッケージ情報
----------------
- バージョン: 0.1.0 (kabusys.__version__)
- 主要ファイル:
  - src/kabusys/config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/portfolio/*
  - src/kabusys/research/*
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/utils/process_priority.py

以上。必要であれば各項目をより詳細に分割（例えばファイル別の小変更ログや関数レベルの差分）して更新します。