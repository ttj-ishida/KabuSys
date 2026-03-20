# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初回リリースはコードベースから推測・要約した内容です。

## [Unreleased]

- 今後のリリースでの注記やマイナー改善（テスト追加、ドキュメント強化、CI の導入など）をここに記載します。

## [0.1.0] - 2026-03-20

初回公開（コードベースより推測）

### Added
- パッケージ基盤
  - kabusys パッケージの基本構成を追加。公開 API として `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` をエクスポート（src/kabusys/__init__.py）。
  - パッケージバージョン `0.1.0` を設定。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数読み込み機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない自動ロード。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env パーサの実装:
    - コメント/空行スキップ、`export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い（クォート有無で挙動を分ける）等、堅牢なパースロジックを提供。
  - 環境変数必須チェック `_require` と Settings クラスを提供。
    - 必須設定例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - データベースパス等の既定値: `DUCKDB_PATH`, `SQLITE_PATH`
    - `KABUSYS_ENV`/`LOG_LEVEL` の検証と補助プロパティ（is_live / is_paper / is_dev）

- Data 層: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API からのデータ取得機能を実装（株価日足 / 財務データ / マーケットカレンダー）。
  - レート制限対応（120 req/min）と固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx のリトライ、429 の Retry-After 優先）。
  - 401 受信時のトークン自動リフレッシュ（id_token キャッシュ共有／1 回のみリフレッシュ）。
  - ページネーション対応の取得処理（pagination_key によるループ）。
  - DuckDB への冪等保存ユーティリティ（`save_daily_quotes`、`save_financial_statements`、`save_market_calendar`）を実装。
    - ON CONFLICT による更新、PK 欠損行のスキップと警告、保存件数ログ。
  - 数値変換ユーティリティ `_to_float`/`_to_int` を提供（フォールトトレラントな変換）。

- Data 層: ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と raw_news テーブルへの冪等保存機能を実装。
  - 検出・防御: defusedxml を使った XML パース、受信サイズ上限（10MB）や URL スキームチェックによる SSRF / DoS 対策。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、パラメータソート）を実装。記事 ID は正規化後の SHA-256 ハッシュ（先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）、バルク挿入のチャンク化（INSERT チャンクサイズ制限）を実装。
  - デフォルト RSS ソースを一つ定義（Yahoo Finance のビジネスカテゴリ）。

- Research 層
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m、200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily から計算。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER（price / EPS）や ROE を raw_financials と prices_daily の組合せで算出。report_date <= target_date の最新財務データを取得。
    - 各関数はデータ不足時に None を返す等、堅牢な処理を提供。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の fwd リターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman の ρ（ランク相関）を実装。サンプル数が不足（3 未満）の場合は None。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク処理（丸め誤差対策として round を使用）。
  - research パッケージのエクスポートを整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- Strategy 層
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールから取得した raw factor をマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）し、トランザクションで原子性を保証。冪等化。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - スコア変換にシグモイド関数を使用し、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、閾値デフォルト 0.60。
    - 重みのバリデーション（未知キー・非数値・負値は無視）と合計 1.0 への正規化処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）で BUY を抑制。
    - SELL（エグジット）判定実装:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - 保有ポジションの価格欠損時は SELL 判定をスキップ、features 未存在銘柄は score=0 と扱う等の安全策あり。
      - トランザクションで signals テーブルへ日付単位置換（冪等）。
    - BUY・SELL の優先ルール（SELL を優先して BUY から除外、BUY のランク付けを再付与）を実装。

- strategy パッケージのエクスポートを整備（build_features, generate_signals）。

### Changed
- 初回公開相当の実装であるため「変更」は過去履歴なし。将来バージョンで記載予定。

### Fixed
- 初回公開相当の実装であるため「修正」は過去履歴なし。実装内では入力欠損や数値検証・トランザクション失敗時のロールバック処理等、堅牢性を高める措置を追加。

### Known limitations / TODO（コード内コメントに基づく）
- シグナル生成の SELL 条件における未実装項目:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（60 営業日超の保有に対する処理）
- 一部ユーティリティ（zscore_normalize 等）は別モジュール（kabusys.data.stats）に依存しており、その実装は別途必要/存在。
- news_collector の RSS フェッチ実装はデフォルトソースが限定的。ソース追加やフィードの健全性チェック強化が今後の改善候補。
- J-Quants クライアントのリトライはネットワーク障害に対して堅牢だが、より詳細なメトリクス／バックオフ戦略の拡張が可能。

### Security
- news_collector で defusedxml を利用して XML 攻撃対策を実施。
- RSS の URL 正規化と受信サイズ制限、news_collector のスキームチェックで SSRF/DoS の緩和策を導入。
- J-Quants クライアントはトークンをメモリキャッシュするが、環境変数の取り扱いやログ出力で機密情報が露出しないよう注意が必要（現在はトークン内容を直接出力しない実装）。

---

バグ報告、改善提案、ドキュメント追記の要望等があればお知らせください。CHANGELOG をより詳細にするため、リリース日や貢献者情報を追加することも可能です。