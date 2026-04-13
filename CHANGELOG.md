# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、提示されたコードベースの内容から推測して作成した変更履歴です。

全般的な注記
- 本ドキュメントは、提示されたソースコードの機能追加・改善・修正点を推測してまとめたものです。
- バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせて記載しています。

Unreleased
- （なし）

[0.1.0] - 2026-04-13
Added
- 基本アプリケーションとユーティリティ群を実装。
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に探索。
  - export KEY=val 形式やクォート・コメントを考慮した堅牢な .env パーサを実装。
  - OS 環境変数を保護するオプション（override/protected）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化もサポート。
  - 各種設定プロパティを提供（DB パス、PID ファイル、しきい値、環境判定など）とバリデーションを実装。
  - PAPER_FILL_MODE 等の列挙的設定に対する検証を追加（無効値は ValueError）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading SQLite を使用し、本番 DB と完全分離する実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション起動を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きに対応（デフォルト 60 秒）。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する設計。
    - プロセス優先度設定、DB 初期化（init_monitoring_db）、DuckDB 接続を統合。
- モニタリング関連
  - init_monitoring_db を通じた監視テーブル初期化の呼び出しを起動スクリプトに統合（冪等性を想定）。
  - SystemMonitor を利用した periodic check の実行ループと例外ハンドリング（個別チェック例外はログに残して継続）。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォームでのプロセス優先度設定を実装（Windows / POSIX の差分吸収）。
  - CPU affinity の設定ユーティリティを追加（指定コア数でプロセスをピン留め）。
  - アクセス権限や実装差異に対する安全なフォールバック（警告ログ）を実装。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定（score 降順／signal_rank タイブレーク）、等金額配分、スコア重み配分（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - risk_adjustment:
    - セクター集中制限を適用する apply_sector_cap 実装（既存保有のセクター別時価でブロック判定）。
    - レジームに応じた投入資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知レジームはフォールバックで1.0）。
  - position_sizing:
    - allocation_method に応じた株数決定ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - cost_buffer を加味した保守的見積り、スケール後の残余配分ロジックを実装。
- リサーチ・ファクター計算（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER/ROE）を DuckDB 上で計算する関数群を実装。
    - 大量データを想定したウィンドウ指定や欠損データ時の None ハンドリングを実装。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリーを標準ライブラリのみで実装。
    - rank ユーティリティは ties を平均ランクで処理し、丸め誤差対策を実施。
  - research パッケージの __all__ エクスポートを追加（zscore_normalize など外部統計ユーティリティとの統合）。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI API（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む機能を実装。
  - 処理フロー:
    - タイムウィンドウ計算（前日 15:00 JST〜当日 08:30 JST を UTC に変換）。
    - 銘柄ごとに記事集約（記事数・文字数上限でトリム）。
    - 最大バッチサイズ（20 銘柄）で API へ送信、JSON Mode による厳密な JSON レスポンス期待。
    - 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - 結果のバリデーション、スコアを ±1.0 にクリップ。
    - 部分成功時にも既存スコアを保護するためコード絞り込みで DELETE→INSERT を実行。
  - API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時は ValueError を送出。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成 CLI を追加。
    - オプションで期間指定（--from / --to）および DB パス（--db）。
    - レポート指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - 各 DB テーブルが存在しない場合の安全なフォールバック（sqlite3.OperationalError を捕捉して N/A を返す）。
    - レポート判定（PASS/FAIL）と閾値の定義（稼働率 >= 99%、注文成功率 >= 90% など）。
- ログ・例外処理
  - 起動スクリプトや主要モジュールに INFO/DEBUG ログを追加し、例外発生時には詳細ログを残して処理継続する実装を採用。
  - DB 存在チェックやファイル読み込み失敗時のユーザ向けエラーメッセージを整備。

Changed
- なし（本バージョンは初期公開として多くの機能を追加）。

Fixed
- なし（既知のバグ修正履歴は未検出。実装側で多くの安全弁／例外処理を追加）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取得を明示化（引数または環境変数）。未設定時は例外とし、意図せぬキー漏洩や未設定運用を防止。

開発者向けメモ（推測）
- DuckDB と SQLite の両方を採用しているため、分析系（DuckDB）と稼働・監視系（SQLite）を分離した設計が意図されている。
- Paper Trading 用の DB を分離しているため、本番データと検証データの混在を避ける設計になっている。
- 将来的な拡張ポイントとして、銘柄ごとの lot_size マスタや価格フォールバック（position_sizing / risk_adjustment の TODO）が残されている。

脚注
- 実際のリリースノート作成時は、変更を加えたコミット履歴・PR・issue 等の情報を参照して正確に記載してください。本ファイルはソースコードからの推測に基づく暫定的なまとめです。