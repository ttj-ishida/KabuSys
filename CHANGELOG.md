# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 全体
  - 新しいモジュール群を追加。
    - ポートフォリオ構築: kabusys.portfolio（銘柄選定、配分重み、リスク調整、株数決定）
    - リサーチ: kabusys.research（ファクター計算・前方リターン計算・IC/統計サマリ）
    - 実行/監視起動スクリプト: run_execution.py / run_monitoring.py
    - ユーティリティ: プロセス優先度/CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
    - Paper Trading 検証ツール: kabusys.tools.paper_verification_report（コマンドラインからレポート出力）
    - ニュース NLP スコアリング（OpenAI を用いた ai/news_nlp.py の骨組み）
    - 設定管理: robust な .env ロードと Settings クラス（kabusys.config）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視処理は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を参照する設計。
  - 停止フラグ（data/stop_requested.flag）を検知して安全に終了。
- run_execution.py
  - ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db など）へ分離して記録。
  - 実行中の PID 管理（data/execution.pid）と停止フラグ検知でのシャットダウンを実装。
  - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker など）を組み込み。
- kabusys.config
  - .env 自動読み込み機能を実装（優先順位: OS 環境 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーの強化:
    - `export KEY=...` 形式に対応
    - クォート内のバックスラッシュエスケープ処理
    - インラインコメントの適切な扱い
    - 読み込み時に OS の既存環境変数を保護（protected set）
  - Settings クラスに多数のプロパティを追加・検証（duckdb/sqlite パス、paper_trading の設定、監視しきい値、env/log_level 検証など）。
- ポートフォリオ（kabusys.portfolio）
  - select_candidates: スコア降順 + tie-breaker（signal_rank）で候補選出
  - calc_equal_weights / calc_score_weights: 重み計算（score 全て 0 の場合は等配分にフォールバック）
  - apply_sector_cap: 既存保有のセクター集中度超過時に当該セクターの新規候補を除外（unknown セクターは除外対象外）
  - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear）
  - calc_position_sizes: allocation_method に応じた株数計算（risk_based / equal / score）、単元株（lot_size）での丸め、aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算を実装（ウィンドウ欠損時の None 取り扱い含む）。
  - calc_forward_returns: 任意ホライズンの将来リターンを高速に取得（LEAD を利用）。
  - calc_ic / rank: スピアマン型 IC（ランク相関）計算およびランク化ユーティリティを実装（同順位は平均ランク）。
  - factor_summary: count/mean/std/min/max/median の統計サマリ生成。
- tools/paper_verification_report.py
  - Paper Trading の検証レポート生成スクリプトを追加。
  - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標算出と PASS/FAIL 判定を出力。
  - 指標の閾値（稼働率 99% など）を定義して自動判定。
- ai/news_nlp.py
  - OpenAI API（gpt-4o-mini）を用いたニュースセンチメントスコアリングの骨子を実装。
  - バッチ処理、スコアクリッピング（±1.0）、リトライ（429/5xx/ネットワーク障害／タイムアウトに対する指数バックオフ）、レスポンスの厳密な JSON バリデーション、部分更新（特定コードのみ置換）などの設計方針を反映。
  - タイムウィンドウ計算は JST ベースで実装され、ルックアヘッドバイアスが入らないよう datetime.today() を直接参照しない設計。
  - （注）提供されたスニペットは途中で切れているため、記事取得後の完全な処理（_fetch_articles の呼び出し以降）が断片的に含まれています。実運用では残りの実装（_fetch_articles 等）の確認・補完が必要。

### Changed
- ロギング / 初期化
  - run_execution.py, run_monitoring.py で起動時にプロセス優先度を "high" に設定する呼び出しを追加。プロセス優先度設定はプラットフォーム差分を吸収し、失敗時は警告でスキップする堅牢な実装に変更。
- DB 接続の扱い
  - 監視処理（run_monitoring）は KABUSYS_ENV に関係なく本番監視 DB（Settings.sqlite_path）を使用する方針に明示的に変更。
  - 実行処理（run_execution）は paper_trading 環境であれば専用 DB を使用して本番 DB と分離。

### Fixed
- 環境変数の数値パース耐性
  - MONITOR_POLL_INTERVAL のパースで 0 以下や不正な値が設定された場合にデフォルトへフォールバックして time.sleep の例外を回避するように修正。
- .env ロードの安全性
  - ファイル読み込み失敗時に警告を出すようにし、読み込みが失敗してもプロセスが停止しないよう耐性を強化。

### Deprecated
- なし

### Removed
- なし

### Security
- .env の自動ロードにおいて OS 環境変数を上書きしない既定動作とし、必要に応じて上書きする .env.local の利用を想定。OS 側の重要な環境変数保護を意図。

---

## [0.1.0] - Initial package metadata
- パッケージの初期バージョン情報を追加（kabusys.__init__.__version__ = "0.1.0"）。
- パッケージの公開に向けた最小メタ情報と __all__ を定義。

---

注:
- 提供されたコードスニペット内で ai/news_nlp.py の処理が途中で途切れており、実際に動作させるには残りの実装（記事取得や _fetch_articles の実装、DB 書き込みロジックの最終化）が必要です。実運用に投入する前に該当部分の完全なレビューとテストを推奨します。
- run_monitoring の「監視は常に本番 DB を利用する」挙動は運用ポリシーにより意図的な仕様と思われますが、環境分離を期待するワークフロー（たとえばテスト/開発環境での監視）では注意が必要です。必要であれば挙動変更（KABUSYS_ENV に依存する等）を検討してください。