CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
安定版の公開履歴は下に新しい順で並びます。

[Unreleased]
-------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 基本パッケージ構成を追加:
  - パッケージメタデータ:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 設定管理:
    - src/kabusys/config.py
      - .env 自動読み込み機能（プロジェクトルートの .git または pyproject.toml を探索）。
      - .env/.env.local の読み込み順序と OS 環境変数保護機構を実装。
      - 複雑な .env パース機能を実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント規則）。
      - Settings クラスでアプリケーション設定を提供（J-Quants / kabu / LINE / DB / 監視パラメータ等）。
      - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - 実行用スクリプト:
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動フローを実装。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite DB を使用して本番 DB と分離。
      - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンを起動。
      - 起動時にプロセス優先度を "high" に設定。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値は警告の上でデフォルトにフォールバック）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を "high" に設定。
  - ユーティリティ:
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX を吸収してプロセス優先度（nice/HIGH_PRIORITY_CLASS）を設定するユーティリティ。
      - CPU affinity 設定ユーティリティを提供（最初の N コアにピン留め）。
      - 権限不足や未対応環境時は警告を出して安全にスキップ。
  - ポートフォリオ構成モジュール:
    - src/kabusys/portfolio/portfolio_builder.py
      - シグナル選定（スコア降順 + tiebreaker）、等金額配分、スコア加重配分（スコア全0は等分にフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（既存保有比率に応じて候補を除外）と市場レジーム乗数（bull/neutral/bear → 1.0/0.7/0.3）。
      - unknown セクターは上限適用除外。
    - src/kabusys/portfolio/position_sizing.py
      - allocation_method (risk_based / equal / score) に応じた株数算出。
      - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと残差配分ロジックを実装。
      - 資金不足時のスケールダウンと lot 単位での再配分アルゴリズム。
    - src/kabusys/portfolio/__init__.py でエクスポートを整備。
  - 研究／リサーチモジュール:
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value といった定量ファクター計算を実装（DuckDB 上で prices_daily / raw_financials を参照）。
      - MA200, ATR20, 各種リターン、volume 指標などを計算。データ不足時は None を返す安全設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（複数ホライズン）、IC（Spearman）計算、ファクター統計サマリー、ランク関数を実装。
      - 外部依存を抑え標準ライブラリのみで実装（pandas 等非依存）。
    - src/kabusys/research/__init__.py で主要 API を公開（zscore_normalize は kabusys.data.stats から）。
  - AI ニューススコアリング:
    - src/kabusys/ai/news_nlp.py
      - raw_news から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）でバッチセンチメント解析して ai_scores に保存する処理を実装。
      - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）、JSON モード期待の厳密なレスポンス検証、スコアクリップを実装。
      - 429 / ネットワーク / 5xx に対する指数バックオフリトライ方針を備える。
      - OPENAI_API_KEY が未設定なら ValueError を送出。
      - タイムウィンドウ計算は JST ベースで実装（前日 15:00 JST 〜 当日 08:30 JST）。
  - ツール:
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを提供（コマンドライン実行可能: python -m kabusys.tools.paper_verification_report）。
      - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計・判定し PASS/FAIL を出力。
      - 判定基準（閾値）を定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <= 200ms）。
      - --from/--to/--db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可能。

Changed
- 新規ライブラリ設計: データ解析は DuckDB を主要ストレージとして想定。duckdb 接続を関数に注入する設計を採用。
- paper_trading 環境では注文送信層をモック化して本番 DB と記録を分離する方針を導入（run_execution 起動時の sqlite_path 切替）。

Fixed
- 初回リリースにつき過去のバグ修正はなし（既知の実装上の注意点は下記参照）。

Known issues / Notes
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後や CWD に依存しない設計）。
- NEWS NLP: OpenAI API のレスポンスの堅牢性は実装しているが、外部 API 依存のため完全な保証はない。API キーの管理に注意。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合はスキップするが、現状は前日終値などのフォールバックを行わない（将来的な拡張ポイント）。
- apply_sector_cap: sector_map に情報がない銘柄は "unknown" 扱いで上限制約から除外される（意図的）。
- run_monitoring の監視 DB は常に settings.sqlite_path（本番パス）を使用する設計。テスト用途での切替は設定で対応する必要あり。
- DuckDB への executemany に関する互換性注意: ai_scores 等の置換処理はパラメータが空でないことを確認する実装になっている（DuckDB 0.10 の制約を想定）。

Security
- 環境変数に API キー等の機密値を期待する設計。公開リポジトリ等で .env を直接公開しないこと。

Migration notes
- 既存の運用から導入する際は以下を確認してください:
  - 環境変数 JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY 等を設定。
  - paper_trading モードを使う場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を適切に指定。
  - MONITOR_POLL_INTERVAL で監視間隔を調整可能（整数秒、1 以上）。

開発メモ (実装上の TODO)
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価）を追加検討。
- news_nlp: レスポンス検証の強化と失敗時の部分ロールバック戦略の改善。
- run_monitoring/run_execution の PID / kill-flag 管理の追加運用ドキュメント化。

-----------------------------------------------------------------------------
脚注:
- 本 CHANGELOG はソースコードから推測して生成しています。実際のリリースノート作成時はコミットログ・issue tracker の内容を反映してください。