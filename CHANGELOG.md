CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースから推測できる変更点・リリース内容を日本語で記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開リリースとして基本コンポーネントを実装。
  - パッケージメタ情報を追加: kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行用エントリポイントを追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じたブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、セッション実行を行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - RiskConfig の初期値（max_position_pct 等）および初期ポートフォリオ値に broker.get_available_cash() を使用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下などの不正値はデフォルトにフォールバックして警告を出力。
    - 監視は「環境にかかわらず本番 sqlite_path を使用」する旨を明示。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - レポート出力（稼働率、注文成功率、送信率、P95 レイテンシ等）。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数でパス指定可能。
- 設定管理モジュールを追加。
  - config.py: .env 自動読み込み機能（.env / .env.local、OS 環境変数優先）、プロジェクトルート探索（.git / pyproject.toml を基準）、.env の堅牢なパーサ実装。
  - Settings クラスで多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID/KILL フラグパス / 環境検証 / paper_fill_mode 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - paper_fill_mode の有効値検証（instant|partial|never|reject）。
    - KABUSYS_ENV の有効値検証（development|paper_trading|live）。
- ポートフォリオ構築関連モジュールを追加（純粋関数群、DB 参照なし）。
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）。
    - 重み計算 calc_equal_weights / calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（既存保有のセクター露出が上限を超える場合に当該セクターの新規候補を除外）。
    - calc_regime_multiplier（market レジームに応じた投下資金乗数: bull/neutral/bear、未知は警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes（risk_based / equal / score の allocation_method をサポート、単元株丸め、aggregate cap スケール処理、cost_buffer を考慮した保守的見積り）。
    - lot_size 単位での端数処理やスケールダウン後の残余配分ロジックを実装。
- リサーチ / ファクター計算モジュールを追加（DuckDB を入力に純粋計算）。
  - research/factor_research.py: momentum / volatility / value ファクター計算（MA200、ATR20、平均売買代金、PER/ROE 等）。DuckDB 上の prices_daily/raw_financials を使用。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman）計算、rank、統計サマリー（count/mean/std/min/max/median）。外部ライブラリに依存せず実装。
  - research/__init__.py で主要関数を公開。
- AI ニュース NLP スコアリングモジュールを追加（OpenAI クライアントを使用）。
  - ai/news_nlp.py:
    - raw_news を銘柄毎に集約し gpt-4o-mini（JSON Mode）へバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ書き込む設計。
    - バッチサイズ、最大記事数・最大文字数、タイムウィンドウ（JST を UTC に変換して DB から抽出）等の制御を実装。
    - 429 / ネットワーク / 5xx に対する指数バックオフリトライ、応答バリデーション、スコアの ±1.0 クリップを実装。
    - API キー未設定時は例外を投げる（api_key 引数または OPENAI_API_KEY 環境変数）。
- ユーティリティを追加。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティ（Windows / POSIX 差分吸収、権限不足時は警告してスキップ）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
- DB 初期化ヘルパー（監視テーブルを保証する）を各起動スクリプトで呼び出し対応（monitoring.monitoring_db.init_monitoring_db を利用）。
- その他
  - tools パッケージ初期化ファイル追加。

Changed
- 新規リリースのための設計注記・デフォルト値を明示（例: デフォルトの SQLite/DuckDB パス、MONITOR_POLL_INTERVAL デフォルト 60 秒）。
- run_execution では paper_trading 環境と本番 DB の分離を明確化。

Fixed
- .env ファイルのパース精度向上:
  - export プレフィックス対応、クォート内のエスケープ、行内コメントの取り扱い等を考慮。
  - override/protected ロジックで OS 環境変数を上書きしない保護機能を実装。

Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーや上限が過小見積もられる注記あり — 将来的に前日終値や取得原価でのフォールバックを検討。
  - lot_size は現状グローバル固定。将来的に銘柄別 lot_map を導入する予定。
- ai/news_nlp.py:
  - 大量 API コール時の部分失敗に備えた部分挿入ロジック（DELETE/INSERT の範囲限定）は実装方針があるが、実運用での耐障害性の追加検証が必要。
- run_monitoring.py:
  - 監視が「環境にかかわらず本番 sqlite_path を使用」する仕様は意図的だが、運用上の注意点（テスト環境での監視分離等）を運用ドキュメントに明記することを推奨。

Security
- OpenAI API キーなどの秘密情報は Settings / 環境変数から取得。自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。README 等での運用上の注意を推奨。

その他補足
- ロギングは基本的に INFO レベルで初期化されるが、Settings.log_level による変更が可能。環境値の検証（LOG_LEVEL, KABUSYS_ENV 等）を行い、不正な値は ValueError を送出するようにしている。
- DuckDB / SQLite を組み合わせてデータ処理・分析基盤を構築する設計になっている（research / ai / monitoring / execution 各コンポーネントで利用）。

--- 

（注）本 CHANGELOG は提示されたソースコードから機能・設計意図を推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに基づいて調整してください。