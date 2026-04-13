CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースから推測される変更点・機能を日本語で記載しています。

Unreleased
----------
- いくつかの TODO / 改善ポイントを検討中（コード内コメント参照）
  - apply_sector_cap: 価格欠損時のフォールバック価格導入の検討
  - position_sizing: 銘柄別単元（lot_size）を stocks マスタに持たせる拡張案
  - DuckDB executemany に関する制約への対処（ai/news_nlp 実装メモ）

[0.1.0] - 2026-04-13
--------------------
初期リリース（推測）。主要な機能群と設計方針を実装。

Added
- 全体
  - パッケージ初期版を追加。パッケージメタ情報は kabusys.__version__ = "0.1.0"。
  - モジュールの公開インターフェースを kabusys/portfolio/__init__.py、kabusys/research/__init__.py で整備。

- 実行 / 監視ランナー
  - run_execution.py: 実運用向け ExecutionEngine 起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite DB を使用して発注処理を本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を使用）。
    - duckdb と sqlite3 の接続管理を実装、終了時に確実にクローズ。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様（監視は本番 DB を参照する想定）。
    - 起動時にプロセス優先度を "high" に設定、monitor.check_once() を例外捕捉付きで繰り返す。

- 設定管理
  - config.py: 環境変数/.env ロード・検証ロジックを実装。
    - プロジェクトルート探索（.git または pyproject.toml を基準）。
    - .env と .env.local の自動ロード（OS 環境変数は保護）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメントなど複数ケースに対応。
    - Settings クラスを提供し、各種設定値（DB パス・API トークン・監視しきい値・環境判定等）をプロパティで取得。入力値検証（例：KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）や pid/kill フラグのパス、リソース閾値（CPU/MEM/DISK）などのデフォルトと取得ロジックを実装。

- 監視・ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。権限不足や未実装 API でも安全にスキップし警告を出す。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。

- Portfolio（銘柄選定・配分・サイズ決定・リスク調整）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分。スコア全てが 0 の場合は等配分へフォールバック（WARNING）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを算出し、1 セクター上限を超える場合に当該セクターの新規候補を除外。
      - "unknown" セクターは上限適用外（除外しない）。
      - sell_codes を受け取り当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックし警告を出す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各配分方式（risk_based, equal, score）に基づき発注株数を算出。単元（lot）丸め、1 銘柄上限、aggregate cap（利用可能現金）でのスケーリング、cost_buffer（手数料・スリッページ想定）を考慮。
    - aggregate スケールダウン時の端数配分は小数残差に基づいて lot 単位で調整するロジックを実装。

- 研究（Research）
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
    - SQL ウィンドウ関数を多用して効率的にデータを集計。データ不足時は None を返すという設計。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（翌日/5日/21日等）を計算。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
  - research/__init__.py: 主要関数を再エクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news テーブルから指定ウィンドウのニュースを集約し、OpenAI API（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理・トークン肥大化対策（1銘柄あたり記事数/文字数制限）、最大 20 銘柄バッチ、429/ネットワーク/5xx の共通リトライ（指数バックオフ）を備える設計。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するために対象コードに絞った置換（DELETE→INSERT）を行う方針。
    - calc_news_window でニュース収集ウィンドウ（JST→UTC 変換）を提供。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出して標準出力にレポートする。
    - 合否判定閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - DB パスは --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト の順に解決。DB 存在チェックと sqlite3.OperationalError に対するフォールバックを実装。

Changed
- 設計上の注意点を明確化
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を参照する仕様とした点をドキュメント（コード内 docstring）で明示。
  - 実行（run_execution）は paper_trading 環境時に専用 SQLite DB を使用して本番 DB と分離することで検証と本番を明確に分離。

Fixed
- 安全性 / ロバスト性の向上
  - 環境変数の自動ロード処理で OS 環境変数を保護（protected set）。
  - .env パーサーを改良しクォート・エスケープ・インラインコメントに耐性を持たせた。
  - process priority / cpu affinity 設定は権限不足や未サポート環境でも例外を握り潰してワーニングログを出す実装とし、起動失敗のリスクを低減。
  - Paper verification レポートや research モジュールでデータ不足時に None を扱う設計とし、例外によるクラッシュを回避。

Security
- 機密情報の取り扱い
  - API キーやパスワードは環境変数経由で取得（Settings で _require を通じて必須チェック）。.env 自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Deprecated
- なし（初期リリース想定）

Removed
- なし（初期リリース想定）

Notes / Known issues
- 一部のコメントにある TODO は未実装（価格欠損時のフォールバック、銘柄別 lot_size マップ等）。将来的な改善点として記録。
- ai/news_nlp.py は堅牢な API エラーハンドリング・レスポンス検証を備えているが、DuckDB に対する実行時の挙動（executemany の空配列制約 等）に注意する必要がある旨の実装メモが残されている。
- apply_sector_cap は "unknown" セクターを上限適用対象外としているため、データ品質次第でセクター集中管理の効果が変わる可能性がある（コード内に警告 / コメントあり）。

今後の予定（候補）
- 銘柄別 lot_size サポート（マスタ連携）
- 価格欠損時のフォールバックロジック導入（前日終値等）
- ai/news_nlp の処理ログ・メトリクス強化、再試行ポリシーの調整
- duckdb/SQL 実行のパフォーマンス最適化（インデックスやパーティショニングの検討）

最後に
----------
本 CHANGELOG はソースコードの docstring と実装内容から推測して作成しています。実際の変更履歴・リリースノート作成時はコミットログ・リリース作業の情報を参照して更新してください。