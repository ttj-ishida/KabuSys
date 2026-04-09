# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。重要な変更点、追加機能、バグ修正等を日本語でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。主要モジュールを実装し、ポートフォリオ構築、リサーチ、AI連携、環境設定、監視永続化などの基盤機能を提供します。

### Added
- パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開用の `__all__` を設定（"data", "strategy", "execution", "monitoring"）。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサは以下に対応:
    - コメント行・空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行でのインラインコメント判定（直前が空白/タブの場合）
  - 読み込み時に OS 環境変数を保護する `protected` セットを適用。
  - 設定取得用 `Settings` クラスを提供。主なプロパティ:
    - J-Quants / kabuステーション / LINE API 関連トークン取得
    - DB パス（DuckDB / SQLite / Paper Trading SQLite）
    - Paper Trading 用設定（PAPER_FILL_MODE 等）と値検証（有効値チェック）
    - 監視関連パス・閾値（PID ファイル、kill flag、CPU/メモリ/ディスク閾値）
    - 環境ラベル（KABUSYS_ENV）の検証（development / paper_trading / live）
    - ログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - 環境判定ヘルパー（is_live / is_paper / is_dev）
  - 必須環境変数未設定時は `ValueError` を送出する `_require` を実装。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定 / 重み付け関数（純粋関数、DB 非依存）
    - select_candidates: score 降順、同点は signal_rank の昇順でタイブレークして上位 N 件を選定
    - calc_equal_weights: 等金額配分（code -> 1/N）
    - calc_score_weights: スコア比率で正規化。全スコアが 0 の場合は等分配にフォールバックし WARNING を出力
  - リスク調整
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、1 セクター上限（デフォルト 30%）を超えるセクターの新規候補を除外。`sell_codes` を考慮して当日売却予定銘柄を除外できる。`unknown` セクターは制限対象外。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に対する投下資金乗数を返却。未知レジームは 1.0 でフォールバックし WARNING を出力。
  - ポジションサイズ決定
    - calc_position_sizes: 以下の方式をサポート: "risk_based"（リスクベース）、"equal"、"score"。
      - 単元株（lot_size）で丸め、単銘柄上限（portfolio_value * max_position_pct）を適用。
      - risk_based: risk_pct / (price * stop_loss_pct) に基づく株数計算。
      - equal/score: weight に基づく割当て（max_utilization を考慮）。
      - aggregate cap: 全銘柄合計が available_cash を超える場合は比例スケールダウンし、その後 lot_size 単位で残差を大きい順に再配分するアルゴリズムを実装。
      - price が欠損/<=0 の場合はスキップし、ログでデバッグ情報を出力。
      - cost_buffer による手数料/スリッページの保守的見積りを考慮。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（MA200）を DuckDB SQL で計算。データ不足時は None を返す。営業日ベースのラグを使用。
    - calc_volatility: 20 日 ATR（true range の平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う。
    - calc_value: raw_financials から直近財務データを取得して PER（EPS が null/0 の場合は None）および ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL クエリで取得。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。欠損除外、有効レコードが 3 未満なら None を返す。ties は平均ランクで処理。
    - rank: 同順位は平均ランクで扱う実装（丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を標本ではなく母分散で計算（分散を n で割る設計）。None と非有限値を除外。

- AI / ニュース NLP（kabusys.ai）
  - news_nlp:
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST → UTC 変換）を提供（前日 15:00 JST 〜 当日 08:30 JST を UTC naive datetime に変換）。
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
      - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数・文字数の上限トリムを実装。
      - API 呼び出しは再試行（429・接続断・タイムアウト・5xx）する指数バックオフ実装。
      - レスポンスの厳格なバリデーション（JSON 抽出、"results" リスト、各要素の code/score 型チェック、未知コードは無視、数値チェック、±1.0 でクリップ）。
      - DB 書き込みは部分成功を考慮して対象コードのみ DELETE → INSERT（トランザクション内）を行い、DuckDB executemany の空リスト制約に対応。
      - API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
      - テスト用に API 呼び出し箇所を差し替え可能（パッチ対象を想定）。
  - regime_detector:
    - 市場レジーム判定ロジック（ETF 1321 の MA200 乖離 70% + マクロニュース LLM センチメント 30%）。
    - _calc_ma200_ratio: look-ahead を防ぐため target_date 未満のデータのみを使用し、データ不足時は中立（1.0）でフォールバック。
    - マクロニュース抽出はキーワードベースでフィルタ（最大件数制限）。
    - LLM 呼び出しは再試行とエラー種別に応じたハンドリング。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - 合成スコアを -1〜1 にクリップし閾値により "bull"/"neutral"/"bear" を決定。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キー解決は news_nlp と同様の振る舞い。

- 監視データベース（kabusys.monitoring）
  - monitoring_db.init_monitoring_db:
    - SQLite 接続に対して冪等にテーブル群（system_status, trade_logs, positions, risk_logs など）およびインデックスを作成するスクリプトを実装（読み書き専用層）。

- パッケージエクスポート
  - kabusys.portfolio と kabusys.research の __init__ で主要関数を公開。
  - kabusys.ai.__init__ で score_news を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- DuckDB を利用する関数群は SQL を直接発行する設計で、外部 API 呼び出しは行わない（研究系関数）。
- AI 関連は外部 API に依存するため、API キー未設定や API エラー時の安全なフォールバックを重視した実装となっている。
- いくつかの箇所で将来的な拡張（銘柄別 lot_size の導入、価格フォールバック等）を TODO コメントで示しています。

### Breaking Changes
- なし（初回リリース）

---

今後のリリースでは、テストカバレッジ強化、銘柄別パラメータの拡張、パフォーマンス改善（DuckDB クエリ最適化やバッチ処理最適化）などを予定しています。