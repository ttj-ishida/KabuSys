# Changelog

すべての破壊的変更は SemVer に従います。  
このファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
最初の公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下の主要コンポーネントを含みます。

### 追加
- パッケージ初期化
  - `kabusys.__init__` にてバージョン "0.1.0" と主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 設定管理
  - `kabusys.config`
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト用等）。
    - 行パーサーの強化: `export KEY=val`、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理、コメント検出の扱い等に対応。
    - `Settings` クラスを提供し、以下の設定取得プロパティを実装:
      - J-Quants / kabu / Slack / DB パスなど（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `duckdb_path`, `sqlite_path`）。
      - `env` (`development` / `paper_trading` / `live`) と `log_level` の検証（不正値は ValueError を送出）。
      - `is_live` / `is_paper` / `is_dev` のヘルパー。

- データ取得・保存（J-Quants API クライアント）
  - `kabusys.data.jquants_client`
    - API レート制限を守る固定間隔スロットリング（120 req/min）を実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を優先。
    - 401 受信時にはリフレッシュトークンによるトークン更新を自動で1回実施してリトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を用いて複数ページ取得）。
    - fetch/save の関数群:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE（冪等）
      - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE（冪等）
      - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE（冪等）
    - データ変換ユーティリティ `_to_float` / `_to_int` を実装（空・不正値は None、int 変換ルールを厳密化）。

- ニュース収集
  - `kabusys.data.news_collector`
    - RSS フィードからニュースを取得して raw_news に保存するための基盤実装（デフォルトに Yahoo Finance のビジネスカテゴリ RSS を含む）。
    - セキュリティ考慮:
      - defusedxml を使った XML パース（XML Bomb 等への対策）。
      - HTTP(S) スキーム以外の URL を拒否（SSRF 緩和）。
      - 受信バイト数上限（10MB）によるメモリ DoS 軽減。
      - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を担保。
    - バルクINSERT のチャンク処理など運用面の配慮（大量挿入時の SQL 長制約回避）。

- 研究（research）モジュール
  - `kabusys.research.factor_research`
    - モメンタムファクター（mom_1m, mom_3m, mom_6m, ma200_dev）を計算（200 日 MA の存在チェック含む）。
    - ボラティリティ／流動性（atr_20, atr_pct, avg_turnover, volume_ratio）を計算（ATR 計算時の NULL 伝播制御）。
    - バリュー（per, roe）を raw_financials と当日の株価から算出（EPS が 0/欠損 の場合は None）。
    - DuckDB のウィンドウ関数を活用しパフォーマンスを配慮した SQL 実装。
    - 計算に用いるスキャンバッファ（カレンダー日数）等を定数化。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）: デフォルトホライズン [1,5,21]、ホライズンの検証（正整数かつ <= 252）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランクで処理、有効サンプル <3 は None）。
    - rank / factor_summary 実装: 基礎統計量（count/mean/std/min/max/median）を返す。

- 戦略（strategy）モジュール
  - `kabusys.strategy.feature_engineering`
    - research モジュールの raw factor を取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）を実行し ±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（DELETE → INSERT のトランザクションで冪等性を確保）。
    - 実装はルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）。

  - `kabusys.strategy.signal_generator`
    - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成。
    - 主要仕様:
      - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights 引数で上書き可（不正値を除外し合計が 1.0 になるよう再スケール）。
      - デフォルト BUY 閾値 0.60。
      - AI スコア未登録銘柄はニューススコアを中立（0.5）で補完、欠損コンポーネントは中立 0.5 で補完して不当な降格を防止。
      - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合は BUY を抑制。
      - SELL 条件（実装済）:
        - ストップロス: (close / avg_price - 1) < -0.08（-8%）
        - スコア低下: final_score < threshold
      - SELL は BUY より優先し、SELL 対象は BUY から除外してランク付けを再付与。
      - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）。

### 変更（設計/実装に関する注記）
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）とし、トランザクションで原子性を保証するように実装。
- 多くの関数で入力データ欠損や NaN/Inf を安全に扱う設計（None チェック、math.isfinite など）。
- ロギングを各モジュールに導入し、運用時の診断を容易にする（INFO/WARNING/DEBUG）。
- J-Quants クライアントでは取得時刻（fetched_at）を UTC ISO 形式で記録し、ルックアヘッドバイアスのトレーサビリティを確保。

### 既知の未実装 / 今後の拡張案
- signal_generator のエグジット条件について、以下は未実装（positions テーブルに peak_price / entry_date 等の拡張が必要）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- news_collector の記事→銘柄紐付け（news_symbols への連携）や INSERT RETURNING を用いた正確な挿入件数集計の詳細実装は今後拡張予定。
- execution / monitoring パッケージは初期スケルトンのみ（今後発注ロジック・モニタリング機能を追加予定）。

---

リリースに関する追加情報や移行手順が必要な場合はお知らせください。