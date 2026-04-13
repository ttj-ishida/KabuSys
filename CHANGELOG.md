CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
許容される変更種別: Added, Changed, Fixed, Removed, Deprecated, Security。

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネント群を実装。
  - パッケージバージョン: __version__ = 0.1.0

- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db、PAPER_TRADING_SQLITE_PATHで上書き可）を使用する仕組みを搭載。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の実行を行う。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils/process_priority.set_process_priority 呼び出し）。
    - duckdb 接続を受け取り、ExecutionEngine に渡す。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトへフォールバック。
    - 監視（monitoring）用 DB は環境に関わらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

- 設定／環境変数管理
  - src/kabusys/config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを実装：export 形式、引用符（シングル/ダブル）内のエスケープ、インラインコメント処理をサポート。
    - Settings クラスを導入し、多数の設定プロパティを提供（DBパス、PID/kill flag パス、閾値、環境種別判定、paper trading 関連設定等）。
    - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- 監視関連
  - src/kabusys/monitoring/*（初期化呼び出しは各起動スクリプトに統合）
    - monitoring DB の初期化を行う init_monitoring_db 呼び出しが起動時に行われ、冪等に監視テーブルを保証。

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合のフォールバックと警告を実装。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄の除外や "unknown" セクター取扱いを明示）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップし、未知レジームはフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size 単位丸め、per-position 上限、aggregate cap スケールダウン、cost_buffer を考慮）。
    - aggregate スケールダウン時に端数の再配分ロジック（lot 単位で残余を配分）を実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージとして公開。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）をプラットフォーム差分を吸収して設定する set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を実装（最初の N コアに固定）。
    - 権限不足や未対応環境では警告を出して安全にスキップする。

- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value ファクター計算を実装（DuckDB を用いた SQL ベースの算出）。
    - mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe などを算出。
    - データ不足時の None 処理や行数条件を厳密に扱う実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns（可変ホライズン対応）、IC（calc_ic）計算、rank、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

  - src/kabusys/research/__init__.py
    - 主要関数と zscore_normalize をエクスポート。

- AI / ニュース NLP
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ書き込むスコアリング機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算する calc_news_window。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、トークン肥大化対策（記事数・文字数のトリム）、429/ネットワーク/5xx に対する指数バックオフによるリトライ、レスポンス検証、スコア ±1.0 のクリップ、部分失敗に備えた差し替え戦略（DELETE→INSERT）を実装。
    - OpenAI API キーの解決（引数または環境変数 OPENAI_API_KEY）と未設定時の例外を実装。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを集計して標準出力にレポートを出力。閾値による PASS/FAIL 判定を実装。
    - DB パスはコマンドライン引数 --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト の順で解決。

Changed
- 設計／振る舞い
  - .env 読み込みロジックは OS 環境変数を保護するため protected キーセットを導入（.env.local の override を許しつつ、OS 側のキーは上書きしない設計）。
  - Monitoring 起動時は常に本番 sqlite_path を使用するポリシーを明示（環境に依存しない監視を想定）。
  - Execution 起動は paper_trading 環境時に DB を分離（本番 DB と完全分離）する仕様化。

Fixed
- 設定の堅牢化
  - MONITOR_POLL_INTERVAL のパースとバリデーションを実装。0 以下や非整数入力を検出してログ警告を出しデフォルトにフォールバックすることで time.sleep の ValueError を回避。

Notes / Known limitations
- 一部の処理は TODO コメントを含む（例: price が欠損した場合のフォールバック価格処理、銘柄毎の lot_size サポートなど）。
- DuckDB の executemany に関する制約を考慮した実装上の注意点がコード内に記載されている。
- OpenAI 連携は外部 API に依存するため、API キー設定やレート制限に応じた運用が必要。
- 現在の実装は外部依存（psutil, duckdb, openai 等）が必要。実行環境でのライブラリインストールと実行権限（プロセス優先度設定など）の確認が必要。

未リリース
- Unreleased: 特になし（初回リリース）。

----- 

（補足）本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートに含める場合は、ビルド/パッケージ時の差分やデプロイ方針に合わせて調整してください。