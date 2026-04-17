CHANGELOG
=========

すべての notable な変更はこのファイルで追跡します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------

- なし（開発中の変更はここに記載してください）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本モジュールを追加。
  主な追加ファイル・機能:
  - パッケージメタ:
    - src/kabusys/__init__.py — バージョン定義 (__version__ = "0.1.0")。
  - 設定・環境変数管理:
    - src/kabusys/config.py
      - .env/.env.local の自動読み込み (プロジェクトルート検出: .git / pyproject.toml)。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - 必須環境変数チェック用 _require。
      - 各種設定プロパティ（DB パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE バリデーション等）。
  - 実行 / 監視用エントリポイント:
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組立て、別スレッドでの engine 実行、停止フラグ・pid 管理。
      - デフォルトでプロセス優先度を "high" に設定。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
      - 監視は環境に関わらず本番 sqlite_path を使用（監視テーブル初期化）。
      - 停止フラグ (data/stop_requested.flag) の検知で安全に終了。
  - 監視 DB 初期化ヘルパー（monitoring 側で利用）:
    - src/kabusys/monitoring/*（init_monitoring_db 等を参照するコードが利用、ファイル本体は別所に存在）
  - ユーティリティ:
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォームでのプロセス優先度設定 (Windows / POSIX の差分吸収)。
      - set_cpu_affinity による CPU affinity 設定ユーティリティ。
      - 権限不足や未サポート環境では警告を出して安全にスキップ。
  - ポートフォリオ構築関連（純粋関数群、DB 非依存）:
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア配分 (calc_score_weights: スコア合計が 0 のときは等配分にフォールバック)。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限 (apply_sector_cap): 既存ポジションからセクター別エクスポージャ計算、上限超過セクターの候補除外。unknown セクターは制限対象外。
      - レジーム乗数 (calc_regime_multiplier): bull/neutral/bear に対応、未知は 1.0 でフォールバック（警告）。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing（risk_based / equal / score）。
      - 単元株（lot_size）で丸め、per-stock 上限や aggregate cap によりスケールダウン。cost_buffer による保守的見積もり。
      - 価格欠損時のスキップや各種安全弁、残差分配ロジックを実装。
    - src/kabusys/portfolio/__init__.py — 上記関数をエクスポート。
  - 研究・リサーチ:
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL ベース実装）。
      - 各関数は prices_daily / raw_financials を参照し、データ不足時は None を返す設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）やランク化・統計サマリ (factor_summary, rank)。
      - pandas 等に依存せず標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py — 主要関数を公開。
  - ツール:
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 検証レポート生成スクリプト（CLI）。
      - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等の計算と PASS/FAIL 判定（デフォルト閾値を定義）。
      - PAPER_TRADING_SQLITE_PATH で DB を指定、--from/--to/--db オプション対応。
  - AI / ニュース NLP （OpenAI 統合、未完部分あり）:
    - src/kabusys/ai/news_nlp.py
      - raw_news を OpenAI (gpt-4o-mini) でセンチメント化して ai_scores に書き込む設計。
      - バッチ送信、トークン肥大対策（記事数・文字数トリム）、429/5xx 等のリトライ（指数バックオフ）、JSON レスポンス検証、スコア ±1.0 にクリップ、部分更新戦略（成功した銘柄のみ置換）等の方針を実装。
      - calc_news_window 等のユーティリティは実装済み。ファイル末尾で実装途中で切れている箇所がある（本リリースでは実装途中の可能性あり）。
  - DB: DuckDB と SQLite の併用を前提に設計（DuckDB は主に時系列・リサーチ DB、SQLite は監視・実行ログ等）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または明示的引数で渡す仕様。未設定の場合はエラーを返す（news_nlp）。

Notes / Known limitations
- news_nlp.py はファイル末尾が途中で切れており、記事取得・API 呼び出しの続き処理が未表示・未確認。リリース時点で該当機能は部分実装の可能性があるため、利用前に実装完了を確認してください。
- position_sizing や apply_sector_cap は価格欠損時のフォールバック（例: 前日終値使用等）を現状サポートしておらず、将来的な拡張がコメントで示されています（TODO）。
- process_priority/set_cpu_affinity は権限不足や未サポート OS の場合にスキップし、警告ログを出力します。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使うため、paper_trading 環境でも監視 DB は分離されません（意図的設計）。

今後の予定（例）
- news_nlp.py の未完了部分の実装と堅牢性テスト。
- 銘柄ごとの lot_size を stocks マスタから読み込む拡張。
- 価格欠損時のフォールバックロジック（前日終値や取得原価の使用）。
- 追加のユニットテストとドキュメント整備。

--- 

（この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。）
