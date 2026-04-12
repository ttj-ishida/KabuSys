CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- Unreleased セクションは将来の変更を示します。
- 各バージョンには日付とカテゴリ（Added / Changed / Fixed / Removed / Security）を付記しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-12

### Added
- パッケージ初期リリース。
- 基本設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
  - export KEY=val 形式やクォート／エスケープ、行内コメントに対応した .env パーサを実装。
  - 環境変数の保護（OS 環境変数を上書きしない挙動）と自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティ（DB パス、API トークン、PID / KILL フラグパス、モニタ閾値、環境判定など）を提供。
- 実行エントリスクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用して本番 DB と分離して実行可能。
    - Execution に必要な OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てを実装。
    - duckdb 接続のサポート。
- 監視エントリスクリプトを追加。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一元化）。
    - ループ内で例外を捕捉してログ出力後に継続するフェイルセーフ実装。
- ポートフォリオ構成ライブラリを追加（src/kabusys/portfolio/*）。
  - 銘柄選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights（score が全て 0 の場合は等金額配分にフォールバック）。
  - セクター集中リスク制御: apply_sector_cap（売却予定銘柄の除外、unknown セクターは上限適用除外）。
  - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に応答、未知のレジームは警告して 1.0 でフォールバック）。
  - 株数決定ロジック: calc_position_sizes（risk_based / equal / score の allocation_method をサポート、lot_size 単位丸め、aggregate cap のスケーリングと端数配分ロジックを実装）。
- 研究／リサーチモジュールを追加（src/kabusys/research/*）。
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB の prices_daily / raw_financials を利用）。
  - 特徴量探索: calc_forward_returns, calc_ic（Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median の算出）。
  - パフォーマンスと欠損値への配慮をした SQL ベース実装。
- AI ニュース NLP モジュールを追加（src/kabusys/ai/news_nlp.py）。
  - raw_news と news_symbols を集約して OpenAI API（gpt-4o-mini）でセンチメントスコアを算出し ai_scores テーブルに書き込むワークフロー。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を実装。
  - バッチ処理（1 バッチ最大 20 銘柄）、記事文字数 / 記事数トリム、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによるリトライ（429/5xx/ネットワーク系）などの堅牢化を実装。
  - API キー未設定時にエラーを返す明示的な検証。
  - API レスポンスの基本バリデーションと部分成功時のテーブル置換方針（部分失敗でも既存スコアを保護）。
- モニタ／ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - Paper Trading 用検証レポートを生成する CLI ツール。
  - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標計算と PASS/FAIL 判定（デフォルト基準値を実装）。
  - --from / --to / --db オプションをサポートし、日付フィルタや DB パスを指定可能。
  - DB 存在チェックやテーブル未作成時のフェールセーフ処理を実装。
- ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX の違いを吸収してプロセス優先度を設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
  - 権限不足や非対応プラットフォームでの安全なフォールバックとログ出力を実装。
- パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 各モジュールの __all__ エクスポートを整備（portfolio, research 等）。

### Changed
- 初期リリースのため該当なし（最初の機能群の追加）。

### Fixed / Hardened
- 設定・環境変数のパースで不正な値に対するフォールバックや警告を追加（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、LOG_LEVEL、KABUSYS_ENV など）。
- run_monitoring のポーリングループで check_once() の例外をキャッチしてループ継続するようにし、単発エラーで監視が停止しないように改善。
- DuckDB executemany 周りの注意（空パラメータ回避）をコメントに記載して安定性を確保。
- position_sizing の aggregate スケールダウン処理で端数配分（lot 単位）の安定化ロジックを実装（残余キャッシュでの追加配分、上限チェック）。
- .env 読み込みでファイル読み込み失敗時に warnings.warn を出力して処理継続するように安全化。

### Removed
- 該当なし

### Security
- OpenAI API キー未設定時に明示的にエラーを出す仕様により、無許可の API 呼び出しを防止。

注記・既知の制約
- news_nlp の OpenAI 呼び出しは API キーとネットワークに依存するため、外部呼び出し失敗時は該当チャンクをスキップして処理を継続する設計になっています（完全な再実行・ロールバック機構は未実装）。
- 一部の計算（セクター露出など）は price_map 中の価格欠損時に過少推計される可能性があり、将来的にフォールバック価格（前日終値等）を導入する予定です（コード内コメントあり）。
- 単元（lot_size）は現在グローバルに共通で扱われます。将来的に銘柄別 lot_map を受け取る拡張を想定しています。

---

開発・運用上の問い合わせや追加のリクエストがあればお知らせください。