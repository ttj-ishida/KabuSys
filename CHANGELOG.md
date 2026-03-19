# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-19

初回リリース。本リリースでは日本株自動売買システム「KabuSys」のコア機能群（データ収集・保存、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、設定管理など）を実装しています。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - 公開モジュールのエクスポート定義を追加（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env の行パーサ実装: export 構文、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - .env 読み込み時の上書き制御（override）と、OS 環境変数を保護する `protected` セットを導入。
  - 必須設定取得ユーティリティ `_require` と Settings クラスを実装。J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャンネル、DB パスなどをプロパティとして提供。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証を実装（許容値のチェックとエラー報告）。
  - DuckDB / SQLite 用のデフォルトパスを Settings で提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制御（固定間隔スロットリング）を行う `_RateLimiter` を実装し、API レート制限（120 req/min）を保護。
  - 汎用 HTTP リクエストラッパー `_request` を実装。ページネーション、JSON デコード、最大リトライ（指数バックオフ）、429 の Retry-After 対応、408/429/5xx に対するリトライロジックを備える。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）を実装。トークン取得は `get_id_token` を通じて行う。
  - トークンキャッシュ（モジュールレベル）を導入してページネーションなどでトークンを共有。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (マーケットカレンダー)
  - DuckDB への保存関数を実装（冪等）:
    - save_daily_quotes: raw_prices テーブルへ挿入。主キー欠損行はスキップして警告を出力。fetched_at を UTC で記録。ON CONFLICT DO UPDATE による上書き。
    - save_financial_statements: raw_financials テーブルへ挿入。主キー欠損行はスキップして警告。fetched_at を UTC で記録。ON CONFLICT DO UPDATE を使用。
    - save_market_calendar: market_calendar テーブルへ挿入。取引日 / 半日 / SQ の判定を bool 型で扱い、ON CONFLICT DO UPDATE を使用。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装（安全な変換、空値や変換失敗時は None を返す）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを取得して raw_news に保存するための基盤を実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。
  - 記事 HTML/XML の安全パースに defusedxml を利用し、XML Bomb 等の攻撃を軽減。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や URL の正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）機能を実装。
  - 記事 ID の生成方針（URL 正規化後の SHA-256 の先頭 32 文字を想定）や、HTTP/HTTPS スキームの検査など設計方針をドキュメント化。
  - バルク挿入のチャンクサイズ定義や、型定義（NewsArticle TypedDict）を追加。

- 研究（Research）モジュール (src/kabusys/research/*.py)
  - ファクター探索ユーティリティ:
    - calc_forward_returns: target_date から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証（正の整数かつ <=252）を実装。
    - calc_ic: ファクターと将来リターン間のスピアマンランク相関（IC）を実装。欠損・サンプル不足（<3）をハンドリング。
    - rank: 同順位は平均ランクで扱うランク付け実装（丸めによる ties 検出漏れ対策として round(v,12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能を実装（None 値を除外）。
  - ファクター計算（factor_research）:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。過去スキャンレンジや必要行数不足時の None を考慮。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御やウィンドウ内カウント条件を考慮。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 / 欠損 の場合は None）。
  - 上記は DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番発注系には依存しない設計。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research で算出した生ファクターを統合・正規化して `features` テーブルへ保存する `build_features` を実装。
  - ユニバースフィルタを適用（最低株価 _MIN_PRICE = 300 円、20 日平均売買代金 _MIN_TURNOVER = 5e8 円）。
  - 正規化対象カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を zscore_normalize により標準化し、±3 でクリップして外れ値影響を抑制。
  - トランザクション + 日付単位の DELETE→INSERT による「日付単位の置換（冪等）」で atomic に書き込み。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - `generate_signals` を実装。features と ai_scores を統合し、最終スコア（final_score）を計算して signals テーブルへ書き込む。
  - コンポーネントスコア:
    - momentum: momentum_20, momentum_60, ma200_dev のシグモイド平均
    - value: PER を 20 を基準に 1/(1+per/20) で変換（低PERを高スコア）
    - volatility: atr_pct の Z スコアを反転してシグモイド化
    - liquidity: volume_ratio をシグモイド化
    - news: ai_score をシグモイド化（未登録は中立）
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
  - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を合成し、ユーザ指定重みは検証・正規化してマージ（合計が 1.0 になるよう再スケール）。
  - Bear レジーム判定: ai_scores の regime_score 平均が負で、かつサンプル数 >= _BEAR_MIN_SAMPLES（3）の場合に BUY を抑制。
  - SELL（エグジット）判定を実装:
    - ストップロス（終値/avg_price - 1 < -8%）
    - final_score が threshold 未満
    - 価格欠損時は SELL 判定をスキップして警告（誤クローズ防止）
    - features に存在しない保有銘柄は final_score = 0.0 と見なして SELL 対象にする旨のログ出力
  - BUY/SELL は signals テーブルに日付単位の置換で保存（トランザクション + バルク挿入）。
  - 設計上、トレーリングストップ・時間決済など一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。

- Strategy パッケージ公開 (src/kabusys/strategy/__init__.py)
  - build_features / generate_signals をパッケージ API としてエクスポート。

- execution パッケージ初期化 (src/kabusys/execution/__init__.py)
  - パッケージの初期化ファイルを追加（現状は空の placeholder）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース収集で defusedxml を使用するなど外部データパース時の安全性に配慮。
- news_collector にて受信バイト数上限を定義し、メモリ DoS に対策。

---

注:
- ドキュメント文字列や関数内コメントに設計上の方針や未実装項目が明記されています（例: トレーリングストップ等）。実運用時は該当テーブル・カラムの整備や追加実装が必要です。
- 本 CHANGELOG はコード内のドキュメントと実装から推定して作成しています。実際のリリースノート作成時はテスト結果やマイグレーション情報、互換性注意事項などを併せて記載してください。