CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース。KabuSys の基礎機能群を実装。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動するエントリポイント。環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading 時は data/paper_trading.db を使用）。起動時にプロセス優先度を上げ、ExecutionEngine を組み立ててセッションを実行。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。なお監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する挙動。
  - 設定管理
    - config.py: .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）を実装。OS 環境変数の保護（protected keys）や .env/.env.local のロード順を実装。必須環境変数取得ヘルパ _require と設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を提供。各種デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）と閾値設定（CPU/MEM/DISK %）をプロパティとして公開。
  - ユーティリティ
    - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定と CPU affinity 設定関数を実装。権限不足や未対応プラットフォームの際は警告を出して安全にスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分へフォールバック）を実装。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（当日売却予定銘柄の除外対応）、市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピングと未知レジームでのフォールバック）を実装。
    - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に対応した株数算出、単元（lot）丸め、aggregate cap によるスケーリング（残差を lot 単位で再配分）を実装。手数料・スリッページのバッファ（cost_buffer）を考慮。
  - リサーチ / ファクター計算
    - research/factor_research.py: DuckDB を使ったモメンタム、ボラティリティ（ATR、出来高関連）、バリュー（PER, ROE）ファクターの計算関数を実装。長期 MA や ATR 等のウィンドウ幅、スキャン用バッファ日数を設計に組み込み、データ不足時の None 扱いを明確化。
    - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、Spearman（ランク相関）ベースの IC 計算、ランク付けユーティリティ、ファクター列の基本統計（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - AI ニュース NLP
    - ai/news_nlp.py: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得、ai_scores テーブルへ書き込む処理を実装。処理ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を明確に計算し、1 銘柄当たりの文字数・記事数の上限を設けてトークン肥大化を防止。API のレート/ネットワーク系エラーに対してエクスポネンシャルバックオフでリトライする設計、応答のバリデーションとスコアのクリップ（±1.0）を実装。OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。
  - CLI ツール
    - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率・注文成功率・送信率・P95 レイテンシ）を集計して標準出力にレポートを出力する CLI を実装。期間指定（--from / --to）と DB パス指定（--db）に対応。P95 実装、データ欠損時の堅牢なハンドリング、判定閾値（稼働率 99%、成功率 90% 等）を組み込む。
  - パッケージ初期化
    - __init__.py にてバージョンを "0.1.0" として設定し、主要サブパッケージを __all__ にエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- 各種入力検証とエラー時のフォールバック（例: MONITOR_POLL_INTERVAL の不正値フォールバック、PAPER_FILL_MODE の不正値チェック、.env ファイル読み込みの失敗時の警告）を追加して堅牢性を向上。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの扱い: score_news は明示的に api_key 引数または環境変数 OPENAI_API_KEY が必要。キー未設定時は ValueError を送出して処理を停止し、意図しない外部送信を防止。

Notes / 重要な挙動
- run_monitoring.py は監視用 DB として KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データと paper_trading を完全に分離したい場合は設定を確認してください。
- .env の自動ロードはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / cpu affinity の設定は実行環境の権限や OS のサポート状況に依存します。設定に失敗した場合は警告ログを出して処理を継続します。

参考: 主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが検証あり）
- SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH
- PAPER_FILL_MODE: instant | partial | never | reject
- OPENAI_API_KEY: ニュース NLP 用 API キー
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、1 以上。無効値はデフォルト 60 秒にフォールバック）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: .env 自動ロードを無効化するフラグ（1 に設定）

今後の改善予定（アイデア）
- position_sizing: 銘柄ごとの lot_size をマスタから読み込む設計への拡張
- news_nlp: OpenAI の応答失敗時の部分ロールバックやテレメトリ強化
- research: 大規模データ向けのパフォーマンス最適化（インクリメンタル処理等）

-----------------------------------------------------------------------------