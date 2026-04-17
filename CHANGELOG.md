# CHANGELOG

すべての重要な変更を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載します。  
このファイルはコードベースの内容から推測して作成しています。

全般的なルール:
- バージョンはパッケージ内の __version__ を基準にしています (src/kabusys/__init__.py: 0.1.0)。
- 日付は本ファイル作成時点 (2026-04-17) を使用しています。

## [Unreleased]
- 今後のリリースで追加・改善予定の項目（現時点では未指定）。

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成
  - パッケージ初期バージョンを導入 (kabusys v0.1.0)。
  - モジュールエクスポート設定を追加 (kabusys/__init__.py)。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - カスタム .env パーサー（コメント・クォート・export 形式に対応）。
  - 必須環境変数検査ユーティリティ _require。
  - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視閾値 /環境種別 など）。
  - 自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
- 実行用スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine をスレッドで起動・監視するフローを実装。
    - paper_trading 環境では paper 用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てと実行。
    - 停止フラグ（data/stop_requested.flag）検出で安全停止。
    - PID ファイル管理（data/execution.pid）。
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor を定期的にポーリングして system_status 等を記録。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用途では環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出で安全にループ終了。
- 監視 DB 初期化ユーティリティ (monitoring_db の初期化呼び出しを各起動で実行)
- プロセス優先度 / CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - Windows / POSIX(Linux / macOS / FreeBSD) の差分を吸収してプロセス優先度設定。
  - CPU affinity を最初の N コアに固定する機能。
  - 権限不足や未サポート環境でのフォールバックとログ出力。
- Portfolio 構築ユーティリティ (src/kabusys/portfolio)
  - 候補選定と重み計算 (portfolio_builder.py)
    - select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合の等配フォールバックを実装）。
  - セクター制約・レジーム乗数 (risk_adjustment.py)
    - apply_sector_cap（既存保有比率に基づくセクター除外ロジック、unknown セクターは除外しない挙動）。
    - calc_regime_multiplier（bull/neutral/bear に対する乗数マップ、未知レジームはフォールバック）。
  - ポジションサイジング (position_sizing.py)
    - risk_based / equal / score の allocation_method をサポート。
    - lot_size 単位で丸め、per-position 上限・aggregate cap を考慮したスケーリング実装。
    - cost_buffer による保守的コスト見積りと残差分配ロジック。
- リサーチ関連 (src/kabusys/research)
  - ファクター計算 (research/factor_research.py)
    - calc_momentum, calc_volatility, calc_value（DuckDB を用いた SQL + Python 実装）。
    - MOMENTUM/ATR/MA 等の仕様とウィンドウ設定が定義済み。
  - 特徴量探索 (research/feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ランク関数、統計サマリー (factor_summary) の実装。
    - pandas 等の外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージの公開 API を整備（zscore_normalize と共に再公開）。
- AI ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - OpenAI API (gpt-4o-mini) を用いたニュースのセンチメントスコア算出フローを実装（バッチ送信・リトライ・レスポンス検証・スコアクリップ）。
  - タイムウィンドウ計算（JST→UTC の変換）、記事集約、1 銘柄当たり文字数・記事数上限の実装。
  - API キーの検証（未設定時は ValueError）。
  - フェイルセーフ設計（API 失敗時にスキップして継続）。
- ツール
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
    - コマンドラインから期間指定で paper_trading DB を解析し、稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL を判定。
    - P95 計算・閾値（稼働率/成功率/送信率/P95 レイテンシ）を定義。
    - DB が存在しない場合やテーブル欠如時の耐障害性を考慮（OperationalError を捕捉して安全に N/A を出力）。

### Changed
- 環境変数読み込みの設計
  - OS 環境変数を保護するため .env 読み込み時に protected set を扱い、.env.local を上書き可能にした。
  - 自動ロードはプロジェクトルートが検出できない場合にスキップ。
- DB ハンドリング
  - monitoring 用 DB 初期化は冪等な init_monitoring_db を使用して起動時に保証。
  - paper_trading 環境用に SQLite パスを分離（settings.paper_sqlite_path）。
- モニタリングと実行の挙動
  - 監視ループは MONITOR_POLL_INTERVAL を用いた可変インターバルに対応。不正値はデフォルトにフォールバックして警告ログを出力。
  - 停止フラグ（data/stop_requested.flag）による外部停止をサポート（監視・実行ともに）。
  - 実行開始時にプロセス優先度を先に設定する設計に変更（set_process_priority を最初に呼び出し）。

### Fixed / Robustness
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ処理とインラインコメント無視ロジックを実装。
  - export KEY=val 形式の対応と不正行のスキップ。
- 研究・統計処理の安定性向上
  - ファクター計算やボラティリティ計算でウィンドウ内のデータ不足時に None を返すなど NULL/欠損値に対する安全な処理を実装。
  - calc_forward_returns: horizons の入力検証（正の整数かつ最大 252）を追加。
  - rank / calc_ic / factor_summary: None と非有限値を除外する堅牢化。
- OpenAI 呼び出し周りの回復力
  - API 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライと最大リトライ回数制限を導入。
  - レスポンス検証とスコアクリップにより DB 書き込み前のデータ整合性を担保。
- ポジションサイジングの数値処理
  - lot_size 単位での切り捨て・端数配分ロジックを実装し、aggregate cap を越えた場合のスケールダウン処理を追加。
  - price が欠損（0.0）の場合はログ出力してスキップする保護。

### Security
- OpenAI API キーは環境変数または引数で明示的に供給する必要がある旨を明示。未設定時は例外を投げることで意図しない公開を防止。
- .env 自動読み込みは OS 環境変数を上書きしない既定挙動（必要な場合のみ明示的に上書き可能）。

### Known limitations / Notes
- news_nlp.py はファイル末尾で途中切れ（コード断片あり）であるため、記事集約フェーズ以降の完全な実装は要確認（この changelog は現状のコードから推測して記載）。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格欠損時のフォールバック）。
- DuckDB に対する executemany 等の挙動はバージョン依存の注意点があるため、空パラメータ集合を渡さない防御ロジックを設計に盛り込むべき箇所がある。
- 実行環境での権限不足によりプロセス優先度や CPU affinity の設定が失敗する可能性がある（ログで警告してスキップする実装）。

---

（補記）この CHANGELOG はコードベースの現状（ファイル内容）からの推測に基づき作成しています。実際のリリースノートとして使用する場合は、開発履歴（Git コミットログ、タグ付け）に基づいて調整してください。