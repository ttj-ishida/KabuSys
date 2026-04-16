# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
リリース日付はスナップショット（このコードベース取得日: 2026-04-16）に基づきます。

## [Unreleased]

- ドキュメントや内部実装の追加・微調整（スナップショット以降の差分に相当する変更はここに記載します）。

---

## [0.1.0] - 2026-04-16

初回公開相当の機能セットをまとめたリリースです。本リリースは自動売買エンジンの主要コンポーネント（実行・監視・ポートフォリオ構築・リサーチ・ニュースNLP 等）を含みます。

### 追加 (Added)
- 実行・監視
  - run_execution.py: ExecutionEngine を起動する CLI エントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用し、本番 DB と分離して動作。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - 実行中の PID 管理（data/execution.pid）、外部停止フラグ（data/stop_requested.flag）に対応。
    - スレッドで engine.run_session をデーモン実行し、停止フラグ検知で安全停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計（監視 DB は一貫して本番 DB を参照）。
    - 停止フラグ検知によるループ終了と例外ハンドリングを実装。

- 設定管理
  - config.py: 環境変数/.env 自動読み込み機構を実装。
    - プロジェクトルートを .git または pyproject.toml を手がかりに自動検出して .env/.env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env パーサは export 形式やクォート・エスケープ、インラインコメントを適切に処理。
    - 必須変数取得ヘルパ（_require）と Settings クラスを提供（各種設定プロパティ、バリデーション含む）。
    - 設定項目（例）：DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE / PID_FILE_PATH / 各種閾値 / KABUSYS_ENV / LOG_LEVEL 等。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - select_candidates: BUYシグナルをスコア降順で選出（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等額配分 / スコア加重配分（全スコアが0の場合は等配分フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各割当方式を実装。lot_size 単位で切り上げ・切り捨て、aggregate cap によるスケールダウン処理を実装。
    - コストバッファ(cost_buffer) の導入によりスリッページ・手数料を保守的に見積もる。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクターエクスポージャー計算と候補の除外）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に基づく投下資金乗数を提供。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200乖離の計算（DuckDB SQL 実装）。
    - calc_volatility: ATR20、相対ATR、平均売買代金、出来高比率の計算。
    - calc_value: raw_financials に基づく PER / ROE の計算（target_date 以前の最新財務データを参照）。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得するクエリ。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary, rank: ファクターの統計要約とランク関数を提供。
  - research/__init__.py に必要エクスポートをまとめる。

- ニュースNLP（AI）
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルへ書き込むための主要ロジックを実装。
    - ニュース収集ウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 時刻）。
    - 銘柄ごとに記事を集約し、文字数・記事数上限を設けてトークン肥大を抑制。
    - バッチ処理（最大 20 銘柄/コール）、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）による安全書き込み方針。
    - （注）スナップショットでは score_news の一部が途中で切れている部分あり（実装継続の余地）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定（high/normal/low）。
    - set_cpu_affinity: カレントプロセスを先頭Nコアにピン留めするユーティリティ（例外処理・権限不足の安全ハンドリングあり）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ(P95) 等を集計し PASS/FAIL 判定を出力。
    - 複数閾値（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）を用いた自動判定を実装。

- パッケージ初期化
  - kabusys/__init__.py にバージョン情報を設定（__version__="0.1.0"）および主要サブパッケージを __all__ に登録。

### 変更 (Changed)
- DB 周りの挙動を明確化
  - 監視(run_monitoring) は常に本番 sqlite_path を使用（監視データの一貫性確保のため）。一方、実行(run_execution) は paper_trading 環境で専用の paper_sqlite_path を使用して本番 DB と完全分離。
- .env ロードの優先順位
  - OS 環境 > .env.local > .env の順で読み込み。OS 環境の既存キーは protected され .env による上書きを防止。
- 環境変数パースの堅牢化
  - export 形式・クォートされた値・エスケープシーケンス・インラインコメントを正しく処理するよう改善。
- position_sizing のスケーリングロジック
  - aggregate cap 超過時のスケールダウンアルゴリズムを導入。端数の再配分を残差（fractional_remainder）順に lot_size 単位で割り当てる処理を追加。

### 修正 (Fixed)
- 環境変数バリデーションの強化
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）を実装し、不正値は ValueError。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを追加。
  - _get_poll_interval: MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してログ警告の上デフォルトにフォールバック。
- 安全な DB 初期化
  - init_monitoring_db を起動時に呼び出し、監視テーブルが存在することを保証（冪等）。
- OpenAI 呼び出し関連（ニュースNLP）
  - リトライ・エラーハンドリング・レスポンス検証・スコアクリッピングなどのフェイルセーフを導入し、API 失敗時も他処理を阻害しない設計に。

### 既知の注意点 (Known issues / Notes)
- ai/news_nlp.py の score_news 関数はスナップショットで途中までしか収録されておらず、完全実装は別途続行が必要な箇所があります。CLI/書き込みロジックは設計で示されていますが、最終的なファイル入出力部分はスナップショットの状態に依存します。
- position_sizing の価格フォールバックは TODO コメントあり（価格欠損時の過少見積りリスク）。将来的に前日終値や取得原価等のフォールバックを想定。
- set_process_priority / set_cpu_affinity は権限不足や未サポート環境においてログ警告を出して処理をスキップします（安全策）。

### 互換性 / Breaking Changes
- 本スナップショットは初版リリースに相当するため、特に既存の後方互換性破壊の報告はありません。ただし、環境変数名・デフォルトパス（data/*.db 等）を前提とした運用を想定しています。運用環境では .env や環境変数の整備をお願いします。

---

メンテナンスや今後の作業候補:
- ai/news_nlp.py の未完部分の実装完了と統合テスト。
- position_sizing の価格欠損対応（フォールバック価格）実装。
- 単体テスト・統合テストの整備（特に DB・API 周りのモック化）。
- ドキュメント（README / Deployment 手順 / 環境変数リファレンス）の整備。