# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。重要な変更点・設計意図はコードの内容から推測してまとめています。

全般的な注意
- 本リリースではプロジェクトのコア機能（実行エンジン、監視、ポートフォリオ構築、リサーチ、補助ツール、ユーティリティ、AI ニューススコアリング等）を一通り実装しています。
- 設定は .env / .env.local / OS 環境変数から読み込みます。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

[Unreleased]

## [0.1.0] - 2026-04-12
初回公開リリース。以下の主要機能と改善を含みます。

Added
- 実行・監視のエントリポイントを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用し MockBrokerClient と分離して動作。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する仕様。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する処理を呼び出す。

- 設定・環境読み込み機能
  - config.py: .env/.env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。OS 環境変数の保護（protected）や export 形式、クォート内エスケープ、インラインコメント処理など堅牢な .env パーシングを追加。
  - Settings クラスを提供し、各種設定（DB パス、Paper Trading 設定、監視閾値、PID/KILL フラグパス、環境判定、ログレベルなど）をプロパティ経由で取得可能に。入力値検証（列挙値チェックや数値変換）を行う。

- 監視関連
  - monitoring_db 初期化呼び出しを追加して監視テーブルが存在することを保証（冪等）。

- 実行（Execution）関連
  - ExecutionEngine の起動フロー組み立てを実装（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler の組立）。
  - RiskManager のデフォルト設定値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 関連、max_drawdown など）を定義。初期ポートフォリオ値は broker.get_available_cash() を使用。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（スコア降順＋タイブレーク）、等金額配分、スコア加重配分（スコア全0 のときは等配分にフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有のセクター比率を計算し上限超過セクターの新規候補を除外）、市場レジームに応じた資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックして 1.0 を返すように設計。
  - portfolio.position_sizing: 株数決定ロジック（risk_based / equal / score の allocation_method）を実装。lot_size（単元株）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）、cost_buffer を考慮した保守的見積り、残差処理による再配分ロジックを実装。

- 研究・ファクター計算
  - research.factor_research: モメンタム（1m/3m/6m、MA200乖離）、ボラティリティ（ATR20、ATR 比率、平均売買代金、出来高比率）、バリュー（PER、ROE の算出）を DuckDB を用いて実装。データ不足時の None ハンドリングを備える。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、Spearman ランク相関（IC）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず、標準ライブラリで完結。

- AI ニュース NLP スコアリング
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）でニュースのセンチメントを -1.0〜1.0 にスコアリングし、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して使用）。
    - 1 銘柄あたりの最大記事数・最大文字数トリム、20 銘柄単位のバッチ送信、JSON モードでの厳密なレスポンス期待。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - 部分失敗時に他銘柄の既存スコアを保持するため、対象コードで DELETE→INSERT を行う戦略。

- 補助ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定（デフォルト閾値を定義）を実施。コマンドライン引数で期間指定（--from/--to）や DB パス指定（--db）に対応。

- ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。サポート外 OS や権限不足時は警告ログを出して安全にスキップする実装。

Changed
- なし（初回リリースのため既存機能の変更履歴はありません）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーや各種パスは環境変数経由で取得する設計。OpenAI 未設定時は明示的にエラーを投げる（score_news の引数検証）。.env 自動ロードでは OS 環境変数を上書きしないよう保護（protected set）を導入。

Notes / その他の設計上の注意点（コードからの推測）
- run_monitoring は説明にある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」するため、監視データが本番 DB に記録される点に注意が必要です（Paper Trading と分離したい場合は別途設定が必要）。
- config._parse_env_line はクォート内のバックスラッシュエスケープやインラインコメントを考慮した堅牢な実装になっているため、複雑な .env フォーマットにも対応可能です。
- portfolio の position_sizing は単元株（lot_size）丸めや aggregate キャップ時の残差処理まで考慮しており、実運用での発注数計算に配慮した実装です。
- DuckDB / SQLite を併用する設計（分析用に DuckDB、状態やトレードログに SQLite）となっている。DuckDB の executemany に関する注意（空 params の扱い）など実運用上の留意点がコメントにあります。
- 多くの箇所で入力不足や OperationalError 等を想定した defensive なエラーハンドリング（データ不足の際の None フォールバック、例外時のログ出力と継続など）が実装されています。

開発者向け
- __version__ は "0.1.0" に設定されています（src/kabusys/__init__.py）。
- 追加されたモジュール群は将来的に単体テスト/統合テストを充実させる余地があります（特に OpenAI 呼び出しや外部 API を想定する箇所）。

リンク
- リリースタグ / 比較リンクはまだ設定されていません。

-----