CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。セマンティックバージョニングを想定しています。

Unreleased
----------

（現在のスナップショットは下の 0.1.0 リリースに対応しています）

0.1.0 - 2026-04-17
-----------------

Added
- 基本アプリケーション機能を実装（初回公開相当）。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - 環境設定読み込み
    - src/kabusys/config.py
      - .env/.env.local の自動読み込み（OS 環境変数を保護する仕組み付き）。
      - プロジェクトルートを .git または pyproject.toml から探索するロジックを実装。
      - .env の行パーサを拡張（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
      - Settings クラスを実装し、各種設定（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境判定など）をプロパティとして提供。
      - PAPER_FILL_MODE の検証ロジックを実装（instant/partial/never/reject のみ許容）。
  - 実行系 / 監視系 起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動用スクリプトを実装。paper_trading 環境では専用の paper DB を使用し、本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて Engine を起動。
      - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に基づく安全な起動・停止フローを実装。
      - リスク設定（RiskConfig）とデフォルトパラメータを明記（max_position_pct, max_utilization, rate_limit_per_sec など）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。
      - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
      - 監視処理は KABUSYS_ENV に依らず本番 sqlite_path を使用する挙動を明記。
      - 起動時にプロセス優先度を上げる（set_process_priority("high") を最初に実行）。
  - プロセス制御ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX の差分を吸収する set_process_priority(level) を実装（high/normal/low）。
      - CPU affinity を制限する set_cpu_affinity(cpu_count) を実装。
      - psutil の権限不足や未対応 OS に対しては警告を出し安全にスキップする実装。
  - ポートフォリオ構築ロジック（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
      - スコア合計が 0 の場合は等金額にフォールバックする警告あり。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限を行う apply_sector_cap を実装（既存保有を考慮し、売却予定銘柄を除外可能）。
      - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - 各種配分方式（risk_based / equal / score）に対応した株数算出 calc_position_sizes を実装。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
      - cost_buffer を使った保守的な約定コスト見積りと、残余キャッシュでの端数配分ロジックを実装。
    - パッケージ公開用 __init__ を整備（各関数のエクスポート）。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - DuckDB を使ったファクター計算モジュールを実装（momentum, volatility, value）。
      - モメンタム: mom_1m/mom_3m/mom_6m, ma200_dev（データ不足時は None）。
      - ボラティリティ: ATR20, 相対 ATR, 20日平均売買代金, 出来高比率。
      - バリュー: PER（EPS が 0 または欠損なら None）, ROE（raw_financials から最新スナップショットを取得）。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
      - 外部ライブラリに依存しない純 Python 実装。
    - src/kabusys/research/__init__.py でエクスポートを整備。
  - AI ニュース NLP（ニュースセンチメント）
    - src/kabusys/ai/news_nlp.py
      - raw_news テーブルを集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを計算し、ai_scores テーブルへ書き込む処理を実装。
      - 処理の主要設計:
        - ニュース集計ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）の算出機能（calc_news_window）。
        - 銘柄あたりの最大記事数 / 最大文字数でトリムしトークン膨張を抑制。
        - 最大バッチサイズ、レスポンス検証、スコアの ±1.0 クリップ、429/5xx/ネットワーク断に対する指数バックオフリトライを想定。
      - フェイルセーフ設計: API キー未設定時は例外、API が一時的に失敗しても部分的に進める（既存スコア保護を考慮）設計。
  - 運用ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成ツールを実装。コマンドライン引数で期間指定可能。
      - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。閾値はソース内に定義（稼働率 >=99% など）。
      - DB の存在チェック、テーブル未存在時の耐障害処理（OperationalError のハンドリング）を実装。

Changed
- （初回リリースのため「追加」が中心。既存振る舞いの微調整や内部ロジックの説明をドキュメント化）

Fixed
- 設計上の注意点・堅牢化
  - .env パーサの強化により、引用符・エスケープ・export 指定などの実際の .env ファイルで発生しがちなケースを正しく扱うようになった。
  - process priority / cpu affinity 設定において権限不足や未対応プラットフォームの例外を捕捉し、プロセスを停止させないようにした。
  - ポートフォリオ算出においてスコア合計 0 の場合に等金額配分へフォールバックする挙動を明確化（ログ警告あり）。
  - position sizing の aggregate cap スケーリングで単元丸めと残余配分を考慮するアルゴリズムを実装し、投下額超過時に再配分する仕組みを導入。

Security
- 外部 API キー（OpenAI 等）は明示的に渡すか環境変数から取得する仕様。自動ロードされる .env は OS 環境変数保護機構（protected set）により、OS 側にセット済みのキーを上書きしないようになっている。

Notes / Breaking changes
- run_monitoring の挙動:
  - 監視プロセスは KABUSYS_ENV の値に関係なく production 相当の sqlite_path を使用するため、開発や paper_trading 環境でこれを期待して実行すると本番 DB を参照する可能性があります。必要に応じて環境変数で sqlite_path を明示的に切り替えてください。
- PAPER_TRADING の DB 分離:
  - run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。paper 用 DB を共有する運用や既存 DB 名と衝突しないよう注意してください。
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI ニュースモジュール:
  - 大量 API 呼び出しやレートリミットを考慮した設計になっていますが、実運用前に OpenAI の利用ポリシー、コスト、レスポンス形式の変化への耐性を確認してください。

Acknowledgements / Implementation remarks
- DuckDB を分析用途に採用し、prices_daily / raw_financials 等のテーブルに対して SQL と Python の組合せでファクター計算を行う設計としました。
- 各種モジュールは副作用を極力排して純関数を多用（ポートフォリオ／リサーチ系）し、ユニットテストやリファクタリングを行いやすい構造としています。
- 一部モジュール（例: ai/news_nlp.py）は外部 API 依存のため、テスト時は環境変数やモックを使って安全に動作確認してください。

今後の予定（例）
- ai/news_nlp のレスポンス処理・DB 書き込み部の堅牢化と全面実装完了。
- 単元サイズの銘柄別カスタマイズ対応（lot_map の導入）。
- position sizing の市場データ欠損時のフォールバック（前日終値や取得原価の利用）。
- 追加単体テストおよび CI の整備。

--- 
（この CHANGELOG はコードスニペットの内容から推測して作成しています。実際のコミット履歴や変更差分に基づく正確な履歴化は git log 等を参照して行ってください。）