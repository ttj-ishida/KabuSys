CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
公開日付は本リリースに対応するスナップショット日です。

## [0.1.0] - 2026-04-09
初回リリース（初期実装）。以下の機能を実装しています。

### 追加
- 環境・設定管理
  - src/kabusys/config.py を追加。
    - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの自動検出は .git または pyproject.toml に基づく（配布後も CWD に依存しない挙動）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 環境変数パースは export 構文、クォート、エスケープ、インラインコメント等に対応。
    - 必須パラメータ取得用の _require と Settings クラスを提供。主要な設定キーをプロパティで公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 参照用のプロパティは無いが OpenAI は環境変数から取得する慣習を採用）。
    - 各種デフォルト値とバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルからスコア降順で候補選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき、単元株丸め、per-position 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（手数料・スリッページ保守）を考慮して発注株数を計算。
    - risk_based: 損切り率・許容リスク率から株数算出。
    - aggregate cap 適用時に残差分を lot_size 単位で再配分するアルゴリズムを実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別既存保有比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（"bull"/"neutral"/"bear"、未知レジームは警告のうえフォールバック）。

- リサーチ（因子計算・特徴探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を DuckDB（prices_daily）で計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（欠損時は None 処理）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（最新の財務レコードを target_date 以前から取得）。
    - 設計上、DuckDB 接続を受け取り外部 API にはアクセスしない純粋関数群として実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（horizons の検証あり、デフォルト [1,5,21]）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクとするランク関数（丸めによる tie 検出漏れ対策あり）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー関数。
  - src/kabusys/research.__init__.py で主要関数を再公開。zscore_normalize は kabusys.data.stats からインポートして公開。

- AI（OpenAI）連携
  - src/kabusys/ai/news_nlp.py
    - ニュース記事から銘柄別センチメントを OpenAI（gpt-4o-mini、JSON Mode）でスコアリングし ai_scores テーブルへ書込み。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）を提供（calc_news_window）。
    - 記事集約、トークン肥大化対策（最大記事数・文字数トリム）、バッチサイズ制御（最大 20 銘柄/コール）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施、その他エラーはスキップ（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results キー、型チェック、スコアの数値化、スコアクリップ ±1.0）。
    - DuckDB への書き込みは部分置換（対象コードに絞り DELETE → INSERT）して部分失敗時の既存データ保護。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（ユニットテスト用パッチ想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の ma200 乖離（70% 重み）とマクロニュース LLM センチメント（30%）を合成して市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロニュース抽出はキーワードベース（複数キーワード一覧）でタイトルを取得し LLM 評価（記事無ければ macro_sentiment=0.0 にフォールバック）。
    - レジームスコア合成、閾値に基づくラベリング、market_regime テーブルへの冪等書込みを実装。
    - OpenAI 呼び出しは retry/backoff、エラー時は安全に 0.0 フォールバック。
  - OpenAI クライアントは environment または引数で API キーを解決。API 呼び出しは gpt-4o-mini を使用し JSON 出力を期待。

- モニタリング永続化
  - src/kabusys/monitoring/monitoring_db.py
    - SQLite（sqlite3.Connection）を用いて監視ログ用のテーブル群（system_status, trade_logs, positions, risk_logs 等）とインデックスを冪等に作成する init_monitoring_db を追加。

- パッケージ初期化
  - src/kabusys/__init__.py で __version__ = "0.1.0" を設定し、主要パッケージ名を __all__ で列挙。

### 変更（設計上の決定）
- DuckDB を主要な分析基盤として採用。prices_daily / raw_financials / raw_news 等のテーブルへ SQL ウィンドウ関数を使った集計処理を行う設計。
- ルックアヘッドバイアスを避ける実装方針を採用：
  - 日次処理は target_date を明示的に受け取り、内部で datetime.today() / date.today() を参照しない。
  - prices_daily クエリでは target_date 未満のデータのみ使用する箇所がある（regime 判定など）。
- OpenAI 呼び出しの取り扱い：
  - JSON Mode を用いて厳密な JSON 出力を期待するが、冗長テキスト混入に備えて最外の {} を抽出して復元する処理あり。
  - API 失敗は可能な限りフェイルセーフ（デフォルト値で継続）とし、書込み等で致命的な失敗が起きた場合のみ例外を上位へ伝播。
- 設定のデフォルト値と検証ルールを設定（env 値のバリデーションは Settings 内で行う）。

### 修正
- N/A（初回リリースのため過去修正履歴なし）。

### 既知の問題 / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）だとエクスポージャーや算出が不適切になり得る旨の TODO コメントあり。前日終値や取得原価などをフォールバックとして使う拡張が検討対象。
  - 将来的に銘柄ごとの lot_size 対応（stocks マスタからの取得）を想定した TODO が存在。
- .env パーサは一般的なケースをカバーするが、極端に複雑なシェル式の解釈は行わない（設計上の簡潔化）。
- news_nlp と regime_detector はそれぞれ独立して OpenAI 呼び出し実装を持つ（意図的に内部関数を共有しない設計）。重複があるため将来的に共通化検討の余地あり。
- DuckDB executemany に対する互換性（空リスト禁止）を考慮したガードを実装しているが、将来的な DuckDB バージョン差異に注意。

### セキュリティ
- OpenAI API キーはコード内にハードコードせず、引数または環境変数 OPENAI_API_KEY から取得する方針。
- 環境変数の自動ロード時、OS 環境変数は保護され .env ファイルで意図せず上書きされないようになっている。

---

注記:
- 本 CHANGELOG は提供されたコードベースから推測して作成したものであり、実際のリリースノートや変更履歴は開発者の手元の記録に従ってください。