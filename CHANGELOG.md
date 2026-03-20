# Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

注: この CHANGELOG は与えられたコードベースの内容から機能・動作を推測して作成した初期リリース履歴です。

## [Unreleased]
- 今後のリリースに向けた既知の改善候補・未実装事項
  - strategy のエグジット条件で記載の「トレーリングストップ」「時間決済」は未実装（positions テーブルに peak_price / entry_date が必要）。
  - execution パッケージはプレースホルダ（空実装）で、発注ロジックは未提供。
  - データ正規化 / 保存に関する追加の検証・モニタリング機能の追加予定。

---

## [0.1.0] - 2026-03-20
初回リリース。以下の主要機能を含みます。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを提供。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント無視。
    - クォート無しのコメント認識ロジック。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得（未設定時は ValueError）。
    - KABU_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
    - データベースパスのデフォルト: DUCKDB_PATH = data/kabusys.duckdb、SQLITE_PATH = data/monitoring.db
    - 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを検証。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL の検証。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - API レート制限を守る固定間隔スロットリング (120 req/min) を実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 応答時はリフレッシュトークンで id_token を再取得して 1 回リトライ。
    - id_token をモジュールレベルでキャッシュしてページネーション間で共有。
    - レスポンス JSON のパースエラーやリクエスト失敗時は適切に例外を投げる。
  - データ取得関数:
    - fetch_daily_quotes (OHLCV)、fetch_financial_statements、fetch_market_calendar（いずれもページネーション対応）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes -> raw_prices に ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar に ON CONFLICT DO UPDATE
    - PK 欠損行はスキップし、スキップ件数をログ出力。
    - 日時は UTC で fetched_at を記録（Look-ahead バイアス追跡目的）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して raw_news に保存する機能（Research/DataPlatform 想定）。
  - セキュリティ・堅牢性の配慮:
    - defusedxml を使った XML パース（XML Bomb 等の防止）。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）。
    - HTTP/HTTPS 以外のスキーム制限・SSRF 回避設計（実装意図）。
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）などで冪等性を確保。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で SQL 長・パラメータ数を抑制。

- リサーチ (kabusys.research)
  - ファクター計算・探索用ユーティリティを提供。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 扱いに注意）。
    - calc_value: per (price / eps), roe を raw_financials と prices_daily から組合せて算出。
    - 各関数は prices_daily / raw_financials テーブルのみ参照。結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数が不足（<3）だと None を返す。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱う（浮動小数の丸めで ties 検出を安定化）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（価格 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ date 単位で置換（削除→挿入、トランザクションで原子性を確保）。
    - 処理は target_date 時点のデータのみを使用（ルックアヘッド防止）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。重みのバリデーションと正規化を実施。
    - デフォルト BUY 閾値: 0.60、STOP LOSS: -8%。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）は BUY を抑制。
    - BUY シグナル生成（threshold 以上）、SELL は保有ポジションに対するストップロス・スコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位の置換を実施。
    - 欠損値の補完ポリシー: コンポーネント None は中立 0.5 で補完（不当な降格を防止）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース XML パースに defusedxml を使用し、XML ベースの攻撃耐性を確保。
- RSS から取り込む URL を正規化し tracking パラメータを除去、SSRF 想定の制約を設計。

### Documentation / Logging
- 各モジュールに詳細な docstring とログ出力（logger）を追加し、処理状況・警告・エラーをログに残す設計。
- DuckDB 操作はトランザクションでラップし、ROLLBACK の失敗は警告ログを出力。

### Known issues / TODO
- positions テーブルに peak_price / entry_date 等の追加がないため、トレーリングストップ・時間決済は未実装。
- execution パッケージは空で、実際の発注処理はまだ含まれていない。
- news_collector の外部ネットワーク周り（スキームチェックや受信サイズ制御・IP/ホスト検査）の実装は設計方針として記載済みだが、運用時の追加検証が必要。
- 一部のユーティリティ（例: kabusys.data.stats の zscore_normalize）は参照されているが、この CHANGELOG の対象コード一式に同梱されているか要確認。

---

リリースノートや利用方法の補足が必要であれば、環境変数一覧（必須/省略可）や各主要関数の簡易使用例を追記します。どの情報を優先して追加しましょうか？