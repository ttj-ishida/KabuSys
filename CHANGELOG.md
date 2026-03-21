Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
バージョン履歴はコードベース（src/ 以下）から推測して作成しています。

[0.1.0] - 2026-03-21
-------------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 / .env ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサ実装: コメント・export 句・シングル/ダブルクォート・エスケープを考慮して安全にパース。
  - .env の読み込みは OS 環境変数を保護する仕組み（protected set）を持ち、.env.local は上書きが可能。
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、環境種別、ログレベル等）。
  - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と利便性メソッド（is_live / is_paper / is_dev）。

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装：
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - API レート制御（120 req/min 固定間隔スロットリング）。
    - リトライ（指数バックオフ、最大 3 回）、ステータス 408/429/5xx に再試行、429 の Retry-After を尊重。
    - 401 応答時は自動でリフレッシュトークンから ID トークンを再取得して 1 回リトライ。
    - ページネーション間で使うモジュールレベルのトークンキャッシュ。
  - DuckDB へ冪等に保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を提供：
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡のため）。
    - ON CONFLICT / DO UPDATE を用いた冪等保存。
    - 入力整形ユーティリティ _to_float / _to_int を提供し不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - デフォルト RSS ソースの定義と RSS 収集設計（URL 正規化、トラッキングパラメータ除去、content 前処理）。
  - セキュリティ考慮点：
    - defusedxml を用いて XML 関連の攻撃を緩和。
    - 受信サイズ上限（MAX_RESPONSE_BYTES, 10MB）を設けてメモリ DoS を防止。
    - URL 正規化とトラッキングパラメータ削除のユーティリティを実装。
  - raw_news への冪等保存（ON CONFLICT / DO NOTHING）や銘柄紐付け（news_symbols）を想定した設計。

- リサーチ / ファクター計算（kabusys.research, research.factor_research）
  - ファクター計算モジュール群を実装：
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算。
  - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計（外部発注 API への依存なし）。
  - calc_forward_returns, calc_ic, factor_summary, rank 等の探索用ユーティリティを提供：
    - calc_forward_returns: 複数ホライズンの将来リターンを一度に取得（LEAD ウィンドウ利用）。
    - calc_ic: Spearman のランク相関（IC）を実装（有効サンプル < 3 は None を返す）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位は平均ランクで処理（浮動小数の丸めで ties を安定検出）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究用ファクター（research モジュール出力）を統合し features テーブルへ保存するパイプラインを実装：
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）後 ±3 でクリップ。
    - 日付単位の置換（DELETE + INSERT をトランザクション内で実行）により冪等性を担保。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して各銘柄の final_score を計算し BUY/SELL シグナルを生成：
    - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算（sigmoid 等を利用）。
    - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10。入力 weights の検証・正規化を行う。
    - BUY 閾値 default = 0.60。
    - Bear レジーム検知: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル数閾値あり）。
    - SELL（エグジット）判定の実装:
      - ストップロス: 現在終値が平均取得価格から -8% を下回る場合即時 SELL。
      - スコア低下: final_score が閾値未満の場合に SELL。
      - SELL 対象は BUY から除外し、ランク付けを再付与。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を担保。

- DB 操作の原子性・効率化
  - 各種書き込み操作はトランザクションとバルク挿入で原子性を担保。
  - 重複管理に ON CONFLICT（DuckDB 想定）を使用。

Security
- defusedxml の採用、受信バイト数上限、URL 正規化、.env ファイル読み込みの警告や保護など、外部入力に対する基本的なセーフガードを導入。

Notes / Known limitations
- 未実装機能（コード内コメントとして明示）:
  - signal_generator: トレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - calc_value: PBR・配当利回りは現バージョンで未実装。
  - news_collector: コメントに示された記事 ID 生成（URL 正規化後の SHA-256）や銘柄紐付けの完全実装は想定されているが、一部処理は完成度に差がある可能性あり（コードベースの範囲で実装済みのユーティリティは存在）。
- execution パッケージは初期化ファイルのみで、発注ロジック（kabu API 連携等）は別途実装が必要。
- DuckDB スキーマ（テーブル定義）は本 CHANGELOG の対象外だが、コードは特定のテーブル構造（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals など）を前提としている。
- 一部の数値パラメータ（閾値や日数）はハードコードされている（将来的に設定化する余地あり）。

未定義 / 将来の改善案（参考）
- 設定を外部化してファクター重み・閾値を運用時に変更可能にする。
- 発注層（execution）の実装・テストおよび安全ガードの強化（注文追跡、注文再試行、部分約定処理など）。
- 単体テスト / 結合テストの追加（特に DB トランザクション周り、API リトライロジック、ニュースパーシングの堅牢性）。
- メトリクス・モニタリング（monitoring パッケージの充実）。

ライセンスや著者情報はソースに含まれていないため本 CHANGELOG には記載していません。

---
（この CHANGELOG は src/ 以下の実装内容から推測して作成しました。実際のリリースノート作成時はコミット履歴・PR/Issue の情報を参照してください。）