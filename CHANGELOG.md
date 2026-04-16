CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
タグやコミット履歴が揃っていない初回リリース相当のスナップショットとして 0.1.0 を記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 設定・環境変数読み込み
  - Settings クラス (src/kabusys/config.py) を導入。アプリケーション設定を環境変数から取得するプロパティ群を提供。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env と .env.local を自動読み込み。
    - OS 環境変数は保護され、.env.local は .env を上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ、行末コメントの扱い等をサポート。
  - 各種設定プロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode のバリデーション、PID/kill フラグパス、閾値等）。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine をスレッドで起動し、stop フラグ検出で安全に停止。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離（MockBrokerClient を利用する想定）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - リスク設定(RiskConfig)に初期ポートフォリオ値として broker.get_available_cash() を利用。
  - 監視（SystemMonitor）起動スクリプト: src/kabusys/run_monitoring.py
    - 監視ループのポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - プロセス優先度を最初に high に設定する処理を共通で実行。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計（重要: 設計上の挙動）。
    - stop_requested.flag による外部停止制御と、KeyboardInterrupt による終了ハンドリング。

- 監視 DB 初期化
  - init_monitoring_db 関数呼び出しで監視用テーブルの存在を保証（冪等な初期化）。

- プロセス優先度 / CPU アフィニティユーティリティ
  - src/kabusys/utils/process_priority.py を追加:
    - set_process_priority(level) で Windows と POSIX（Linux/Mac/FreeBSD）を吸収して優先度を設定。アクセス権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアにプロセスを固定（未サポート環境は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio:
    - portfolio_builder.py: select_candidates（スコア降順選抜）、calc_equal_weights、calc_score_weights（スコア合計 0 の場合に等分配へフォールバック）。
    - risk_adjustment.py: apply_sector_cap（セクター集中上限チェック、"unknown" セクターは除外せず）、calc_regime_multiplier（レジームに応じた投下資金乗数、未知レジームは 1.0 にフォールバック）。
    - position_sizing.py: calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位丸め、コストバッファ考慮、aggregate cap によるスケーリングと残差配分ロジック）。
  - モジュールエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）、calc_value（PER/ROE の計算）を DuckDB SQL を用いて実装。データ不足時は None を返却する設計。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターン、一度のクエリで複数ホライズン取得、horizons のバリデーション）、calc_ic（Spearman ランク相関の IC 計算、最小サンプル数チェック）、factor_summary（基本統計量）、rank（同順位の平均ランク）。
  - research パッケージのエクスポートを追加（src/kabusys/research/__init__.py）。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py:
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI API（デフォルト gpt-4o-mini）へバッチで問い合わせて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装（バッチサイズ、文字数上限、記事数上限を導入してトークン肥大化を抑制）。
    - エクスポネンシャルバックオフによるリトライ（429/5xx/タイムアウト等）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に他銘柄データを保護するための局所的なDELETE/INSERT戦略などを設計。
    - calc_news_window(target_date) によるニュース収集ウィンドウ計算（JST ベースの定義を UTC naive datetime に変換）。

- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）に対して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、閾値と比較して PASS/FAIL を判定。
    - P95 計算ユーティリティ、日付フィルタ構築、SQLite のテーブル存在に柔軟に耐える設計（OperationalError をハンドリングしてデフォルト値にフォールバック）。
    - コマンドライン引数 --from / --to / --db をサポート。

Changed
- （初回リリースのため該当なし）

Fixed
- .env ファイル読み込みでファイルオープン失敗時に警告を出してスキップするなど堅牢化（config._load_env_file）。
- プロセス優先度や CPU affinity の設定で権限不足や未対応環境が発生した場合に警告でスキップするようにし、実行継続を保証。

Security
- OpenAI API キーは引数で渡せ、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を送出して誤動作を防止。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Breaking Changes / 注意事項
- 監視プロセス（run_monitoring）は意図的に「環境（KABUSYS_ENV）に依存せず」本番 sqlite_path を使用する実装になっています。paper_trading 環境でも監視が本番 DB を参照するため、環境切り替え時に期待と異なる挙動になる可能性があります。運用時は注意してください。
- 実行エンジン（run_execution）は paper_trading 環境のときのみ paper_trading 用 SQLite を使用する設計です（本番 DB 分離が望まれる用途向け）。
- position_sizing の lot_size は現状グローバル固定（関数引数で渡す設計だが、銘柄ごとの単元対応は将来的な拡張予定）。
- research.calc_forward_returns の horizons は最大 252（日）までの正の整数で検証されます。入力チェックにより不正な値は ValueError を送出します。

その他 / 開発メモ
- DuckDB を分析用 DB として広く使用しており、prices_daily / raw_financials / raw_news / ai_scores 等のテーブルを前提に実装されています。
- 多くのモジュールは「外部 API（発注/本番口座）へアクセスしない」設計方針で、研究・バックテスト用コードと実行エンジンの分離を意識しています。
- ロギングは基本 INFO レベルで初期化されますが、Settings.log_level で制御可能です（環境変数 LOG_LEVEL）。

今後の予定（例）
- 銘柄別 lot_size の導入（stocks マスタを使った拡張）。
- news_nlp の完全実装（API 呼び出し後のレスポンス処理実装の継続）。
- テストカバレッジの拡充と CI パイプライン整備。

---

参考: 主なファイル一覧
- src/kabusys/config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py

（以上）