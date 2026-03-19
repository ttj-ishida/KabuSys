Keep a Changelog — 変更履歴
このファイルは Keep a Changelog のフォーマットに準拠しています。
https://keepachangelog.com/ja/1.0.0/

すべての変更はセマンティックバージョニングに従います。

Unreleased
- （なし）

[0.1.0] - 2026-03-19
Added
- 基本パッケージ初期実装
  - kabusys パッケージの公開 API を追加（kabusys.__init__ にて version=0.1.0、data/strategy/execution/monitoring をエクスポート）。
- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込みする機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォートのエスケープ、行内コメントの取り扱いなどに対応）。
  - .env.local を .env より優先して上書き（既存 OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須設定取得ヘルパー _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境（KABUSYS_ENV）とログレベルの入力検証を実装（許容値チェック・例外通知）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足データ、財務データ、マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - 固定間隔スロットリングによるレート制限制御（120 req/min を想定、モジュール内 RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
  - 401 受信時は自動でリフレッシュトークンを使って ID トークンを再取得し 1 回リトライする実装（無限再帰を防止）。
  - DuckDB への保存関数を実装（save_daily_quotes/save_financial_statements/save_market_calendar）。ON CONFLICT による冪等保存を実現。
  - 型安全な変換ユーティリティ (_to_float/_to_int) を実装（不正値は None）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の基盤実装（既定ソースに Yahoo Finance を追加）。
  - RSS 解析に defusedxml を使用し XML Bomb などの攻撃を軽減。
  - 受信バイト数上限（MAX_RESPONSE_BYTES）や SSRF 対策用 URL 検査、トラッキングパラメータ除去、URL 正規化処理を実装。
  - 記事ID生成（URL 正規化後の SHA-256 などを想定）・冪等保存・バルク挿入のチャンク化を考慮した設計。
- ファクター計算・リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value を提供し、prices_daily/raw_financials に基づく各種ファクターを算出。
  - calc_forward_returns（デフォルトホライズン [1,5,21]）を実装。範囲スキャンの最適化（カレンダーバッファ）あり。
  - calc_ic（Spearman の ρ）実装。ties の扱いは同順位平均ランク、丸め誤差対策のため round(..., 12) を適用。
  - factor_summary（count/mean/std/min/max/median）を実装。
  - 研究ユーティリティ（zscore_normalize を外部に依存せず提供する設計を反映）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを統合して features テーブルへ書き込む build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
  - Z スコア正規化を適用し ±3 でクリップ（外れ値抑制）。
  - 日付単位での置換（DELETE→INSERT をトランザクションでラップ）により冪等性・原子性を確保。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
  - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、閾値 0.60 を実装。ユーザー指定の weights を検証して合計 1.0 に再スケール。
  - コンポーネントスコア算出（シグモイド変換、欠損値は中立 0.5 で補完）や AI ニューススコアの統合（欠損時は中立）を実装。
  - Bear レジーム判定：ai_scores の regime_score 平均が負で、サンプル数が閾値以上（デフォルト 3）なら BUY を抑制。
  - エグジット判定（STOP-LOSS: -8% しきい値、スコア低下）を実装。保有銘柄で価格欠損時は SELL 判定をスキップして警告を出力。
  - signals テーブルへの日付単位置換（トランザクション）で冪等性を確保。
- ロギング / エラーハンドリング
  - 主要処理でのログ出力（info/debug/warning）と例外時のトランザクションロールバック処理を実装。ロールバック失敗時は警告を出力。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- RSS 解析に defusedxml を利用、RSS URL 正規化・トラッキングパラメータ除去、受信サイズ制限により外部入力に対する堅牢性を向上。
- J-Quants API のトークン扱いにおいて、自動リフレッシュ時の無限再帰を防止する設計を導入。

Notes / Known limitations
- 未実装機能（コード中に TODO/Note として記載あり）
  - signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - calc_value では PBR や配当利回りは未実装。
  - news_collector の記事 ID 生成や記事→銘柄の紐付け（news_symbols テーブルへの実装）は設計上言及されているが、現状のコードスナップショットでの実装状況は限定的。
- settings._require は未設定の必須環境変数に対して ValueError を送出するため、本番運用前に必要な環境変数が揃っていることを確認してください。
- DuckDB スキーマ（テーブル定義）は本リリースに含まれていないため、実行前に適切なスキーマを準備する必要があります。

開発者向け参考
- デフォルトの閾値や定数（例: 最低株価 300 円、最低売買代金 5e8、Z スコアクリップ ±3、STOP-LOSS -0.08、J-Quants レート制限 120 req/min 等）はソースコードの先頭定数で定義されています。調整はそこを変更してください。
- 外部 API 呼び出し（J-Quants）や DB 操作を含む関数は副作用が大きいためテスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD や DuckDB の一時 DB を利用して分離テストを推奨します。

作者注: 本 CHANGELOG は提供されたコードベースの内容と docstring から推測して作成しています。リリースノートとして公式に使う場合は実際のコミット履歴・差分に合わせて調整してください。