CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- ai/news_nlp モジュールは実装途中のため部分的に未完成（API 呼び出し前の集約処理でソースコードが途中で途切れています）。リトライ・レスポンス検証・DB 更新ロジックは設計済みだが、追加のテストと例外処理の強化が必要。
- 複数箇所に TODO コメントあり（例: 価格フォールバック、銘柄ごとの lot_size 拡張など）。将来的な改善予定として記載。

[0.1.0] - 2026-04-17
--------------------
最初の公開リリース。プロジェクトのコア機能群を実装しました。主要な追加点・設計上の決定と既知の挙動は以下の通りです。

Added
- パッケージ初期化
  - kabusys.__version__ を設定（0.1.0）。
- 環境設定 / ロード
  - 強力な .env ローダー実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込み。
    - export 形式や引用符を含む値、インラインコメントの扱いに対応するパーサーを実装。
    - OS 環境変数の保護（.env.local が OS 環境変数を上書きしないよう制御）。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、監視しきい値、モード判定等）をプロパティで取得できるようにした。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - PAPER_FILL_MODE のバリデーション（instant / partial / never / reject）。
    - LOG_LEVEL のバリデーション。
- 実行エントリポイント
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ処理を実装。
    - プロセス優先度を起動時に "high" に設定（utils/process_priority.set_process_priority）。
  - システム監視起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイル検知でループを安全に終了。
- 監視 DB 初期化ユーティリティ
  - monitoring_db 初期化呼び出しを run scripts 内で行い、監視テーブルが存在することを保証（冪等）。
- プロセス/リソース管理ユーティリティ
  - src/kabusys/utils/process_priority.py を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収してプロセス優先度（nice/HIGH_PRIORITY）を設定。
    - CPU affinity（最初の N コアに固定）機能を実装。
    - 権限不足や未対応 OS の場合は警告ログを出力してスキップするフェイルセーフを搭載。
- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/* を実装。
    - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等配分へフォールバックして警告を出す。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。未知レジームや未知セクターに対するフォールバックロジックを用意。
    - position_sizing: 株数決定ロジック（calc_position_sizes）。単元（lot_size）丸め、リスクベース/等配分/スコア配分に対応。aggregate cap によるスケーリング、端数処理の再配分アルゴリズムを実装。
  - モジュールエクスポートを整備（portfolio.__init__）。
- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py を実装。
    - Momentum（mom_1m / mom_3m / mom_6m / MA200乖離）、Volatility（ATR20、相対ATR、平均売買代金、出来高比）、Value（PER / ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - データ不足時の None ハンドリング（行数不足や NULL の伝播を考慮）。
  - src/kabusys/research/feature_exploration.py を実装。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを追加。
- AI ニュース NLP（設計と部分実装）
  - src/kabusys/ai/news_nlp.py を追加。
    - OpenAI API を使ったニュースセンチメントスコアリングの設計を実装。ウィンドウ計算、バッチ処理、API エラー時の指数バックオフ、レスポンス検証、スコアクリッピング等を含む。
    - 実装は途中でファイルが切れているため、完全動作前に追加実装・テストが必要。
- ツール
  - src/kabusys/tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（P95）などを集計・判定し CLI でレポート出力。
    - デフォルトの DB パスは data/paper_trading.db。--db オプションで上書き可能。
    - 複数の SQL 実行でテーブル未存在時に例外をキャッチして安全に N/A を返す設計。
- DuckDB 統合
  - DuckDB 接続を利用する設計を多数導入（research, ai など）。duckdb の接続オブジェクトを受け渡して SQL と Python を組み合わせて処理。

Changed
- 環境変数の自動読み込み
  - .env / .env.local のロード順序と保護ポリシーを明確化（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化機能を追加。
- モニタリングのポーリング間隔
  - MONITOR_POLL_INTERVAL を整数で指定可能に。0 以下や不正値はログ出力の上でデフォルト値（60 秒）へフォールバックする安全設計。

Fixed
- 環境変数パーサーの堅牢性向上
  - export 形や引用符内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理するよう改善。
- calc_score_weights の不安定ケース対処
  - 全スコア合計が 0 の場合に等金額配分にフォールバックすることで 0 除算や NaN を回避。
- ボラティリティ計算の true_range 伝播
  - high / low / prev_close のいずれかが NULL の場合は true_range を NULL とし、ATR の行数カウントを正しく扱うことで過大評価を防止。
- run_execution/run_monitoring の安全停止
  - data/stop_requested.flag を検知して安全に停止する仕組みを追加（両スクリプト）。
- process_priority のフォールバック
  - 未対応 OS や権限不足で設定ができない場合は警告ログを出して処理を続行するよう修正。

Security
- 機密情報の取り扱い
  - API キーやパスワードは Settings を通じて環境変数から取得する設計。README 等で .env.example に基づいた設定方法を案内する想定。

Known Issues / Notes
- ai/news_nlp.py は途中で切れており、実運用前に完了実装と追加のテストが必要。
- position_sizing の price フォールバック（価格欠損時の扱い）について TODO があり、現在は price が 0 や欠損の銘柄はスキップされる挙動。
- 単元（lot_size）は現状グローバル固定で銘柄別対応は未実装（将来的に stocks マスタに lot_size を持たせる予定）。
- ユニットテストはこのリリースに含まれていないため、回帰防止のためのテスト追加が推奨される。
- DuckDB バージョン依存の挙動（executemany の空パラメータ制約など）に注意。tools では params が空の場合の保護ロジックを設けているが、環境による差異の確認を推奨。

Contributors
- このリリースは内部実装に基づく推測的な CHANGELOG です。実際のコミット履歴や著者情報はソース管理履歴（Git）を参照してください。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。リリース日や項目は実際のリリース運用に合わせて調整してください。）