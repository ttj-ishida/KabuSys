# CHANGELOG

すべての重要な変更履歴を記載します。フォーマットは「Keep a Changelog」に準拠します。

当プロジェクトはセマンティックバージョニングを採用しています。  

## [0.1.0] - 2026-04-17
初回リリース

### 追加 (Added)
- パッケージ初期実装を追加。
  - バージョン: kabusys.__version__ = 0.1.0

- 実行 / 監視用エントリポイントスクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - process priority を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行と停止フラグ検知を実装。
    - 停止フラグファイルを用いた安全なシャットダウンをサポート。
    - デフォルトの RiskConfig 値（max_position_pct 等）を設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を見る設計）。
    - 停止フラグファイルを検知してループを終了する仕組みを実装。

- 環境設定・読み込みユーティリティを追加。
  - config.py
    - .env / .env.local の自動ロード機能（プロジェクトルート自動検出: .git または pyproject.toml）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは以下をサポート:
      - 空行・コメント行（先頭 #）の無視
      - export KEY=val 形式
      - クォート（' または "）とバックスラッシュエスケープ対応
      - インラインコメントの取り扱い（クォートの有無に応じた処理）
    - 環境設定クラス Settings を提供し、主要な設定プロパティをラップ（J-Quants / kabu API トークン、DB パス、paper_trading 関連、監視閾値、KABUSYS_ENV 確認など）。
    - 設定バリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）。
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレーク: signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は警告と等配分フォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を超える場合に候補を除外（unknown セクターは除外対象にならない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告の上 1.0 をフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を考慮した保守的見積りを実装。
    - risk_based 方式は (portfolio_value * risk_pct) / (price * stop_loss_pct) による算出を実装。
  - portfolio パッケージの __all__ を定義。

- 研究（Research）モジュールを追加（DuckDB を用いたファクター計算 / 統計）。
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。データ不足時は None を返す。
    - calc_volatility: ATR20、相対ATR、平均売買代金、出来高比率を計算。NULL 伝播に気を付けた実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の財務データを target_date 以前の最新として取得）。
  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（horizons）を一括クエリで計算。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量計算（count/mean/std/min/max/median）。
  - research/__init__.py で公開関数を統合。

- AI ニュース NLP スコアリングモジュールを追加（OpenAI 経由）。
  - ai/news_nlp.py
    - raw_news テーブルから対象時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を計算して記事を集約。
    - OpenAI (gpt-4o-mini) を JSON Mode でバッチ（最大 _BATCH_SIZE=20）送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を取得して ai_scores テーブルへ書き込むフローを実装（レスポンス検証、スコアクリップ、429/ネットワーク/5xx の指数バックオフリトライなど）。
    - トークン肥大化対策（1銘柄あたり _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK 制限）を実装。
    - API キー未設定時は ValueError を送出。
    - （設計方針として）ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない。

- 運用ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト（コマンドライン実行可能）。
    - デフォルト DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で上書き可）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを集計して出力。
    - PASS/FAIL 判定の閾値を設定（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200 ms）。
    - 日付フィルタ (--from / --to) をサポート。DB テーブル欠如時のフォールトトレランスあり。

- ユーティリティを追加。
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。権限不足時は警告ログを出力してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定。None の場合は何もしない。バリデーションあり。
    - クロスプラットフォーム差分のラッピング（Windows 用優先度定数 / POSIX 用 nice 値）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制約 / 注意事項 (Notes)
- run_monitoring は監視用の sqlite DB を常に settings.sqlite_path（本番）で開きます。テスト環境で監視を分離したい場合は設定を見直してください。
- config の自動 .env ロードはプロジェクトルート検出に依存します。配布後（プロジェクトルートが見つからない）場合は自動ロードがスキップされます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- portfolio/position_sizing の lot_size は現状グローバル共通の固定値（デフォルト 100）を想定しています。将来的な拡張で銘柄別単元対応を検討中。
- ai/news_nlp の実行は OpenAI API 利用料が発生します。API キー設定と利用にご注意ください。
- news_nlp のファイルは大きいため（本リリースのソースは一部長文実装）、API のタイムアウトやレート制限に対する挙動はログを確認してください。

### マイグレーション / アップグレード情報
- 環境変数追加 / 仕様:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。正の整数を指定。無効値は 60 秒にフォールバック。
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite ファイルパス（run_execution の paper_trading モードと tools/paper_verification_report が参照）。
  - PAPER_FILL_MODE: paper trading の MockBrokerClient の fill 動作（instant|partial|never|reject）。無効値は ValueError。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込み無効化（1 を設定）。
  - OPENAI_API_KEY: ai/news_nlp の API キー（score_news 実行時に引数で指定しない場合に参照）。
  - KILL_FLAG_PATH, PID_FILE_PATH 等は Settings によりデフォルトが設定されています。カスタマイズは環境変数で可能です。

---

今後の予定（予定事項、実装案）:
- portfolio の lot_size を銘柄マスタに基づく可変化対応。
- news_nlp の部分失敗時のリトライ/ロールフォワード戦略の強化。
- ExecutionEngine / Monitoring のメトリクス収集と可視化強化。

もし特定の変更点について詳細な説明や、追加のリリースノート（例: 各関数の使用例、API 契約、環境構築手順）を希望される場合はお知らせください。