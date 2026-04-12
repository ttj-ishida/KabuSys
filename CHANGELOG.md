Keep a Changelog
=================

本ドキュメントは Keep a Changelog の書式に準拠しており、後方互換性・変更履歴の明確化を目的としています。

Unreleased
----------

追加予定 / 既知の注意点
- 一部モジュールに TODO や注記あり（例: price のフォールバック処理、DuckDB executemany の空パラメータ回避など）。
- news_nlp モジュールの一部処理（記事フェッチやテーブル書き込みの細部）は将来的な堅牢化・リトライ強化の余地あり。
- テストで環境変数自動ロードを無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD の活用を推奨。

v0.1.0 - 2026-04-12
-------------------

Added
- 全体
  - 初回リリースとして、自動売買システム KabuSys の主要コンポーネントを実装。
  - パッケージバージョンを "0.1.0" として設定（src/kabusys/__init__.py）。

- 実行・監視
  - run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度設定を行い（高優先度指定）、SQLite / DuckDB に接続して ExecutionEngine を起動。
    - KABUSYS_ENV=paper_trading の際は paper_trading 用の SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（監視データは環境で分離しない想定）。
    - SystemMonitor の check_once を定期実行するポーリングループを実装。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml により判定）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境変数のパースロジックを強化（export 形式、クォート・エスケープ、インラインコメント処理など）。
    - 各種プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / システムフラグ等）。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値検証を実装（不正値は ValueError）。

- ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して p.nice または HIGH_PRIORITY_CLASS を使用。
    - set_cpu_affinity で最初の N コアに固定可能。権限不足や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築
  - 銘柄選定・重み計算関数群を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates / calc_equal_weights / calc_score_weights を提供。score が全て 0 の場合のフォールバック警告あり。
  - セクター上限適用とレジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有を考慮したセクター集中制限ロジック。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ）。
  - ポジションサイジングを追加（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer の考慮等を実装。
    - スケールダウン時に余剰キャッシュを利用して lot_size 単位で調整するアルゴリズムを実装。

- 研究（Research）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、出来高指標）、バリュー（PER/ROE）を DuckDB 上で計算。
    - ウィンドウやデータ不足時の None ハンドリングを実装。
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（可変ホライズン）、IC（Spearman）計算、ファクター統計サマリ、ランク変換ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリで実装。
  - research パッケージの公開 API を整備（src/kabusys/research/__init__.py）。

- AI / ニュース
  - ニュース NLP スコアリングを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理フローを実装。
    - バッチサイズ（20）、リトライ方針（429/タイムアウト/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ等を実装。
    - target_date に基づくニュース収集ウィンドウ計算（JST→UTC の変換）を提供。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs 等から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出して標準出力へ整形表示。
    - CLI オプションで期間指定（--from, --to）や DB パス指定（--db）に対応。
    - 合格基準（稼働率 99% 等）を定義し、PASS/FAIL 判定を出力。

Changed
- DB 周り
  - 監視テーブルの初期化処理を冪等に実行する init_monitoring_db の呼び出しを起動スクリプト内で保証（run_execution, run_monitoring）。
  - Execution 起動時、paper_trading 環境では paper_sqlite_path を優先して使用し、本番データと完全分離する仕様を確立。

Fixed
- 環境変数パースの堅牢性向上（src/kabusys/config.py）
  - export プレフィックス、クォート付き値のバックスラッシュエスケープ、インラインコメント処理、無効行のスキップ等を実装。
- MONITOR_POLL_INTERVAL の不正値（0 や負数、非数）に対するフォールバック処理を追加（警告ログを出してデフォルト 60 秒を使用）。
- プロセス優先度・CPU affinity 設定で権限不足や未対応プラットフォームに対して安全にスキップし、警告ログを出すよう改善（src/kabusys/utils/process_priority.py）。

Security
- OpenAI API キーは明示的に引数か環境変数からのみ取得し、未設定時は処理を停止してエラーを出す設計（news_nlp）。

Notes / Known issues
- src/kabusys/portfolio/risk_adjustment.py の apply_sector_cap 内に price が 0.0 の場合の過小見積りに対する TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
- DuckDB の executemany に関する注意（空パラメータを渡さない）や、ai_scores 更新時のトランザクション分割など、実運用での堅牢化余地が残る。
- news_nlp モジュールは API 失敗時のスキップ設計だが、部分失敗時のリトライ・ロールバックポリシーを要検討。

開発者向け補足
- 自動環境ロードはプロジェクトルートを .git または pyproject.toml から探索するため、パッケージ配布後でも同様の挙動となる（ただしルートが特定できない場合はスキップされる）。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できる。

今後の予定
- price フォールバックロジックの追加（セクターエクスポージャ正確化）。
- news_nlp の処理失敗時の部分リカバリ / ロールバック戦略の強化。
- 単体テスト・統合テストの拡充と CI パイプライン整備。

--------------------------------------------------------------------------------
注: 上記はソースコード内の実装・コメントから推測して作成した CHANGELOG です。実際のリリースポリシーやタグ付けは開発ワークフローに合わせて調整してください。