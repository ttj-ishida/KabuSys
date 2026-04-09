# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

### Added
- CHANGELOG の初期テンプレートを追加。

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-09

初回リリース。主要な機能と実装の概要は以下の通り。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"、主要サブパッケージを __all__ で公開）。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local からの自動読み込みを実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を起点に上位ディレクトリを探索）。
  - .env パーサーを実装：
    - 空行・コメント行（先頭 `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく扱う。
    - インラインコメント判定（クォート外かつ直前が空白/タブの `#` をコメントとみなす）。
  - `.env` 読み込みで OS 環境変数を保護（既存キーは上書きしない / `.env.local` は上書きを許可するが OS 変数は保護）。
  - 必須環境変数チェック用の `_require()`、および各種設定プロパティを提供（J-Quants・kabuAPI・LINE・DBパス・監視閾値・ログレベル等）。
  - 環境変数値のバリデーションを追加（例：KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定（portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順にソート、同スコア時は signal_rank の昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバックし警告を出力。
  - リスク調整（risk_adjustment.py）
    - apply_sector_cap: 現在保有のセクター別時価総額を計算し、1セクター上限（max_sector_pct）を超える場合にそのセクターの新規候補を除外。`unknown` セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（'bull'/'neutral'/'bear'）に基づく投下資金乗数を提供（未定義レジームは警告を出して 1.0 にフォールバック）。
  - 株数決定（position_sizing.py）
    - calc_position_sizes: 以下の方式に対応して発注株数を計算
      - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく計算。
      - equal / score: 各銘柄の weight に基づく配分。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、投下資金の aggregate cap（available_cash）を実装。コスト見積り係数（cost_buffer）をサポートして保守的に計算。
    - aggregate cap 超過時のスケーリング実装と、lot_size 単位での端数配分（残差の大きい順に追加）を再現性を保って行うロジックを追加。
    - 価格未取得（None/<=0）の銘柄はスキップしてログ出力。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB SQL で算出。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高変化率を DuckDB SQL で算出。true_range の NULL 伝播を適切に扱う実装。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS 欠損や 0 の場合は None）。
    - 全関数とも DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照（外部 API に依存しない）。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL クエリで取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。欠損/非有限値を除外し、有効レコード数が 3 未満の場合は None を返す。
    - rank / factor_summary: 同順位は平均ランクで処理するランク関数、各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
    - pandas 等の外部依存を用いず、標準ライブラリ + DuckDB で実装。

- AI（OpenAI）関連（src/kabusys/ai/*）
  - news_nlp.py
    - calc_news_window: ニュース集計ウィンドウ（前日15:00 JST ～ 当日08:30 JST）を UTC naive datetime で計算。
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込むフルパイプラインを実装。
      - 1銘柄あたりの最大記事数、文字数を制限（トリム）してトークン肥大化を抑制。
      - 最大 _BATCH_SIZE 件（20）ずつバッチ送信。
      - 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフとリトライを実装。その他の例外はスキップして継続（フェイルセーフ）。
      - レスポンスの厳格なバリデーション（JSON 抽出・results 配列・型チェック・既知コードのみ採用・数値チェック）を実施。スコアは ±1.0 にクリップ。
      - 書き込みは部分失敗時に他銘柄スコアを保護するため、対象コードのみ DELETE → INSERT の形で冪等に行う（トランザクション使用）。DuckDB の executemany の制約を考慮した実装。
      - API キー未設定時は ValueError を送出。
  - regime_detector.py
    - score_regime: ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して 'bull'/'neutral'/'bear' を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュースの抽出はキーワードベース（複数の日本/国際ワード）で行い、記事が無ければ LLM 呼び出しをスキップして macro_sentiment=0.0 を用いるフェイルセーフを採用。
    - LLM 呼び出しは retries とエラー分類（5xx 再試行、非5xx は即スキップ）を行い、最終的に macro_sentiment の安全なフォールバックを実装。
    - OpenAI 呼び出し関数は news_nlp と意図的に別実装としてモジュール間の結合を抑制。

- モニタリング DB（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite を使った監視ログ永続化のためのテーブル群（system_status, trade_logs, positions, risk_logs など）とインデックス作成を冪等で実装。

- モジュールエクスポート
  - kabusys.portfolio, kabusys.research, kabusys.ai など主要機能を __all__ で公開。

### Changed
- なし（初回公開）

### Fixed
- なし（初回公開）

### Security
- OpenAI API キーは引数優先、その次に環境変数（OPENAI_API_KEY）を参照する明示的な扱いを採用。未設定時は例外で明示的に通知。

### Notes / Implementation decisions
- ルックアヘッドバイアス防止のため、日次指標・レジーム判定・ニュース集計などで datetime.today() / date.today() を参照せず、呼び出し側から target_date を受け取る実装。
- DuckDB を用いた SQL ベースのファクター計算を優先し、外部 API や Pandas への依存を避ける設計。
- AI 関連はフェイルセーフ志向：API 失敗やパース失敗があっても例外で処理を中断せず、可能な範囲で安全な値（例: macro_sentiment=0.0）を用いて継続する方針。

---

将来的なリリースでは、ユニットテスト、型注釈の強化、銘柄ごとの lot_size サポート、より詳細なエラーメトリクスの収集などを予定しています。