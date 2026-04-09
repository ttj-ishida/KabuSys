# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-09

初回公開リリース。以下の主要機能・モジュールを実装しています。

### Added
- パッケージ情報
  - kabusys パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - public API エクスポートを定義（portfolio, research, ai などの主要関数を __all__ に追加）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - .env パーサを実装（コメント、export 形式、クォート／エスケープ対応、インラインコメント扱いの細かい挙動）。
  - OS 環境変数を保護する protected 機構を実装。
  - 必須項目チェック用 _require()（未設定時は ValueError）。
  - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / Paper Trading / 監視閾値 / ログレベル / 環境種別 等）。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値検証（不正値は ValueError を投げる）。
  - path プロパティは expanduser を呼び出してチルダ展開に対応。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で並べ上位 N を選択。
  - 重み計算
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコアに基づく配分。全スコアが 0 の場合は等分配にフォールバックし警告を出力。
  - リスク調整
    - apply_sector_cap: セクター毎の既存エクスポージャーが上限を超えている場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数（フォールバックと警告処理あり）。
  - 株数決定
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") による発注株数計算。単元株（lot_size）丸め、max_per_stock 上限、available_cash に応じた aggregate キャップとスケーリング、cost_buffer による保守的見積り、残差配分ロジックを実装。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す設計。
  - calc_volatility: 20日 ATR（true range の扱いに注意）、相対 ATR、20日平均売買代金、出来高変化率を計算。必要行数が不足する場合は None を返す。
  - calc_value: raw_financials（最新レポート）と prices_daily を組み合わせて PER / ROE を計算。EPS 不正値時は None。
  - 研究ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）で将来リターンを一括取得。ホライズン検証と範囲限定を行う。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコード数が足りない場合は None。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。

- AI / 自然言語処理（src/kabusys/ai/*）
  - ニュース NLP（news_nlp）
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを算出し ai_scores テーブルへ書込む。
    - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム、JSON Mode を想定した厳密なレスポンスバリデーションを実装。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数設定）。
    - スコアは ±1.0 にクリップ。部分失敗時に既存データを保護するため、DELETE → INSERT は対象コードのみで実行（冪等性）。
    - OpenAI API キー未設定時は ValueError を投げる。
    - ルックアヘッドバイアスを防ぐ設計（date.today() 非依存、target_date ベースのウィンドウ計算）。
  - レジーム判定（regime_detector）
    - score_regime: ETF 1321 の ma200 乖離（70% ウェイト）とマクロニュースの LLM センチメント（30%）を合成して market_regime テーブルへ冪等書込み。
    - マクロキーワードによる raw_news フィルタ、最大記事数制限、LLM 呼び出しのリトライとフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - ma200 のデータ不足やその他エラーでの安全なフォールバックとログ出力。
    - OpenAI API キー未設定時は ValueError を投げる。

- モニタリング永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite ベースの監視ログ永続化層を実装。
  - init_monitoring_db: system_status, trade_logs, positions, risk_logs などのテーブルとインデックスを冪等的に作成。

### Security / Safety
- AI 呼び出し周りは以下の安全策を実装
  - レスポンスの厳密な JSON 検証と不正レスポンス耐性（部分的に余分なテキストが混入した場合の {} 抽出ロジックを含む）。
  - リトライ／バックオフ戦略とフェイルセーフ（API失敗時にもシステム全体が停止しない設計）。
  - スコアのクリッピング（±1.0）による極端な出力抑制。
  - API キーは引数優先、その後環境変数 OPENAI_API_KEY を参照する明示的な仕様。

### Notes / Implementation details
- DuckDB / SQLite 接続は関数引数で受け取る設計（副作用を避け、テスト容易性を確保）。
- datetime/weekend 等の扱いはカレンダー日で余裕を持ったスキャン範囲を設ける実装（ルックアヘッド対策を含む）。
- 外部依存を極力抑え、research の統計処理は標準ライブラリのみで実装している（pandas 等に依存しない）。

### Known limitations / TODO
- position_sizing の lot_size は現状グローバル共通（将来的に銘柄別 lot_map に拡張予定）。
- apply_sector_cap は price が欠損（0.0）の場合エクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格導入を検討。
- OpenAI SDK の将来の API 変更に備え、status_code の取得は getattr を使って安全に行う等の互換性対策を行っているが、将来 SDK 変更で追加作業が必要となる可能性あり。

---

（以降のリリースでは Unreleased → リリース履歴へ移動し、Added / Changed / Fixed / Removed などを明確に分けて記載します。）