# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

※ 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴ではなく、コードベースに含まれる機能・修正・設計上の注意点等を要約しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-09

Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル・ダブルクォート、バックスラッシュエスケープに対応。
    - インラインコメントの扱い（クォートあり/なしの差異）に対応。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 必須キー検証関数 _require を提供（未設定時に ValueError を送出）。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境モード / ログレベル 等）。
  - 入力値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）とデフォルト値を提供。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄候補選定:
    - select_candidates: score 降順、同点時は signal_rank 昇順で上位 N を選択。
  - 重み計算:
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - リスク調整:
    - apply_sector_cap: 同一セクターの既存エクスポージャーが上限を超える場合に該当セクターの新規候補を除外。unknown セクターは制限を適用しない。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマップと未知レジームでのフォールバック）。
  - 発注株数決定:
    - calc_position_sizes:
      - allocation_method により "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り。
      - aggregate スケールダウン時の再配分アルゴリズム（小数端数の取扱いと優先順付け）を実装。
      - 価格欠損時のスキップ・ログ出力。

- リサーチ・特徴量計算 (src/kabusys/research/*)
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB SQL で計算。必要行数不足時は None 扱い。
  - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う。
  - calc_value: raw_financials から直近レポートを取得して PER / ROE を計算（EPS 欠損時は None）。
  - calc_forward_returns: 任意ホライズンの将来リターンを一クエリで取得。horizons の検証（正の整数かつ <=252）を実施。
  - calc_ic / rank / factor_summary: Spearman（ランク相関）による IC 計算、同順位の平均ランク処理、基本統計量の集約。外部ライブラリに依存せず実装。

  設計方針:
  - DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（本番 API にアクセスしない）。
  - ルックアヘッドバイアス対策を意識した日付範囲指定（target_date 未満・未満/含むの扱い等）。

- AI 系機能 (src/kabusys/ai/*)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを取得。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数/文字数のトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 再試行戦略: 429 / ネットワークエラー / タイムアウト / 5xx を指数バックオフでリトライ（上限あり）。
    - レスポンス検証: JSON 抽出、"results" 構造検証、未知コードの無視、スコアの数値検証、±1.0 にクリップ。
    - DuckDB への書き込みは部分的冪等（対象コードだけ DELETE → INSERT）で実行。部分失敗時に既存スコアを保護。
    - API キーは引数・環境変数 OPENAI_API_KEY のいずれかで解決。未設定時は ValueError。
    - フェイルセーフ: API 失敗時はそのチャンクをスキップして処理継続（例外を全体に拡散させない設計）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio のデータ不足時は 1.0（中立）でフォールバックし WARNING を出力。
    - マクロニュース抽出はキーワードベース（複数キーワードに対する ILIKE 検索）。
    - LLM 呼び出しの失敗時は macro_sentiment = 0.0（中立）でフォールバックするフェイルセーフ実装。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。API キーの解決は news_nlp と同様。

  - OpenAI 呼び出しラッパーはモジュール単位で分離（テスト時にモックしやすい設計）。

- 監視データベース（src/kabusys/monitoring/monitoring_db.py）
  - SQLite ベースの永続化層初期化: system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを作成する init_monitoring_db 実装（冪等）。

Changed
- なし（初回公開のため、「追加」が中心）。

Fixed
- なし（コードに記述されたフォールバックや警告を反映）。

Security
- 環境変数に依存する機密情報（API キー等）に対して明示的な検証を実装。未設定時は ValueError を送出して早期に検出する（OpenAI 関連、J-Quants 等）。
- .env 自動ロード時に OS 環境変数は protected として扱い、.env/.env.local からの上書きを防止する設計。

Notes / Design decisions（設計上の注意）
- ルックアヘッドバイアス防止:
  - AI/レジーム/ニュース処理・リサーチ関数は datetime.today()/date.today() を使用しない設計（すべて target_date を外部から与える）。
  - prices_daily クエリでは target_date 未満のデータのみを使用する等の注意が払われている。
- DuckDB を用いたローカル分析重視（研究関数は外部 API を呼ばない）。
- OpenAI 呼び出しに関しては局所的にリトライ・パース耐性を実装しており、API 失敗が全体停止につながらないよう配慮。
- TODO / 将来拡張:
  - position_sizing の lot_size を銘柄別に拡張する旨のコメント（将来的にマスタから lot_size を取り込む設計）。
  - apply_sector_cap の price 欠損時の見積り改良（現状は 0.0 で計算される点に注意）。

お問い合わせ
- この CHANGELOG はコード内容からの推測に基づいて作成しています。差分や追加の履歴が必要な場合は、実際のコミットログやリリースノートを提供してください。