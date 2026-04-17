# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はソース内のバージョン情報や実装状況から推定できないものは省略または未記入としています。

## [Unreleased]

### 追加
- プロセス起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全な終了処理。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 例外時はログ出力して次ポーリングへ継続するフェイルセーフ実装。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - 起動時に停止フラグが立っている場合は起動を行わない。
    - エンジンは別スレッドで実行、停止フラグ検知時に Engine.stop() を呼んで安全停止。
    - 実行 PID を data/execution.pid に記録する想定（pid_file の扱い）。
- 設定・環境変数管理
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き可能）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。
    - .env パーサの強化: export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理の改善。
    - Settings クラスを導入し多数のプロパティを提供（DB パス、PID パス、監視閾値、環境種別判定など）。入力値検証を実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証等）。
- ポートフォリオ構築モジュール
  - portfolio_builder.py
    - 銘柄候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - セクター集中制限の適用（既存ポジションを基にセクター露出を計算し上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知値はログ警告の上フォールバック）。
  - position_sizing.py
    - 株数算出ロジック（risk_based / equal / score）。
    - 単元株（lot_size）に基づく丸め、1 銘柄上限・投下予算（aggregate cap）調整、コストバッファ反映、スケールダウン時の端数配分ロジックなどを実装。
- リサーチ・ファクタモジュール
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金 等）、バリュー（PER/ROE）の計算関数を実装。DuckDB の prices_daily/raw_financials テーブルを利用。
    - データ不足時は None を返す堅牢な実装。
  - research/feature_exploration.py
    - 将来リターン（fwd_1d 等）の計算、Spearman ベースの IC 計算（rank による同順位処理）、ファクター統計サマリを実装。外部依存を避け標準ライブラリのみで実装。
  - research パッケージの __all__ を整備して主要 API を公開。
- AI ニュース NLP モジュール
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でバッチ処理して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込むロジックを実装（バッチサイズ、最大記事数・文字数トリム、429/ネットワーク/5xx のリトライ、レスポンス検証、スコアクリップ等）。
    - ニュース収集ウィンドウ（JST 基準 → UTC 変換）を calc_news_window で提供し、ルックアヘッドバイアスを避ける設計。
    - API キーの解決方法（引数または環境変数 OPENAI_API_KEY）と未設定時の例外を明確化。
- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定（Windows と POSIX を吸収）、set_process_priority を提供（high/normal/low）。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
    - 権限不足や未実装 API へのフォールバックで警告を出してスキップするフェイルセーフ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加（コマンドラインから実行可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力（閾値定義あり）。
    - 日付フィルタ、DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更
- DB の取り扱いに関する設計上の明示化
  - 監視（monitoring）は環境に関わらず本番 sqlite_path を参照する仕様を明記（run_monitoring）。
  - 実行（execution）は paper_trading 環境を検出して専用 DB を使用する（run_execution）。
- .env 読み込みの優先度と保護挙動を明確化（OS 環境変数は保護、.env.local で上書き可能）。

### 修正（設計上の安全性/ロバストネス強化）
- 長時間ループやスレッド運用時の安全停止処理（停止フラグの検知、KeyboardInterrupt ハンドリング、接続クローズの保証）。
- DuckDB / SQLite 接続は起動時に確立し、終了時に確実に閉じる実装。
- .env パーサでのクォート・エスケープ処理の改善により特殊文字を含む値の誤解釈を低減。
- AI モジュールでの API レスポンス検証と部分失敗時のデータ保護（対象コードのみ差し替え）を想定した実装方針。

### 互換性の注意点 / Breaking Changes
- 監視プロセスは常に settings.sqlite_path（本番 monitoring.db）を使用するため、KABUSYS_ENV の設定が期待どおりに動作する以前の運用と異なる可能性あり。Paper Trading の監視を分離したい場合は別途対応が必要。
- PAPER_FILL_MODE に許容される値を厳格化（instant/partial/never/reject）。不正値は起動時に ValueError を送出する。
- LOG_LEVEL / KABUSYS_ENV の値検証を強化。既存の環境値が許容リストにない場合はエラーとなる。

## [0.1.0] - (初回リリース)
注: ソース内 __version__ に基づく初期バージョン。上記 Unreleased に列挙した主要機能群がこのバージョンに相当します。
- 初期リリースとして以下を含む:
  - 実行/監視用エントリポイント（run_execution, run_monitoring）
  - 環境設定管理（Settings, .env 自動読み込み）
  - Portfolio 構築、リスク調整、ポジションサイジング関数群
  - Research（ファクター計算、将来リターン、IC、統計サマリ）
  - AI ニュース NLP スコアリング基盤（OpenAI バッチ処理設計）
  - ツール: Paper Trading 検証レポート生成
  - ユーティリティ: プロセス優先度 / CPU affinity 管理

---

変更履歴の記載はソースコードから推定して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに合わせて日付・詳細を更新してください。