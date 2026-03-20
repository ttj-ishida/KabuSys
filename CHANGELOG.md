Keep a Changelog に準拠した CHANGELOG
（内容はソースコードからの推測に基づき日本語で記載しています）

フォーマット方針:
- 各リリースごとに主要な追加・変更・修正・セキュリティ関連を記載しています。
- 小項目はモジュール名 / 関数名を明記しています。

Unreleased
- なし

[0.1.0] - 2026-03-20
追加 (Added)
- 全体
  - 初期公開バージョン 0.1.0 を追加。
  - パッケージ名: kabusys、パッケージ変数 __version__ = "0.1.0" を設定。トップレベルのエクスポート: data, strategy, execution, monitoring。

- 環境設定: src/kabusys/config.py
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: ファイル位置から上位ディレクトリを探索し .git または pyproject.toml を検出してルートを特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート（クォート内のインラインコメントを無視）。
    - クォートなしの値では '#' の前がスペース/タブの場合のみコメント扱い。
    - 無効行はスキップ。
  - _load_env_file により既存 OS 環境変数を保護する protected 引数を導入し、.env.local での上書き制御を可能に。
  - Settings クラスを実装し、環境変数から各種設定を取得:
    - 必須設定の取得時に未設定なら ValueError を投げる _require() を利用。
    - J-Quants / kabu API / Slack / データベース（DuckDB/SQLite）などのプロパティを提供。
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）と LOG_LEVEL の検証（DEBUG/INFO/...）を実装。
    - is_live / is_paper / is_dev の便宜プロパティを提供。

- データ取り込みクライアント: src/kabusys/data/jquants_client.py
  - J-Quants API クライアントを実装:
    - 固定間隔のレートリミッタ（120 req/min）を実装（_RateLimiter）。
    - HTTP リクエストに対するリトライロジック（指数バックオフ、最大 3 回）を実装。429 の場合は Retry-After ヘッダを尊重。再試行対象ステータスは 408/429/5xx。
    - 401 を検出した場合にリフレッシュトークンから ID トークンを自動更新して 1 回だけリトライする仕組みを導入（無限再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装し、pagination_key による繰り返し取得を行う。
    - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。DuckDB へ INSERT ... ON CONFLICT (PK) DO UPDATE による冪等保存を行う。
    - 取得時刻（fetched_at）を UTC ISO 形式で記録し、look-ahead バイアスのトレースを可能に。
    - 型安全な変換ユーティリティ _to_float / _to_int を実装（不整合値は None に変換）。

- ニュース収集: src/kabusys/data/news_collector.py
  - RSS フィードから記事を取得・正規化して raw_news へ保存する仕組みを実装。
    - defusedxml を利用した XML 解析で XML Bomb 等の攻撃を軽減。
    - 受信最大バイト数（MAX_RESPONSE_BYTES = 10MB）で応答サイズを制限。
    - URL 正規化 (_normalize_url): スキーム/ホスト小文字化、トラッキングパラメータ (utm_*, fbclid, gclid, ref_, _ga 等) の除去、フラグメント削除、クエリキーでソート。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を採用し冪等性を確保する設計方針を記載。
    - HTTP スキーム検証や SSRF 対策（IP/ホスト検査）などのセキュリティ方針を実装方針で明記。
    - DB 保存は 1 トランザクションにまとめ、チャンクサイズでバルク挿入を行う設計（_INSERT_CHUNK_SIZE による分割）。
    - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを設定。

- ファクター計算（研究）: src/kabusys/research/factor_research.py
  - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を計算。足りないウィンドウは None。
    - calc_volatility: 20 日 ATR（true_range を正しく扱う）、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を算出（EPS 欠損や 0 は None）。
  - DuckDB のウィンドウ関数を活用し、対象テーブル only（prices_daily / raw_financials）で完結する設計。

- 特徴量エンジニアリング: src/kabusys/strategy/feature_engineering.py
  - build_features(conn, target_date) を実装:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを zscore 正規化（kabusys.data.stats.zscore_normalize を利用）、Z スコアを ±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で削除→挿入するトランザクションによる置換（冪等）を行う。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を用いたフィルタリングを実装。

- シグナル生成: src/kabusys/strategy/signal_generator.py
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features / ai_scores / positions を参照して final_score を計算。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を個別計算するユーティリティを実装（_sigmoid, _avg_scores, 各 _compute_*）。
    - weights のマージ、検証、合計が 1.0 でない場合のリスケーリング処理を実装。無効なユーザー指定重みはスキップ。
    - AI スコア（ai_scores）を受け取り、未登録銘柄は中立（0.5）で補完。レジームスコアを集計して Bear レジームを検知すると BUY シグナルを抑制。
    - BUY シグナルは threshold を超えた銘柄に付与（Bear 時は抑制）。SELL シグナルは保有ポジションに対してストップロス（-8%）／スコア低下で判定。
    - 未実装だが将来的に導入予定のエグジット条件（トレーリングストップ、時間決済）をコード内に注記。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）で冪等性を保証。
    - SELL 優先ポリシーにより SELL 対象は BUY から削除し、BUY のランクを再付与。

- 研究支援ツール: src/kabusys/research/feature_exploration.py
  - calc_forward_returns(conn, target_date, horizons=[1,5,21]) を実装: 指定ホライズンの将来リターンを一括で計算（LEAD を利用）。horizons の検証（正の整数かつ <=252）を実施。
  - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装。ties は平均ランクで処理。有効サンプル数 < 3 は None を返す。
  - rank(values): ランク計算で round(..., 12) による丸めを行い浮動小数点の ties 検出漏れを防止。
  - factor_summary(records, columns): count/mean/std/min/max/median を計算するユーティリティを実装（None 値は除外）。

- パッケージのエクスポート
  - src/kabusys/research/__init__.py、src/kabusys/strategy/__init__.py による主要 API export を用意（calc_momentum 等、build_features, generate_signals）。

改善/仕様注記 (Notes / Known limitations)
- generate_signals の SELL 判定には「トレーリングストップ」「時間決済（保有 60 営業日超過）」が未実装（positions テーブルに peak_price / entry_date が必要であり、将来的な追加が予定されている）。
- news_collector のデフォルト RSS ソースは限定的（現状は Yahoo の business カテゴリ）。実運用ではソース一覧の拡張が想定される。
- 外部依存を最小化する方針（pandas 等未使用）で実装されているため、データ処理は純粋な SQL/標準ライブラリベースで記述されている。
- DuckDB スキーマ（テーブル列名/PK など）はコード側の期待に依存している（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）。実行環境では該当スキーマが存在することが前提。

セキュリティ (Security)
- news_collector: defusedxml を利用、受信サイズ制限、トラッキングパラメータ除去、HTTP スキーム検証によりある程度の入力攻撃/SSRF/DoS 対策を取り入れている旨を明記。
- jquants_client: 401 での自動トークンリフレッシュ時に無限再帰を防ぐ設計を実装。

その他ログ/運用
- 多くの処理箇所で logger を利用し INFO/WARNING/DEBUG レベルのログ出力を行うよう実装されている（例: fetch/save 関数、build_features, generate_signals の進捗ログ）。
- config の LOG_LEVEL / KABUSYS_ENV に対するバリデーションで誤設定を早期検出する。

以上

（注: 本 CHANGLEOG は提供されたソースコード内容を基に機能・設計・既知制限を推測して作成しています。実際のリリースノート作成時はコミット履歴や CHANGELOG 元情報を合わせて調整してください。）