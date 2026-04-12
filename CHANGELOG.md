# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングを使用します。

※コードベースから推測して作成しています。実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース。システム全体のコア機能（設定管理、起動スクリプト、ポートフォリオ構築、ポジションサイズ計算、リスク調整、リサーチ用ファクター計算、ニュースNLP スコアリング、監視・検証ツール、ユーティリティ）を含む。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys/__init__.py に __version__ = "0.1.0"）。
  - モジュールのエクスポートを整理（kabusys/portfolio/__init__.py, kabusys/research/__init__.py）。

- 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env 読み込みでの詳細なパースロジックを実装（export 構文、クォート、エスケープ、インラインコメント処理をサポート）。
  - OS 環境変数を保護する `protected` 処理、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化を実装。
  - 設定取得用 Settings クラスを導入（各環境変数の取得、デフォルト値、妥当性チェックを含む）。
  - 環境フラグ（development / paper_trading / live）や各種パス/しきい値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）を管理。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）と明示的エラー。
  - 環境判定用のプロパティ（is_live/is_paper/is_dev）を追加。

- 起動スクリプト
  - 実行エンジン起動用スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - プロセス優先度を起動時に設定する処理を追加。
    - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - duckdb を分析用 DB として接続。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告を出してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計（監視は本番 DB を前提）。
    - SystemMonitor を用いた単一チェックループを実装（例外はログに記録して継続）。
    - 起動時にプロセス優先度を設定。

- ポートフォリオ構築（src/kabusys/portfolio）
  - 候補選定・重み付け（portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank でタイブレークして上位 N 件を選定。
    - calc_equal_weights: 等金額分配（1/N）。
    - calc_score_weights: スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
  - リスク調整（risk_adjustment.py）
    - apply_sector_cap: セクター別既存保有比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外規制対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）。未知レジームは 1.0 にフォールバックして警告ログ。
  - ポジションサイズ計算（position_sizing.py）
    - calc_position_sizes: weight/candidates/portfolio_value/available_cash 等を元に買付株数を算出する多機能実装。
      - allocation_method に応じたリスクベース/等分/スコア方式をサポート。
      - lot_size（単元）丸め、1 銘柄上限（max_position_pct）、合計投資額の aggregate cap、cost_buffer を考慮した保守的見積り、スケーリング（スケールダウン）ロジックを実装。
      - スケールダウン後の残余キャッシュを用いた余剰配分ロジック（remainders）により再現性を保った追加配分を実現。

- リサーチ（src/kabusys/research）
  - ファクター計算（research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（ウィンドウのデータ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を結合して PER/ROE を計算（最新財務データを銘柄ごとに取得）。
    - DuckDB 接続を受け取り SQL ベースで効率的に計算する設計。
  - 特徴量探索（research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算、horizons の妥当性チェックあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。レコード数が不足すると None を返す。
    - rank: 同順位は平均ランクにする安定なランク関数を実装（丸めで ties の検出漏れを防止）。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を取得する統計サマリ。
  - すべて外部 API に依存せず、prices_daily/raw_financials のみ参照する純粋関数群として設計。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングし、ai_scores テーブルへ書き込む処理を実装。
  - 特徴:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を正確に計算して記事を抽出。
    - 銘柄ごとに記事を集約し、1 銘柄あたり記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄ずつのバッチ送信、JSON Mode を期待するプロンプトを使用して厳密な JSON 応答を要求。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（上限設定あり）。
    - レスポンス検証（構造・型・既知コード・スコア数値型）とスコアの ±1.0 クリッピング。
    - 部分成功に備え、更新は対象コードに限定して置換（既存の他コードスコアを保護）。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用、未設定時は ValueError。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI から日付範囲指定（--from, --to）や DB パス指定（--db）が可能。
    - system_status, trade_logs, risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ指標（avg/max/P95）を集計。
    - P95 計算、NULL/データ不足時の N/A 表示を実装。
    - 合格基準（閾値）を定義し PASS/FAIL 判定を出力（稼働率、fill率、send率、P95 レイテンシなど）。
    - PAPER_TRADING_SQLITE_PATH 環境変数をサポート（デフォルト: data/paper_trading.db）。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プロセス優先度設定 API を追加（set_process_priority(level)）。Windows / POSIX(Linux/Mac/FreeBSD) の差分を吸収。
  - CPU affinity 設定（set_cpu_affinity(cpu_count)）を追加。
  - 権限不足や未実装環境での例外をキャッチし警告ログでフォールバックする堅牢な実装。

- DB 初期化ヘルパー呼び出し
  - run_execution と run_monitoring で init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）。

### Changed
- なし（初回リリースのため変更履歴はありません）。

### Fixed
- なし（初回リリース）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- OpenAI API キーの取り扱いは引数または環境変数から解決し、未設定時は明示的にエラーを出すなど安全性に配慮。

---

将来的なリリースでは、実動作のログ/メトリクス改善、ユニットテスト追加、さらに細かいエラーハンドリングや外部サービスへの接続制御（タイムアウト・リトライ戦略の拡張）などが考えられます。必要であれば各機能ごとに詳細なリリースノートを分割して作成します。