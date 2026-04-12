CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" のフォーマットに準拠します。  
セマンティックバージョニングを意識して変更内容を記録します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-12
--------------------

初回リリース — KabuSys の基礎機能を一通り実装しました。以下はコードベースから推測してまとめた主要な追加点・注意点です。

Added
- 基本パッケージ
  - kabusys パッケージ（__version__ = 0.1.0）。
  - パッケージ公開時に利用するモジュール群を整理し、主要 API を __all__ でエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パースは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、監視閾値、環境種別など）。
  - 必須環境変数が未設定の場合は ValueError を送出するヘルパーを実装。

- 実行系スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント切り替え。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて Engine を実行。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は本番 sqlite_path を使用する（KABUSYS_ENV に依存しない設計）。
    - 起動時にプロセス優先度を "high" に設定。

- 監視関連
  - monitoring_db の初期化呼び出しを実行前に行い、監視用テーブルの存在を保証（冪等）。

- ポートフォリオ構築関連 (kabusys.portfolio)
  - portfolio_builder: 候補選定（score / signal_rank に基づくソート）、等重み・スコア重みの重み付け関数を提供。
  - position_sizing: 発注株数計算ロジック（risk_based / equal / score）を実装。lot_size（単元）丸め、aggregate cap によるスケールダウンや端数配分ロジックを含む。
  - risk_adjustment: セクターキャップ適用（既存保有を考慮して候補を除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクターを DuckDB（prices_daily, raw_financials 等）から計算する関数群を実装。
    - mom_1m/3m/6m、MA200乖離、ATR20、avg_turnover、volume_ratio、PER/ROE 等。
    - SQL ウィンドウ関数を多用し、欠損・データ不足時は None を返す安全設計。
  - feature_exploration: 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計サマリ、ランク付け関数を実装。
    - 外部依存ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - OpenAI API（gpt-4o-mini + JSON Mode）を使って raw_news を銘柄ごとに集約しセンチメント（-1.0〜1.0）をスコアリングして ai_scores テーブルへ書き込む機能を実装。
  - バッチ（最大 20 銘柄/コール）、トークン肥大対策（記事数上限 / 文字数上限）、レスポンス検証、スコアクリッピング（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
  - OPENAI_API_KEY の未設定時は ValueError を発生させる明示的チェックを実装。
  - ニュース対象ウィンドウは JST 基準で前日 15:00 〜 当日 08:30（UTC に変換）を採用し、ルックアヘッドバイアスを避ける設計。

- ユーティリティ (kabusys.utils)
  - process_priority: psutil を用いて Windows / POSIX（Linux, Darwin, FreeBSD）でプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを実装。サポート外 OS や権限不足時は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装（--from/--to/--db オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL を判定する基準を実装。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH で上書き可能。

- データストア
  - DuckDB（データ分析向け）と SQLite（モニタリング / 発注履歴）を併用する構成を採用。デフォルトパスは data/kabusys.duckdb / data/monitoring.db / data/paper_trading.db。

Fixed
- MONITOR_POLL_INTERVAL が無効（非整数や 0 以下）の場合にデフォルト（60 秒）へフォールバックするログ出力を追加（time.sleep に不正値が渡らないように保護）。

Changed
- なし（初回リリース）

Removed
- なし

Breaking Changes
- なし（初回リリース）

Notes / Migration / Usage
- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等は Settings のプロパティで必要に応じて参照され、未設定時は ValueError になるのでデプロイ前に .env を準備してください。
  - 自動 .env 読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - PAPER_FILL_MODE の有効値は instant / partial / never / reject。
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。整数値を指定、1 未満や非整数の場合は 60 秒にフォールバック。

- Paper Trading
  - paper_trading 環境は sqlite を分離しているため、本番データと混ざらない構成になっています（PAPER_TRADING_SQLITE_PATH で変更可）。

- OpenAI
  - news_nlp.score_news は OPENAI_API_KEY（または api_key 引数）が必須。API レート制限やネットワーク障害は内部リトライで保護されるが、API キーの管理・コストに注意してください。

Known Issues / TODOs
- apply_sector_cap:
  - price_map に欠損（0.0）があるとエクスポージャーが過少評価され、ブロックが外れる可能性がある。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - lot_size は現在グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map に拡張する旨の TODO コメントあり。
- ai/news_nlp:
  - DuckDB の executemany 周り（空パラメータ扱い）や部分失敗時のスコア保護など細かい実装上の注意がコメントに存在。大量データ処理時のメモリ・レイテンシに注意。
- research モジュール:
  - P95 等パーセンタイル計算や大規模銘柄数での全値フェッチはメモリ消費の懸念あり（現状は単純実装）。
- process_priority:
  - OS 標準での権限やプラットフォーム依存のため、失敗時は警告を出すだけで動作を継続する仕様。

Acknowledgements
- DuckDB を分析用に採用し、psutil をプロセス制御に利用。
- OpenAI をニュースセンチメントに利用（利用には別途 API キーが必要）。

以上が、本リポジトリの初回リリース（0.1.0）の主な内容です。今後のリリースでは上記 Known Issues の改善や拡張（銘柄別 lot_size、価格フォールバック、より効率的なパーセンタイル計算など）を予定しています。