CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- 基本情報
  - 初期リリース。パッケージメタ情報は kabusys.__version__ = "0.1.0"。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 自動ロード順序: OS環境変数 > .env > .env.local（.env.local は上書き）。
    - プロジェクトのルートは .git または pyproject.toml を基準に __file__ から親ディレクトリを探索して特定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - OS 環境変数は保護され、protected set により .env による上書きを防止。
  - .env パーサの実装:
    - コメント行と空行のスキップ、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値の inline コメント処理（直前が空白/タブ の場合のみ # をコメントとみなす）。
  - Settings クラスを追加し、環境変数をプロパティ経由で取得：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須取得時は未設定で ValueError）
    - KABU_API_BASE_URL のデフォルト、LINE 関連トークン、各種 DB パス（DuckDB/SQLite/ Paper Trading 用）
    - Paper Trading の PAPER_FILL_MODE 値検証（instant/partial/never/reject）
    - 監視ファイルパス、閾値（CPU/MEMORY/DISK）、KILL フラグのクリア挙動
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証および is_live / is_paper / is_dev ヘルパー

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 銘柄選定・重み計算 (portfolio_builder.py)
    - select_candidates: score 降順、同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は警告を出して等金額配分へフォールバック。
  - リスク調整 (risk_adjustment.py)
    - apply_sector_cap: セクターごとの既存エクスポージャーを算出し、1セクター上限を超過している場合は当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に対する投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 でフォールバック。
  - ポジションサイジング (position_sizing.py)
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジックを実装。
      - risk_based: 許容リスク率 (risk_pct) と損切り率 (stop_loss_pct) に基づく算出。
      - equal/score: weight に基づく割当。
      - 単元株 (lot_size) による丸め、1銘柄上限（max_position_pct）、全体 aggregate cap（available_cash）を考慮。
      - cost_buffer により手数料/スリッページを保守的に見積もる。
      - aggregate scaling 実装: 合計コストが available_cash を超える場合にスケール & lot_unit 切り捨て、残余で fractional remainder の大きい順に lot 単位で再配分するアルゴリズム。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を DuckDB SQL で計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（true range の平均）、相対 ATR、20日平均売買代金、出来高比率などを計算。NULL 伝播やカウント条件を考慮。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER, ROE を計算（EPS が 0/NULL の場合 PER は None）。
    - DuckDB 接続を受ける設計で外部 API に依存しない純粋な計算関数。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL で取得する高速実装。horizons の入力検証あり。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。欠損および有効レコード数による None フォールバック。
    - rank: 同順位は平均ランク扱い（丸めによる ties 検出改善）。
    - factor_summary: count/mean/std/min/max/median の統計要約（None は除外）。
  - research パッケージ __all__ に zscore_normalize（kabusys.data.stats 経由）等を公開。

- AI 関連 (src/kabusys/ai/)
  - news_nlp.py:
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST を UTC に変換）を提供。
    - score_news: raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ書き込むバッチ処理を実装。
      - バッチサイズ、最大記事数・文字数トリム、JSON mode 利用、レスポンス検証（results キー、code, score の型検証、既知コードのみ採用）、スコアの ±1.0 クリップ。
      - API の 429/ネットワーク/タイムアウト/5xx を対象とした指数バックオフリトライ、その他エラーは安全にスキップ。
      - DuckDB への書き込みは部分失敗時に他コードの既存スコアを保護するため、対象コードのみを DELETE → INSERT（executemany）で処理。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
      - 実行時に datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）。
  - regime_detector.py:
    - score_regime: ETF 1321 の 200日 MA 乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等的に書き込む処理を実装。
      - ma200_ratio は target_date 未満データのみで計算し、データ不足時は中立（1.0）として警告ログを出す。
      - マクロニュースはキーワード検索でタイトルを抽出、記事がある場合のみ LLM 評価。LLM 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - レジームスコア合成式、閾値、書き込みトランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出し部分は news_nlp と意図的に別実装（モジュール間の private 関数共有を避ける）。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite に対して監視用テーブル群（5テーブル）とインデックスを冪等作成するスクリプトを実装。
    - 作成されるテーブル例: system_status, trade_logs, positions, risk_logs（ファイル内に加えて合計 5 テーブルと複数インデックスを作成）。

Documentation / Design notes
- 多くの関数は DuckDB 接続を引数に取り、外部 API や実際の発注を行わない純粋関数的な実装（研究・テストで安全）。
- 時刻・日付に関わる処理はルックアヘッドバイアスを避けるために date.today() / datetime.today() を直接参照しない設計。
- OpenAI 連携は明示的に API キーを要求し、失敗時はフォールバックや警告ログで安全に続行する方針。
- 多くの箇所に入力検証・値検査・ログ出力を追加し、安全性とデバッグ性を向上。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または各関数引数で供給する必要があります。
- J-Quants / kabuAPI のトークン・パスワードも環境変数での供給を想定（未設定時は例外）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Notes for users / migration
- .env の自動読み込みはプロジェクトルートの検出に依存します。配布後に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のスキーマやテーブルはパッケージ内の関数が期待する形式に合わせてください（research / ai / monitoring の各関数が参照）。
- OpenAI の呼び出し部分はテストで差し替え可能（モジュール内の _call_openai_api を patch することを想定）。

-----