# Keep a Changelog
すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

最新版: [0.1.0] - 2026-04-12

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-04-12
初回リリース — KabuSys のコア機能群を実装しました。以下は主要な追加点と設計上の注意点です。

### Added
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0"

- 設定・環境読み込み
  - kabusys.config.Settings: 環境変数／.env ファイルからの設定取得を提供。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env, .env.local の優先度処理（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - 各種設定プロパティ（DB パス、PID ファイル、監視閾値、環境判定等）を提供。
    - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 実行 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の際は paper_trading 用 SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）。
    - DuckDB 接続を受け取り、監視テーブルの存在を保証する初期化処理を実施。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - プロセス優先度設定、SQLite / DuckDB 接続、例外ハンドリング（check_once() 内の例外はログ出力して次ループへ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N 件を選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告を出力）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用。既存保有のセクターエクスポージャー算出（売却予定銘柄の除外可）。
      - "unknown" セクターは上限判定の対象外。
      - price の欠損に関する注意コメントあり（将来的にフォールバック価格を検討）。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に応じた乗数を返す。未知のレジームは 1.0 でフォールバック（警告）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数算出ロジック。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: 損切り幅・risk_pct に基づいた株数算出。
      - equal/score: 重み（weights）に基づく配分。per-position 上限、aggregate cap（available_cash）を考慮。
      - lot_size（単元株）考慮、cost_buffer による保守的見積り、スケーリング時の残差配分アルゴリズム実装。
      - 将来的に銘柄別 lot_size を導入するための TODO コメントあり。

- 研究（research）モジュール
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率等を計算（DuckDB の prices_daily を使用）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（直近財務レコードの抽出ロジックあり）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）の一括取得（1 クエリで複数ホライズンを処理）。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ数不足時に None を返す挙動。
    - factor_summary / rank: 基本統計量とランク付けユーティリティ。
  - duckdb 接続を前提にし、外部依存（pandas 等）なしで実装。

- ニュース NLP（AI 統合）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約し、OpenAI API（gpt-4o-mini）へバッチ送信して銘柄ごとの sentiment スコアを ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、記事・文字数上限、JST → UTC のニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算。
    - OpenAI クライアント生成、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ（上限あり）。
    - レスポンスのバリデーションとスコアクリップ（±1.0）。部分失敗でも他コードの既存スコアを保護するため、対象コードを限定して置換（DELETE + INSERT）する戦略。
    - 実装は安全策（API キー必須検査、空の結果でのログ出力など）を含む。
    - （ソースは途中までの抜粋含むが、設計と挙動は明確）

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定。権限不足や未対応 OS は警告出力してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity を設定（引数 None で無効、1 未満は ValueError）。
    - psutil を使用。platform による分岐と例外ハンドリング実装。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプト（コマンドラインツール）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算、日付フィルタ、DB 存在チェック、OperationalError に対して保守的にデフォルト値でレポートを生成。
    - 合格基準（閾値）を定義して PASS/FAIL 判定を出力。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得する設計。キー未設定時は明示的なエラーを送出して失敗を避ける。

## 注意点・既知の制約 / TODO
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用する設計です。意図的な仕様だが、運用上の注意が必要。
- .env パーサは多くのケース（クォート、エスケープ、コメント）に対応するが、極端に複雑な .env の構文は想定外の振る舞いをする可能性あり。
- position_sizing:
  - price が 0.0 の場合にエクスポージャーが過小見積もられる旨の TODO がある（将来的にフォールバック価格を導入予定）。
  - lot_size の将来的拡張（銘柄別単元）のための TODO コメントあり。
- process_priority / set_cpu_affinity: 実行環境の権限や OS により設定が失敗する場合があり、その場合は警告ログを出して安全にスキップする実装。
- DuckDB 側: 一部処理（ai/news_nlp）で executemany の前に params が空でないことを確認する等、DuckDB の実装差異に配慮したコメントがある。
- ai/news_nlp: API エラー耐性や部分更新戦略を持つが、外部 API を利用するためコスト・レイテンシ・利用制限に注意が必要。
- research モジュールは prices_daily / raw_financials のデータ品質に依存する。データ不足時は None を返す仕様（上位で除外・補完が必要）。

## 発行者
- KabuSys 開発チーム

（必要であれば各モジュールごとの変更履歴を更に細分化して追記できます。例: 個別関数の引数やデフォルト値の変更、バグ修正履歴等）