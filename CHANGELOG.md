# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、ソースコードから推測できる機能追加・変更点・修正点をまとめたものです。

現在のバージョン: 0.1.0

## [Unreleased]

### Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止判定に data/stop_requested.flag を使用。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する実装。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、本番 DB と分離。
  - BrokerClientFactory 経由でブローカークライアントを生成。
  - ExecutionEngine をバックグラウンドスレッドで起動し、停止フラグ（data/stop_requested.flag）を監視。
  - 起動時にプロセス優先度を設定（High）。
- config.py: 環境変数／.env 管理を強化。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
  - .env ファイル読み込み実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
  - .env/.env.local の読み込み優先順位と OS 環境変数保護（protected）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスに各種プロパティを追加（duckdb/sqlite/paper_sqlite/paper_fill_mode 等）。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証を追加。
- portfolio パッケージ（銘柄選定・配分・リスク調整・株数決定）
  - portfolio_builder.py: select_candidates、calc_equal_weights、calc_score_weights を追加。
    - score が全て 0 の場合に警告を出して等金額配分へフォールバック。
  - risk_adjustment.py: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジーム乗数）を追加。
    - unknown セクターはセクター上限の制限を適用しない挙動。
    - レジームマップ（bull/neutral/bear）とフォールバックの挙動を定義。
  - position_sizing.py: calc_position_sizes（単元株丸め、risk_based / equal / score の配分アルゴリズム、aggregate cap のスケーリング、cost_buffer を使った保守的見積り）を追加。
    - lot_size（単元）対応、価格欠損時のスキップ、利用可能現金超過時のスケールダウンと再配分ロジックを実装。
- research パッケージ（ファクター計算・解析）
  - factor_research.py: calc_momentum、calc_volatility、calc_value を追加（DuckDB を使った SQL ベース実装）。
    - momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - value: raw_financials と prices_daily を結合して PER/ROE を計算。
  - feature_exploration.py: calc_forward_returns、calc_ic（Spearman ランク相関による IC）、factor_summary、rank を追加。
    - forward returns は複数ホライズンを同時に取得する最適化クエリを実装。
    - rank は同順位を平均ランクで処理する実装（丸めによる ties 対応）。
- tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
  - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。
  - 日付フィルタ（--from / --to）対応、DB パス指定オプション（--db / 環境変数）対応。
  - P95 の計算、各クエリに対する OperationalError のフェイルセーフ処理を実装。
- ai/news_nlp.py: ニュース NLP スコアリングモジュールを追加（OpenAI API 経由）。
  - 対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
  - バッチ送信、レスポンスバリデーション、スコア ±1.0 のクリップ、リトライ（429・ネットワーク・5xx に対する指数バックオフ）等の仕様を記載。
  - DuckDB の raw_news / news_symbols / ai_scores を参照してスコアを更新（部分更新で他コードの既存スコアを保護）。
- utils/process_priority.py: プロセス優先度・CPU affinity ユーティリティを追加。
  - set_process_priority(level) で Windows / POSIX（Linux, Darwin, FreeBSD）に対応。
  - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン留め可能（失敗時は警告でスキップ）。
  - psutil の例外（AccessDenied 等）を捕捉して安全にフォールバック。
- パッケージ初期化・メタデータ
  - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を追加。
  - research/__init__.py で提供 API を整理してエクスポート。

### Changed
- DB 周りの運用方針を明確化。
  - run_monitoring は常に production の sqlite_path（デフォルト data/monitoring.db）を読む設計で、環境変数 KABUSYS_ENV に依存しない旨を明記。
  - run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を利用するよう分離。
- .env ローダの挙動整理。
  - .env の読み込み順を明確化（OS 環境 > .env.local > .env）。
  - override/protected の概念を導入して OS 環境の保護を実現。

### Fixed
- 環境変数パースに関する耐性向上。
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
- position_sizing のスケーリングロジックで残差配分の再帰性・安定性を考慮した実装に改善（lot_size 単位での追加配分、上限チェック）。

### Security
- API キー（OpenAI）取得時に明示的なチェックを追加。未設定時は ValueError を送出して失敗を早期に検出。

---

## [0.1.0] - 2026-04-16

最初の公開リリース。上記の主要機能群を含む初版。
- 自動売買エンジンのコア（ExecutionEngine 起動フロー、OrderManager / RiskManager / Reconciler の組立て）
- 監視コンポーネント（SystemMonitor 起動スクリプト、monitoring DB 初期化ユーティリティ）
- ポートフォリオ構築ライブラリ（選定・重み付け・レジーム乗数・セクター上限・株数決定）
- リサーチ用ファクタ計算（Momentum / Volatility / Value）と解析ユーティリティ（forward returns / IC / summary）
- Paper Trading 用検証レポートツール
- ニュース NLP スコアリング（OpenAI 経由。バッチ処理・リトライ・出力検証仕様）
- 環境設定管理（.env ローダ、Settings クラスによる環境変数ラッパー）
- プロセス優先度/CPU affinity 設定ユーティリティ

注: 一部のモジュール（ai/news_nlp.py など）は外部 API や DB スキーマに依存します。実運用前に環境変数設定（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）と DB スキーマ（prices_daily, raw_financials, raw_news 等）が整っていることを確認してください。

---

今後の予定（未確定）
- ai/news_nlp の完全実装（ファイル末尾の未完部分の実装完了、エラーハンドリング強化）。
- 銘柄ごと単元情報（lot_size）をマスタで管理する拡張。
- position_sizing の追加テストと境界ケースの微調整。
- DuckDB のバルク書き込み運用時のトランザクション最適化と部分ロールバック戦略。

---
参考: 上記はソースコードから推測して作成した変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の Git 履歴や追加のコンテキストに基づいて修正します。