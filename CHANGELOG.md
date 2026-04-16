# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注意: 以下のログは提示されたソースコードから推測して作成した要約です。実装状況や未実装箇所については該当ファイルのコメントや TODO を参照してください。

## [0.1.0] - 2026-04-16
初回リリース。システム全体のコア機能（設定読み込み、監視・実行ランナー、ポートフォリオ構築、ポジション算出、ファクター計算、研究用ユーティリティ、ニュース NLP スコアリング、ユーティリティ）が追加されました。

### 追加
- 全体
  - パッケージ初期化とバージョン設定を追加（kabusys.__version__ = 0.1.0）。
- 設定管理
  - 環境変数／.env 自動ロード機能を追加（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む。
    - エクスポート形式や引用符付き値・インラインコメントに対応したパーサを実装。
    - OS 環境変数を保護する override/protected の取り扱いを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、アプリケーション設定（API トークン、DB パス、監視閾値、環境判定等）をプロパティとして取得可能に。
    - PAPER_FILL_MODE のバリデーションを追加（instant/partial/never/reject のみ許容）。
    - KABUSYS_ENV, LOG_LEVEL などの検証ロジックを追加。
- 実行ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを実装。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止する仕組みを実装。
- 監視ランナー
  - システム監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（意図的分離のための設計）。
    - process priority を起動時に high に設定（utils/process_priority 経由）。
    - SystemMonitor の check_once() を定期実行し、例外はログに記録して次ポーリング継続。
- ポートフォリオ構築
  - 候補選定・重み計算モジュールを追加（kabusys.portfolio.portfolio_builder）。
    - select_candidates（スコア降順、同点時 signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコアゼロ時のフォールバック警告）。
  - セクター集中制限・レジーム乗数モジュールを追加（kabusys.portfolio.risk_adjustment）。
    - apply_sector_cap（既存保有を考慮してセクター上限を適用、unknown セクターは除外しない）。
    - calc_regime_multiplier（bull/neutral/bear に基づく乗数、未知レジームは 1.0 にフォールバック）。
  - ポジションサイジングロジックを追加（kabusys.portfolio.position_sizing）。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、最大ポジション比率、投下資金上限、コストバッファを考慮したスケーリング。
    - aggregate cap（利用可能現金を超過した際のスケールダウン）と残差に応じた追加配分アルゴリズムを実装。
- 研究（Research）機能
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - calc_momentum（1M/3M/6M リターン、MA200 差分）、calc_volatility（ATR/出来高/売買代金）、calc_value（PER/ROE）。
    - DuckDB 接続を受け取り SQL を用いて効率的に計算。
  - 特徴量探索ユーティリティを追加（kabusys.research.feature_exploration）。
    - calc_forward_returns、calc_ic（Spearman 相関）、factor_summary、rank。
    - 外部依存を避けた純 Python 実装。
  - research パッケージのエクスポートを整備。
- ニュース NLP（AI）
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）でスコアリングするモジュールを追加（kabusys.ai.news_nlp）。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST、UTC に変換）と記事集約ロジック（銘柄ごとに最大記事数・最大文字数でトリム）。
    - 最大 20 銘柄/バッチ、JSON Mode を期待する system prompt、スコアの ±1.0 クリップ、429/5xx 等のエクスポネンシャルバックオフによるリトライ。
    - OpenAI API キーの解決（引数 or OPENAI_API_KEY 環境変数）。
    - レスポンス検証と ai_scores テーブルへの差分置換（失敗時に他コードの既存スコアを保護）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
    - DB の存在チェック、期間フィルタ、P95 算出ロジック、各種 SQL クエリを実装。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows と POSIX の差分を吸収して set_process_priority(level)、set_cpu_affinity(cpu_count) を実装。
    - 権限不足や未対応プラットフォームでの安全なフォールバックとログ出力。

### 変更（設計上の決定）
- 監視機能は環境にかかわらず本番の sqlite_path を使う設計（run_monitoring）。
- run_execution は paper_trading 環境時に paper_sqlite_path を用いることで paper/live DB を明確に分離。
- .env 読み込みの優先度: OS 環境 > .env.local（上書き）> .env（未設定のみ）。

### 修正（堅牢性・バリデーション）
- .env パーサで引用符・エスケープ・インラインコメントを正しく処理するよう改善。
- MONITOR_POLL_INTERVAL の負の値・無効値に対してフォールバックロジックを追加（ログ警告を出してデフォルト 60 秒を使用）。
- PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値検証を追加し、不正値時に明確な例外を投げる。
- position_sizing / risk_adjustment / portfolio_builder 各関数でデータ欠損（価格なし等）に対するスキップ処理とログ出力を追加。

### 既知の問題 / 注意点
- news_nlp.py の末尾でコードが途中で切れている箇所が見られます（提示されたソースでは _fetch_articles 呼び出し後に処理が中断）。実運用前に記事フェッチ部分と DB 書き込みの完全な実装・テストが必要です。
- 監視（run_monitoring）が常に本番 sqlite を参照することは誤操作の原因になり得るため、運用時の注意（環境変数やパスの確認）を推奨します。
- OpenAI API の利用にはキー設定が必須。score_news() はキー未設定時に ValueError を送出します。
- DuckDB に対する executemany などの制約（説明中に言及されている）があるため、DB 操作のパラメータが空の場合は実行前にチェックすること。

### ドキュメント / テスト
- 各モジュール内に設計意図・使用例・TODO コメントが記載されており、ドキュメント化が進められていますが、統合テスト・ユニットテストの記述はソースからは確認できません。実運用前にテスト整備を推奨します。

---

（今後のリリースでは、news_nlp の未完了箇所の実装完了、テスト追加、CLI / デプロイ手順の明文化、エラー監視やメトリクス出力強化などを予定してください。）