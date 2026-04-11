Changelog
=========

すべての変更は「Keep a Changelog」形式に従い、日本語で記載します。

[0.1.0] - 2026-04-11
--------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 設定・環境変数の取り扱い（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロードする機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env ローダーは OS 環境変数を protected として上書きを制御し、.env.local は .env を上書き可能。
  - .env のパース実装を強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなしのコメント処理（# の前が空白またはタブのときのみコメント扱い）
  - Settings クラスを導入し、各種設定をプロパティとして提供（DBパス、APIトークン、閾値、環境判定等）。
  - 設定値のバリデーション:
    - KABUSYS_ENV は development / paper_trading / live のみ許可。
    - LOG_LEVEL は許可された値のみ許可。
    - PAPER_FILL_MODE の有効値チェック（instant / partial / never / reject）。
  - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や各種しきい値（CPU/MEM/DISK）等を読み取り可能。

- 実行エントリスクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite DB（data/paper_trading.db デフォルト）を使用して本番 DB と完全分離。
    - duckdb を併用して解析用 DB 接続を確立。
    - BrokerClientFactory を使ったブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下や非整数）はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（監視は常に本番 DB を監視する想定）。
    - 監視ループは例外を捕捉してログ出力し、継続する堅牢な設計。
    - KeyboardInterrupt を捕捉してクリーンに終了し、DB 接続を確実に閉じる。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームでのプロセス優先度設定を追加（Windows / POSIX の差分を吸収）。
  - set_process_priority(level: "high" | "normal" | "low") を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
  - set_cpu_affinity(cpu_count: int | None) を実装。指定された最初の N コアにプロセスを固定。値チェックとエラーハンドリングあり。

- ポートフォリオ構築関連（src/kabusys/portfolio/）
  - portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークは signal_rank 昇順で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存保有比率を算出し、上限超過セクターの新規候補を除外。sell_codes（当日売却予定）をエクスポージャー計算から除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームは 1.0 にフォールバックして警告。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。lot_size 単位で丸め、max_position_pct / max_utilization を考慮。aggregate cap 超過時はスケーリングし、残差（fractional）に基づき lot_size 単位で追加配分するロジックを実装。cost_buffer を考慮して保守的にコスト見積り。

- リサーチ / ファクター計算（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。必要なウィンドウ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時の扱いに注意。
    - calc_value: raw_financials から直近報告データを取得して PER / ROE を計算。価格・EPS の欠損・0 に対する保護あり。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons は正の整数かつ <=252 を検証。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なサンプル数（>=3）未満時は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出。丸め誤差を避けるため round(...,12) を用いる。

- AI 関連機能（src/kabusys/ai/）
  - news_nlp.py:
    - raw_news テーブルから銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を計算して ai_scores テーブルへ書き込むワークフローを実装。
    - バッチ処理: 最大 20 銘柄 / API コール、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - レート制限(429)・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（最大リトライ数の設定あり）。
    - レスポンスの堅牢なバリデーション: JSON パース、results 配列の存在、各要素に code/score があること、未知コード除外、スコア数値・有限値検査、スコアを ±1.0 にクリップ。
    - DB 書き込みは冪等に行う（BEGIN / DELETE（対象コードごと） / INSERT / COMMIT）。部分失敗時に他コードの既存スコアを消さない方針。
    - calc_news_window を提供し、JST ベースのニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を厳密に計算。
    - API 呼び出し関数はテストで差し替え可能に設計（_call_openai_api を抽象化）。
  - regime_detector.py:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（'bull'/'neutral'/'bear'）を判定する機能を実装。
    - raw_news からマクロキーワードでフィルタした記事を取得し、OpenAI でマクロセンチメントを取得（記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0）。
    - レジームスコア合成ロジックとしきい値（BULL/BEAR）に基づく分類、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のため、prices_daily クエリで target_date 未満のデータのみ使用。

Changed
- なし（初回リリース）

Fixed
- DuckDB 互換性考慮
  - DuckDB 0.10 の executemany に空リストを渡せない点への対処（duckdb executemany を呼ぶ前に params が空でないことを確認）。これにより ai_scores 書き込み処理が安定。

- OpenAI 応答の堅牢化
  - JSON mode でも前後に余分なテキストが混在するケースに備え、最外側の {} を抽出してパースを試みるフォールバックを追加。無効応答は警告ログを出してスキップ。

Security
- OpenAI API キー取り扱い
  - ai モジュールでは api_key 引数または環境変数 OPENAI_API_KEY を使う仕様。API キー未設定時は ValueError を発生させ安全に失敗させる。

Notes / Implementation details
- 「ルックアヘッドバイアス防止」の設計方針が各 AI / リサーチ処理に一貫して適用されている（datetime.today()/date.today() を直接参照しない、prices_daily のクエリで target_date の未来データを排除）。
- 多くの関数は副作用を持たない純粋関数として設計（ポートフォリオ関連、計算ロジック等）。DB 参照は明示的に conn を渡す設計。
- ロギングは標準 logging を利用。重要な異常は logger.warning / logger.exception で記録され、フェイルセーフで継続する設計が多い（監視ループ、AI 呼び出し等）。

今後の改善候補（README 等で検討）
- position_sizing の lot_size を銘柄別に拡張する（stocks マスタへの lot_size フィールド追加）。
- price_map の欠損価格（0.0）に対するフォールバック方法（前日終値や取得原価など）を改善してエクスポージャー評価の精度向上。
- OpenAI 呼び出しのメトリクス収集・ログ詳細化（API レイテンシー、失敗割合、再試行回数など）。
- テスト用のモックやインテグレーションテスト（DuckDB テストデータ、OpenAI モック）を整備。

--- 

開発者・利用者向け注記:
- まず .env.example を参考に .env を作成してから起動してください。
- 自動 .env ロードを無効にしたいユニットテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。