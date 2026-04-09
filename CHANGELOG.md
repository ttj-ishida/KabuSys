# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
リリース日付はコードベースから推測して設定しています。

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ情報を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境変数 / 設定管理
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの検出は __file__ を起点に親ディレクトリを探索し、`.git` または `pyproject.toml` を目印に判定。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - .env パーサは export 形式、クォート付き値（エスケープ対応）、行内コメント処理をサポート。
    - override / protected（OS 環境変数保護）オプションを備え、.env.local は .env を上書きする設計。
  - 必須設定取得関数とバリデーションを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
  - 各種デフォルト値や検証を実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- ポートフォリオ構築ロジック（純粋関数）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank の昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分。全スコアが 0 の場合は等金額へフォールバック（WARNING ログ）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター時価を計算し、1セクターの上限（max_sector_pct）を超えるセクターの新規候補を除外。`unknown` セクターは上限チェックの対象外。
    - calc_regime_multiplier: market_regime に基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（WARNING）。
    - 価格欠損時の注意点（コメントで将来的なフォールバック案を記述）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じて発注株数を算出（risk_based / equal / score をサポート）。
    - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく算出。
    - equal/score: 配分比率に基づく算出。lot_size（単元）で丸め、単元丸め後に aggregate cap（available_cash）を考慮してスケールダウン。スケール時は残差に基づき lot 単位で追加配分するロジックを実装。
    - cost_buffer により手数料・スリッページ見積りを保守的に扱う。

- リサーチ / ファクター計算（DuckDB ベース、外部ライブラリ不要）
  - モメンタム・ボラティリティ・バリュー（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ウィンドウ不足時は None）。
    - calc_volatility: 20日 ATR（true_range の NULL 伝播に注意）、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS が 0 または NULL の場合は PER を None）。
    - DuckDB SQL を使用して1クエリで集計する設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons は 1〜252 の整数のみ許容。
    - calc_ic: スピアマンのランク相関（IC）を実装。利用可能レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクにする実装（round で浮動小数誤差を吸収）。
    - factor_summary: count/mean/std/min/max/median の要約統計を計算。
  - モジュールエクスポート: zscore_normalize（kabusys.data.stats 経由）を含む公開 API を定義（src/kabusys/research/__init__.py）。

- AI（OpenAI）統合機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を集約し、銘柄ごとに gpt-4o-mini（JSON mode）でセンチメント評価を実行。
    - 処理単位は最大 _BATCH_SIZE=20 銘柄、1銘柄あたりの記事数・文字数上限を設定（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - API 呼び出しは指数バックオフでリトライ（429, ネットワーク, タイムアウト, 5xx）。
    - レスポンスは厳密な JSON 構造を検証（results: [{code, score}, ...]）。スコアは ±1.0 にクリップ。
    - DB 書き込みは部分失敗に配慮して対象コードのみ DELETE → INSERT（トランザクション）で上書き。
    - API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError。
    - タイムウィンドウ（JST 基準）の計算ユーティリティを提供（calc_news_window）。
    - フェイルセーフ設計: API 失敗時は該当チャンクをスキップして処理継続。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で日次レジーム判定（'bull'/'neutral'/'bear'）。
    - マクロニュースはタイトルをマクロキーワードでフィルタし上位件数を LLM に送る（最大 _MAX_MACRO_ARTICLES）。
    - composite スコアをクリップし閾値でラベル付け。マクロ評価失敗時は macro_sentiment=0.0 で継続（WARNING）。
    - DB 書き込みは冪等（DELETE → INSERT をトランザクションで実行）。
    - API キーは引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。

- 監視ログ永続化（SQLite）
  - MonitoringDB 初期化スクリプトを実装（src/kabusys/monitoring/monitoring_db.py）。
    - system_status, trade_logs, positions, risk_logs など複数テーブルとインデックスを冪等に作成。

- パッケージの公開 API（__all__）
  - portfolio, research, ai など主要関数をパッケージレベルでエクスポート（src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py, src/kabusys/ai/__init__.py）。

### Changed
- （初版リリースのため適用なし）

### Fixed
- （初版リリースのため適用なし）

### Known issues / Notes
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされ、ブロックが外れる可能性がある旨をコメントで注意喚起。将来的に前日終値や取得原価でのフォールバックを検討。
- calc_position_sizes:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map を受ける拡張を想定。
- news_nlp / regime_detector:
  - OpenAI SDK の例外やレスポンスの変化に対して保守的に設計しているが、API 仕様変更時はモック／テストを含めた検証が必要。
- config:
  - .env パースは一般的シェルの記法を考慮しているが、特殊ケースは扱えない場合があります。

---

今後の予定（参考）
- 銘柄別単元情報の導入（lot_size を銘柄別に）。
- price 欠損時のフォールバックロジック実装（前日終値等）。
- news_nlp と regime_detector の LLM 呼び出し抽象化・テストカバレッジ強化。