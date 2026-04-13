CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」フォーマットに準拠しています。  
コードベースの内容から推測して作成しています（実装意図・挙動に基づく要約）。

注意: リリース日付は現時点（ファイル内のコメントやコードの想定時期）を基に設定しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 全体
  - 初期リリース。パッケージのバージョンは kabusys.__version__ = "0.1.0"。
  - モジュール構成を整備（config / utils / portfolio / research / ai / monitoring / execution / tools 等を提供）。

- 設定管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env および .env.local を読み込み、読み込み順に応じた上書きルール（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みの無効化をサポート。
  - .env パーサを実装（export 形式対応、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理）。
  - 必須環境変数チェック関数 _require を提供（未設定時は ValueError）。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システムフラグ等）。
  - 設定値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の値検証と不正時の例外）。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 不正な間隔（0以下や非数）はデフォルトにフォールバックし警告を出力。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB 初期化を行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のセッション実行を行う。

- 監視関連
  - monitoring_db の初期化呼び出しを run_monitoring と run_execution の両方で行い、監視テーブルが存在することを保証（冪等）。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装（Windows / POSIX を吸収）。
  - set_cpu_affinity(cpu_count) を追加（指定コア数にプロセスを固定）。
  - アクセス権限不足や未対応 OS の場合は警告ログを出し安全にスキップ。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: シグナル選定 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights（全スコア 0 の場合は警告と等金額フォールバック）。
  - risk_adjustment: セクター集中制限 apply_sector_cap（既存保有を考慮、unknown セクターは制限対象外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 でフォールバック）。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を用いた保守的見積もり、スケールダウン時の残差扱い（lot 単位での再配分）を実装。

- リサーチ機能 (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。DuckDB の prices_daily/raw_financials を用い、ウィンドウ処理・移動平均・ATR 等を計算。データ不足時は None を返す保守的実装。
  - feature_exploration: 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ランク変換 rank、ファクター統計 summary（count/mean/std/min/max/median）を提供。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news から銘柄ごとにテキストを集約し、OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ格納する機能を実装。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1 銘柄当たりの最大記事数・文字数制限、JSON Mode による厳密な JSON レスポンス期待。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（最大 _MAX_RETRIES）。
  - スコアを ±1.0 にクリップ、部分失敗時に他コードの既存スコアを保護するため対象コードのみ削除→挿入で更新。
  - target_date に基づく明示的なニュースウィンドウ計算（datetime.today() に依存せずルックアヘッドバイアスを防止）。
  - API キー未指定時は ValueError を送出。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading の検証レポート生成スクリプトを追加（CLI サポート: --from, --to, --db）。
  - 稼働率・注文成功率・送信率・API レイテンシ（P95 等）を算出し、閾値による PASS/FAIL 判定を行う。
  - P95 計算、日付フィルタ構築、DB の存在チェックおよび sqlite3.OperationalError に対する耐性を実装。

Changed
- 監視/実行の挙動
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を監視 DB に使用する設計（監視は実環境の状態を監視する想定）。
  - run_execution は paper_trading 環境で紙取引専用 DB を使用して本番と完全分離するように変更（paper_trading 用 DB パスを設定可能）。

Fixed / Robustness
- 環境読み込みとパース
  - .env のクォート文字列内バックスラッシュエスケープ処理や export 形式への対応で .env の多様な記法に耐性を追加。
  - .env.local の override 動作で OS 環境変数を保護する実装により予期せぬ上書きを防止。
- process_priority / CPU affinity
  - psutil のアクセス権限不足や未対応プラットフォーム時に例外で終了せず警告ログを出してスキップするよう安全化。
- research / factor 計算
  - データ不足時に None を返すことで downstream の処理が壊れにくい設計に。
- ai/news_nlp
  - OpenAI API 呼び出しのエラー（429 等）に対するリトライ・バックオフを実装し信頼性を向上。
  - API キー未設定時の明示的なエラー報告。

Notes / Known limitations
- position_sizing:
  - price が欠損（0.0）の場合、エクスポージャー・サイズ算出が過小評価される旨の TODO コメントがあり、将来的に前日終値や取得原価でのフォールバックを検討。
- news_nlp:
  - 外部 API（OpenAI）に依存するため、API 利用制限やコストに注意が必要。
- .env 自動読み込み:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする（配布先での動作を考慮した設計）。

License
-------
- 記載なし（コードベースに基づくため CHANGELOG にも記載していません）。必要に応じてプロジェクトの LICENSE を参照してください。