# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

※日付はこのリビジョンを生成した日付です。

## [Unreleased]

## [0.1.0] - 2026-04-11

### Added
- 初期リリースとして主要機能を追加。
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン定義 __version__ = "0.1.0" を追加。
- 設定・環境変数読み込み
  - src/kabusys/config.py
    - プロジェクトルート検出による .env 自動ロード（.git / pyproject.toml を基準）。
    - .env / .env.local の読み込みロジック実装（上書き優先順位・OS 環境変数保護）。
    - 行パーサー (_parse_env_line) によるクォート・エスケープ・インラインコメント対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 各種設定プロパティ（DBパス、APIトークン、PID/killフラグパス、閾値、環境判定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 実行用スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - プロセス優先度を最初に設定し、SQLite/DuckDB 接続、監視ループの例外ハンドリングを実装。
    - 監視処理は環境に関わらず本番の sqlite_path を使用する旨の設計。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用して本番と分離。
    - BrokerClientFactory を用いたブローカークライアント生成と ExecutionEngine 組み立て。
    - RiskManager / Reconciler / OrderManager / OrderRepository の組立てと run_session 呼び出し。
- プロセス優先度・CPU アフィニティユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) による Windows / POSIX を吸収した優先度設定。
    - set_cpu_affinity(cpu_count) によるプロセスのコア固定（例外に対する安全処理あり）。
- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選択（タイブレークに signal_rank 使用）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（スコア合計が 0 の場合等金額にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score に対応した株数計算、単元株丸め、per-stock 上限、aggregate cap スケーリング、cost_buffer を考慮した保守的見積り。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（除外対象：unknown セクターや当日売却予定銘柄）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）、未知レジームは警告してフォールバック。
  - src/kabusys/portfolio/__init__.py でエクスポートを整理。
- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB を用いたモメンタム・ボラティリティ・バリュー計算。200日移動平均やATR、平均売買代金などを算出。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン一括取得（動的ホライズン対応）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時に None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・統計サマリー（count/mean/std/min/max/median）。
  - src/kabusys/research/__init__.py にて公開関数をまとめてエクスポート。
- AI 関連機能
  - src/kabusys/ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）、記事集約、銘柄ごとのトリム（文字数/記事数上限）、20 銘柄バッチ処理、リトライ（429/接続/タイムアウト/5xx）、レスポンスバリデーション、スコアクリップ（±1.0）、トランザクションによる部分失敗耐性のある DB 更新。
    - テスト用に API 呼び出し関数の差し替えを想定（_call_openai_api の分離）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の ma200 乖離とマクロ記事の LLM センチメントを合成して日次の market_regime を判定・書き込みする機能を実装。データ不足・API失敗時のフォールバック挙動を備える。

### Changed
- .env の自動読み込み振る舞いを明確化（OS 環境変数を保護し .env.local を上書き可能にする等）。
- DuckDB への書き込みでは executemany の空リスト制約を回避する実装（互換性対策）。
- 研究/探索モジュールは外部ライブラリに依存せず、DuckDB + 標準ライブラリのみで実装。

### Fixed / Robustness
- run_monitoring のポーリング間隔取得で不正値を検出するとログを出しデフォルトへフォールバックする実装を追加（_get_poll_interval）。
- process_priority の実行で権限不足や未対応 OS の場合に警告ログを出して失敗を無害化。
- calc_score_weights: 全銘柄スコアが 0 の場合に警告を出して等金額配分へフォールバック。
- feature_exploration.rank: 浮動小数丸め（round(..., 12)）を導入し同値判定の安定性を向上。
- ai.news_nlp._validate_and_extract: LLM の前後余分なテキストが混入するケースに対し最外の {} を抽出して復元する耐性を追加。
- ai.news_nlp の API リトライは 429 / 接続断 / タイムアウト / 5xx に限定し、その他エラーは即時失敗としてログを出す安全設計。
- regime_detector: prices_daily クエリは target_date 未満のデータのみ参照しルックアヘッドを防止、データ不足や API 失敗時に中立値で継続。

### Security
- OpenAI API キーが未設定の場合に明確な ValueError を返すようにし、無条件で API を叩くことを防止。

---

今後は各機能（ExecutionEngine・Broker クライアント・SystemMonitor 等）の単体テスト追加、エラーメトリクス・監視強化、銘柄別単元・手数料モデルの拡張などを予定しています。仕様や挙動に誤り・追記希望があれば指摘ください。