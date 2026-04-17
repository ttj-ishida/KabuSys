# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

注意: 以下は提供されたソースコードから推測して作成した変更履歴です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17
最初のリリース。システム全体のコア機能を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動スクリプト
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル `data/stop_requested.flag` による安全停止検知。
    - Monitoring は環境に依らず本番用 `sqlite_path` を使用する実装。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` 時は Paper Trading 用 DB に分離して動作。
    - 実行中の PID 管理ファイル、停止フラグの検知とエンジン停止処理を実装。

- 設定管理
  - 環境変数・.env 読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - .env/.env.local の優先順位読み込み、既存 OS 環境変数の保護機能。
    - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント）のパース対応。
    - 各種設定プロパティ（DB パス、Paper Trading 設定、監視しきい値、環境判定等）を公開。

- 監視 DB 初期化ユーティリティ連携
  - run_monitoring / run_execution から監視用 DB テーブルの初期化を呼び出し（init_monitoring_db の利用）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates / calc_equal_weights / calc_score_weights（スコア全0時は等配分にフォールバックして警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションのセクター比率を計算し上限超過セクターの候補除外）。
    - calc_regime_multiplier（bull/neutral/bear に応じた資金乗数。未知レジームはフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元（lot_size）に基づく丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り。
    - 価格欠損時のスキップ等、実運用での安全弁を実装。

- 実行系ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収した set_process_priority。
    - set_cpu_affinity によるコア固定（アクセス権限や未対応環境では警告でスキップ）。

- 研究・ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、平均売買代金、出来高比）、バリュー（PER, ROE）。
    - DuckDB を用いた SQL + Python 実装で高速に計算。
  - 特徴量探索・統計ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算、IC（Spearman）の計算、rank/統計サマリー。
  - research パッケージ のエクスポートを整理（src/kabusys/research/__init__.py）。

- AI ニュース評価（OpenAI 統合）
  - ニュース NLP スコアリングモジュールを実装（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON モード）でセンチメントを算出。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、最大リトライ・指数バックオフ、レスポンスバリデーション、スコアクリッピング等を実装。
    - スコア書き込みは銘柄絞り込みで安全に行う（部分失敗時に既存スコアを保護）。
    - ニュースウィンドウ計算ユーティリティを実装（JST → UTC 変換の取り扱いを明記）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - 日付フィルタ、DB 存在チェック、SQL のエラーに対するフォールバックを実装。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Notes / Implementation details / Known limitations
- .env 読み込み:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする設計（配布環境での安全性向上）。
  - OS 環境変数（既存の os.environ）はデフォルトで保護される。.env.local は override=True で上書き可能だが、保護されたキーは上書きされない。

- run_monitoring の挙動:
  - Monitoring は KABUSYS_ENV の値にかかわらず本番 sqlite_path を使用する旨が明記されているため、監視データは環境分離されない点に注意。

- Paper Trading 分離:
  - run_execution は paper_trading 環境時に別 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB とデータを分離する。

- 欠損データ・フォールバック:
  - apply_sector_cap のコメントに将来の改善点（価格欠損時のフォールバック価格利用）が記載されている。
  - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックする実装。

- position_sizing の丸め・スケール処理:
  - lot_size（単元）での丸め・残余配分ロジックを実装。aggregate cap 超過時はスケールダウンしてから残余キャッシュで追加配分するアルゴリズムを採用。

- news_nlp は OpenAI API キー必須（引数または環境変数 OPENAI_API_KEY）。API の障害はリトライ実装により耐性を持たせるが、永久障害時は部分スキップとなる。

- research モジュール:
  - 多くの集計は DuckDB 上の prices_daily / raw_financials テーブル前提で実装。必要なテーブル構造が存在しない場合はエラーが発生する可能性がある。

### TODO / 今後の改善候補（ソース内コメントより）
- apply_sector_cap: 価格欠損時の前日終値や取得原価でのフォールバック実装検討。
- position_sizing: 銘柄別単元対応（stocks マスタに lot_size を持たせる）への拡張。
- news_nlp: DuckDB executemany の挙動や部分失敗時のトランザクション制御について追加の堅牢化。
- process_priority: 一部環境で設定に失敗した場合の詳細なログ・診断強化。

---

参照:
- 主なファイル: src/kabusys/{__init__.py,config.py,run_monitoring.py,run_execution.py,utils/process_priority.py,portfolio/*,research/*,ai/news_nlp.py,tools/paper_verification_report.py}