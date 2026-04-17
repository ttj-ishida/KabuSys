Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" の慣例に従います。

[Unreleased]
-------------

なし

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アプリケーションを初回リリース（バージョン 0.1.0）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用することで本番 DB と完全分離する設計を導入。起動前に停止フラグ(data/stop_requested.flag)をチェックし、安全に停止できるループを実装。プロセス優先度を高優先（"high"）に設定する処理を最初に行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視データは環境にかかわらず本番 sqlite_path を使用する仕様。停止フラグでループを終了し、接続を確実にクローズする。
- 設定管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。優先順位は OS 環境変数 > .env.local > .env。export 形式やクォート・エスケープ、行末コメントのパースに対応。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できる。各種設定プロパティ（DB パス、PID ファイル、監視閾値、PAPER_FILL_MODE 等）を提供し、値検証を行う（無効値は例外）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: BUY シグナルの候補選定（スコア降順、signal_rank でタイブレーク）、等金額配分・スコア加重配分関数を実装。スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。unknown セクターはセクター上限の対象外とする挙動を採用。未知レジームはログ警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 単元株（lot_size）を考慮した発注株数算出を実装。risk_based / equal / score の割当方式をサポート。ポジション上限・利用可能現金に応じた aggregate cap スケーリング、スケーリング時の残差処理（lot_size 単位で追加配分）を実装。手数料・スリッページ想定の cost_buffer を考慮。
- 研究 (research)
  - research/factor_research.py: DuckDB 上の prices_daily/raw_financials を利用したファクター計算を実装（モメンタム、ボラティリティ、バリュー各ファクター）。SQL ベースでの窓集計を採用し、データ不足時は None を返す安全設計。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計サマリを実装（外部ライブラリ不使用）。rank 関数は同順位を平均ランクで扱う実装。
  - research/__init__.py: 主要関数のエクスポートを整理。
- ニュース NLP（AI）
  - ai/news_nlp.py: raw_news から銘柄別にテキストを集約し OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルへ書き込む処理を実装。大まかな特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で記事を抽出
    - 1 銘柄あたり記事数・文字数上限でトリム（トークン肥大化対策）
    - 最大バッチサイズ、JSON Mode 期待の厳密なレスポンス検証
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（上限あり）
    - スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護するため code を限定して置換更新
    - API キー未設定時は ValueError を投げる（api_key 引数または OPENAI_API_KEY 環境変数から取得）
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を集計し、PASS/FAIL を出力する。閾値定義と日付フィルタ（--from/--to）をサポート。PAPER_TRADING_SQLITE_PATH 環境変数/--db オプションで DB 指定可能。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。Windows と POSIX を吸収するクロスプラットフォーム実装で、権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
- パッケージ
  - kabusys/__init__.py: __version__ を "0.1.0" に設定し、主要サブパッケージを __all__ で明示。

Changed
- 監視関連: init_monitoring_db を起動時に呼び出して監視テーブルの存在を保障（冪等）。run_monitoring/run_execution ともに起動直後にプロセス優先度を設定するよう統一。

Fixed
- 環境変数パーサの堅牢化（config._parse_env_line）
  - export キーワード対応、シングル/ダブルクォート中のエスケープ、行末コメント処理を改善し実運用の .env フォーマット差異を吸収。
- ポジションサイズ計算のスケーリングでの端数処理・単元株制約の扱いを明確化し、不整合によるオーバーコミットを抑制。
- run_execution: 停止フラグ検知時にエンジンを起動せず即時終了するログ制御を追加（不必要な起動防止）。
- リサーチ/特徴量処理: 欠損・データ不足時に None を返す一貫した動作に統一し、例外の伝播を抑制。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に api_key 引数か OPENAI_API_KEY 環境変数で提供する必要があることを明記。キー未設定時は処理を失敗させることで誤動作を防止。

Notes / Migration
- .env の自動読み込みを行うため、既存の環境変数が優先されます。自動ロードを完全に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING_SQLITE_PATH による paper_trading 用 DB 分離を導入しています。本番 DB と paper_trading DB を明確に分けたい場合は環境変数を設定してください。
- MONITOR_POLL_INTERVAL に不正な値（0 以下や非整数）を設定するとデフォルト 60 秒にフォールバックします。ログに警告が出ます。

Acknowledgments
- 初回リリースにあたり、DuckDB を用いたオンチェーン（ローカル）分析・OpenAI 統合・堅牢な .env パーシングなどの実装を含めています。今後は単体テスト・ドキュメント追補・エラーハンドリングのさらに詳細な改善を予定しています。