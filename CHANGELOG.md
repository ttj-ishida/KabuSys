# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。日付はリポジトリ内の現行実装を初回リリースと見なし、2026-04-13 としています（ソースコードのコメントやバージョン情報に基づく推定）。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 設定管理
  - `src/kabusys/config.py`
    - 環境変数および .env ファイルの読み込みロジックを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml に基づく）。
    - `.env` / `.env.local` を読み込み、OS 環境変数を保護する仕組みを実装。
    - 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - 各種プロパティを持つ `Settings` クラスを提供（J-Quants／kabu Api トークン、DB パス、Paper Trading の挙動、監視パラメータなど）。
    - 入力検証（例: `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` 等）と未設定時のエラー化（必須 env は `_require` で ValueError）。

- 実行スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する実装。
    - 起動時にプロセス優先度を High に設定する処理を組み込み。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading DB（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - Broker クライアント生成（`BrokerClientFactory`）、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を High に設定する処理を組み込み。

- 監視/検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、合否判定を出力。
    - CLI オプション `--from` / `--to` / `--db` に対応。DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数でも指定可能。
    - 指標の閾値（稼働率 99%、成功率 90% など）を定義し、明確な PASS/FAIL 判定を行う。

- ポートフォリオ構築関連（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルのソート/候補選定 (`select_candidates`)。
    - 等配分 / スコア加重配分の重み計算 (`calc_equal_weights`, `calc_score_weights`)。スコア全てが 0 の場合は等配分にフォールバックして警告を出力。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限の適用 (`apply_sector_cap`)。既存ポジションのセクター別エクスポージャーを計算して過剰セクターの新規候補を除外。
    - 市場レジームに応じた資金乗数 (`calc_regime_multiplier`)。既定値: bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告の上 1.0 にフォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - 株数決定ロジックを実装（allocation_method: risk_based / equal / score）。
    - 1銘柄上限、aggregate cap（available_cash）へのスケーリング、lot_size（単元）丸め、cost_buffer による保守的見積りなどを考慮。
    - スケーリング時は残余キャッシュで端数を lot_size 単位で再配分するアルゴリズムを導入。

- 研究/ファクター計算
  - `src/kabusys/research/factor_research.py`
    - Momentum / Volatility / Value ファクターの計算を実装。DuckDB の `prices_daily` / `raw_financials` テーブルを参照。
    - mom_1m/3m/6m、MA200 乖離、ATR20、avg turnover、volume ratio、PER、ROE 等を計算。
    - データ不足時の None ハンドリングやウィンドウ幅の定義を含む。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（fwd_1d/5d/21d 等）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク化（同順位は平均ランク）を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB で完結する実装。

- AI / ニュース NLP
  - `src/kabusys/ai/news_nlp.py`
    - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を計算し、`ai_scores` に書き込む処理を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ定義（UTC 変換）を提供（ルックアヘッドバイアスを避けるため datetime.today() を参照しない）。
    - 1回あたり最大 20 銘柄でバッチ送信、記事数/文字数の上限（各銘柄: 最大10記事、最大3000文字）でトリム。
    - API 呼び出しは 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフでリトライ。レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗耐性（既存スコア保護のためコード絞り込みで更新）を実装。
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から取得。未設定時は ValueError を発生させる。

- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差を吸収してプロセス優先度を設定する `set_process_priority(level)` を実装。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity(cpu_count)` を実装。
    - 権限不足や未対応プラットフォーム時は警告を出してスキップするフェールセーフ。

- パッケージ公開用エクスポート
  - `src/kabusys/portfolio/__init__.py` / `src/kabusys/research/__init__.py` にて主要関数を再エクスポートし、外部からの利用を容易に。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーなど機密値は環境変数経由で取得。`.env` 自動読み込み時に OS 環境変数を保護する設計（`protected` set）を採用。

### Notes / Implementation details / TODOs
- 多くのモジュールは「DB 参照なしの純粋関数」として設計されており、ユニットテストの作成が容易。
- `portfolio.position_sizing` の lot_size は現状グローバル固定（100）を前提としている。将来的には銘柄ごとの lot_size を持たせる拡張予定（TODO コメントあり）。
- `risk_adjustment.apply_sector_cap` は sector_map に存在しない code を `"unknown"` 扱いにして上限チェックから除外する挙動。
- `news_nlp.score_news` は処理中に外部 API の失敗でスコア取得が得られなかった場合でも、他の銘柄のスコアを可能な限り保持する実装（部分更新、DELETE→INSERT を絞ったコード集合で行う）。
- `config._parse_env_line` はクォートやエスケープ、インラインコメントを細かく扱うため、複雑な .env も比較的安全に読み込める設計。

もしリリースノートをバージョン別に細かく分けたい、あるいは変更カテゴリ（Added/Changed/Fixed 等）をさらに詳細化したい場合は、その方針に合わせて追記・分割できます。必要であれば、各ファイルごとの API ドキュメントや主要関数の利用例も生成します。