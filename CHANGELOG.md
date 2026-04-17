CHANGELOG
=========

すべての重大な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

Unreleased
----------

- なし（現時点のコードは 0.1.0 として初期リリース相当の機能群を含みます）。
- 注意事項 / 未完了メモ:
  - ai/news_nlp モジュールはニュース集約〜API呼び出し〜書き込みの処理フローを実装していますが、コード末尾が途中で切れているため（スニペットの末尾）最終的な記事フェッチ／API送信ループの完結・検証が必要です。
  - position_sizing、apply_sector_cap のコメントに将来的な拡張（銘柄別 lot_size、価格フォールバック等）が記載されています。必要に応じて実装を追加してください。

0.1.0 - 2026-04-17
------------------

追加 (Added)
- 実行／監視プロセス起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID 管理（data/execution.pid）を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離する挙動をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

- 設定・環境変数管理モジュールを追加
  - config.py
    - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - export 形式や引用符ありの値、インラインコメント扱いなどを考慮した堅牢な .env パーサ実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（DB パス、API トークン、各種閾値、PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証など）。
    - OS 環境変数の保護（既存の環境変数を上書きしない / protected keys）。

- ポートフォリオ構築・リスク調整・ポジションサイズ計算
  - portfolio.portfolio_builder
    - 投資候補選定 (select_candidates)、等金額／スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を実装。スコア全0時のフォールバックを実装。
  - portfolio.risk_adjustment
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームでのフォールバック、ログ出力あり。
  - portfolio.position_sizing
    - allocation_method（"risk_based", "equal", "score"）に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による手数料/スリッページ見積りを考慮した保守的な算出。

- 研究（Research）モジュール
  - research.factor_research
    - モメンタム、ボラティリティ、バリュー系ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。DuckDB におけるウィンドウ関数を利用した集計／ウィンドウ制御。データ不足時は None を返す扱い。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。

- AI ニュース NLP スコアリング
  - ai.news_nlp
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント（-1.0〜+1.0）を取得し、ai_scores テーブルへ書き込む処理を設計・実装。
    - バッチ処理（_BATCH_SIZE=20）、トークン肥大化対策（記事数・文字数制限）、レスポンスバリデーション、スコアの±1.0クリップ、429/ネットワーク/5xx に対する指数バックオフとリトライ、部分成功時の DB 保護（コードを絞った置換）などフェイルセーフ設計を反映。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収するプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を実装。パーミッション不足や未対応 OS 時に警告を出して安全にスキップする実装。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加。CLI で期間指定可能（--from/--to）、PAPER_TRADING_SQLITE_PATH で DB 指定可能。
    - 稼働率、注文成功率、送信率、P95レイテンシ等を計算し PASS/FAIL を判定する閾値（稼働率 >= 99%、注文成功率 >= 90% 等）をデフォルトで設定。
    - DB のテーブルが存在しない場合やデータ不足時の保護処理（sqlite3.OperationalError を捕捉）を実装。

変更 (Changed)
- 設定読み込みの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- モニタリングの DB 接続方針
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視データは本番 DB を記録する想定）。

修正 (Fixed)
- 環境変数パースの堅牢性向上
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど edge case を考慮して .env パーサを改善。
- ポーリング間隔の不正値ハンドリング
  - MONITOR_POLL_INTERVAL の 0 以下や非整数値を検出した際にデフォルトへフォールバックし、警告ログを出す実装。

破壊的変更 (Breaking Changes)
- なし（初期リリース）。ただし以下の点は運用上の注意点:
  - run_monitoring が常に本番 sqlite_path を使用するため、開発環境で監視を走らせると本番 DB に書き込まれる可能性があります。テスト時は環境変数で sqlite_path を明示的に切り替えるか、監視を起動しないでください。
  - .env 自動ロードはプロジェクトルート検出に依存します。配布後にプロジェクトルートを検出できない場合、自動ロードはスキップされます。

セキュリティ (Security)
- なし

その他 / ドキュメント・TODO
- position_sizing:
  - 将来的に銘柄別 lot_size を持たせる拡張がコメントで示唆されています（現状は全銘柄共通の lot_size 引数）。
- apply_sector_cap:
  - price が欠損（0.0）の場合のエクスポージャー過小見積りについて TODO コメントあり（前日終値や取得原価でのフォールバック検討）。
- ai/news_nlp:
  - コードに詳細な設計（ウィンドウ定義、バッチサイズ、リトライ戦略、出力 JSON スキーマ）が含まれており、安全性（APIキー必須、未設定時は例外）と部分更新の保護を考慮した設計になっています。実行前に OPENAI_API_KEY の設定と API 利用料/レート制限の運用設計確認を推奨します。

--- 
注記:
- この CHANGELOG は与えられたソースコードから推測して作成した要約です。実際のコミット履歴が利用可能な場合は、その履歴に基づいてより詳細かつ正確なログを生成することを推奨します。