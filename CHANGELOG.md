CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
このファイルは、ソースコードの内容から推測して作成した変更履歴です。

Unreleased
----------
- なし

[0.1.0] - 2026-04-13
--------------------
初回リリース（コードベースの初期実装をまとめたバージョン）。以下の主要機能・改善・修正が含まれます。

Added
- 実行コンポーネント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。Environment に応じて paper_trading 用の専用 SQLite DB を使用する（KABUSYS_ENV=paper_trading 時は paper_sqlite_path を利用）。
  - BrokerClientFactory を利用したブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせたセッション実行フローを実装。
  - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。

- 監視コンポーネント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する挙動を明示。

- 設定管理
  - config.py: .env / .env.local の自動読み込み（プロジェクトルート検出）と保護された上書きロジックを実装。export KEY=... 形式やクォート文字列、インラインコメントに対応したパーサを追加。
  - Settings クラスに多数のプロパティを実装（DB パス、paper_trading 用設定、監視関連しきい値、環境判定ユーティリティ等）。

- ポートフォリオ構築
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定（スコア降順）・等金額／スコア加重の重み計算。
    - position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリングと余剰配分アルゴリズムを実装。
    - risk_adjustment: セクター集中上限 (apply_sector_cap) とレジーム乗数 calc_regime_multiplier を実装。

- 研究用モジュール（DuckDB ベース）
  - research パッケージを追加:
    - factor_research: Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）。
    - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（スピアマンランク相関）計算(calc_ic)、ファクター統計サマリー(factor_summary)、ランク関数(rank) を実装。
  - DuckDB を用いた大規模データの SQL + Python 処理を想定。

- ニュース NLP（AI）機能
  - ai/news_nlp.py: raw_news から銘柄ごとに記事を集約して OpenAI API でセンチメントをスコアリングし、ai_scores テーブルへ書き込む機能を実装。
  - バッチ処理（最大 20 銘柄／リクエスト）、レスポンス検証、スコア ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライなどの耐障害機構を実装。
  - ニュース集計ウィンドウ計算(calc_news_window)を JST ベースで定義（UTC に変換して DB 比較に使用）。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows/POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加（psutil を使用）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出して人間向けに出力。

Changed / Improved
- 起動処理
  - run_execution.py / run_monitoring.py で起動直後にプロセス優先度を "high" に設定するように統一（set_process_priority 呼び出しを最初に実行）。

- DB 利用方針の明確化
  - run_monitoring は常に production の sqlite_path を使用する設計になっている点を明示（監視は環境に依存せず本番 DB を参照する仕様）。

- エラーハンドリングとロバスト性の向上
  - 監視ループ内で check_once() が例外を出してもループ継続するよう、例外時にログを残して待機する実装に変更（単一エラーでプロセスが停止しないように設計）。
  - ai/news_nlp の API 呼び出しは部分失敗を許容し、取得済みのスコアは保持して書き込むロジックとした（部分失敗時の既存スコア保護のため、対象コードを絞って置換）。

- 設計上の明示
  - research と portfolio の関数群は副作用がなく（純粋関数設計）、DB 参照に限定する旨をコメント・実装で明示（本番口座や発注 API にアクセスしない）。

Fixed
- 環境変数パースの改善
  - _parse_env_line にて export プレフィックスやクォート内のエスケープ、インラインコメントの扱いをきめ細かく実装し、.env のパース精度を向上。

- MONITOR_POLL_INTERVAL の挙動
  - MONITOR_POLL_INTERVAL の不正（非整数・0 以下）の扱いを明確化。_get_poll_interval は不正値を検出して警告を出しデフォルト値にフォールバックするようにした（time.sleep に 0 以下を渡さないためのガード）。

- 重み付けと配分のフォールバック
  - calc_score_weights: 全銘柄のスコア合計が 0.0 の場合、等金額配分にフォールバックして警告ログを出すようにした。

- 株数計算に関する修正
  - calc_position_sizes:
    - lot_size による丸めを厳密に適用し、単元株数単位で発注数を決定する実装。
    - aggregate cap（available_cash）オーバー時のスケーリングと小数端数の再配分アルゴリズムを導入し、残余キャッシュを利用して lot 単位で追加配分するロジックを追加。

- apply_sector_cap の扱い
  - sector_map に存在しないコードを "unknown" と扱い、"unknown" セクターはセクター上限ルールの対象外とすることで誤除外を避ける挙動を採用。

- ニュースウィンドウ計算
  - calc_news_window で JST を基準に開始／終了を計算し、UTC naive datetime を返す設計にして DB 比較時のズレを防止。

Notes / Known limitations / TODO
- position_sizing の TODO: 将来的に銘柄毎の lot_size（単元）を stocks マスタで扱い、銘柄別 lot_map を受け取る拡張を想定している。
- price 欠損時の扱い（apply_sector_cap 内の TODO）: price が 0.0 の場合にエクスポージャーが過少評価される可能性があるため、前日終値や取得原価のフォールバックを検討すべき。
- ai/news_nlp のスコア更新は部分的にデータベースへ置換（DELETE → INSERT）を行う設計だが、複数プロセス並列時の整合性確保（トランザクション／ロック設計）には注意が必要。
- .env 自動ロードはプロジェクトルートを基準に行うため、配布後にプロジェクトルートが特定できない場合は自動ロードがスキップされる点に注意。

Developers
- パッケージのバージョンは cabusys/__init__.py にて __version__ = "0.1.0" を設定。
- ログレベルやしきい値は Settings を介して環境変数で細かく調整可能（LOG_LEVEL, CPU_THRESHOLD_PCT など）。

Security
- 本リリースで特定のセキュリティ修正は明示されていません。OpenAI API キー等の機密情報は環境変数で管理する想定です（Settings._require により未設定時は明確にエラーを出す箇所あり）。

----------------------------------------
（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。