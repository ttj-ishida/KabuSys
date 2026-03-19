# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは、パッケージバージョン（src/kabusys/__init__.py の __version__）とソースコードのコメントから推測して作成しています。

※ 日付はリリース日として推測で設定しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初期リリース。日本株自動売買システムのコア機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブモジュールをエクスポート）。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出：.git / pyproject.toml を基準）。
  - export KEY=val 形式やクォート/エスケープ、インラインコメント処理に対応した .env パーサ実装。
  - OS 環境変数を保護する上書き制御（.env.local は上書き、.env は未設定時のみ設定）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパ（_require）と型チェック（環境値の妥当性検証：KABUSYS_ENV / LOG_LEVEL）。
  - 設定アクセス用 Settings クラス（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス等）。

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（jquants_client）を実装
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大試行回数、HTTP 408/429/5xx を対象）。
    - 401 時の自動トークンリフレッシュ（1 回だけリトライ）。
    - ページネーション対応の fetch_* 関数（株価日足、財務、マーケットカレンダー）。
    - DuckDB へ冪等保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除。
    - 取得時刻を UTC ISO8601 で記録（fetched_at）し、Look-ahead バイアスのトレーサビリティを確保。
    - 型変換ユーティリティ（_to_float / _to_int）で安全に変換、欠損や不正値を None として扱う。
  - ニュース収集モジュール（news_collector）
    - RSS フィードから記事を収集し raw_news に保存する処理基盤。
    - URL 正規化（トラッキングパラメータ削除、ソート、フラグメント削除、小文字化）実装。
    - defusedxml を用いた XML パースで XML-Bomb 等の攻撃に備慮。
    - 受信サイズ上限（10 MB）や SSRF を防ぐスキーム制御、チャンク化によるバルク INSERT の最適化。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を保証。
- 研究（research）モジュール
  - factor_research
    - Momentum, Volatility, Value（PER/ROE）などのファクター計算実装。
    - prices_daily / raw_financials テーブルを参照し、mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe を算出。
    - ウィンドウ不足時の None 処理を実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）対応。
    - Information Coefficient（calc_ic）: スピアマンランク相関（ties は平均ランク）を実装。サンプル不足時は None を返す。
    - factor_summary（基本統計量：count/mean/std/min/max/median）実装。
    - rank ユーティリティ（同順位は平均ランク、浮動小数丸めで ties 検出の安定化）。
  - research パッケージのエクスポートを整理（calc_momentum 等を公開）。
- 戦略（strategy）モジュール
  - feature_engineering
    - research で算出した生ファクターを統合・正規化し features テーブルへ保存する機能（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - z-score 正規化（外部 zscore_normalize ユーティリティを利用）、±3 でクリップ。
    - 日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を確保（トランザクション使用）。
  - signal_generator
    - features と ai_scores を統合し最終スコア final_score を算出（重み付け合算、デフォルト重みあり）。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算：
      - momentum: momentum_20/momentum_60/ma200_dev のシグモイド平均
      - value: PER を 20 を基準に 1/(1+per/20) で変換
      - volatility: atr_pct の Z スコアを反転してシグモイド変換
      - liquidity: volume_ratio のシグモイド
      - news: ai_score のシグモイド（未登録は中立）
    - 重みのバリデーション（未知キーや不正値を無視）、合計が 1.0 でない場合は再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 -> BUY 抑制、サンプル数閾値あり）。
    - BUY シグナル閾値（デフォルト 0.60）、SELL（exit）ロジック：ストップロス（-8%）およびスコア低下。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、日付単位での置換による冪等性。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照。
- データ統計ユーティリティ（kabusys.data.stats を想定、zscore_normalize を利用可能にしていることをエクスポート）

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- news_collector で defusedxml を利用して XML パース攻撃に対策。
- RSS URL 正規化と受信上限（MAX_RESPONSE_BYTES）でメモリ DoS リスクを低減。
- jquants_client におけるトークン自動リフレッシュは allow_refresh フラグで無限再帰を防止。

### Known limitations / Notes
- signal_generator のトレーリングストップや時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date 情報が必要）。コード内で未実装としてコメントあり。
- calc_value は現状で PBR・配当利回りをサポートしていない（コメントとして未実装を明記）。
- news_collector の記事 ID は正規化 URL の SHA-256 の先頭 32 文字を使用しているため、将来的にハッシュ長などの仕様変更では互換性を要検討。
- J-Quants クライアントはネットワークエラー／HTTP エラーへのバックオフ・リトライを実装しているが、エッジケース（非常に高頻度の同一クライアント並列呼び出しなど）では別途レート制御の調整が必要な場合あり。

---

以上がコードベースから推測して作成した CHANGELOG.md（Keep a Changelog 準拠）の内容です。必要であれば、各変更点に対する具体的なコミット例や影響範囲（テーブル定義、環境変数一覧、外部依存ライブラリ）を追記します。どのレベルの詳細を追加しますか？