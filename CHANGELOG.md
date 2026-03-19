# CHANGELOG

すべての非趣味的・破壊的変更はこのファイルに記録します。
このファイルは「Keep a Changelog」準拠の書式で記述されています。

フォーマット:
- 主要カテゴリ: Added / Changed / Deprecated / Removed / Fixed / Security
- バージョンは semver、日付はリリース日（YYYY-MM-DD）

なお、本 CHANGELOG は提供されたコードベースの内容から実装意図・設計方針を推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアライブラリを実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0）。
  - __all__ に data / strategy / execution / monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数の読み込み機構を追加。
    - 自動ロード順: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出: .git または pyproject.toml を基準に __file__ から親ディレクトリを探索（CWD 非依存）。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - コメント処理（クォート外で # の直前がスペース/タブの場合はコメント扱い）
  - settings オブジェクトを提供（Settings クラス）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時は ValueError）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ有効）
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - is_live / is_paper / is_dev の便宜プロパティ

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - API レート制限遵守のための固定間隔 RateLimiter（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）。リトライ対象に 408/429/5xx を含む。
    - 401 Unauthorized 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライ（無限再帰を防止）。
    - ページネーション対応でデータを全件収集。
    - 取得タイミングを UTC の fetched_at に記録し、look-ahead bias をトレース可能に。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存。
    - 型変換ユーティリティ: _to_float / _to_int（不正値は None とする。_to_int は小数部が 0 以外の文字列は変換せず None を返す）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存するための基盤を実装。
    - デフォルト RSS ソース（yahoo_finance）を定義。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリDoSを防止。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリキーソート。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭を利用し冪等性を確保する設計（実装方針記載）。
    - defusedxml を利用し XML Bomb 等の攻撃対策を行う設計。
    - HTTP(S) 以外のスキーム拒否や SSRF 対策の考慮。
    - DB へはチャンク化してバルク INSERT（_INSERT_CHUNK_SIZE）する設計。

- リサーチ (kabusys.research)
  - ファクター計算と探索用ユーティリティ群を提供。
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照し、Momentum / Volatility / Value 系ファクターを算出。
      - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日ウィンドウのカウント検査あり）
      - Volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播制御等の実装）
      - Value: per, roe（raw_financials の target_date 以前の最新レコードを取得）
    - calc_forward_returns: target_date から将来リターンを複数ホライズン（デフォルト [1,5,21]）で算出。horizons の妥当性検査あり（1..252）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（有効レコードが 3 未満なら None）
    - rank: 同順位は平均ランク（比較前に round(v,12) で丸め、ties の扱いを明示）
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）
  - 外部依存を排し（pandas 等不使用）、DuckDB 経由での高速集計を想定した実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールの生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ: 最低株価 >= 300 円、20日平均売買代金 >= 5億円（_MIN_PRICE, _MIN_TURNOVER）
    - 正規化: zscore_normalize を利用、対象カラムを Z スコア化後 ±3 にクリップ（_ZSCORE_CLIP）
    - 冪等性: target_date の行を削除してから一括挿入（トランザクション保証）
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して売買シグナル（BUY / SELL）を生成する generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）
    - 合成重みのデフォルト値を実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。入力 weights は検証・正規化して合計を 1.0 に再スケール。
    - BUY 閾値デフォルト: 0.60（_DEFAULT_THRESHOLD）
    - Stop-loss 閾値: -8%（_STOP_LOSS_RATE）
    - Bear レジーム判定: ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合に BUY を抑制（_BEAR_MIN_SAMPLES）
    - AI スコア未登録銘柄は中立値（0.5）で補完、欠損コンポーネントは 0.5 で補完して不当な降格を防止
    - 保有ポジションのエグジット判定（stop_loss / score_drop）を実装。SELL 優先で BUY から除外。
    - 冪等性: target_date の signals を削除してから一括挿入（トランザクション保証）

- DB/トランザクション設計
  - features / signals 等への更新は「日付単位の置換」戦略を採用（DELETE date=target_date → INSERT 一括）し、BEGIN / COMMIT / ROLLBACK により原子性を保証。
  - 各所でロールバック失敗時の警告ログを実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- news_collector で defusedxml を採用して XML 関連の脆弱性を緩和。
- news_collector の URL 正規化・スキーム制限・レスポンスサイズ制限などで SSRF・DoS のリスクを低減する設計を採用。
- J-Quants クライアントは 401 自動更新・レート制限・リトライを組み合わせることで、誤ったトークン管理や過剰リクエストによるアカウントブロックのリスクを軽減。

### Known limitations / TODO
- execution 層はパッケージに含まれるが実装ファイルは空（execution/__init__.py）。発注 API への接続・注文実行ロジックは未実装。
- signal_generator の一部エグジット条件は未実装（トレーリングストップ、時間決済）。comments にて「positions テーブルへ peak_price / entry_date が必要」として記載あり。
- news_collector の完全な実装（RSS パース → DB 保存処理の詳細）はファイルの末尾で切れているため、実装が続く想定。
- save_* 関数は DuckDB のテーブル定義に依存する。テーブルスキーマとの整合性を確認すること。
- calc_forward_returns の日付範囲は「max_horizon * 2」日のカレンダーバッファを使う実装。特殊な市場カレンダー（多祝日等）でデータ不足になる可能性あり。
- .env のパースは多くのケースを想定しているが、すべての corner case を網羅しているわけではない（複雑なネストクォート等）。

### Migration / Upgrade notes
- settings の必須環境変数（JQUANTS_REFRESH_TOKEN など）が未設定だと ValueError を投げるため、導入時は .env を準備すること。
- 自動 .env ロードが不要な環境（CI/テスト等）では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止する。

---

注: 本 CHANGELOG は実装されたコード、内部コメント、および設計ノートから推測して作成しています。実際のリリースノートとして用いる場合は、リリース担当者による確認・追記（変更点の抜け漏れ、日付の確定、責任者など）を推奨します。