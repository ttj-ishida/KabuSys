# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。主にコードベースから推測される実装内容・振る舞いを元にまとめています。

最新
-----
### [0.1.0] - 2026-04-12

Added
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動するエントリスクリプトを追加。プロセス優先度を「high」に設定し、ブローカークライアントの生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てを行い、セッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動。
- 設定管理
  - config.py: .env 自動読み込み機能を導入（プロジェクトルートの検出に .git または pyproject.toml を利用）。.env/.env.local の読み込み順序・上書きルールを実装。高度な .env パーサ（export プレフィックス、引用符付き値、インラインコメント処理、保護された OS 環境変数）が実装され、Settings クラスで各種設定値（データベースパス、環境モード、しきい値、PID/KILL ファイルパス、paper_trading モードなど）をプロパティとして提供。
- モジュール化されたポートフォリオ構築
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（等金額/スコア重み calc_equal_weights, calc_score_weights）を実装。スコア全0の際のフォールバック警告あり。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。unknown セクターやデータ不足時の挙動を明記。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数計算（risk_based / equal / score の allocation_method）を実装。単元株丸め、per-position 上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer による保守的見積り、残差配分ロジックなどを実装。
- 研究・リサーチ機能（DuckDB ベース）
  - research/factor_research.py: モメンタム、ボラティリティ、バリュー系のファクター計算を実装。prices_daily / raw_financials テーブルを用いて複数の定量指標（mom_1m/3m/6m、MA200乖離、ATR20、平均売買代金、PER/ROE 等）を算出。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）やランク付けユーティリティ (rank)、ファクター統計サマリー（factor_summary）を追加。外部ライブラリに依存せず実装。
  - research/__init__.py: 主要な研究 API を公開 (calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank)。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news と news_symbols をソースに OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を実装。以下の特徴を持つ：
    - スコアリング対象ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を明確に算出する calc_news_window。
    - 記事を銘柄ごとに集約して文字数/記事数でトリム。
    - 最大バッチサイズ 20 件でのバッチ送信、429/ネットワーク/5xx に対する指数バックオフとリトライ処理の方針を持つ（_MAX_RETRIES 等で設定）。
    - レスポンスのバリデーション、スコアを ±1.0 にクリップ、部分成功時に既存スコアを保護する（該当コードのみ削除→挿入）などフォールトトレラントな書き込み方針。
    - API キーは引数または環境変数 OPENAI_API_KEY で解決し、未設定時は ValueError を投げる。
- ユーティリティ
  - utils/process_priority.py: psutil を利用したクロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限エラー等は警告でスキップ。
- モニタリング用 DB 初期化ユーティリティ（参照）
  - monitoring/monitoring_db の初期化呼び出しが各エントリポイントで行われ、監視テーブルの存在を保証（冪等）。

Tools
- tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL を判定・表示。しきい値定義や P95 計算、日付フィルタ処理、欠損テーブルへの耐性（OperationalError の捕捉）を備える。CLI 引数 --from/--to/--db をサポート。

Changed
- なし（初回リリース想定のため既存仕様との互換履歴は無し）

Fixed
- なし（リリース内で明示的なバグ修正履歴は無し。ただし各モジュール内にデータ不足時の保護処理や例外捕捉を多数実装）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。.env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを用意しているため、CI/テスト環境での意図しないキー読み込みを抑止可能。

Notes / Known limitations / TODO（コード内コメントより）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的な価格フォールバック（前日終値や取得原価）を検討する旨の TODO がある。
- position_sizing:
  - 将来的には銘柄別の lot_size をサポートする設計へ拡張する余地あり（現在は全銘柄共通で 100 を想定）。
- ai/news_nlp.py:
  - 実装は堅牢化を図っているが、API 呼び出し周りや部分失敗時の振る舞いについては実運用での検証が必要。
- run_monitoring/run_execution:
  - いずれもプロセス優先度を起動直後に「high」に設定するため、権限やプラットフォームによっては警告が出る可能性がある（utils は権限エラーを警告で処理）。

開発者向けメモ
- 環境切り替え:
  - Settings.env は development / paper_trading / live のいずれかを許容。paper_trading モード時は run_execution が paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と完全に分離する設計。
- DB 組み合わせ:
  - 実運用は SQLite（監視・注文ログ）と DuckDB（時系列価格やファクター計算）を併用。各処理で該当 DB への接続を受け渡すことで副作用を限定。
- ロギング:
  - 各エントリポイントは basicConfig(level=INFO) を設定。詳細デバッグはモジュール内で logger.debug を利用可能。

今後のリリースに向けて（提案）
- ai/news_nlp の追加テスト・エンドツーエンド検証（API レスポンスの多様性や JSON Mode の堅牢性）。
- price フォールバックロジックの実装（portfolio/risk_adjustment の TODO 解消）。
- 銘柄別 lot サイズをサポートするためのマスタ拡張と position_sizing の改修。
- モニタリングの稼働率・アラート連携（LINE など）を run_monitoring と連携して自動通知化。

以上。コードコメント・実装の意図に基づいて CHANGELOG を作成しました。追加の粒度（個別ファイル毎の詳細変更やコミット単位の履歴）をご希望であればお知らせください。