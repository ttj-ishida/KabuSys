CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリース履歴はコードベースから推測して作成しています。

Unreleased
----------

なし

0.1.0 - 2026-04-12
-----------------

初回リリース。自動売買システム KabuSys のコア機能群を実装しました。
以下はコードベースから抽出した主な追加点・仕様・注意点です。

Added
- 基本バージョン情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定する。
    - 監視用 DB（sqlite）と DuckDB に接続して監視を実行。
    - 監視は KABUSYS_ENV の値にかかわらず本番 sqlite_path を使用する点に注意。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト data/paper_trading.db）を使用し、MockBrokerClient による分離された動作を想定。
    - 起動時にプロセス優先度を "high" に設定する。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を適用。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポートを生成する CLI ツール。
    - --from / --to / --db オプションをサポート。環境変数 PAPER_TRADING_SQLITE_PATH でも DB 指定可能。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 重み付けロジック（スコアが全て 0 の場合は等重でフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限による候補フィルタリング（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに基づく資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数計算。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size 単位で丸め、aggregate cap（available_cash）を超える場合はスケーリングと残差の再配分を行う。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

- リサーチ・ファクターモジュール（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: 各種ファクター（モメンタム、ATR、流動性、PER/ROE 等）を DuckDB SQL で計算。
    - データ不足時は None を扱う設計（ウィンドウサイズ判定あり）。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターンを複数ホライズンで計算（horizons デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数が 3 未満なら None。
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ。
    - 標準ライブラリのみで実装（pandas 等の外部依存なし）。
  - research パッケージは data.stats からの zscore_normalize を公開。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py
    - raw_news を集約して OpenAI API (gpt-4o-mini) にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルに書き込む処理を実装。
    - バッチサイズやトークン肥大化対策（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、リトライ（429/5xx/ネットワーク/タイムアウト）を備える。
    - calc_news_window でニュース収集ウィンドウを厳密に算出（ルックアヘッドバイアス対策）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。

- 設定管理・.env ローダ
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み（.env → .env.local の順、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パーサーは以下をサポート:
      - export KEY=val 形式
      - シングル／ダブルクォート、エスケープシーケンス
      - インラインコメント処理（クォートなしは '#' の直前が空白/タブならコメント）
    - Settings クラスで各種設定値をプロパティ経由で取得:
      - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PID/KILL フラグ: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - しきい値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
      - 環境: KABUSYS_ENV（development | paper_trading | live のみ許容）
      - LOG_LEVEL のバリデーション
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD） の差を吸収して優先度設定（psutil を使用）。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定（アクセス権限や未対応 OS は警告を出してスキップ）。
    - 例外（AccessDenied 等）を安全にハンドリングして実行継続。

Changed
- なし（初回リリース相当のため新規追加が中心）

Fixed
- なし（初回リリースのため明示的な修正ログはありませんが、各モジュールは以下のような堅牢性対策を含みます）
  - MONITOR_POLL_INTERVAL の不正値はデフォルトにフォールバックしてログ警告を出す。
  - .env ファイル読み込みでファイルアクセス失敗時は warnings.warn を発行してスキップ。
  - DuckDB 側で executemany 前にパラメータの空チェック（ai モジュールの注意点）。

Breaking Changes
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかでなければ ValueError を送出するようにバリデーションがあるため、既存の任意文字列を想定していた運用は調整が必要。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で指定。未設定時は明示的にエラーを返す（誤って未設定のまま実行することによる不正な動作を抑止）。

Notes / Usage
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。1 未満や不正値はデフォルト 60 秒にフォールバック。
  - 監視はデフォルトで settings.sqlite_path（data/monitoring.db）を使用する（KABUSYS_ENV に依存せず本番 DB を参照する設計）。
- 実行エンジン起動:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）を使用して本番 DB と分離。
- 環境変数自動ロード:
  - プロジェクトルートに .env(.local) を置くと自動でロードされる（ただし OS 環境変数を保護）。テスト等で自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Paper 検証レポート:
  - コマンド例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db または環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定。

今後の改善候補（コード内コメントより抜粋）
- portfolio.position_sizing: 銘柄ごとの lot_size を stocks マスタから取得するよう拡張。
- risk_adjustment.apply_sector_cap: price の欠損時に誤ったエクスポージャー評価が生じる点の改善（前日終値等のフォールバック導入）。
- ai.news_nlp: API 失敗時の部分的リトライ戦略やエラー時のテーブル保護ロジックの追加強化。

--- 

この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に基づき調整してください。