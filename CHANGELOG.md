Changelog
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース。KabuSys — 日本株自動売買システムの基盤機能を実装。
- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - .env.local は .env の上書き（ただし OS 環境変数は保護され上書きされない）。
  - Settings クラスでアプリ設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL 等）。
  - 各種検証とデフォルト値:
    - PAPER_FILL_MODE の許容値チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の許容値チェック（development/paper_trading/live）。
    - LOG_LEVEL の許容値チェック。
    - DB パスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db 等）。
    - 必須環境変数が未設定の場合は ValueError を送出（_require を介して明示的）。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定ロジック（portfolio_builder.select_candidates）
    - スコア降順、同点は signal_rank の昇順でタイブレーク。
  - 重み計算
    - 等金額配分 calc_equal_weights
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額へフォールバックし WARNING を出力）
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - セクター集中制限 apply_sector_cap（保有セクター比率が閾値を超える場合、新規候補を除外。unknown セクターは除外対象外）
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはフォールバック）
  - ポジションサイジング（kabusys.portfolio.position_sizing）
    - allocation_method に応じた株数計算（risk_based / equal / score）
    - risk_based: 許容リスク率（risk_pct）と損切り幅（stop_loss_pct）から基準株数を算出
    - equal/score: 重みと max_utilization に基づく割当
    - 単元株(lot_size)で丸め、_max_per_stock による per-stock 上限を適用
    - aggregate cap: 全銘柄合計コストが available_cash を超過する場合はスケーリングし、残余キャッシュで端数配分（lot 単位）を行う
    - cost_buffer により手数料・スリッページを保守的に見積もる

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - ボラティリティ/流動性 calc_volatility（20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率）
    - バリュー calc_value（raw_financials の最新財務データと株価から PER/ROE を算出）
    - 全て DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照（外部 API に依存しない実装）
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（指定ホライズンの将来リターンを一括取得、horizons のバリデーションあり）
    - IC 計算 calc_ic（Spearman ランク相関、record 結合と欠損除外、3 銘柄未満は None）
    - ランク化ユーティリティ rank（同順位は平均ランク）
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）
  - zscore_normalize をエクスポート（kabusys.data.stats からの再公開）

- AI / ニュース NLP（kabusys.ai）
  - ニュースセンチメントスコア（kabusys.ai.news_nlp.score_news）
    - raw_news と news_symbols を集約して銘柄毎のニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを取得
    - 入力トークン肥大化対策（1 銘柄あたり最大記事数、最大文字数でトリム）
    - バッチ処理（最大 20 銘柄 / API コール）・リトライ（429/ネットワーク/タイムアウト/5xx に対して指数バックオフ）
    - レスポンス検証（JSON 解析、"results" リスト形式、code/score チェック、既知コードのみ採用、スコアは ±1.0 にクリップ）
    - 書き込みは部分冪等（DELETE WHERE date=? AND code=? を executemany → INSERT）で、部分失敗時に他コードの既存スコアを保護
    - API キーが未設定（引数か OPENAI_API_KEY）だと ValueError を送出
    - 失敗ケースはフェイルセーフ（個別チャンク失敗はスキップ、全体失敗時は 0 を返す等）
    - ルックアヘッドバイアス防止のため内部で date.today() を参照しない設計
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し regime_label を判定（bull/neutral/bear）
    - マクロニュース抽出はタイトルのキーワード検索（複数キーワード定義済み）
    - LLM 呼び出し失敗時は macro_sentiment=0.0 をフォールバック（フェイルセーフ）
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API キー未設定時は ValueError を送出
    - news_nlp の calc_news_window を共用してニュース収集ウィンドウを整合

- モニタリング DB 永続化（kabusys.monitoring.monitoring_db）
  - SQLite ベースの監視ログ永続化層を実装
  - system_status, trade_logs, positions, risk_logs 等のテーブル（およびインデックス）を冪等に作成する init_monitoring_db を提供

Security
- 環境変数や API キーの取り扱いに関して、明示的に OS 環境変数を保護する設計（.env ファイルが OS 環境変数を上書きすることはない）。

Notes / Implementation details
- DuckDB を直接使用する関数群は SQL を内部で組み立てており、対象テーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）のスキーマ前提があるため、本番データに適用する前にデータ互換性を確認してください。
- AI 関連機能は OpenAI の Chat Completion（gpt-4o-mini + JSON mode）に依存します。API 仕様やモデルの挙動の変化によりパース・検証ロジックを調整する必要が生じる可能性があります。
- ログ出力や WARNING は設計上意図的に導入されています（データ不足時のフォールバックや不正入力時の通知など）。
- Position sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別単元対応のため拡張を想定する注記あり。

Breaking Changes
- 初回リリースのため破壊的変更はありません。

Acknowledgments
- ドキュメント内の参照（PortfolioConstruction.md, StrategyModel.md 等）に基づく設計が反映されています。