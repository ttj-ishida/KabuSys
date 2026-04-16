CHANGELOG
=========
本ドキュメントは「Keep a Changelog」形式に従って、本リポジトリの主要な変更点を日本語でまとめたものです。セマンティックバージョニングの採用を想定しています。

注意: 以下はソースコードの内容から推測して作成した変更履歴です。実際のリリースノート作成時は必要に応じて日付・影響範囲・細部を調整してください。

Unreleased
----------
### 追加 (Added)
- 起動スクリプトを追加/整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を上げ、停止フラグファイル検出でループを終了する仕組みを導入。
  - run_execution.py: ExecutionEngine をスレッドで起動する起動スクリプトを実装。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用するなど、本番と paper_trading を分離。

- 設定管理機能の強化
  - config.py: プロジェクトルート自動検出（.git / pyproject.toml）と .env/.env.local の自動読み込み実装（OS 環境変数の保護・override 振る舞いを明示）。.env 行のパースは `export`、クォート、エスケープ、コメントなどに対応。各種設定値（DB パス、閾値、PAPER_FILL_MODE など）を Settings クラスとして提供し、バリデーションを実施。

- ポートフォリオ構築関連関数を追加
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルから候補選定（スコア降順、タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を制限する候補フィルタリング。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップとフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の割当方式を実装。lot（単元）丸め、1 銘柄上限、aggregate cap スケーリング、cost_buffer を考慮した保守的見積り、残差の再配分ロジックなどを含む。

- 監視・運用ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）を設定する関数と、必要に応じて CPU affinity を固定する関数を実装。psutil を利用しアクセス権限エラー等は警告ログでスキップする安全な実装。

- リサーチ / ファクター計算機能
  - research.factor_research: DuckDB を用いたモメンタム／ボラティリティ／バリュー系ファクター計算（各種ウィンドウ集計、ATR、MA200 等）。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman）計算、ランク関数、ファクター統計サマリーを実装。外部ライブラリに依存しない純粋 Python 実装。

- Paper Trading 検証ツール追加
  - tools/paper_verification_report.py: paper_trading の SQLite DB を参照して稼働率・注文成功率・送信率・レイテンシ（P95）を集計し、PASS/FAIL 判定付きレポートを CLI で出力するツールを追加。期間指定と DB パス指定の CLI オプションを提供。

- ニュース NLP / OpenAI 連携（下書き実装）
  - ai/news_nlp.py: ニュース収集ウィンドウ計算、OpenAI API を用いた銘柄別センチメントスコアリングの方針（バッチ処理、リトライ、JSON 検証、スコアクリップ等）を実装。API キーの必須化など安全策を導入。ファイル末尾が切れているため、score_news の続きを想定した実装が含まれる（バッチ取得→検証→ai_scores への書き込み）。

### 変更 (Changed)
- DB 動作の分離と既定値
  - 監視 (run_monitoring) は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するように明示（監視データは常に本番 DB に記録）。
  - 実行エンジン (run_execution) は paper_trading 環境時に専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使い、本番 DB と完全分離。

- 起動時のプロセス優先度設定を早期に行うように統一（run_monitoring / run_execution の両方で起動直後に set_process_priority("high") を呼び出し）。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の取り扱いを堅牢化:
  - 環境変数の値を整数として解釈し、0 以下や不正値の場合はデフォルトにフォールバックし、警告ログを出すように修正（time.sleep に負の値を渡さないようにするための防御）。
- .env 読み込みの堅牢化:
  - ファイルが開けない場合は警告を出してスキップするように変更。OS 環境変数を保護する protected 機構を導入。
- ファクター / リサーチ SQL でデータ不足時に None を返す挙動を明確化（集計ウィンドウが不十分な場合に None を許容）。

### セキュリティ (Security)
- OpenAI API 利用時の安全策:
  - score_news は API キーが未設定の場合に ValueError を送出し、明示的な設定を要求する。

### その他 (Other)
- パッケージバージョンを設定: kabusys.__version__ = "0.1.0" を定義。
- モジュールのエクスポート整備: portfolio / research パッケージで主要関数を __all__ としてエクスポート。

0.1.0 - 2026-04-16
-----------------
(初回リリース想定: 上記機能群のまとめ)

- 初回公開として以下の主要機能を実装・提供
  - 自動売買エンジン起動基盤: run_execution（ExecutionEngine 起動、リスク管理、注文管理、Reconciler 組立て）
  - 監視基盤: run_monitoring（SystemMonitor ポーリング、監視 DB 初期化）
  - 設定管理: Settings クラス、.env/.env.local 自動読み込み、環境値バリデーション
  - ポートフォリオ構築ライブラリ: 候補選定・重み計算・リスク調整・ポジションサイズ計算
  - リサーチライブラリ: ファクター計算（Momentum/Volatility/Value）、特徴量探索ユーティリティ（forward returns, IC, summary）
  - 運用ユーティリティ: process priority / cpu affinity 設定ユーティリティ
  - Paper Trading 検証ツール: paper_verification_report CLI
  - ニュース NLP（OpenAI 連携）機能の下書き実装（ニュースウィンドウ計算、バッチ/リトライ方針など）
  - ドキュメント/設計注記: 各モジュールに設計方針や TODO コメントを含む

注記
----
- 上記はソースコードから読み取れる挙動・意図に基づいて作成した変更履歴です。実際のリリースノートやリリース日付は別途決定してください。
- ai/news_nlp.py はファイル末尾が切れているため、score_news の完全な実装はリポジトリ内の続きコードで補完される前提です。必要に応じてその実装と動作確認を行ってください。