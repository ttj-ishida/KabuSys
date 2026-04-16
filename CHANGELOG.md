# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

全般: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-16

初回リリース。本リポジトリの主要コンポーネントを実装・公開しました。以下はコードベースから推測してまとめた主要な追加・変更点です。

### Added
- 基本バージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0"
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、本番 DB と完全分離する挙動を想定
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行用 PID ファイル管理
    - ExecutionEngine をスレッドで実行し停止フラグを監視するループ実装
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は環境に依らず本番 sqlite_path を使用（監視データは本番 DB に蓄積）
    - 停止フラグ検知でループ終了、例外発生時はログ出力後に次ポーリングへ継続
- 設定・環境変数管理
  - Settings クラスを実装（src/kabusys/config.py）
    - .env/.env.local の自動読み込み機能（OS 環境変数の保護・上書きルールを実装）
    - export KEY=val、クォート付き値、インラインコメント処理などをサポートする .env パーサ実装
    - 各種必須/選択設定プロパティ（J-Quants / kabu API / DB パス / 監視閾値 / 環境種別 等）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート
- ユーティリティ
  - プロセス優先度・CPU affinity 制御ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX(Linux, Darwin, FreeBSD) を吸収する実装
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供
    - 権限不足や未対応 OS の場合は安全に警告を出してスキップ
- Portfolio 構築ライブラリ（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・同点 tie-breaker 実装）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合に等配分へフォールバック）
  - リスク制約（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター別上限チェック、売却予定銘柄の除外対応、"unknown" セクターの扱い）
    - calc_regime_multiplier（market レジームに応じた投下資金乗数: bull/neutral/bear のマップ、未知レジームはフォールバック）
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算（risk_based / equal / score）
    - 単元株（lot_size）丸め、per-position 上限 / aggregate cap（available_cash）によるスケールダウン
    - cost_buffer を用いた保守的なコスト見積もり、余剰キャッシュを用いた再配分ロジック実装
  - モジュールエクスポート（src/kabusys/portfolio/__init__.py）
- Research（因子・特徴量）モジュール（DuckDB を想定）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、ATR 比率、20日平均売買代金、出来高比率）
    - calc_value（PER, ROE を raw_financials と prices_daily から算出）
    - SQL（DuckDB）ウィンドウ関数を多用した効率的実装
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（任意ホライズンの将来リターン一括取得）
    - calc_ic（スピアマンランク相関による IC 計算、レコード不足時は None）
    - factor_summary / rank（基本統計量・ランク付けユーティリティ）
  - research パッケージの公開 API を整備（src/kabusys/research/__init__.py）
- AI ニュース NLP（草案実装）
  - src/kabusys/ai/news_nlp.py にニュース記事を OpenAI API でスコア化するロジックを追加
    - タイムウィンドウ算出（前日 15:00 JST ～ 当日 08:30 JST の記事を対象）
    - 銘柄ごとの記事集約、トークン肥大化対策（最大記事数・最大文字数）
    - バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフでのリトライ方針
    - レスポンスバリデーション・スコアクリップ（±1.0）、DuckDB へ差分上書き（部分失敗耐性）
    - 注: ファイル末尾が切れているため一部実装は継続中の模様
- 運用ツール
  - Paper Trading 検証レポート CLI（src/kabusys/tools/paper_verification_report.py）
    - 指標（稼働率 / 成功率 / 送信率 / P95 レイテンシ）を集計して PASS/FAIL 判定
    - 日付フィルタ（--from / --to）と DB パス指定 (--db) をサポート
    - デフォルト DB: data/paper_trading.db、しきい値定数をソース内に明示
    - レポートは標準出力に整形して出力

### Changed
- DB 周りの扱いを明確化
  - 監視（monitoring）系は環境に関わらずデフォルト sqlite_path（本番）を使用する設計と明記
  - Paper Trading 実行は専用 sqlite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
- 環境変数ロードの振る舞い
  - .env/.env.local の読み込み順序と上書きルール（OS 環境変数の保護）を定義
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止を追加
- ロギング・安全停止
  - 起動スクリプトは起動時にプロセス優先度を設定し、停止フラグ/PID 管理など運用上の安全策を導入
  - 例外時はログを記録してループ継続するフェイルセーフな監視ループ

### Fixed / Hardening
- .env パーサの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ処理、インラインコメント判定の改善
  - 無効行や不正な行に対しては無視する実装（読み込み失敗時は警告）
- Settings プロパティでの入力検証強化
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の許容値チェックと明確なエラーメッセージ
- process_priority の例外ハンドリング（権限不足や未対応 OS を安全に無視してログ化）
- position_sizing 等でのゼロ/欠損価格に対する guard（価格欠損時はスキップしてログ出力）

### Notes / オペレーション上の注意
- 停止フラグ:
  - プロジェクトルートの data/stop_requested.flag を作成すると run_execution / run_monitoring は検出して安全停止します。
- PID / Kill フラグ:
  - pid_file_path / kill_flag_path 等は Settings 経由で環境変数により上書き可能。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは mock ブローカー／paper DB を使用する想定（run_execution の docstring）
- OpenAI API:
  - news_nlp.score_news は API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。API 呼び出しは失敗時にスキップして処理継続する設計。
- DuckDB:
  - 研究向けの集計／ファクター計算は DuckDB 接続を受け取り SQL で完結する実装のため、大量データを効率的に処理可能。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注: 本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のコミットログやリリースノートと差異がある場合があります。補足・修正したい点があれば該当箇所（ファイル・機能）を指定してください。