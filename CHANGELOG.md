CHANGELOG
=========

すべての重要な変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

リリース 0.1.0 - 2026-04-16
-------------------------

Added
- プロジェクト初回リリース相当の機能群を追加。
- 実行系 / 監視系エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite(DB: data/paper_trading.db をデフォルト) を使用し、本番 DB と完全に分離。  
    - BrokerClientFactory を利用してブローカークライアントを組み立て、OrderRepository / OrderManager / RiskManager / Reconciler を構成して ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告を出力。  
    - 監視は環境にかかわらず production の sqlite_path を使用する設計（注意点あり：下記 Breaking Changes 参照）。停止フラグでループ終了。
- 設定管理
  - config.py: 環境変数/.env の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。読み込み順は OS > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。  
  - Settings クラスを提供し、アプリケーション設定（DB パス、Paper Trading の挙動、監視しきい値、env 判定など）をプロパティとして取得可能に。いくつかのプロパティは入力検証を行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py: 候補選定と重み付け関数を追加（select_candidates, calc_equal_weights, calc_score_weights）。score がすべて 0 の場合は等分配にフォールバックして警告。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。unknown セクターは上限適用対象外。未知のレジームは 1.0 でフォールバック（警告出力）。
  - position_sizing.py: 発注株数決定ロジックを追加（calc_position_sizes）。  
    - allocation_method: "risk_based" / "equal" / "score" をサポート。  
    - lot_size による丸め、per-stock 上限、aggregate cap でスケールダウン、cost_buffer（手数料/スリッページ見積り）を考慮した安全な割付を実装。残余キャッシュを使った追加配分ロジックも搭載。
- 研究・ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB を受け取り SQL で計算）。200 日移動平均や ATR 等を含む。データ不足時は None を返す挙動を確定。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関 (IC) 計算、ファクター統計サマリーを追加。外部ライブラリに依存せず純粋 Python で実装。
- ニュース NLP（AI）
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini 想定）でスコアリングして ai_scores に書き込む処理を実装。  
    - 銘柄ごとの記事集約、1 銘柄あたりの文字数/記事数制限、バッチ送信（最大 20 銘柄）、エラーハンドリング（429/5xx/タイムアウトで指数バックオフ）を含む設計。  
    - API キーの引数指定 or 環境変数 OPENAI_API_KEY を使用。レスポンスの検証・スコアクリッピング（±1.0）・部分書き換え（対象コードのみ DELETE → INSERT）で部分失敗時の保護を実現。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を追加。  
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシなどを集計し、閾値に基づく PASS/FAIL 判定を行う。date フィルタ（--from/--to）と --db オプションをサポート。P95 計算や NULL/テーブル未存在時のフォールバック処理を実装。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。Windows / POSIX を吸収し、権限不足や未対応環境では警告を出してスキップ。

Changed
- パッケージ初期化
  - kabusys/__init__.py に __version__="0.1.0" を設定。モジュールの公開 API を __all__ で定義。

Fixed
- 各モジュールで入力検証やデフォルト挙動の安定化（例: MONITOR_POLL_INTERVAL の不正値ハンドリング、PAPER_FILL_MODE の検証、ファクター計算でのデータ不足時の None 戻し）。

Deprecated
- なし

Removed
- なし

Security
- なし

Breaking Changes / 注意点
- 監視用スクリプト (run_monitoring.py) はドキュメントに明記の通り「KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。監視 DB を別にしたい場合は設定（環境変数 SQLITE_PATH 等）を適切に調整してください。
- .env 自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml を探索）。配布後や特殊なデプロイ環境では想定どおりに検出されない場合があります。その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、必要な環境変数を OS 環境に直接設定してください。

今後の改善候補（ToDo）
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の使用）を実装してエクスポージャー過少見積りを防ぐ。
- stocks マスタに lot_size を持たせ、銘柄別単元に対応する設計拡張。
- ai/news_nlp の堅牢化（完全なエンドツーエンドのユニットテスト、失敗時の部分的リカバリ戦略強化）。
- run_monitoring/run_execution のランレベル管理（systemd などとの統合用ユーティリティ）やログ設定の柔軟化。

--- 

バグ報告や改善提案は issue を立ててください。