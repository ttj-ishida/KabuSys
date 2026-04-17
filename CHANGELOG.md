# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式に従って記載します。  
バージョン付けは semver の考え方に準拠しています。

なお、本 CHANGELOG はリポジトリ内のソースコードから挙動・追加機能を推測して作成しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-17

Added
- 初回リリース。以下の主要機能およびモジュールを追加。
  - 実行用エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading 用の分離された SQLite DB を使用する。停止フラグ／PID ファイルの取り扱い、スレッドでのエンジン実行制御を実装。
      - ファイル: src/kabusys/run_execution.py
  - 監視用エントリポイント
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - ファイル: src/kabusys/run_monitoring.py
  - 設定管理
    - config.py: .env 自動ロード機構（.env / .env.local、OS 環境変数保護、override の挙動）、高度な .env 行パーサ（export 対応、クォート・エスケープ、インラインコメント取り扱い）を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、設定値取得用 Settings クラス（各種パス・閾値・フラグ・環境確認メソッド）を提供。
      - ファイル: src/kabusys/config.py
  - ポートフォリオ構築（純粋関数群）
    - portfolio_builder.py:
      - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
      - 重み計算：calc_equal_weights（等分配）、calc_score_weights（スコア正規化、全スコア 0 の場合に等分配へフォールバックして WARNING を出力）。
      - ファイル: src/kabusys/portfolio/portfolio_builder.py
    - risk_adjustment.py:
      - apply_sector_cap：既存保有を基にセクター単位の上限チェックを行い、上限を超えたセクターの新規候補を除外（"unknown" セクターは除外しない）。
      - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは警告の上 1.0 でフォールバック。
      - ファイル: src/kabusys/portfolio/risk_adjustment.py
    - position_sizing.py:
      - calc_position_sizes：allocation_method（risk_based / equal / score） に基づく株数決定、単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング処理、cost_buffer を考慮した保守的見積り、および残余キャッシュによる端数配分ロジックを実装。
      - ファイル: src/kabusys/portfolio/position_sizing.py
    - モジュール公開: src/kabusys/portfolio/__init__.py により主要関数をエクスポート。
  - リサーチ / ファクター計算
    - research/factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
      - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率（windows と NULL の厳密な扱い）。
      - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（target_date 以前の最新財務レコード選択ロジック含む）。
      - ファイル: src/kabusys/research/factor_research.py
    - research/feature_exploration.py:
      - calc_forward_returns: 複数ホライズンの将来リターンをまとめて取得（入力検証あり）。
      - calc_ic: スピアマンランク相関（IC）を計算（結合・欠損除外・有効レコード数チェック）。
      - rank / factor_summary: ランク変換（同順位は平均ランク）や基本統計量算出（count/mean/std/min/max/median）を実装。
      - ファイル: src/kabusys/research/feature_exploration.py
    - research パッケージのエクスポートを追加（zscore_normalize を含む）。
      - ファイル: src/kabusys/research/__init__.py
  - データ処理ユーティリティ
    - data.stats（参照のみ、エクスポートされる zscore_normalize を research パッケージで利用）。
  - ニュース NLP（AI 統合）
    - ai/news_nlp.py:
      - raw_news を OpenAI（gpt-4o-mini）でバッチセンチメント解析し、ai_scores テーブルへ反映する処理を実装。
      - バッチサイズ、トークン肥大対策（記事数・文字数トリム）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）、部分失敗時の DB 保護（対象コードのみ置換）等を設計に含む。
      - ファイル: src/kabusys/ai/news_nlp.py
  - ツール
    - tools/paper_verification_report.py:
      - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を抽出し PASS/FAIL 判定を出力。閾値（稼働率 99% 等）・P95 算出ロジックを含む。
      - CLI 引数（--from, --to, --db）に対応。
      - ファイル: src/kabusys/tools/paper_verification_report.py
  - 実行環境ユーティリティ
    - utils/process_priority.py:
      - cross-platform なプロセス優先度設定（Windows と POSIX の差分吸収）、CPU affinity 設定関数を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
      - ファイル: src/kabusys/utils/process_priority.py
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

Changed
- 設定読み込みの挙動
  - .env の自動ロードはデフォルトで有効。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env.local は .env を上書きするための優先順位で読み込まれる（ただし OS 環境変数は保護される）。

Fixed / Improved
- .env パーサの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントや空白扱いの改善などを実装し、意図しないパースを防止。
- 環境変数検証の追加
  - Settings.paper_fill_mode: 有効値チェック（instant/partial/never/reject）。不正値時には ValueError を送出。
  - Settings.env / log_level: 許容値検査を導入し不正設定検出時に明示的なエラーを発生させる。
- run_monitoring の堅牢化
  - MONITOR_POLL_INTERVAL の値検証（0 以下や非整数はデフォルトへフォールバックし、警告を出力）。
  - 停止フラグ検知による安全なループ終了、check_once() 内例外をキャッチしてループ継続するフォールトトレラント設計。
- DB 初期化の冪等性確保
  - init_monitoring_db(sqlite_conn) を実行し、監視テーブルが存在することを保証（Execution 側でも呼び出し）。
- position_sizing の集約上限スケーリング
  - available_cash 超過時のスケールダウンとロット単位での再配分ロジックを実装。cost_buffer による保守的見積りを導入。
- research / factor 計算の NULL・データ不足処理改善
  - ウィンドウ内の行数が不足する場合は None を返すなど、安全に欠損を扱う。

Security
- OpenAI API キーの取り扱い
  - ai/news_nlp.score_news は引数 api_key または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して明示的に失敗させる（秘匿鍵の誤使用防止）。

Notes / Usage
- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離する設計。MockBrokerClient の動作は設定（PAPER_FILL_MODE）に依存。
- モニタリング
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を調整可能（正の整数、デフォルト 60 秒）。
- プロセス優先度
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出してプロセス優先度を上げようとする（権限不足時は警告でスキップ）。

References (主要ファイル)
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/config.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

---

今後のリリースノート案
- Unreleased には以下を想定している改善案をメモしておくとよいでしょう:
  - news_nlp の部分的失敗リトライ戦略のログ・メトリクス強化
  - position_sizing の銘柄別 lot_size 対応（マスタ参照）
  - テストカバレッジの追加（特に .env パーサとスケーリングロジック）
  - ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）の API 参照を整備

以上。必要であれば各項目をさらに分割して詳細なコミット/チケット参照（例: ファイル・関数単位）を追加できます。