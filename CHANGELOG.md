# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、提供されたコードベースの内容から推測して作成したリリースノートです。

全般方針:
- 可能な限りソースコードのコメントや docstring、関数名・環境変数名から機能を抽出して記述しています。
- 実装上の挙動（デフォルト値やフォールバック動作、エラーハンドリング等）についてもコードの挙動に基づき明記しています。

------------------------------------------------------------------

未リリース
- 現時点の開発中の変更点はありません。

[0.1.0] - 2026-04-13
--------------------

Added
- プロジェクト基盤と主要機能を初回リリースとして追加。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
  - 設定・環境変数管理 (src/kabusys/config.py)
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env のパース機能強化（export 形式対応、シングル/ダブルクォート中のバックスラッシュエスケープ処理、インラインコメント処理）。
    - 必須環境変数未設定時にわかりやすいエラーを送出する _require()。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 実行環境フラグなど）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の Paper Trading 用設定をサポート。
  - 実行系エントリポイント
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、本番 DB と分離して data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）を使用。
      - BrokerClientFactory を利用して実ブローカー / MockBroker を切替可能。
      - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を run_session() 実行。
      - 起動時にプロセス優先度を high に設定するユーティリティを使用。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下など不正値はデフォルトにフォールバックし警告を出す）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
      - DuckDB / SQLite の接続および監視 DB 初期化を行う。
  - 監視関連
    - monitoring_db 初期化ユーティリティの呼び出しを各起動スクリプトから行い、監視テーブルの存在を保証（冪等）。
  - ユーティリティ
    - process_priority.py
      - Windows と POSIX (Linux/Mac/FreeBSD) を吸収するプロセス優先度設定関数 set_process_priority(level) を追加（"high" / "normal" / "low"）。
      - CPU affinity を設定する set_cpu_affinity(cpu_count) を追加（任意）。
      - 権限不足や未対応環境では警告を出してスキップする安全策を実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio_builder.py
      - シグナル選定(select_candidates)、等分配(calc_equal_weights)、スコア加重(calc_score_weights) を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
    - risk_adjustment.py
      - セクター集中制限 (apply_sector_cap) の実装。既存保有を考慮して特定セクターをブロックするロジックを提供（unknown セクターは無視）。
      - 市場レジームに応じた投下資金の乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 でフォールバック）。
    - position_sizing.py
      - allocation_method に基づく株数決定ロジック calc_position_sizes を実装（risk_based / equal / score）。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer による保守的見積り、残差配分ロジックを提供。
      - 価格欠損時には銘柄をスキップしログ出力。
    - portfolio パッケージのエクスポートを整備。
  - 研究・リサーチ機能（DuckDB ベース、外部 API なし）
    - research.factor_research
      - モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) のファクター計算を追加。prices_daily / raw_financials を参照して DuckDB 内で計算。
      - 200日移動平均やATRなどの窓計算を SQL ウィンドウ関数で実装。データ不足時には None を返す方針。
    - research.feature_exploration
      - 将来リターンの一括取得(calc_forward_returns)、IC（Spearman）計算(calc_ic)、ランク化ユーティリティ(rank)、ファクター統計サマリー(factor_summary) を実装。外部依存なしで完結。
    - research パッケージの __all__ を整備。
  - AI ニュース NLP スコアリング (OpenAI)
    - ai/news_nlp.py
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウの定義（前日 15:00 JST 〜 当日 08:30 JST → UTC に変換）が明確に定義され、calc_news_window() として提供。
      - バッチ処理（最大 20 銘柄 / リクエスト）、記事トリム（最大記事数・最大文字数）やレスポンスバリデーション、スコアクリッピング（±1.0）等の安全策を実装。
      - API キー未設定時は明示的エラーを投げる（api_key 引数または OPENAI_API_KEY 環境変数）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装（リトライ上限・初回待機秒の定義あり）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）を読み、指定期間の稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計してコンソール出力するレポート生成スクリプトを追加。
      - PASS/FAIL 判定基準（稼働率 99% など）を定義し、閾値を超えた指標を失敗理由として表示。
      - コマンドライン引数 (--from, --to, --db) をサポート。

Changed
- 監視・実行起動の初期化フローを統一化
  - どちらの起動スクリプトも最初にプロセス優先度を high に設定し、DB 初期化（監視テーブルの確保）→コンポーネント組み立て→メインループ というシーケンスを踏むように設計。
- .env の読み込み優先度
  - OS 環境 > .env.local > .env の順でロードする挙動を明確化。既存 OS 環境変数は保護される（protected set）。

Fixed
- 環境変数パースの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメント識別を改善し、より現実的な .env 記述に対応。
- MONITOR_POLL_INTERVAL の不正値（0 や負値、文字列など）に対して警告を出しデフォルトへフォールバックするようにして、time.sleep に渡して ValueError が発生するリスクを回避。

Security
- OpenAI API キーの扱いについて明記（環境変数または引数での提供が必須）。キー未提供時には処理を中断して明示的エラーを投げる実装とし、誤ったキーの流布を防止するガイドラインに寄与。

Notes / Known limitations
- DuckDB / SQLite のテーブル存在チェックはありつつ、スキーマ整合性や列の有無については一部関数で sqlite3.OperationalError をキャッチして N/A として扱う設計になっている（実運用前に必要テーブル/列が揃っていることを確認してください）。
- position_sizing、apply_sector_cap 等はいずれも価格やマスタデータの欠損に対して一部安全弁を実装していますが、欠損データがあると過少評価やスキップが生じる場合があります（コメントに将来のフォールバック案あり）。
- ai/news_nlp の処理途中メッセージはログに出力するが、部分失敗時の永続化戦略は「スコア取得済みコードのみ置換」を採用しており、部分的な失敗が他銘柄の既存スコアを破壊しないよう配慮している。

------------------------------------------------------------------

今後の提案（参考）
- テストカバレッジ: .env パースや position sizing のエッジケース、AI API のリトライロジックについてユニットテスト拡充を推奨。
- ドキュメント: PortfolioConstruction.md / StrategyModel.md 等の参照セクション名がコードに散見されるため、該当設計文書をリポジトリに含めると開発・運用が容易になります。
- モニタリング: SystemMonitor の詳細実装に基づき、アラート出力先（LINE 等）や履歴ローテーション方針を明示するドキュメント整備を推奨。

------------------------------------------------------------------

（以上）