CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-16
-------------------

Added
- 基本リリースとして日本株自動売買ライブラリ "KabuSys" を追加。
  - パッケージメタ情報: __version__ = 0.1.0

- 環境設定・読み込み
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - export KEY=val 形式、クォート文字列（バックスラッシュエスケープ考慮）、およびインラインコメントの扱いに対応した .env パーサを実装。
  - OS 環境変数を保護する protected オプションを導入（.env.local は上書き可能だが既存 OS 環境変数は上書きしない）。
  - Settings クラスで環境変数の取得・検証を集中管理（KABUSYS_ENV, LOG_LEVEL, 各種 DB パス, PAPER_FILL_MODE 等の妥当性チェックを実装）。
  - settings インスタンスをモジュールレベルで提供。

- 実行 / 監視スクリプト
  - run_execution.py:
    - ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading 時には paper_trading 用の SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由で実際のブローカー／モックを切り替え。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。エンジンスレッドをデーモンで実行し、data/stop_requested.flag を検知すると安全に停止。
    - 起動時にプロセス優先度を "high" に設定。PID ファイル出力に対応。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する挙動を明記。
    - data/stop_requested.flag による停止検知、例外発生時のログ残しと次回ポーリング継続、KeyboardInterrupt による終了処理を実装。

- 監視 DB 初期化
  - init_monitoring_db により実行前に監視テーブルの存在を保証（冪等な初期化処理）。

- ポートフォリオ構築（純関数群）
  - kabusys.portfolio:
    - portfolio_builder:
      - select_candidates: BUY シグナルのスコア降順で上位 N を選択（同点時は signal_rank でタイブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバック）を実装。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限を適用する関数を提供。既存保有のセクター別時価で上限を判定し、上限超過セクターの新規候補を除外。"unknown" セクターは除外対象にしない（フォールバック挙動）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告の上 1.0 にフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた株数決定ロジックを実装。
        - 単元（lot_size）丸め、1 銘柄上限（portfolio_value * max_position_pct）、aggregate cap（available_cash）超過時のスケールダウン、および残余キャッシュを用いた lot 単位の再配分ロジックを実装。
        - 不正な価格（<=0）の銘柄はスキップし、ログで指摘。
        - 将来的な拡張（銘柄別 lot_size、価格フォールバック）についての TODO を記載。

- 研究／ファクター計算
  - kabusys.research:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離などの計算を DuckDB SQL で実装。必要行数が不足する場合は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。true_range の NULL 伝播を考慮。
      - calc_value: raw_financials から直近の財務データを取得して PER/ROE を算出。
    - feature_exploration:
      - calc_forward_returns: 任意ホライズンの将来リターンを計算（horizons 引数で指定、検証済みの範囲チェックあり）。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。3 件未満で計測不可の場合は None を返す。
      - factor_summary / rank: 基本統計量サマリとランク付けユーティリティを実装。
    - 研究用に zscore_normalize を外部（kabusys.data.stats）から再エクスポート。

- ニュース NLP（AI）
  - kabusys.ai.news_nlp:
    - ニュース記事を OpenAI (gpt-4o-mini) に問い合わせて銘柄ごとのセンチメントスコア（-1.0～1.0）を生成する仕組みを追加。
    - 処理設計:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
      - バッチサイズ、1 銘柄あたりの記事数・文字数制約、スコアのクリップ範囲、エクスポネンシャルバックオフによる再試行、レスポンスの厳密な JSON 検証などのガードを導入。
      - score_news 関数は API キー解決、ウィンドウ計算、記事集約、API 送信、結果検証、ai_scores テーブルへの置換書き込みを行う設計。ただしファイルが途中で切れているため（実装の一部が途切れていることを確認）、完全な処理フローは将来のコミットで補完予定。
    - フェイルセーフ: API 失敗時は当該チャンクをスキップして他銘柄の処理を継続する方針。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) を実装。Windows / POSIX (Linux/Mac/FreeBSD) の違いを吸収して nice 値や Windows の優先度クラスを設定。未対応 OS はスキップし警告。権限不足や実装未対応例外は警告で安全にスキップ。
    - set_cpu_affinity(cpu_count) を実装。指定したコア数にプロセスをピン留め（権限不足時は警告でスキップ）。

- ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading 検証用レポート生成スクリプトを追加（CLI 実行可能）。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, P95 レイテンシ 等を算出し、閾値（デフォルト）と比較した PASS/FAIL 判定を出力。
    - DB パスはコマンドライン引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
    - P95 算出、各種クエリに対する OperationalError 耐性を実装。

Changed
- DB 周りの分離ポリシーを明文化
  - 監視 (run_monitoring) は環境に関係なく本番 sqlite_path を使用する設計（監視データを一元化するため）。
  - 実行 (run_execution) は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB を使用することで本番データと分離。

Fixed
- 設定値・入力の頑健化
  - MONITOR_POLL_INTERVAL の値が不正（整数に変換不能・0 以下）の場合にデフォルトにフォールバックして警告を出すよう改良。
  - PAPER_FILL_MODE の値検証を追加（有効値以外は ValueError）。
  - LOG_LEVEL / KABUSYS_ENV の不正値検出と明示的なエラーを追加。

Notes
- ai/news_nlp の score_news 実装はファイル末尾が途中で切れているため（行末 "if not articl" 等）、実運用する場合は該当箇所を補完する必要があります。
- position_sizing や apply_sector_cap は価格欠損（price が 0 または None）に対するフォールバックを注記しており、将来的に前日終値や取得原価を用いた改善が想定されています（TODO コメントあり）。
- DuckDB を用いる研究モジュールは SQL を中心に実装されており、大量データの効率的な集計を想定しています。
- 実行・監視スクリプトは data/ ディレクトリ下の stop_requested.flag や PID ファイルを用いた運用を想定しています。デプロイ時のディレクトリ権限やファイル配置に注意してください。

Contributing
- バグ報告・プルリクエスト歓迎。README/CONTRIBUTING を参照してください（本 CHANGELOG には開発手順は含まれません）。

---
この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして使用する際は、テスト済みの変更点やマージ履歴に基づく追記・修正を行ってください。