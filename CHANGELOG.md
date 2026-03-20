Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。

注意: 実際のコミット履歴ではなく、提供されたコード内容から機能追加・仕様を推測してまとめた「初回リリース」向けの CHANGELOG です。

# CHANGELOG

すべての注目に値する変更はこのファイルで記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [0.1.0] - 2026-03-20

### Added
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージ公開用 __init__ を実装（data/strategy/execution/monitoring を公開）。

- 環境変数 / 設定管理 (kabusys.config)
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）。
  - .env / .env.local の自動読み込み（OS 環境変数を優先、.env.local は override）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env の行パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート対応（バックスラッシュエスケープ処理含む）。
    - インラインコメント処理（クォート有無で挙動を分離）。
  - Settings クラスを提供（J-Quants トークン、Kabu API、Slack、DB パス、環境モード、ログレベル等のプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性検証と便利な is_live/is_paper/is_dev プロパティ。

- データ取得 / 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔のレートリミッタ実装（120 req/min 相当のスロットリング）。
  - リトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュ対応。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 変換ユーティリティ (_to_float, _to_int) 実装。
  - 取得時刻 (fetched_at) を UTC で記録し Look-ahead バイアスの追跡を容易に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集用モジュールを実装。
  - URL 正規化機能（トラッキングパラメータ除去、ソート、フラグメント除去、スキーム/ホストの小文字化）。
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）を使用して冪等性を確保。
  - defusedxml による XML Bomb 対策、受信バイト数上限（10MB）などの DoS 対策。
  - SSRF 対策や HTTP スキーム制限を想定した設計（注釈あり）。
  - bulk insert のチャンク処理と INSERT RETURNING による正確な挿入数管理。
  - デフォルト RSS ソースとして Yahoo Finance を定義。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均のカウントチェックあり）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播に配慮）
    - calc_value: per, roe（raw_financials の最新レポートから取得）
  - DuckDB のウィンドウ関数を活用して効率的に集計。
  - 欠損・データ不足時の None ハンドリング。

- 研究支援ツール (kabusys.research.feature_exploration)
  - 将来リターン計算 (calc_forward_returns): 任意ホライズン（デフォルト [1,5,21]）に対応、スキャン範囲最適化あり。
  - IC（Information Coefficient）計算 (calc_ic): スピアマンランク相関、同順位（ties）を平均ランクで処理。
  - rank ユーティリティ: 同順位の平均ランク処理（丸め対策付）。
  - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で計算した raw factor を正規化・合成して features テーブルへ保存する build_features 実装。
  - ユニバースフィルタ実装:
    - 最低株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - zscore_normalize 利用、±3 でクリップ、日付単位での置換（トランザクションで冪等）。
  - target_date 時点のデータのみを使用する設計（ルックアヘッドバイアス対策）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し signals テーブルへ書き込む generate_signals 実装。
  - コンポーネントスコアの計算:
    - momentum（momentum_20/momentum_60/ma200_dev を平均）
    - value（PER を 20 を基準に変換）
    - volatility（atr_pct の逆符号をシグモイド化）
    - liquidity（volume_ratio のシグモイド）
    - news（AI スコアのシグモイド、未登録は中立補完）
  - スコア正規化にシグモイド関数を使用、重みのマージ・検証・再スケール実装（デフォルト重みを定義）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）で BUY を抑制。
  - BUY 閾値デフォルト 0.60、SELL のエグジット条件実装:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満（score_drop）
  - positions / prices を参照して SELL 判定を行い、SELL 優先で BUY から除外。
  - 日付単位で signals テーブルを置換（トランザクションで冪等性を保証）。
  - _generate_sell_signals を分離してロジックを整理。

- モジュールエクスポート整備
  - kabusys.research / kabusys.strategy の __init__ で主要 API を公開。

### Security
- news_collector で defusedxml を利用し XML 攻撃を軽減。
- news_collector で受信バイト数上限やスキーム制約、トラッキングパラメータ除去など複数の安全対策を実装。
- J-Quants クライアントで 401 時にトークン自動更新を行うための安全ガード（allow_refresh フラグで無限再帰を回避）。

### Notes / Known limitations
- execution パッケージは空であり、発注実装（kabu ステーション連携等）は未実装。
- SELL 条件の一部（トレーリングストップ、時間決済）はコメントで未実装として明記。これらは positions テーブルに peak_price / entry_date 等の追加情報が必要。
- news_collector の RSS ソースはデフォルトで 1 件（Yahoo）に限定。実運用では追加設定が想定される。
- J-Quants のリトライの対象ステータスは一部（408, 429, 5xx）に限定。アプリ要件により拡張の余地あり。
- DuckDB スキーマ（テーブル定義）はこの変更履歴に含まれておらず、スキーマ整備は別途必要。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

今後のリリースで予定される項目（提案）
- execution 層の実装（kabu ステーションとの注文送信 / 約定確認 / 再試行制御）。
- SELL ロジックの拡張（トレーリングストップ、時間決済など）。
- news_collector の追加 RSS ソース管理や記事と銘柄紐付けの精度向上（NLP によるシンボル抽出）。
- テストカバレッジの拡充・CI による自動テスト、DuckDB スキーマのバージョニング対応。

--- 

必要であれば、この CHANGELOG を英語版に翻訳したり、各項目をさらに細分化してコミット/PR 単位のエントリへ展開できます。どの形式がよいか指示してください。