# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

※この CHANGELOG は提供されたソースコードから実装内容を推測して作成しています。

### [Unreleased]
- 開発中 / 未リリースの変更はここに記載します。

---

### [0.1.0] - 2026-04-16
初回公開リリース

#### 追加
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として設定。

- 設定管理
  - 環境変数 / .env ファイル読み込み機構を提供（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export プレフィックス、クォート、エスケープ、コメントの扱いに対応した .env パーサを実装。
    - 必須変数未設定時に分かりやすいエラーメッセージを投げる _require() を提供。
    - 設定項目（J-Quants / kabu API / LINE / DuckDB/SQLite パス / Paper Trading 設定 / 監視閾値 / 環境種別 等）を Settings クラスでプロパティとして集約。

- 実行/監視エントリポイント
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - 監視用 DB 初期化（monitoring テーブル確保）を行い、SQLite（本番パス）および DuckDB に接続して SystemMonitor を利用。
    - 起動時にプロセス優先度を "high" に設定。

  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使い、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成と、ExecutionEngine の起動シーケンスを実装。
    - 停止フラグを検知するとエンジン停止処理を呼び出し安全に終了。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル管理（data/execution.pid）に対応。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークで上位 N を選択
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分（スコアが全て 0 の場合のフォールバックロジック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率に基づき新規候補を除外（"unknown" セクターは無視）
    - calc_regime_multiplier: "bull" / "neutral" / "bear" に基づく乗数（フォールバックの警告を含む）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の各配分方式対応
    - 単元株（lot_size）丸め、1銘柄上限・max_utilization、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り
    - スケールダウン時の残差配分ロジック（lot 単位で再配分）

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（一定行数未満は None）
    - calc_volatility: ATR20、ATR 比率、20日平均出来高、出来高比率
    - calc_value: latest raw_financials（report_date <= target）と株価を組み合わせて PER / ROE を算出
    - DuckDB を用いた SQL ベース実装で performance を考慮したスキャンレンジ
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズンの将来リターン（LEAD を利用）
    - calc_ic: スピアマン ランク相関（IC）計算（欠損・最小件数チェック）
    - factor_summary, rank: 統計サマリーとランク付けユーティリティ

- AI / ニュース NLP
  - ニュースセンチメント集約・スコアリング（src/kabusys/ai/news_nlp.py）
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC へ変換）
    - OpenAI（gpt-4o-mini）を用いたバッチスコアリング設計（最大 20 銘柄/リクエスト、JSON Mode を前提）
    - 返却スコアのクリッピング（±1.0）、429/5xx/ネットワーク断に対する指数バックオフリトライ、レスポンス検証
    - API キー指定（引数または OPENAI_API_KEY 環境変数）

- ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority(level): Windows / POSIX を吸収して nice / priority を設定、失敗時は警告してスキップ
    - set_cpu_affinity(cpu_count): 指定コア数に固定する機能（検証・例外ハンドリングあり）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを計算して標準出力へレポートを表示
    - P95 算出ユーティリティ、日付フィルタ、DB 存在チェック、テーブル未存在時の耐障害処理（OperationalError を捕捉してデフォルト値を使用）
    - コマンドライン引数 (--from, --to, --db) による期間/DB 指定

#### 変更
- なし（初回リリース）

#### 修正 / 安全性向上
- .env パーサの堅牢化（export プレフィックス、クォート文字列のエスケープ処理、インラインコメントの扱い）
- 空の P95 対応やテーブルが存在しない場合の耐障害処理を tools/paper_verification_report.py に追加
- 設定値検証の強化（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL の許容値チェック）
- 実行中の停止フラグ／PID 管理の導入により安全なシャットダウンを実現（run_monitoring / run_execution）

#### 既知の注意点 / TODO（ソース内コメントより抽出）
- price_map に価格欠損（0.0）がある場合、apply_sector_cap のエクスポージャーが過小見積りされる可能性がある。将来的に前日終値や取得原価をフォールバック価格として使用することを検討。
- position_sizing の lot_size は将来的に銘柄別に拡張する余地あり（stocks マスタ等）。
- news_nlp モジュールは OpenAI API のレスポンス形式/JSON の厳密な検証に依存しており、API 仕様変更時のフォールバック設計が必要。

---

メンテナンスやバグ修正の履歴は今後このファイルに追記してください。