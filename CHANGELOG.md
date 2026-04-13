CHANGELOG
=========

すべての注目すべき変更履歴を記載します。フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-13
--------------------

追加
- 基本パッケージ初回リリース（バージョン 0.1.0）。
- 起動用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を最初に High に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と明確に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 構成の流れを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。プロセス優先度を High に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
- 設定・環境読み込み（kabusys.config）
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の読み込み順序と override/保護（OS 環境変数を上書きしない）ルールを実装。
  - .env 行パーサーを実装し、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを実装し、各種設定値（DBパス、PID/KILL フラグパス、閾値、env/log_level 判定など）をプロパティとして提供。
  - Paper Trading 用設定（PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH）を実装。
- 監視・ツール
  - monitoring_db 初期化を保険的に呼び出すユーティリティの利用を各起動スクリプトに追加（冪等保証）。
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。--from / --to / --db オプションに対応。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計・表示。
    - 判定用しきい値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を導入し PASS/FAIL 判定を出力。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定（score 降順、signal_rank によるタイブレーク）、等金額・スコア重み計算を実装。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、マーケットレジームに基づく乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやフォールバックの挙動を定義。
  - position_sizing: 発注株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を使った保守的見積り、残余の lot 単位での追加配分アルゴリズム等を実装。
- 研究用モジュール（kabusys.research）
  - factor_research: DuckDB を使ったモメンタム / ボラティリティ / バリュー計算（各種ウィンドウ・欠損処理あり）。
  - feature_exploration: 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、rank / factor_summary（基本統計量）を実装。外部ライブラリ非依存で実装。
  - research パッケージのエクスポートを整備（zscore_normalize 等を含む）。
- AI ニューススコアリング（kabusys.ai.news_nlp）
  - raw_news から銘柄毎に記事を集約し OpenAI（gpt-4o-mini）でセンチメントスコアを算出、ai_scores テーブルへ書き込むワークフローを実装。
  - バッチサイズ、トークン肥大化対策（最大記事数・最大文字数）を導入。API 呼び出しはチャンク単位で処理。
  - 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ、レスポンス検証、スコアの ±1.0 クリップを実装。
  - 部分失敗時に他銘柄の既存スコアを保護するため、書き込みは対象コードに限定して置換（DELETE → INSERT）する方針を採用。
- ユーティリティ（kabusys.utils.process_priority）
  - プロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）のクロスプラットフォーム実装（Windows と POSIX を吸収）。権限不足や未対応環境では警告を出してスキップ。

変更
- 全体設計
  - DuckDB を内部分析（research / ai / factor 計算）に利用する設計を採用し、SQL による集約処理でパフォーマンスを確保。
  - 起動スクリプト・ツールはデフォルトでログレベル INFO に設定。

修正（注意点 / 安全策）
- 環境変数読み込み
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが特定できない場合は自動読み込みをスキップ。
  - .env の読み込み時に OS 環境変数は保護され、.env.local は既存値を上書き可能（ただし OS 環境変数は上書きされない）。
- データ欠損とフォールバック
  - ファクター計算・ポジションサイズ・セクターエクスポージャー等でデータ不足が考えられる箇所は None を返すか、安全にスキップするよう実装（例: 価格欠損でのスキップ、MA200 行数不足で ma200_dev を None）。
- API キーの扱い
  - ai.news_nlp.score_news は API キーが未設定の場合 ValueError を送出して明示的に失敗させる（環境変数 OPENAI_API_KEY または引数で指定が必要）。
- フェイルセーフ
  - monitor のポーリングループや AI API 呼び出し等、外部エラーの際は例外をキャッチしてログ出力後に継続する（サービス継続性を重視）。

既知の制約 / TODO
- position_sizing: price が欠損（0.0）の場合のエクスポージャー過少見積りを改善するため、将来的に前日終値や取得原価等のフォールバック価格を検討する旨の TODO を残しています。
- 単元株（lot_size）は現状グローバル共通値（デフォルト 100）で、将来的に銘柄別単元対応を想定。

免責
- 本 CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴や設計意図と完全に一致しない可能性があります。挙動や API の厳密な仕様はソースコード／ドキュメントを参照してください。