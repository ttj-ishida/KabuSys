# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
日付はコードベースから推測可能な最新の状態（2026-04-16）を用いています。

## [Unreleased]
- 該当なし

## [0.1.0] - 2026-04-16
初期リリース。以下の主要機能・改善点を含みます。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合は専用の paper DB を使用し MockBrokerClient を使う運用が可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。監視停止はプロジェクトルートの data/stop_requested.flag により行える。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書き対応（デフォルト 60 秒）。
- 設定管理
  - config.py: プロジェクトルート自動検出（.git / pyproject.toml）と `.env` / `.env.local` の自動ロードを実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化対応。`.env` のパースは export プレフィックス、クォート文字、インラインコメント、エスケープ等に対応。
  - Settings クラスを実装し、各種環境変数（データベースパス、API トークン、監視閾値、実行環境フラグ等）をプロパティ経由で安全に取得。値検証（env, LOG_LEVEL, PAPER_FILL_MODE など）を追加。
- データベース
  - DuckDB / SQLite 両接続サポートを追加（複数モジュールで使用）。
  - 監視用 DB 初期化関数 init_monitoring_db を起動時に呼び、監視テーブルの存在を保証（冪等）。
- Execution コンポーネント（概要）
  - BrokerClientFactory によるブローカークライアント生成。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動ロジックを追加。
  - RiskManager にデフォルト設定を導入（最大ポジション比率、利用率、レートリミット、サーキットブレーカー等）。初期ポートフォリオ値は broker.get_available_cash() を参照して決定。
  - Engine はスレッドで run_session を実行し、停止フラグ検知時に安全停止を行う。
- 監視 (Monitoring)
  - SystemMonitor を利用した定期チェックの実行、例外時のロギングとリトライ（次ポーリングまで待機）を実装。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）設定、CPU affinity 固定機能を追加。Windows / POSIX の差分吸収、権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額およびスコア加重の重み計算を追加（スコア合計が0の場合のフォールバック実装）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックしてログ出力。
  - portfolio/position_sizing.py: 各配分方式（risk_based / equal / score）に基づく発注株数計算を実装。lot_size による丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）、cost_buffer を用いた保守的コスト見積り、残差分の再配分ロジックを実装。
- 研究 / リサーチ
  - research/factor_research.py: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、avg turnover、volume ratio）、バリュー（PER、ROE）ファクター計算を DuckDB を使って提供。データ不足時は None を返す設計。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、IC（Spearman rank）計算、rank（平均ランク、同順位の扱い）、factor_summary（count/mean/std/min/max/median）を実装。外部依存なしで標準ライブラリのみで動作。
- AI / ニュース NLP
  - ai/news_nlp.py: raw_news テーブルから記事を集約し OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ書き込むワークフローを実装。記事数・文字数トリム、バッチサイズ、429/ネットワーク/5xx のエクスポネンシャルバックオフ、結果のバリデーション、スコアの ±1.0 クリッピング、部分成功時に既存スコアを保護する書き込み戦略（該当コードのみ差し替え）などを設計。
  - calc_news_window(target_date) ユーティリティを提供（JST 時間ウィンドウ -> UTC 範囲変換）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。閾値はソース内で定義（稼働率 99.0%、注文成功率 90% 等）。コマンドライン引数で期間指定・DB パス指定に対応。

### 変更 (Changed)
- ロギング初期化を簡潔化し、起動時に INFO レベルで基本設定を行う（run_execution/run_monitoring）。
- run_monitoring の polling 関連: 環境変数 MONITOR_POLL_INTERVAL が不正（非数・0 以下等）の場合は警告を出してデフォルトにフォールバックするように変更。
- .env パーサのコメント処理・クォート処理を強化し、より実運用の .env 書式に耐性を持たせた。

### 修正 (Fixed)
- DB 初期化を冪等にして、既存 DB 上で何度実行しても問題にならないようにした（init_monitoring_db の呼び出し）。
- プロセス優先度設定が未対応な OS や権限不足でクラッシュしないよう例外処理を追加。失敗時は警告ログでスキップ。
- ExecutionEngine スレッド実行中に停止フラグを検知した際、安全に engine.stop() を呼ぶループを実装し、スレッドの終了待機を改善。

### 注意点 (Security / Notes)
- ai/news_nlp.score_news は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する設計のため、運用時は環境変数設定が必要。
- monitoring は設計上「環境」にかかわらず本番 sqlite_path を参照するため、テスト環境で使用する場合は sqlite_path の切り替えや停止フラグ配置に注意してください。
- position_sizing の価格取得で price が欠損（0.0）だとエクスポージャーが過少見積りされる点に TODO コメントあり。将来的な価格フォールバックが推奨される。

### 削除 (Removed)
- 該当なし

### 非推奨 (Deprecated)
- 該当なし

--- 

補足:
- 上記はソースコードの実装・コメントから推測してまとめた変更履歴です。実際のコミット履歴やリリースノートと差異がある場合があります。