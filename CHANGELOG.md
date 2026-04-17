# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本CHANGELOGはリポジトリのコード内容から推測して作成しています（実装上の意図・挙動に基づく記述）。実際のリリースノート作成時は必要に応じて調整してください。

## [Unreleased]

- 開発中の変更・提案（ドキュメント化のためのプレースホルダ）。
  - 追加予定: ai/news_nlp.py の処理完了（記事集約後の OpenAI 呼び出し・DB 書き込み処理の続き）。

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・モジュールを含みます。

### Added
- 基本アプリケーション情報
  - パッケージ初期化とバージョン定義 (kabusys.__version__ = "0.1.0") を追加。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用し、本番 DB と完全分離。
    - 実行中の停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う仕組みを実装。
    - BrokerClientFactory によるブローカークライアント選択と、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - RiskManager 用のデフォルト RiskConfig を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は常に本番用 sqlite_path を使って監視テーブルを初期化／更新する実装。

- 設定・環境変数管理
  - config.Settings クラスを導入し、環境変数経由の各種設定をプロパティとして提供（DB パス・API トークン・監視閾値・環境判定など）。
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パーサーで export 形式やクォート・エスケープ・インラインコメントに対応。

- 監視・ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（アクセス権限がない場合は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を追加（既存保有を基にセクター別エクスポージャを計算して候補を除外）。
    - 市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を追加（bull/neutral/bear をサポート、未知レジームは警告とともに 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮した安全な発注数決定を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、出来高関連）、バリュー（PER、ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時は None を返すことで安全に扱えるよう設計。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）やファクター統計サマリー（factor_summary）およびランク変換（rank）を実装。
    - 外部ライブラリに依存せず純粋な Python と DuckDB SQL で実装。

- AI ニュース NLP
  - ai/news_nlp.py（部分実装）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント評価を行い、ai_scores テーブルへ書き込む設計。
    - バッチサイズ、API リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンスバリデーション、スコアクリッピング（±1.0）等の堅牢化方針を実装。
    - ニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST のUTC変換）を提供する calc_news_window を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI ツールを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算し、閾値（稼働率 99%、成立率 90% など）に基づく PASS/FAIL 判定を出力。
    - DB が存在しない・テーブルがない等のエラーを安全に扱う（OperationalError をキャッチして N/A を表示）。

- DuckDB / SQLite の併用
  - DuckDB は時系列・リサーチ用途（prices_daily, raw_financials 等）に使用。
  - SQLite は監視・発注ログ等の永続化に使用。paper_trading 環境では専用 SQLite を用意して本番と分離。

### Changed
- 設定ロード順序
  - OS 環境変数 > .env.local > .env の優先順位でロードする挙動を導入（.env.local は上書き可能）。
  - OS 環境変数群は protected として .env の上書きを防止。

- ロギング・フェールセーフ
  - 多くの箇所で不正な設定値（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、LOG_LEVEL、KABUSYS_ENV など）に対して警告を出し、安全なデフォルトへフォールバックする処理を追加。
  - process_priority の設定失敗時は例外を投げずに警告を出して処理継続するように変更。

### Fixed
- 正常停止の扱い
  - run_execution/run_monitoring で data/stop_requested.flag を検出して安全に停止する処理を追加。既にフラグが立っている場合は起動を抑止する（run_execution）。

- calc_score_weights のゼロスコアケース
  - 全銘柄のスコア合計が 0 の場合、分母ゼロを避け等金額配分にフォールバックするように修正（警告ログ付き）。

- .env パーサーの堅牢性
  - export プレフィックス・クォート（シングル/ダブル）・バックスラッシュエスケープ・インラインコメントの扱いを改善し、誤読を減らす実装に変更。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給する設計。未設定の場合はエラーを出して明示的に拒否することで、秘密鍵の取り扱いミスを低減。

---

注:
- この CHANGELOG はソースコードから推測した機能と設計意図に基づいて記載しています。実際のバージョン管理・リリース日・コミット単位の変更履歴とは差異がある可能性があります。必要に応じて実環境の変更履歴（Git のコミットログ等）を参照して確定版を作成してください。