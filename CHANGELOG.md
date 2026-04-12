CHANGELOG
=========

すべての変更は Keep a Changelog の書式に準拠して記載しています。以下の内容はリポジトリ内のソースコードから推測して作成した変更履歴です（実際のコミット履歴ではありません）。

Unreleased
----------

- なし

0.1.0 - 2026-04-12
------------------

Added
- 基本機能一式の初回リリース相当の実装を追加。
  - 実行用エントリポイント
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）と MockBrokerClient を使って本番 DB と分離して実行する。
    - run_monitoring.py: SystemMonitor をポーリング実行する起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間指定や DB パス指定オプションをサポートし、稼働率・注文成功率・送信率・レイテンシ等の指標を算出して判定（PASS/FAIL）を出力する。
  - 設定管理
    - config.Settings: 環境変数／.env ファイル経由の設定取得ユーティリティを実装。自動 .env ロード（.env → .env.local、OS 環境変数優先）と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - .env パーサー: export プレフィックス、クォート（エスケープ対応）、インラインコメントの扱いなどを考慮したパーサーを実装。
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、しきい値、環境判定プロパティなど）を提供。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: 候補選定（score 降順 + tie ブレーク）、等金額／スコア加重の重み計算を実装。
    - portfolio.position_sizing: 発注株数算出ロジックを実装（risk_based / equal / score）。最大ポジション上限、lot 単位丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分を実装。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投入資金乗数（calc_regime_multiplier）を実装。
  - リサーチ / ファクター
    - research.factor_research: Momentum / Volatility / Value 等のファクター計算を DuckDB 上で実行する関数（calc_momentum, calc_volatility, calc_value）を追加。200日移動平均、ATR、20日平均売買代金等を計算。
    - research.feature_exploration: 将来リターン計算（calc_forward_returns）、Spearman ランク相関による IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク関数（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - AI / ニュース NLP
    - ai/news_nlp.py: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む処理を実装。バッチ処理（最大 20 コード/回）、トークン肥大化対策（記事数・文字数トリム）、429/ネットワーク/5xx に対するエクスポネンシャルバックオフ・リトライ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分成功時の差分置換（DELETE→INSERT）などを備える。API キーは引数または OPENAI_API_KEY 環境変数で指定し、未設定時はエラー（ValueError）。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティと、CPU affinity を最初 N コアに固定する関数を追加。権限不足や未対応 OS は警告でスキップ。

Changed
- DB 初期化と接続ポリシー
  - run_monitoring.py: Monitoring 処理は KABUSYS_ENV に関わらず production の sqlite_path（Settings.sqlite_path）を使用して接続する設計となっている。
  - run_execution.py: paper_trading 実行時は paper_sqlite_path を使用して本番 DB と完全に分離する。
  - 両スクリプトともに duckdb をデータ分析用に接続し利用するようになっている。
  - 監視テーブルが存在することを保証するため、起動時に init_monitoring_db を呼び出して冪等にテーブルを作成する（存在チェック＆作成）。
- .env 自動読み込み順の明確化
  - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env → .env.local の順で読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 設定値検証
  - Settings 内で KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検証を行い、不正値は ValueError を送出するようになった（早期検出）。
- paper_verification_report
  - 検証スクリプトは DB 存在チェックや sqlite3.OperationalError を捕捉して許容し、欠損テーブルに対しても N/A 表示でフォールバックするようにした。P95 は単純パーセンタイル実装。

Fixed
- run_monitoring のポーリング間隔取得関数 _get_poll_interval の振る舞いを明確化
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合は警告ログを出してデフォルト 60 秒にフォールバックし、time.sleep に不正値が渡らないように保護。
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメント扱いのルール化等により実運用の .env フォーマット差異に耐性を持たせた。
- news_nlp の安全性向上
  - API 呼び出し失敗時にフェイルセーフで処理を継続する（個別チャンク失敗で他の銘柄への影響を最小化）。空のレスポンスや不正な JSON は無視してログを残す設計。

Security
- OpenAI API キー等の機密情報を OS 環境変数優先で扱い、.env の自動ロードは OS 環境変数を上書きしない保護あり（.env.local は override 可だが OS 環境は保護）。

Breaking Changes
- 監視プロセスの DB 接続先の仕様
  - run_monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（本番想定）を使用するため、従来の「環境毎に監視 DB を切り替える」運用はできない点に注意が必要（必要なら監視スクリプト側で環境分岐を実装すること）。
- Settings の検証強化により、不正な環境変数値（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）で起動時に ValueError が発生する可能性がある。CI / デプロイ前に環境変数の整合性を確認してください。

Notes / Implementation details
- DuckDB を分析用に使用しており、prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等のテーブルを想定している。
- Execution 側の RiskManager / EngineConfig 等は初期パラメータをコード内で設定しており、リスク関連パラメータ（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）がデフォルトで構成されている。RiskManager は broker.get_available_cash() を初期資金として利用。
- position_sizing の aggregate cap は cost_buffer を考慮して投資額を保守的に見積もり、利用可能現金を超える場合はスケールダウンしつつ lot 単位で端数処理を行うことで再現性と安全性を担保している。
- ai/news_nlp の実行は OpenAI クライアント（OpenAI パッケージ）依存であり、API レートやネットワークエラーに対する対処（リトライ）が実装されているが、運用上は API キー管理とレート制御に注意が必要。

補足
- ここに記載した内容はコード内の実装から推測してまとめたリリースノートです。実際の変更履歴（コミット単位の差分やリリースタグ）とは異なる場合があります。必要であれば各ファイルの変更差分や実装箇所を元にさらに詳細なエントリを作成します。