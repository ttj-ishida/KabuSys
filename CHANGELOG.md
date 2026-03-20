CHANGELOG
=========
すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- バージョン見出しは YYYY-MM-DD を含みます
- セクションは主に Added / Changed / Fixed / Deprecated / Removed / Security を使用します

Unreleased
----------
（なし）

0.1.0 - 2026-03-20
------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にバージョン定義と公開 API を追加。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする機能を実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装:
    - コメント行（#）や export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなしの値では、直前がスペース/タブの '#' をコメント扱い。
  - ファイル読み込み時の上書きルール:
    - OS 環境変数 > .env.local > .env の優先順位。
    - protected set により OS 環境変数の上書きを防止。
  - Settings クラスを提供し、以下の設定プロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装:
    - rate limiter（120 req/min 固定間隔スロットリング）、モジュールレベルのトークンキャッシュ。
    - リトライロジック: 指数バックオフ、最大3回（408/429/5xx、ネットワークエラー対応）。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - 取得時に fetched_at を UTC ISO8601 で記録（Look-ahead バイアス対策）。
    - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）でページネーション対応。
  - DuckDB への保存関数を実装（冪等性を確保するため ON CONFLICT を使用）:
    - save_daily_quotes: raw_prices テーブルに保存（PK 欠損行はスキップし警告を出力）。
    - save_financial_statements: raw_financials テーブルに保存（PK 欠損行はスキップ）。
    - save_market_calendar: market_calendar テーブルに保存（取引日/半日/SQ 日フラグを解釈）。
  - ユーティリティ変換関数 _to_float / _to_int を実装（安全な型変換と不正値排除）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存するモジュールを実装。
  - セキュリティ・耐障害性対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を防止。
    - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid 等）、スキーム/ホストの小文字化、フラグメント削除、クエリソート。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - SSRF 対策や非 HTTP(S) スキームの拒否を考慮（実装箇所に基づく）。
  - バルク INSERT のチャンク処理、INSERT RETURNING による挿入判定を想定した実装方針。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - モメンタム、ボラティリティ、バリュー ファクターを計算する関数を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日分のカウント検査）。
    - calc_volatility: atr_20, atr_pct, avg_turnover（20日平均売買代金）, volume_ratio（当日出来高 ÷ avg_volume）。
    - calc_value: target_date 以前の最新 raw_financials と prices_daily を組合せて per, roe を算出。
  - DuckDB の SQL を多用し、外部ライブラリ（pandas 等）に依存しない設計。
  - スキャン範囲やウィンドウサイズは定数で管理（200日/20日等）。

- 研究支援ユーティリティ（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用）。
  - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）計算（有効レコードが 3 件未満の場合 None を返す）。
  - rank: 同順位は平均ランクで扱うランク関数（丸めで ties 検出を安定化）。
  - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

- 特徴量生成（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を用いて raw factors を取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
    - 指定カラムを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ（_ZSCORE_CLIP = 3.0）。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等性を保証。
    - ユニバースフィルタ用に target_date 以前の最新終値を参照して欠損・休場日に対応。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features / ai_scores / positions テーブルを参照して最終スコア final_score を計算。
    - コンポーネントスコア:
      - momentum: momentum_20, momentum_60, ma200_dev の平均（シグモイド変換適用）
      - value: per に基づくスコア（per=20 -> 0.5、per→0 -> 1.0、per→∞ -> 0）
      - volatility: atr_pct の Z スコアを反転してシグモイド変換
      - liquidity: volume_ratio のシグモイド
      - news: ai_scores の ai_score をシグモイド（未登録は中立）
    - weights の検証・補完: _DEFAULT_WEIGHTS を基準に未知キーや不正値を破棄し、合計が 1.0 でなければ再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 のとき BUY を抑制。
    - BUY シグナルは threshold（デフォルト 0.60）を超える銘柄に付与（rank を付与）。
    - SELL シグナル（エグジット）判定:
      - ストップロス: (close / avg_price - 1) < -0.08（-8%）
      - スコア低下: final_score < threshold
      - positions の最新レコードを参照し、価格欠損時は SELL 判定をスキップして警告を出力。
    - SELL 対象銘柄は BUY から除外し、signals テーブルへ日付単位で置換保存（冪等）。

- strategy パッケージの公開 API（src/kabusys/strategy/__init__.py）
  - build_features, generate_signals を __all__ で公開。

Security
- news_collector で defusedxml を利用するなど、外部データ取り込み時にセキュリティ対策を考慮。
- J-Quants クライアントでトークン管理と自動リフレッシュの実装により不正アクセスや無限再帰を回避。

Known limitations / Notes
- SELL 判定の未実装項目（設計書に言及）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の情報が必要で、現版では未実装。
- research モジュールは pandas 等に依存しない純 SQL/標準ライブラリ実装のため、大量データ処理に対しては DuckDB の性能に依存。
- news_collector の SSRF や URL 検証は設計方針に基づいた実装を行っているが、運用環境での追加検証を推奨。
- .env パーサは多くの実用ケースに対応しているが、極端な形式の .env 行はスキップされることがある。

Migration notes
- 初期リリースのため既存リリースからの移行作業はありません。

Acknowledgements / References
- 各モジュールの docstring に記載された設計方針（StrategyModel.md, DataPlatform.md 等）に従って実装されています。

---
この CHANGELOG はソースコードからの実装・設計意図を基に作成しています。運用・リリース時には実際の変更履歴（コミットログ等）に合わせて更新してください。