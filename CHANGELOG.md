# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。セマンティック バージョニングを採用しています。

## [0.1.0] - 2026-03-20

初回リリース。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、トップレベル __version__ = "0.1.0" を設定。
  - __all__ を定義して主要モジュール群を公開（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索し判定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサ実装:
    - export プレフィックス対応、コメント対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応などを考慮した堅牢なパース処理。
    - override / protected キー制御により OS 環境変数の上書きを保護。
  - Settings クラスを提供し、必須環境変数取得（_require）と各種設定プロパティを公開。
    - J-Quants / kabu API / Slack / DB パス / ログレベル / 環境種別などのプロパティ。
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック）と is_live / is_paper / is_dev の判定ヘルパ。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - API レート制限を守る固定間隔スロットリング RateLimiter（120 req/min 相当）。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx 対象）。429 時は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンを用いた ID トークン自動再取得を 1 回行ってリトライ（再帰防止フラグあり）。
    - ページネーション対応を含む fetch 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - fetch の結果を DuckDB に保存する save_* 関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar。
      - ON CONFLICT（UPSERT）により冪等保存を実現。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有し無駄な再取得を抑制）。
    - JSON デコード失敗やネットワーク例外に対する明確なエラー処理。
  - データ変換ユーティリティ: _to_float, _to_int（不正値を安全に None に変換）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の基盤実装（DEFAULT_RSS_SOURCES に Yahoo Finance をデフォルト登録）。
  - URL 正規化 (トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去、クエリソート) を実装。
  - セキュリティ上の設計方針を反映:
    - defusedxml を用いた XML パース（XML Bomb などの防御）。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）などの DoS 対策。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を保証。
    - バルク INSERT のチャンク化で DB へ安全に保存。
  - raw_news / news_symbols への保存方針（ON CONFLICT DO NOTHING 等）を考慮した実装方針を導入。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照してファクターを計算。
    - 各関数は (date, code) 単位の dict リストを返す設計。
    - 計算に伴うウィンドウ長やスキャンバッファを明示。
  - feature_exploration:
    - calc_forward_returns (複数ホライズンの将来リターン算出、範囲チェック)
    - calc_ic (Spearman のランク相関 / IC 計算)
    - factor_summary (count/mean/std/min/max/median)
    - rank (同順位は平均順位で扱うランク計算)
  - DuckDB を直接利用し、外部依存（pandas など）なしで統計解析を実行する方針。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 関数を実装:
    - research のファクターを取得しマージ、ユニバース（価格・流動性）フィルタを適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT）することで冪等性と原子性を担保（トランザクション使用）。
    - ユニバース条件は最低株価 300 円、20日平均売買代金 5 億円。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 関数を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換や欠損値補完（None を中立 0.5）を組み合わせた final_score 算出。
    - weights の入力検証と補完（既定値フォールバック、合計が 1.0 でない場合の正規化）。
    - Bear レジーム判定（AI の regime_score 平均が負 → BUY を抑制するロジック）。
    - BUY（threshold デフォルト 0.60）・SELL（ストップロス/スコア低下）を判定し signals テーブルへ日付単位の置換で保存。
    - SELL 優先ポリシー（SELL の銘柄は BUY から除外しランクを再付与）。
    - エグジット条件の一部（トレーリングストップ、時間決済）は未実装で注記あり。

- DB/トランザクション設計
  - features / signals / raw_* 等への更新はトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入で原子性を確保。
  - DuckDB を想定した SQL（ウィンドウ関数、ROW_NUMBER 等）を活用した実装。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- RSS パースに defusedxml を採用し XML 攻撃を緩和。
- ニュース取得で受信バイト数を制限しメモリ DoS を緩和。
- news_collector にてトラッキングパラメータ除去と URL 正規化を行い、重複・同一記事の誤登録を防止。
- J-Quants クライアントの HTTP エラー処理で Retry-After を尊重する等、外部 API とのやり取りで堅牢性を確保。

### Notes / Known limitations
- research / strategy 層はルックアヘッドバイアス回避を設計要件としており、target_date 時点のデータのみ参照する方針を採用している。
- generate_signals の SELL 条件のうち「トレーリングストップ」「時間決済」は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）。
- news_collector の SSRF や IP 検査用のユーティリティは設計に言及されているが、実装の追加・拡張余地がある（将来の強化ポイント）。
- 各関数は DuckDB の特定テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）が存在することを前提とする。スキーマの準備が必要。
- ロギングは各処理で行われるが、運用時にログ設定（ハンドラ/フォーマット/レベル）を適切に行うことを推奨。

---

今後のリリースでは、以下を検討しています:
- execution 層の実装（kabu API 経由での発注/注文管理）
- ニュースと銘柄紐付けの精度向上（NER 等の導入）
- signal/backtest の統合テストと CI の整備
- positions テーブル強化（ピーク価格・エントリ日など）とトレーリングストップ実装

もし誤りや補足希望があればお知らせください。