# Changelog

すべての重要な変更は Keep a Changelog の規約に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

現在のバージョン: 0.1.0

## [Unreleased]

---

## [0.1.0] - 2026-04-13

初回リリース。自動売買システム「KabuSys」のコア機能群を追加。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュールの公開 API を整理（各サブパッケージの __all__ を整備）。

- 実行・監視
  - 実行エントリスクリプトを追加
    - run_execution.py: ExecutionEngine の起動スクリプト。環境変数 KABUSYS_ENV による挙動（paper_trading 時はペーパートレード用 MockBrokerClient を利用し、専用の SQLite を使用する）をサポート。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
  - 起動時にプロセス優先度を設定する仕組みを採用（set_process_priority("high") を呼び出し）。

- 設定（kabusys.config）
  - .env/.env.local の自動ロード機構を追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル／ダブルクォートのエスケープ処理、行内コメント処理などに対応。
    - override と protected オプションにより OS 環境変数を保護しつつ .env.local で上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを追加し、各種設定値をプロパティで取得可能に:
    - DB/ファイルパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など）
    - 環境 (KABUSYS_ENV) の検証（development / paper_trading / live）
    - PAPER_FILL_MODE の検証（instant / partial / never / reject）
    - 閾値（CPU/MEMORY/DISK）やログレベルの整合性チェック

- 実践用ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows と POSIX の差分を吸収してプロセス優先度を設定（許可エラーは警告でスキップ）。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピンニング（アクセス権限がない場合は警告でスキップ）。
  - DuckDB/SQLite 接続を用いる各コンポーネントを用意（実行エンジンやモニタ初期化で使用）。

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を制限するフィルタ（既存ポジションのセクター比率が上限を超える場合に新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投資乗数を返す（未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を計算。
    - 単元（lot_size）, コストバッファ（cost_buffer）, max_position_pct, max_utilization などを考慮。
    - aggregate cap 超過時にはスケールダウンし、lot 単位で残差配分を行う再現性のあるアルゴリズムを実装。

- Research（ファクター計算・探索）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離率を計算。
    - calc_volatility: 20日 ATR・ATR 比率・平均売買代金・出来高比を計算。
    - calc_value: 財務データ（raw_financials）と株価から PER/ROE を計算。
    - DuckDB を用いて prices_daily / raw_financials を参照する実装。
  - research.feature_exploration:
    - calc_forward_returns: 各ホライズンの将来リターンを計算（horizons のバリデーションあり）。
    - calc_ic: スピアマン式のランク相関（IC）を計算。
    - rank / factor_summary: ランク変換と基本統計量サマリーを実装。
  - research パッケージに zscore_normalize を外部（kabusys.data.stats）からインポートして公開。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news から記事を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0～1.0）を算出し ai_scores に書き込む処理を実装。
    - ニュース時間ウィンドウの計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - バッチサイズ、文字数上限、記事数上限などトークン肥大化対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライロジック、レスポンス検証、得られたスコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードのみ置換）などを備えた堅牢な処理フローを追加。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 稼働率／注文成功率／送信率／レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。閾値は定数で定義（稼働率 99%、成功率 90% 等）。
    - 日付フィルタ（--from / --to）及び --db オプションをサポート。P95 計算と欠損時の N/A 表示。

### Changed
- DB 初期化
  - monitoring 用のテーブル初期化を起動時に冪等に保証（init_monitoring_db を呼び出す）。これにより起動時に監視用テーブルの存在が担保される。

### Fixed
- 環境変数・入力検証
  - MONITOR_POLL_INTERVAL: 不正な値（0 以下や非整数）を検出するとログ警告を出しデフォルト（60 秒）にフォールバックする挙動を実装し、time.sleep に渡す際の例外回避を行う。
  - Settings の各プロパティで不正な値が与えられた際に明確な例外を送出するよう整備（LOG_LEVEL, KABUSYS_ENV, PAPER_FILL_MODE など）。
- プラットフォーム差分
  - プロセス優先度設定でアクセス権限不足や未対応 OS の場合に例外を握り潰して警告ログを出すよう改善（実行環境の堅牢化）。

### Notes / Implementation details
- 多くの計算系関数（portfolio / research）は副作用を持たない純粋関数として実装され、テスト可能性を高める設計を採用。
- DuckDB / SQLite を利用する箇所は接続を外部から受け取り、SQL クエリを明示的に定義しているため、データソースに依存しない再利用が容易。
- AI モジュールは OpenAI の API 利用を前提とするが、API キー未設定時に ValueError を送出するなど明確な入力検証を行う。
- 将来的な拡張点や注意事項（TODO コメント）をコード内に残している（例: price のフォールバック、lot_size の銘柄別化等）。

---

今後のリリースでは以下を想定しています:
- テストカバレッジの強化（ユニット・統合テスト）
- Strategy / Execution の詳細実装と実運用でのチューニング
- エラーモニタリング・メトリクスの追加
- docs の整備（API レファレンス・運用ガイド）