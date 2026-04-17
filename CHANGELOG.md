KEEP A CHANGELOG形式で、今回のリポジトリ状態から推測される変更点をまとめた CHANGELOG.md（日本語）を作成しました。初回リリース相当（v0.1.0）として記載しています。必要に応じて日付や「Unreleased」セクションの調整を行ってください。

=======
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

このファイルはリポジトリの現在のコードベースから推測して作成した変更履歴です。
=======

Unreleased
- なし

[0.1.0] - 2026-04-17
Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: __version__ = "0.1.0"
- 設定管理
  - kabusys.config.Settings: 環境変数から設定を取得する統一的な設定クラスを追加。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。.env と .env.local の読み込み順をサポート。環境変数による自動ロード無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) を追加。
  - .env パーサを強化（export 句対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い改善）。
  - 各種設定プロパティ追加: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE（値検証）/ PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（CPU/MEMORY/DISK）など。
  - settings インスタンスをエクスポート。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository/OrderManager/Reconciler/RiskManager を組み立てて ExecutionEngine を起動。
    - エンジンの PID 管理（data/execution.pid）と外部停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - 起動直後にプロセス優先度を High に設定。
  - run_monitoring.py: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
    - 停止フラグ（data/stop_requested.flag）の検出でループを終了。
    - duckdb 接続と sqlite 接続を利用した初期化処理（init_monitoring_db）を実行。

- ユーティリティ
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level): Windows / POSIX(Linux, macOS, FreeBSD) を吸収して優先度を設定（権限不足時は警告を出してスキップ）。
    - set_cpu_affinity(cpu_count): 指定した最初の N コアにプロセスをピン留めする機能を追加（権限不足・未対応環境でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークを考慮した候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等分へフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有のエクスポージャー計算、売却予定銘柄除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を提供（既定値とフォールバック挙動を明記）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従った株数決定ロジックを実装。
      - risk_based ではポジションごとのリスク・ストップロスを考慮した株数決定。
      - aggregate cap（available_cash）超過時のスケーリング処理と lot_size（単元）丸め、残差のロット単位再配分アルゴリズムを実装。
      - cost_buffer による保守的コスト見積りを考慮。

- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（target_date 以前の最新財務データを使用）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターンを効率的に取得（horizons バリデーションあり）。
    - calc_ic / rank / factor_summary: IC（スピアマンρ）計算、ランク関数、ファクター統計サマリーを実装。
  - research パッケージは zscore_normalize を外部モジュールから取り込み、上記機能をエクスポート。

- AI / ニュース NLP
  - kabusys.ai.news_nlp
    - raw_news テーブルからニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別にセンチメントスコア（-1.0〜1.0）を算出する処理を実装。
    - バッチサイズ・トークン制限（各銘柄最大記事数、最大文字数）による対策、最大 20 銘柄/コールのバッチ送信、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンスのバリデーション、スコアのクリッピング、部分成功に耐える DB 更新戦略（該当コードのみ差し替え）などの設計方針を盛り込む。
    - ニュースウィンドウ計算ユーティリティ（前日 15:00 JST 〜 当日 08:30 JST の UTC 変換）を実装。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI を追加（--from/--to/--db オプション対応）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数などを算出。閾値を定義して PASS/FAIL を判定。
    - P95 計算関数、各種 SQL クエリ（system_status/trade_logs/risk_logs 参照）および出力整形を実装。

Changed
- データベース取り扱いの設計方針
  - 監視 (run_monitoring) は環境にかかわらず本番 sqlite_path を参照する仕様（監視情報は本番 DB に集約する意図）。
  - 実行エンジン (run_execution) は paper_trading 環境時に専用 DB を使用して本番 DB と完全分離。
- .env 読み込みの挙動
  - OS 環境変数を保護するため、.env の上書き時に既存 OS 環境変数を protected として扱う。 .env.local は .env の上書きとして読み込まれる。

Fixed
- 環境変数パースの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメント取り扱いの不具合を考慮した実装により、.env の複雑な値を安全に扱えるように改善。
- 監視ループのポーリング間隔
  - MONITOR_POLL_INTERVAL 環境変数値が不正（0 や負値、非整数）の場合に例外を投げず、警告出力してデフォルト 60 秒にフォールバックするように変更。

Security
- OpenAI API キーの扱い
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY が未設定のときに ValueError を投げ、キー未設定での誤動作を防止。

Notes / Design Decisions
- 多くのモジュールは「DB を直接書き換えない」「duckdb / sqlite を読み取り/書き込みに使う」など設計制約を明記しているため、運用時の DB 分離やフェイルセーフ挙動に注意してください。
- position sizing や risk management 周りは将来的な拡張（銘柄別 lot_size、価格フォールバックなど）用の TODO コメントを含み、現行実装は単元株 100 の共通仮定を置いています。
- news_nlp モジュールは堅牢性（バッチ処理・再試行・レスポンス検証）を重視しているため、API コストとレート制限（MODEL / バッチサイズ）に注意してください。

今後の提案（未実装／検討事項）
- price の欠損時フォールバック（前日終値や取得原価）を用いたエクスポージャー推定の実装。
- position_sizing の銘柄別 lot_size サポート（stocks マスタ参照）への拡張。
- news_nlp の処理結果を非同期キューに流す等スケーラビリティ向上。
- テストカバレッジの強化（特に .env パーサ、position sizing のスケーリングロジック、news_nlp の API 失敗ハンドリング）。

--- 
注: この CHANGELOG は与えられたソースコードからの推測に基づく初期リリース向けの記述です。実際のコミット単位や既往の変更履歴が存在する場合はそちらに合わせて調整してください。