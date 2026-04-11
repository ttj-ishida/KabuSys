# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のフォーマットに準拠します。  
このファイルは、ソースコードから推測される機能追加・修正点を基に作成した推定の変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-11

初期公開リリース。以下の主要機能と設計方針を実装／追加しました。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。
  - Keep a Changelog に準拠した想定のリリースノートを作成。

- 起動スクリプト
  - 実行用スクリプト `run_execution.py` を追加。
    - プロセス優先度を高（High）に設定して起動。
    - 環境変数 `KABUSYS_ENV` が `paper_trading` の場合、Mock ブローカクライアントを使用し、Paper Trading 用の SQLite データベース（`data/paper_trading.db` 既定）へ完全分離して記録する挙動をサポート。
    - DuckDB を補助データ処理用に接続。
    - ExecutionEngine を組み立ててセッションを実行（OrderRepository / OrderManager / RiskManager / Reconciler を組合せ）。
    - 起動時に監視テーブル生成を冪等に保証（init_monitoring_db を呼び出し）。
  - 監視用スクリプト `run_monitoring.py` を追加。
    - プロセス優先度を高に設定して起動。
    - 監視ループのポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。無効値や 0 以下はデフォルト 60 秒にフォールバックし、警告ログを出す。
    - Monitoring は環境に関わらず本番用の `sqlite_path` を利用する仕様（監視データは本番 DB を参照／書き込み）。

- 設定管理
  - `kabusys.config.Settings` を実装（src/kabusys/config.py）。
    - `.env` / `.env.local` 自動ロード（OS 環境変数の保護、`.git` または `pyproject.toml` を基準にプロジェクトルートを検出）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
    - `.env` のパースは `export KEY=val`、クォート付き値、インラインコメント等を考慮した堅牢な実装。
    - 各種設定プロパティを提供（API トークン、DB パス、PID ファイル、閾値、ログレベル、環境種別 等）。
    - `PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の有効値チェック。`is_live` / `is_paper` / `is_dev` 補助プロパティを追加。

- ポートフォリオ構築（portfolio）
  - 銘柄選定・重み算出関数群を追加（純粋関数、メモリ内計算）。
    - select_candidates: スコア降順かつタイブレークで signal_rank を使って上位 N を選択（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外するロジック（売却予定銘柄の除外、未知セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未定義レジームでのフォールバック。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）でスケールする実装。
    - 手数料・スリッページ想定の cost_buffer を考慮した保守的見積り、スケーリング時の端数配分（lot_size 単位）を実現。

- 研究（research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）等を DuckDB の SQL によって計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を算出。NULL の取り扱いに注意。
    - calc_value: raw_financials（財務）と prices_daily を組合せた PER / ROE 計算（最新報告期データを取得）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを LEAD を使って一度のクエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。レコードが不足する場合は None。
    - factor_summary / rank: 統計サマリーや同順位の平均ランク処理を提供。
  - research パッケージのエクスポートを整理（src/kabusys/research/__init__.py）。

- AI 関連（ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価し、ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数制限（最大記事数／最大文字数）でトークン膨張を抑制。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx には指数バックオフでリトライ、その他はスキップしてフェイルセーフに。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリッピング。
    - DuckDB に対する冪等な書き込み（DELETE → INSERT、executemany の空リスト回避）を実装。
    - OpenAI 呼び出しをラップした _call_openai_api を分離し、テスト時の差し替えを考慮。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみを使用し、API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - マクロニュース抽出はキーワードベース。LLM の呼び出しは news_nlp を直接参照せず独立実装。

- ユーティリティ（utils）
  - process_priority（src/kabusys/utils/process_priority.py）
    - プラットフォーム差を吸収してプロセス優先度を設定（Windows: HIGH_PRIORITY_CLASS 等 / POSIX: nice 値）。
    - CPU Affinity を最初の N コアに固定する機能を追加（アクセス権限失敗や未対応 OS は警告でスキップ）。
    - 例外（AccessDenied 等）は警告でハンドリングして安全にフォールバック。

### Changed
- 設計方針（全体）
  - 外部 API（OpenAI 等）の呼び出しは失敗してもシステム全体を停止させないフェイルセーフ実装を採用。
  - datetime.today()/date.today() による暗黙の時刻参照を避け、全ての処理が引数で渡された target_date を基準に動作する設計（ルックアヘッドバイアスの防止）。
  - DuckDB を主要な分析エンジンとして利用し、SQL と Python の組合せでファクター算出を行う方針を採用。

### Fixed
- 仕様上の注意点実装
  - `.env` パーサーでのクォート内のバックスラッシュエスケープや inline コメントの扱いを正しく処理するように実装（環境変数読み込みの堅牢化）。
  - MONITOR_POLL_INTERVAL が不正な値（非数値や 0/負数）の場合に ValueError を発生させず、警告ログを出してデフォルトにフォールバックする挙動を追加。

### Security
- API キー取り扱い
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を発生させる（news_nlp.score_news / regime_detector の前提）。
  - `.env` 自動ロード時に OS 環境変数を保護（.env が OS 環境を上書きしない）する挙動を採用。

### Known limitations / Notes
- 一部処理で価格が欠損（0.0）の場合、セクターエクスポージャや position sizing の結果が過少/除外される可能性がある旨をログで注意しており、将来的には前日終値や取得原価を用いるフォールバックが検討されている（TODO を記載）。
- 単元株（lot_size）は現状全銘柄共通の 100 を想定しており、将来的には銘柄別設定へ拡張予定。
- DuckDB の executemany に関する制約（空リスト不可）を回避するため、空パラメータチェックを入れている。
- OpenAI API 呼び出しのモデルは現時点で gpt-4o-mini に固定。将来的に切替可能な設計の検討余地あり。

---

この変更履歴はコードの実装内容およびドキュメンテーション（docstring）から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合がありますので、必要に応じて具体的な差分情報で更新してください。