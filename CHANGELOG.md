CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに基づいて記載しています。  
日付はコードベースから推測した作成/リリース時期を使用しています。

Unreleased
---------
Added
- MONITOR_POLL_INTERVAL 環境変数の値取得と検証を追加。0 以下や非整数値は警告を出してデフォルト（60 秒）にフォールバックするようにした。（src/kabusys/run_monitoring.py）
- プロセス優先度を簡単に設定できるユーティリティを拡張（set_process_priority 実装の安定化とログ出力改善、例外時は警告でスキップ）。また CPU affinity 設定用の set_cpu_affinity を追加し、利用可能コア数超過時の挙動を明示。（src/kabusys/utils/process_priority.py）
- Paper Trading 用の検証レポート生成ツールを追加。期間指定や DB パス指定が可能で、稼働率・注文成功率・送信率・API レイテンシ等を集計して PASS/FAIL を出力する CLI を提供。（src/kabusys/tools/paper_verification_report.py）
- ニュース NLP モジュールを追加。OpenAI（gpt-4o-mini）を用いた記事単位のセンチメント集約・銘柄別スコア算出を実装。チャンク処理、トークン過大対策、スコアクリップ、部分失敗時に既存スコアを保護する更新方式などを備える。（src/kabusys/ai/news_nlp.py）
- リサーチ用モジュール群を追加。モメンタム/ボラティリティ/バリューなどのファクター計算と、将来リターン計算、IC 算出、ファクター統計サマリ等を DuckDB 接続で実行可能にした。（src/kabusys/research/*）
- ポートフォリオ構築用モジュール群を追加。候補選定（スコア順）、等金額/スコア加重の重み計算、セクター制限の適用、ポジションサイズ（risk_based / equal / score）計算、単元株丸め、aggregate cap のスケーリングロジックなどを提供。（src/kabusys/portfolio/*）
- 実行エンジン／監視用起動スクリプトを追加。ExecutionEngine 用の起動ファイル（本番/ペーパー別 DB の選択、依存コンポーネントの組み立て）と SystemMonitor 用のポーリングループを実装。（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
- 設定ロード機構を強化：.env/.env.local の自動読み込み（プロジェクトルート検出ロジック付き）、export KS=val 形式やクォート/エスケープ/インラインコメントの取り扱いをサポート。OS 環境変数を保護する protected オプションを実装。（src/kabusys/config.py）

Changed
- 設定 API をオブジェクト化（Settings クラス）。環境変数取得をプロパティ化してバリデーションやデフォルトを明示。（src/kabusys/config.py）
- Paper Trading の DB は本番 DB と完全分離する挙動を明確化（settings.is_paper の場合は専用パスを使用）。監視テーブルの初期化は冪等に行う。（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py）
- DuckDB / SQLite を併用する設計を導入（データ分析用に DuckDB を採用、監視/トレードログは SQLite 管理）。起動処理で両方の接続を確立し、終了時に確実にクローズするようにした。（各起動スクリプト）

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックし、警告ログを出すようにしてゼロ除算等の問題を回避。（src/kabusys/portfolio/portfolio_builder.py）
- position_sizing: 単元株（lot_size）単位での丸めと、aggregate cap 超過時のスケーリングロジックを改善。残余キャッシュで端数分を再配分するロジックを導入し、上限超過抑止を実装。（src/kabusys/portfolio/position_sizing.py）
- risk_adjustment: セクター不明（"unknown"）の扱いを明確化し、既存保有の計算で売却予定銘柄を除外するオプションを追加。価格欠損時の注意点を TODO コメントで明示。（src/kabusys/portfolio/risk_adjustment.py）
- research モジュール: ファクター計算や将来リターン計算でのスキャン範囲を保守的に設定（カレンダー日バッファ）し、データ不足時の None ハンドリング、列名・ウィンドウ長の定数管理を改善。（src/kabusys/research/*）
- ai/news_nlp: API 呼び出しでのリトライ（429・ネットワーク・5xx）、レスポンス検証、結果のクリップ、部分更新（DELETE + INSERT）による部分失敗耐性を追加。API キー未設定時のエラーを明示。（src/kabusys/ai/news_nlp.py）
- .env パーサ: コメント・クォート・エスケープ処理を堅牢化し、無効行の無視や読み込み失敗時のワーニング出力を追加。（src/kabusys/config.py）

0.1.0 - 2026-04-13
------------------
Added
- 初回公開: 日本株自動売買システム "KabuSys" のコアモジュール群を追加。
  - execution: ExecutionEngine, BrokerClientFactory, OrderManager, OrderRepository, Reconciler, RiskManager（設定付き）。起動スクリプト run_execution を提供。（src/kabusys/run_execution.py、実行関連パッケージ）
  - monitoring: SystemMonitor と監視用 DB 初期化機能、run_monitoring ポーリングループ。（src/kabusys/run_monitoring.py、src/kabusys/monitoring/*）
  - portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数等のポートフォリオ構築ロジック。（src/kabusys/portfolio/*）
  - research: ファクター（Momentum, Volatility, Value）計算、将来リターン、IC、統計サマリなどの研究ユーティリティ（DuckDB ベース）。（src/kabusys/research/*）
  - ai: ニュース NLP スコアリング（OpenAI 統合）。（src/kabusys/ai/news_nlp.py）
  - tools: Paper Trading 検証レポート生成 CLI。（src/kabusys/tools/paper_verification_report.py）
  - utils: プロセス優先度と CPU affinity 設定ユーティリティ、共通ユーティリティ群。（src/kabusys/utils/*）
  - config: 環境変数/.env 自動ロード、Settings クラスによる設定取得とバリデーション。（src/kabusys/config.py）
  - パッケージバージョンを __version__ = "0.1.0" として設定。（src/kabusys/__init__.py）

Changed
- プロジェクト構成を整理し、DuckDB を分析用データベースとして採用。SQLite はモニタリング・取引ログ格納に利用。
- CLI ツール群とライブラリ API を分離。研究・検証ツールは本番取引と直接結合しない設計を採用。

Fixed
- 各種 NIL/NULL/データ不足ケースへの耐性を追加（ファクター計算、レポート生成などで None を許容して N/A 表示に対応）。
- OpenAI 周りのエラーハンドリングと部分的書き込みの安全化。

Notes
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 実行時はペーパートレード用 DB（data/paper_trading.db がデフォルト）を使用して本番 DB とデータ分離します。

参考
- コード内の docstring / TODO に設計方針や注意点が多数記載されています。具体的な利用方法や運用ルールはそれらを参照してください。