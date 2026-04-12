CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティックバージョニングに従います。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて記載

[0.1.0] - 2026-04-12
-------------------

概要: 初回リリース相当の機能群を追加。自動売買システムのコアユーティリティ（実行・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング・ツール群）を含む。

Added
- 全体
  - パッケージ初期バージョンを導入。パッケージバージョンは kabusys.__version__ = "0.1.0"。
- 実行・監視ランナー
  - 実行用エントリポイント run_execution.py を追加。ExecutionEngine の起動、ブローカーファクトリ経由で本番/ペーパートレード切替、paper_trading 環境では専用 SQLite DB を使用する実装を提供。
  - 監視用エントリポイント run_monitoring.py を追加。SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL によるポーリング間隔設定（デフォルト 60 秒）、プロセス優先度設定の呼び出しを導入。
- 設定管理
  - kabusys.config.Settings を追加。.env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）、.env/.env.local の読み込み順序、OS 環境変数保護（上書き回避）を実装。各種環境変数のプロパティ（DB パス、PID ファイルパス、各しきい値、env 判定、paper trading 関連等）を提供。
  - .env パーサーはクォートやエスケープ、インラインコメント取り扱いに対応。
- ポートフォリオ構築
  - portfolio モジュールを追加:
    - portfolio_builder: シグナル選定 (select_candidates)、等金額・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を実装。スコア全0 時のフォールバック警告あり。
    - risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未登録セクターは "unknown" 扱いで上限適用をスキップ。
    - position_sizing: 各銘柄の発注株数決定ロジック (calc_position_sizes) を実装（risk_based / equal / score方式、損切り率、単元株丸め、aggregate cap によるスケールダウンと端数配分のアルゴリズム等）。
- リサーチ / ファクター計算
  - research モジュールを追加:
    - factor_research: momentum / volatility / value ファクター計算関数（DuckDB 接続を受け、prices_daily / raw_financials を参照。MA200、ATR20、各種リターン等を算出）。
    - feature_exploration: forward returns 計算、Spearman ランク相関に基づく IC 計算(calc_ic)、ファクター統計サマリ(factor_summary)、rank ユーティリティを実装。外部ライブラリ非依存で実装。
    - research パッケージエクスポートに zscore_normalize を含める（kabusys.data.stats から）。
- AI ニューススコアリング
  - ai/news_nlp.py を追加。raw_news / news_symbols を集約し OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントを -1.0〜1.0 にスコアリングして ai_scores テーブルへ書き込むワークフローを実装。
    - 処理はバッチ（最大 20 銘柄）、トークン肥大化対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスの厳密な JSON バリデーション、スコアのクリップ処理を含む。
    - ニュース対象ウィンドウ計算（JST 基準で前日15:00〜当日08:30相当の UTC 時刻）を提供。
    - OpenAI API キー未設定時はエラーになる安全チェックを導入。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポート生成ツール。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し、PASS/FAIL 判定（閾値はソース中の定数で定義）。日付フィルタ (--from/--to) と DB パス指定 (--db) をサポート。
- ユーティリティ
  - utils/process_priority.py を追加。Windows/Linux/Mac の差分を吸収してプロセス優先度設定(set_process_priority) と CPU affinity 設定(set_cpu_affinity) を提供。権限不足や未対応 OS 時は安全に警告を出してスキップ。
  - utils パッケージ初期化ファイルを追加。

Changed
- 監視・実行プロセスの起動フロー
  - いずれの起動スクリプトでもプロセス優先度を最初に設定してから起動処理を行うように設計（set_process_priority("high") の呼び出し）。これにより起動直後のリソース割当を優先。
- DB の扱い
  - 監視 (run_monitoring.py) は環境に依らず本番用 sqlite_path を参照する設計（監視データは環境分離しない方針）。
  - 実行 (run_execution.py) は paper_trading 環境のとき paper_sqlite_path を使用し、本番 DB とデータを完全に分離。
- 環境変数の読み込み優先度
  - OS 環境変数 > .env.local > .env の順で適用。OS 環境変数は保護され上書きされない。

Fixed
- 設定パーサー耐久性向上
  - .env 行パーサーがクォート・バックスラッシュエスケープ・コメントを正しく処理するよう改善。無効行や export プレフィックスへの対応を追加。
- フォールバック値の安全化
  - MONITOR_POLL_INTERVAL 等に不正な値が与えられた場合、ログ警告を出してデフォルト値にフォールバックする処理を追加（time.sleep に負の値が渡らないように）。
  - PAPER_FILL_MODE の検証を追加し、不正値時は ValueError を送出して早期検出。
- DB 操作の堅牢化
  - paper_verification_report の各クエリ呼び出しを個別に try/except で保護し、テーブルが存在しないケースでもレポート生成が極端に失敗しないようにした（OperationalError を捕捉して N/A 表示や 0 カウントで継続）。

Security
- OpenAI API キーの必須チェックを導入（ai.news_nlp.score_news）。キー未設定時は例外を投げ、誤って未設定で API を呼ばない保護を追加。

Notes / Implementation details
- DuckDB を分析用 DB として使用（prices_daily / raw_financials テーブル想定）。exec/analysis 用関数は DuckDB 接続を引数に取る純粋関数中心の設計。
- position_sizing の aggregate cap は壊れにくいスケールダウン設計（小数端数処理、lot_size 単位での再配分ロジックを実装）。
- ai/news_nlp の出力期待は厳密な JSON（{"results":[...]}）を想定。部分失敗時のテーブル更新は対象コードを限定して安全に行う設計。

Unreleased / 今後の予定（予定項目の例）
- 銘柄別単元サイズ(lot_size)を銘柄マスタから取得する対応
- position_sizing の手数料・スリッページ推定ロジックの拡張（現状は cost_buffer による簡易見積）
- ai/news_nlp のレスポンス検証強化とメトリクス記録（失敗率・APIコスト）
- research モジュールの追加ファクター・Pandas 等による高速化オプション

--- 

注: 上記 CHANGELOG は提供されたソースコードから推測して作成したもので、実際の変更履歴（コミットログ等）ではありません。必要であれば、各ファイルごとの詳細な実装ノートや想定ユースケースを追記します。