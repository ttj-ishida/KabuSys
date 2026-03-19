# CHANGELOG

すべての notable な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、本 CHANGELOG は提示されたソースコードの内容から機能・挙動を推測して作成しています。

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージ基盤
  - パッケージ名を kabusys として初期リリース（__version__ = 0.1.0）。
  - パッケージ公開用の __all__ を設定（data, strategy, execution, monitoring をエクスポート）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - 読み込みは OS 環境変数を優先し、.env.local は .env を上書きする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途を想定）。
  - .env のパース機能を強化（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応）。
  - Settings クラスを提供し、必須環境変数取得時の検証・例外処理を実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
  - 環境種別 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証を実装。is_live / is_paper / is_dev のユーティリティプロパティを提供。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）を Path として扱う。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限対策として固定間隔スロットリング（120 req/min）を実装（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx に対してリトライを行う。
  - 401 Unauthorized を検知した場合、リフレッシュトークンを用いた id token 自動リフレッシュを 1 回試行してリトライする仕組みを実装。
  - ページネーション対応の fetch_* 関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等保存を実現。
  - レスポンス→DB 格納時の型変換ユーティリティ（_to_float / _to_int）を実装。PK 欠損行はスキップしてログ出力。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の基礎実装を追加（デフォルトで Yahoo Finance のビジネス RSS を参照）。
  - テキスト前処理・URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減する方針を採用。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）や SSRF 対策を想定した実装方針を記載。
  - DB 挿入はバルクチャンク化して効率化（チャンクサイズ制限を導入）。

- 研究用モジュール (kabusys.research)
  - ファクター計算（factor_research）を実装:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
    - バリュー (calc_value): raw_financials と価格から PER/ROE を計算。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日不連続やデータ不足に対する保護を実装。
  - 特徴量探索 (feature_exploration) を実装:
    - 将来リターン calc_forward_returns（複数ホライズン対応、最大 252 日の検証）。
    - 情報係数（IC） calc_ic（Spearman の ρ ランク相関、同順位は平均ランク処理）。
    - factor_summary（count/mean/std/min/max/median）や rank ユーティリティを実装。
  - 研究モジュール群は外部ライブラリ（pandas 等）に依存しない設計。

- 戦略用モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research の calc_* を統合して features テーブル用の正規化済み特徴量を生成。
    - ユニバースフィルタ（最低株価、最低平均売買代金）を適用。
    - 指定列を Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位での置換（DELETE + INSERT）により冪等処理を保証。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重みの取り扱い（無効な入力値は無視、合計で再スケール）を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数閾値以上で判定）により BUY を抑制。
    - BUY シグナルは閾値（デフォルト 0.60）超で生成。SELL はストップロス（-8%）およびスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、および日付単位の置換挿入で冪等性を保証。
    - 無効または欠損するコンポーネントスコアは中立値 0.5 で補完して過度な降格を防止。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- news_collector で defusedxml を採用、受信バイト数制限や URL 正規化等を設計方針に含めることで外部入力に対する基本的な防御を実装。

### 既知の制限・未実装の機能 (Known limitations / Notes)
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要であり、現バージョンでは未実装。
- news_collector の完全な SSRF 防御や HTTP レスポンス読み込み・パースの実装詳細は設計方針に示されているが、提示コードは一部（フェッチ/パースの全処理）を省略している可能性がある。
- 一部ユーティリティ（zscore_normalize など）は別モジュール（kabusys.data.stats）に依存しており、当該モジュールの実装に依存して正常動作する。
- J-Quants クライアントはネットワーク呼び出しを行うため、実行環境のネットワーク設定や API トークンの設定が必要。

---

今後の開発で取り組む想定タスク（例）
- positions テーブルを拡張してトレーリングストップと時間決済を実装
- news_collector の完全な取得・パース・銘柄紐付けの実装とテスト
- モジュール間のエンドツーエンド統合テストおよび CI 設定
- ドキュメント整備（StrategyModel.md / DataPlatform.md などの参照文書の整備）

（以上）