CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。
このプロジェクトは Keep a Changelog のガイドラインに準拠します。
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初回公開（バージョン: 0.1.0）。
- 基本パッケージ情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" とモジュールエクスポート設定を追加。
- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）または OS 環境変数から設定を自動読み込み（プロジェクトルートは .git / pyproject.toml を起点に探索）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサ実装（export プレフィックス、クォート処理、インラインコメント処理、エスケープ対応）。
    - 読み込み時の上書き制御: override フラグと OS 環境変数保護（protected set）。
    - 必須設定チェック（_require）と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - パラメータ検証: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の有効値チェック（不正時は ValueError を送出）。
    - デフォルト値の整理（データベースパス、PID/kill flag 周り、しきい値等）。
- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates): score 降順 + tie-break に signal_rank を使用。
    - 重み計算: 等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア合計が 0 の場合は等配分へフォールバック（Warning ログ）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing 実装 (calc_position_sizes): risk_based / equal / score の各割当方式をサポート。
    - 単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer を用いた保守的見積り。
    - 価格欠損・負値に対するログとスキップ処理。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限適用 (apply_sector_cap): 既存保有のセクター別時価を計算し上限超過のセクターから新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier): bull/neutral/bear マッピング、未知レジームはログを出して 1.0 にフォールバック。
  - パッケージエクスポートを追加（portfolio/__init__.py）。
- リサーチ（ファクター計算・特徴量解析）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR）、バリュー（PER、ROE）の計算を DuckDB SQL＋Python で実装。
    - データ不足時は None を返す仕様、SQL 内でウィンドウ集計を利用して効率的に算出。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を実装。
    - pandas 等外部依存を使わず標準ライブラリと DuckDB のみで実装。
  - research パッケージの公開インターフェースを整備（__init__.py に必要関数をエクスポート）。
- AI 関連機能（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントスコアを計算・ai_scores テーブルへ保存。
    - タイムウィンドウの厳密定義（JST ベース → DB 比較用 UTC 変換）。
    - トークン肥大化対策（1銘柄あたりの記事数・文字数制限）、最大バッチサイズ、JSON Mode を使った堅牢な応答検証。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはフェイルセーフでスキップ。
    - レスポンス検証で未知コードや非数値スコアを無視、スコアを ±1.0 にクリップ。
    - DuckDB への書込みは部分失敗に備え DELETE→INSERT（対象コードで絞る）、トランザクション管理（BEGIN/COMMIT/ROLLBACK）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を計算・格納。
    - マクロニュース選別はキーワードマッチ（複数キーワード）でのタイトル抽出、LLM 呼び出しやレスポンス失敗時の安全フォールバック（macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止のため target_date 未満のデータ利用や datetime.today() を参照しない実装。
  - ai パッケージの公開インターフェース（score_news のエクスポート）。
  - 両モジュールとも OpenAI API キーが必須（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。
- 監視ログ永続化（SQLite）
  - src/kabusys/monitoring/monitoring_db.py
    - SQLite を用いた監視ログ用 DB 初期化関数を実装（system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを作成、冪等）。
    - システム稼働状況・取引ログ・ポジション・リスクイベントの永続化基盤を提供。
- ログ出力とエラーハンドリング
  - 各モジュールで詳細な debug/info/warning ログを追加し、欠損データや API 失敗時の挙動を明示。
  - DB 書込み時のトランザクション制御（BEGIN/COMMIT/ROLLBACK）を徹底。

Security
- .env 自動読み込みでは OS 環境変数が優先され、既存 OS 環境変数を上書きしない保護機構を実装（protected set）。.env.local は override=True による上書き挙動を取るが、OS 環境変数は保護される。
- OpenAI API キーの取り扱い: 引数または環境変数 OPENAI_API_KEY を推奨。未設定時は API 呼び出しを行わず ValueError を返すことで誤発注リスクを低減。

Notes / 用語
- DuckDB を内部で利用する機能が多く含まれます（research / ai モジュール）。適切なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）の存在が前提です。
- AI 呼び出しのテストしやすさを考慮し、API 呼び出し箇所は内部関数をモックできるよう設計されています（unittest.mock.patch 等で差し替え可能）。
- 多くの関数は「純粋関数（副作用なし）」を意図して実装されています（ポートフォリオ/リスク/ポジション算出など）、副作用を持つ DB 書込は ai モジュールの明示的箇所に限定。

既知の制約 / TODO
- position_sizing の lot_size は現状グローバル固定（100）で、将来的に銘柄ごとの単元情報を取り込む拡張を想定。
- apply_sector_cap の価格欠損時の取扱い（price が 0.0 の場合にエクスポージャー過小見積りとなりブロックが外れる）について注釈と将来的なフォールバック検討。
- monitoring_db.py のテーブル定義は初期化スクリプト内に記載。一部テーブル定義は将来的に拡張される可能性あり。

ライセンス
- （コードベースにはライセンス表記が含まれていません。公開時は適切なライセンスファイルを追加してください。）

その他
- 今後のリリースではテストカバレッジ、CI ワークフロー、マイグレーション / データ検証ユーティリティの追加を予定しています。