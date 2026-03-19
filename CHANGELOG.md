# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
慣例: 変更は目的別に分類（Added / Changed / Fixed / Security / Removed / Deprecated / Notes）しています。

## [0.1.0] - 2026-03-19
初回リリース — 日本株の自動売買・データプラットフォームのコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの基本構成を追加。バージョンは `0.1.0`。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルパーサは以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート内でのバックスラッシュエスケープ
    - インラインコメントの扱い（クォート外での # を条件付でコメントと認識）
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル判定等のプロパティ）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限 (120 req/min) 制御。
  - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx に対するリトライ、429 の Retry-After 優先処理。
  - 401 発生時はリフレッシュトークンによる id_token 自動更新（1 回のみ）を実装。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）ユーティリティ:
    - save_daily_quotes、save_financial_statements、save_market_calendar。
  - レスポンスパースの堅牢化（数値変換ユーティリティ _to_float / _to_int 等）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する仕組み（デフォルトソース: Yahoo）。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去、スキーム/ホスト小文字化）。
  - defusedxml を使った XML パース、安全対策（XML Bomb 等の緩和）。
  - 受信バイト数上限（10MB）や SSRF を意識した URL フィルタリング、バルク INSERT チャンク化。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。

- 研究用ファクター計算 (kabusys.research)
  - ファクター計算モジュール群を実装:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（ウィンドウ要件あり）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - calc_value: PER / ROE（raw_financials の最新レコードを利用）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン計算（1 クエリで取得）。
    - calc_ic: スピアマンのランク相関（IC）計算、サンプル不足時は None を返却。
    - factor_summary: 各ファクター列の統計量（count, mean, std, min, max, median）。
    - rank: 同順位を平均ランクにするランク付け（丸めによる ties 対応）。
  - 研究モジュールは外部ライブラリに依存せず、DuckDB の prices_daily / raw_financials のみを参照。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で算出した raw ファクターをマージ → ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 正規化: 指定列の Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
  - features テーブルへ日付単位の置換（DELETE + バルク INSERT、トランザクションで原子性確保）。
  - build_features API を公開。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、signals テーブルへ保存する一連の処理を実装。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news（AI スコア）。
  - 重み付け管理: デフォルト重みを持ち、ユーザ提供重みは検証・補完・正規化（合計 1.0 に調整）。
  - Bear レジーム検知（ai_scores の regime_score 平均が負なら Bear。サンプル閾値あり）。
  - BUY シグナルは threshold（デフォルト 0.60）超で発行、Bear レジームでは BUY を抑制。
  - SELL シグナル（エグジット）:
    - ストップロス（終値 / avg_price - 1 < -8%）、
    - final_score が threshold 未満（score_drop）。
  - 保有ポジションの判定は positions / prices_daily を参照。価格欠損時は判定をスキップして安全性を優先。
  - signals テーブルへの日付単位置換（トランザクションで原子性確保）。
  - generate_signals API を公開。

- パッケージ API エクスポート
  - strategy パッケージから build_features / generate_signals を公開。
  - research パッケージから主要関数を公開。

### Changed
- （該当なし）初回リリースのため既存変更はありません。

### Fixed
- （該当なし）初回リリースのため不具合修正履歴はなし。

### Security
- news_collector で defusedxml を使用し XML 攻撃を緩和。
- RSS 受信で最大バイト数制限を導入しメモリ DoS を軽減。
- jquants_client の HTTP レスポンス処理で JSON デコードエラー時に詳細を報告するようにし、トークン操作の無限再帰を防止。

### Notes / Known limitations
- signal_generator のエグジットロジックで一部要件は未実装（ドキュメント記載）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）など
- news_collector の記事→銘柄紐付け（news_symbols 関連）は本バージョンでは実装の記述のみ（実運用のアタッチ処理は別実装が必要）。
- research モジュールは pandas 等を使わない純 Python 実装のため、非常に大規模データセットではパフォーマンスチューニングが必要になる可能性あり。
- jquants_client のレートリミッタは固定間隔スロットリングを採用しており、バースト対応が必要な場合は改善検討。

---

今後のリリースで予定している改善（例）
- execution 層の実装（kabu ステーション / 発注 API 統合）
- モニタリング / アラート機能の強化（Slack 通知統合の実装）
- features / signals のバリデーションとユニットテスト充実
- news_collector の記事→銘柄自動マッチング精度向上（NLP を利用した分類など）

（終）