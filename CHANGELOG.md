CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
バージョニングは SemVer に従います。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
------------------

最初の公開リリース。システム全体のコア機能（実行エンジン・監視・ポートフォリオ構築・リサーチ・ニュース NLP・ユーティリティ・各種ツール）を実装しています。

Added
- 全体
  - パッケージ初期リリース。バージョンは kabusys.__version__ = "0.1.0" に設定。
  - DuckDB / SQLite を用いたデータレイヤーを前提とした設計。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading モードを切り替え、paper_trading 時は専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離する実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照する設計になっている旨を明記。

- 設定 / 環境変数管理
  - config.py: 環境変数／.env ファイル読み込みユーティリティを導入。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
    - 行パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
    - Settings クラスを提供し、各種設定（パス、API トークン、閾値、モード判定など）をプロパティで取り出せるように実装。
    - 入力検証を行い、不正な値時には ValueError を送出（例: KABUSYS_ENV の許容値、LOG_LEVEL、PAPER_FILL_MODE）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全てが0のとき等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用 (apply_sector_cap)：既存の保有エクスポージャーを計算して、上限を超えるセクターの新規候補を排除するロジックを追加。
    - レジーム乗数 (calc_regime_multiplier)：レジームに応じた投下資金の乗数を定義（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数を計算する calc_position_sizes を実装（risk_based / equal / score の配分方式、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer 加味）。

- リサーチ
  - research/factor_research.py
    - Momentum / Volatility / Value などのファクター計算関数を実装（DuckDB 接続を受け取り SQL + Python で計算）。MA200、ATR20、各期間のリターン等を算出。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns、IC（スピアマン ランク相関）計算 calc_ic、列ごとの統計 summary を実装。pandas 等の外部ライブラリに依存しない実装。
  - research パッケージは kabusys.data.stats の zscore_normalize を再エクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメントスコア化して ai_scores に書き込む機能を実装。
    - 処理の特徴：
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算して対象記事を抽出。
      - 1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大化対策）。
      - 最大 20 銘柄ずつバッチ送信、JSON Mode 出力を期待。
      - ネットワークエラー・429・5xx に対して指数バックオフでリトライ、失敗してもフェイルセーフで継続。
      - レスポンス検証・スコアクリッピング（±1.0）を行い、部分成功時に既存データを保護するため対象コードのみ DELETE→INSERT。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 向けの検証レポート生成ツールを追加。コマンドライン引数 --from/--to/--db を受け取り、稼働率・注文成功率・送信率・レイテンシ（P95）等を計算して PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99% など）を定義し、P95 を自前で計算するユーティリティを持つ。
    - DB が存在しない場合のエラーメッセージや、テーブル未存在時の例外ハンドリングを含む。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）で差を吸収し、権限不足や未対応 OS の場合は警告を出してスキップする堅牢設計。

Changed
- （初期リリースのため変更履歴なし）

Fixed
- config._parse_env_line: クォート内のバックスラッシュエスケープやインラインコメントの取り扱いを考慮する堅牢なパーサ実装。
- run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）に対し警告を出してデフォルトにフォールバックする挙動を実装（time.sleep に渡して ValueError になるのを防止）。

Notes / Implementation details
- Monitoring と Execution はそれぞれ独立した DB を使う設計（監視は常に sqlite_path、本番 DB を監視。paper_trading は paper_sqlite_path を利用）。
- DuckDB は各種リサーチ・AI モジュールで読み取り主体に使われる想定。
- 外部 API（OpenAI、kabu API、J-Quants 等）はファクトリや設定経由で切り替え可能（paper_trading 用の MockBrokerClient 等を利用する設計思想）。
- 各モジュールは可能な限り副作用を排した純粋関数（portfolio / research）または DI（依存注入）しやすい設計（接続やクライアントを外部から注入）になっています。

開発者向けメモ
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布パッケージ等で自動ロードが不適切な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE や KABUSYS_ENV などの設定は厳密な検証が入るため、CI でのテスト時やデプロイ前に環境変数の妥当性確認を推奨します。

--- 

（この CHANGELOG はソースコードの内容から機能・振る舞いを推測して作成しています。実際の変更履歴や公開バージョンポリシーに合わせて必要に応じて調整してください。）