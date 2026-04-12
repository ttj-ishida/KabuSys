CHANGELOG
=========
すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はバージョンごとに整理しています。
- 日付はリリース日を示します。

[Unreleased]
------------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-12
-------------------

Added
- 初期リリース: KabuSys 0.1.0 を公開。
  - 日本株自動売買システムのコア機能群を実装。
  - パッケージバージョンは src/kabusys/__init__.py にて 0.1.0。

- 環境設定管理 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env のパースを堅牢化（export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
  - Settings クラスを導入し、各種設定プロパティ（DB パス、PID/KILL フラグ、閾値、PAPER_TRADING 用設定、env/log レベル検証など）を提供。
  - 必須環境変数未設定時に明確なエラーを送出。

- 実行エントリポイント (src/kabusys/run_execution.py)
  - ExecutionEngine 起動スクリプトを実装。
  - プロセス優先度設定（High）を起動時に適用。
  - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite DB を使用（本番 DB と分離）し、BrokerClientFactory により MockBrokerClient を使用可能。
  - 監視テーブルの初期化を行い、duckdb 接続を併用。
  - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）とセッション実行を実装。
  - RiskConfig のデフォルトパラメータを明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値に broker.get_available_cash() を使用。

- 監視エントリポイント (src/kabusys/run_monitoring.py)
  - SystemMonitor ポーリングループ起動スクリプトを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバックして警告）。
  - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
  - 例外発生時はログ出力して次のポーリングへ継続、KeyboardInterrupt で正常終了。DB 接続は finally でクローズ。

- モジュール群: ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder: 候補選定 (select_candidates)、等分配・スコア加重配分 (calc_equal_weights, calc_score_weights) を提供。スコア合計が 0 の場合は等分配へフォールバック。
  - risk_adjustment: セクターキャップ適用 (apply_sector_cap)、レジーム乗数計算 (calc_regime_multiplier) を提供。未知レジームはフォールバック値をログ警告付きで使用。
  - position_sizing: ポジションサイズ算出 (calc_position_sizes) を実装。risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、aggregate cap（available_cash）超過時のスケーリングと残差処理を実装。

- 研究・ファクター計算 (src/kabusys/research/)
  - factor_research: momentum / volatility / value ファクター計算を DuckDB SQL で実装（prices_daily, raw_financials 利用）。200日移動平均やATR等に対する欠損ハンドリングを含む。
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマン）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク付け (rank) を実装。外部ライブラリに依存せず純粋 Python 実装。
  - research パッケージのエクスポートを整備（zscore_normalize 等を含む）。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores に書き込むロジックを実装。
  - JST の定義済みニュースウィンドウ（前日 15:00 ～ 当日 08:30）に基づく記事集約を実装（UTC 変換）。
  - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの文字数と記事数上限、API レスポンス検証、スコアクリップ（±1.0）、再試行（指数バックオフ）を備える。
  - OpenAI API キーの解決（引数優先、環境変数 OPENAI_API_KEY）と未設定時の ValueError。

- ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX を吸収し、アクセス権限不足などは警告ログでスキップする堅牢性を確保。

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 向け検証レポート生成ツールを実装。
  - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計・判定（閾値付き PASS/FAIL）して CLI 出力。
  - --from / --to / --db オプションや環境変数 PAPER_TRADING_SQLITE_PATH による DB 指定をサポート。DB が存在しない場合のエラーメッセージを提供。
  - 各クエリでテーブルが存在しない場合の例外（sqlite3.OperationalError）を捕捉してフォールバック。

Changed
- ログ出力・例外処理の強化
  - ポーリングループや OpenAI 呼び出し等、失敗してもプロセスを停止させない設計（例外時はログ出力して継続）。
  - DB 接続やリソースは finally ブロックで確実にクローズ。

Fixed
- .env の読み込み周りでの互換性と堅牢性を改善（export 形式、クォート内エスケープ、コメント扱い等）。
- ポーリング間隔 MONITOR_POLL_INTERVAL の不正値に対してデフォルトへフォールバックして ValueError を回避。

Notes / Known issues
- apply_sector_cap 内の価格欠損 (price == 0.0) によるエクスポージャー過小評価の可能性が存在。将来的に前日終値や取得原価をフォールバックする拡張を検討中（ソースに TODO コメントあり）。
- OpenAI 連携部分はネットワーク/API レスポンスの堅牢化を図っているが、API レートや費用の管理は運用面での配慮が必要。
- 本リリースは初版のため、将来的にモジュール分割や単体テストの追加、設定の細分化（銘柄別 lot_size 等）を予定。

ライセンス・安全注意
- 実運用での利用にあたっては API キーや秘密情報の管理、paper_trading の活用による事前検証、リスクパラメータの調整を必ず行ってください。

補足
- 本 CHANGELOG はコードベース（src 以下の実装）から推測して作成しています。実際の変更履歴やリリースノートは開発プロセスに応じて調整してください。