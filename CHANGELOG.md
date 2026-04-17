# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお本CHANGELOGはソースコードから推測して作成しています（コード内コメントや実装意図を元に要約）。実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- コア機能・初期実装を追加
  - パッケージ初期化
    - src/kabusys/__init__.py にバージョン情報 __version__="0.1.0" を追加。
  - 環境設定
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み機能を実装（OS 環境変数を保護するオプションあり）。
      - export KEY=val 形式、クォート付き値（バックスラッシュエスケープ対応）、コメント扱いなどを考慮した堅牢な .env パーサを実装。
      - 各種設定プロパティ (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEMORY/DISK 閾値 等) を提供。
      - 環境変数値のバリデーションを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - 実行用スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用する旨を明示。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了、例外発生時はログを出して次回ポーリングへ継続。
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory 経由のブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組立て、ExecutionEngine 起動を実装。
      - 停止フラグ検知でエンジンを停止、デーモンスレッドで実行する実行モデル。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（high/normal/low）。
      - CPU affinity を最初の N コアへ固定する set_cpu_affinity を実装。
      - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。
  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（スコア降順・タイブレーク）、等分配・スコア加重配分関数を実装。スコア全0時は等分配へフォールバック。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
      - unknown セクターは上限制限の対象外にする等のポリシーを明示。
    - src/kabusys/portfolio/position_sizing.py
      - 発注株数決定ロジック（risk_based / equal / score）を実装。
      - 単元（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer を加味した保守見積りを実装。
      - スケールダウン時の端数処理（lot 単位で残差順に追加配分）を実装。
    - src/kabusys/portfolio/__init__.py で公開 API を整理。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER, ROE）ファクターを DuckDB クエリにより実装。
      - データ不足時の None 扱い、ウィンドウ設計やスキャンバッファを考慮。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計 summary を実装。
      - ties（同順位）は平均ランクで処理する rank ユーティリティを実装。
    - src/kabusys/research/__init__.py で公開 API を整理（zscore_normalize を data.stats から再輸入）。
  - AI ニュース NLP（概要実装）
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini を想定）でセンチメントを取得して ai_scores に書き込む処理設計を実装。
      - バッチ処理（最大 20 銘柄/回）、記事数・文字数上限、API リトライ（429/5xx/タイムアウト）と指数バックオフ、レスポンス検証、スコアを ±1.0 にクリップして部分更新する方針を含む。
      - 注意: ファイル末尾で score_news の処理が途中で切れている（ソースが途中で終端）ため、実装は未完または抜粋である可能性あり。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 検証レポート生成スクリプトを実装（CLI: --from/--to/--db）。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を出力する。
      - P95 計算、日付フィルタのビルド、DB 存在チェック・例外ハンドリングを実装。
    - src/kabusys/tools/__init__.py を追加（パッケージ化用）。

Changed
- 設計上の決定（実装に明示）
  - run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する（監視は常に本番 DB を参照する方針）。
  - run_execution は paper_trading 環境の場合に専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB から分離。
  - .env 自動ロードの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings の各種プロパティは未設定時に ValueError を投げる / デフォルトを返す等の明確な挙動を持つ。

Fixed
- 入力値の堅牢化 / フォールバック
  - MONITOR_POLL_INTERVAL が不正（数値ではない・0 以下）の場合にデフォルト値へフォールバックして警告を出す（run_monitoring）。
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
  - process_priority, set_cpu_affinity: 権限不足・未対応プラットフォームでは警告ログを出して安全にスキップ。

Security
- 環境変数必須値の検証
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などの必須キーが未設定の場合は Settings が ValueError をスローして早期検出を促す。
- OpenAI API キーが未設定の場合は score_news は ValueError を送出（未設定で API 呼び出しを試行しない）。

Internal / Notes / TODO
- risk_adjustment.apply_sector_cap の価格欠損時のフォールバックについて注記あり（TODO: 前日終値や取得原価でフォールバック検討）。
- position_sizing は将来的に銘柄別単元（lot_size）をサポートする設計に拡張予定（TODO コメントあり）。
- ai/news_nlp.py は大枠の処理設計を備えるが、ソースが途中で切れている（score_news の途中終端: "if not articl..." で終わっている）。本ファイルは未完あるいは抜粋の可能性があり、実動作には追加実装が必要と推測される。
- DuckDB を積極活用する方針（research / ai / monitoring の分析用途で使用）。

互換性
- paper_trading モードでは DB を分離しており、本番 DB とはデータ分離されるため互換性の問題は少ない設計。
- OS による process priority / affinity の挙動は異なるため、プラットフォーム差分に注意。

参考: 主要ファイル一覧（このリリースで追加/変更が確認できるもの）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/ai/news_nlp.py

---

今後の作業候補（推奨）
- ai/news_nlp.py の未完部分の実装と統合テスト
- テストカバレッジの追加（.env パーサ、position_sizing のスケーリング挙動、process_priority の例外処理等）
- ドキュメント（API 使用法、環境変数一覧、運用手順）の整備
- price の欠損時フォールバック実装（risk_adjustment の TODO 対応）