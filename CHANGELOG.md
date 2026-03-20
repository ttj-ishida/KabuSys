# CHANGELOG

すべての変更点は Keep a Changelog の形式に準拠して記載しています。  
慣例: 主要な追加は "Added", 挙動変更は "Changed", 不具合修正は "Fixed", セキュリティ関連は "Security"、互換性の破壊がある場合は "Breaking Changes" に記載します。

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__ にバージョンとエクスポート定義）。
  - モジュール構成: data, strategy, execution, monitoring（execution は空のプレースホルダ）。

- 環境設定管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動ロード対象を決定するため、CWD に依存しない動作。
  - .env パーサーの強化:
    - コメント行と空行のスキップ。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなしの値でのインラインコメント扱い（'#' の直前が空白/タブの場合のみコメントと判定）を実装。
  - .env 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを導入し、各種必須設定（J-Quants トークン、kabu API パスワード、Slack トークン等）やデフォルト値（DBパス等）、環境（development/paper_trading/live）・ログレベル検証を提供。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min 相当）。
  - リトライロジック: 指数バックオフで最大 3 回（408/429/5xx などを対象）、429 の Retry-After ヘッダ考慮。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）と再試行。
  - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - 冪等性を担保するため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO 8601 で記録し Look-ahead バイアスのトレースを可能に。
    - 型変換ユーティリティ（_to_float / _to_int）を提供し、不正データは安全に None として扱う。
    - PK 欠損レコードのスキップとログ警告。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news へ保存する処理を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によりメモリ DoS を緩和。
    - URL 正規化（スキーム/ホスト小文字化、tracking パラメータ除去、フラグメント除去、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保（トラッキングパラメータ除去後）。
    - HTTP/HTTPS スキーム以外の URL 拒否等の SSRF 対策（実装方針として明記）。
  - バルク INSERT のチャンク処理とトランザクション集約で効率的な DB 保存を行う。
  - デフォルト RSS ソース（Yahoo Finance ビジネスカテゴリ）を提供。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を算出。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を算出。true_range の NULL 伝播を適切に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出。最新の財務レコードを report_date <= target_date で選択。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足（<3 件）では None。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位（ties）に対して平均ランクを与えるランク付けユーティリティ（丸めにより ties 検出漏れを防止）。
  - research パッケージは zscore_normalize を再公開。

- 戦略（strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research 側の生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラム群を Z スコア正規化（kabusys.data.stats を利用）、±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT）して冪等性と原子性を確保（トランザクション使用）。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合してコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - 各成分の変換関数（シグモイドなど）と欠損補完（None を中立 0.5 で補完）を実装。
    - 重み付けはデフォルト値を持ち、ユーザー指定 weights は検証・スケーリングしてマージ。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でサンプル数が閾値以上）により BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）を用いた BUY 生成。
    - エグジット判定（SELL）:
      - ストップロス（終値/avg_price - 1 < -8%）優先。
      - final_score が閾値未満で売却。
      - 保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを回避。
    - signals テーブルへ日付単位で置換（冪等）して保存。
  - strategy パッケージは build_features / generate_signals を公開。

### Changed
- 初回リリースのため過去の変更はありません（新規実装）。

### Fixed
- 初回リリースのため過去のバグ修正履歴はありません。

### Security
- news_collector: defusedxml による安全な XML パース、受信サイズ制限、URL 正規化で SSRF/トラッキングの影響を低減。
- jquants_client: トークン自動リフレッシュ・リトライ制御・RateLimiter により API の誤利用やレート超過を抑制。

### Breaking Changes
- なし（初回リリース）。

### Notes / Implementation details
- トランザクションとバルク挿入により features / signals / raw_* / market_calendar への保存は日付単位で置換する実装になっており、冪等性および原子性を重視しています。
- 環境変数の必須チェックは Settings._require で ValueError を送出します。テスト等で自動 .env ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- jquants_client の _request は最大試行回数を超えると RuntimeError を送出します。401 の際は一度のみ自動でトークンリフレッシュを行い再試行します（無限再帰を避けるため allow_refresh 引数で制御）。
- research モジュールは外部依存（pandas 等）を用いず、標準ライブラリ + DuckDB の SQL を主体に実装されています。

今後の予定（未実装／検討事項）
- positions テーブルに peak_price / entry_date を保存してトレーリングストップや時間決済を実装する（signal_generator のエグジットロジック拡張）。
- news_collector のシンボル紐付け（news_symbols）ロジックの強化と自然言語処理を用いた news_score の導入。
- monitoring / execution 層の実装（kabu ステーション接続、発注ロジック、モニタリングダッシュボード）。

以上。