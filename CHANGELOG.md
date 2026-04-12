CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
日付はコードの最終更新を推測して 2026-04-12 を使用しています。明示が必要な場合は適宜調整してください。

Unreleased
----------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 基本アプリケーション構成を実装
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite DB を使用する（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory を通じて本番/モックのブローカークライアントを切替え、ExecutionEngine を組み立ててセッションを実行。
    - RiskManager のデフォルト設定（max_position_pct や rate_limit 等）を組み込み、broker.get_available_cash() を初期ポートフォリオ値に使用。
  - システム監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）処理は実行環境にかかわらず本番の sqlite_path を使用して記録。
- 設定管理
  - 環境変数／.env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local をロード（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複数のプロパティ（DB パス、PID ファイルパス、閾値、PAPER_FILL_MODE 等）を Settings クラスとして提供。
    - 設定値の検証（KABUSYS_ENV の許容値や LOG_LEVEL、PAPER_FILL_MODE の有効値など）を実装。
- ポートフォリオ構築ライブラリ（src/kabusys/portfolio）
  - 銘柄選定および重み計算: select_candidates, calc_equal_weights, calc_score_weights。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier。
  - 株数計算・リスク制限: calc_position_sizes（単元株丸め、per-stock 上限、aggregate cap スケーリング、cost_buffer を考慮した保守的見積り）。
- 研究（Research）機能（src/kabusys/research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns, calc_ic（スピアマンのランク相関）、factor_summary、rank、および zscore_normalize のエクスポート。
- ニュース NLP スコアリング（AI）機能（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いたニュース記事センチメントスコア算出と ai_scores テーブルへの書き込み機能を実装。
  - 処理フロー: 時間ウィンドウ計算、記事集約、バッチ送信（最大 20 銘柄/回）、リトライ（429/ネットワーク/5xx 用の指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分更新（DELETE/INSERT）による部分失敗耐性。
  - API キー未設定時に明示的な ValueError を送出。
- ツール
  - Paper Trading 検証レポート生成 CLI ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率・注文成功率・送信率・P95 レイテンシを算出し PASS/FAIL を判定する簡易レポートを出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。
- ユーティリティ
  - プロセス優先度／CPU affinity 制御ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) で最初の N コアにピンニング可能（引数 None の場合は無設定）。
    - 権限不足や未対応 OS を検出して警告出力しフォールバック。

Changed
- DB 関連の挙動
  - 監視（monitoring）用 DB は環境に依存せず常に Settings.sqlite_path を使用し記録（run_monitoring）。
  - 実行エンジンは paper_trading 環境時に paper_sqlite_path を使用して発注ログを本番 DB と分離（run_execution）。
- .env 読み込みの挙動
  - .env の読み込み順序は OS 環境 > .env.local > .env。既存 OS 環境は保護される（protected 引数）。
  - .env の行パーサは export プレフィックス、クォート、エスケープ、インラインコメントに対応。
- ログ・デフォルト設定
  - 各実行スクリプトで logging.basicConfig(level=logging.INFO) を呼び出して起動ログを標準化。
- 整合性向上
  - Monitoring の初期化で init_monitoring_db(sqlite_conn) を呼び出して監視テーブルの存在を保証（冪等）。
  - Paper verification ツールはテーブル未存在時に sqlite3.OperationalError を捕捉してデフォルト値でレポート生成を継続。

Fixed
- 環境変数パーサの堅牢化（src/kabusys/config.py）
  - クォート文字列内のバックスラッシュエスケープ処理、クォートなし行のコメント検出ロジックを実装し誤読を低減。
  - 空行やコメント行、export KEY=val 形式を正しく扱うよう改善。
- MONITOR_POLL_INTERVAL の入力検証（src/kabusys/run_monitoring.py）
  - 0 以下や非数値が設定された場合、ログ警告を出してデフォルト（60 秒）にフォールバック。time.sleep に渡せない値の回避。
- 各計算関数の欠損値安全対策
  - ファクター計算やボラティリティ計算において、ウィンドウ不足時に None を返すようにし、NULL 伝播や分母 0 を回避。
  - calc_score_weights: 全銘柄スコアが 0 の場合は等金額配分にフォールバックして警告を出力。
  - calc_position_sizes: 価格欠損（None / 0）の場合はスキップして不正発注を防止。
- News NLP の耐障害性
  - API リトライ、レスポンス検証、スコアクリップ、部分成功時の DB 保護（対象コードのみを置換）など、フェイルセーフを強化。

Known issues / Notes
- 一部 TODO / 将来改善点をコード内に記載
  - position_sizing: 銘柄単位の lot_size を stocks マスタで管理する拡張案が残っている。
  - apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価されブロックが外れるリスクに関する注記。
- AI モジュールは OpenAI API の利用に依存しており、API レート・コストや利用規約に注意が必要。
- set_process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告でスキップする設計。

ライセンス、貢献
- 本リポジトリの初版リリース（0.1.0）として、上記機能群を実装しました。今後はテストケースの追加、ドキュメント強化、エッジケースの補完、性能プロファイリングを予定しています。