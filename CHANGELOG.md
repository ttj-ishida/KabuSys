CHANGELOG
=========
すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------
（現在の開発中の変更はここに記載）

[0.1.0] - 2026-03-21
--------------------

Added
- 初回リリース: 日本株自動売買システム "KabuSys" のコア機能を追加
  - パッケージ初期化とバージョン情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - export KEY=val, クォート/エスケープ、インラインコメント等に耐性のある .env パーサを実装。
      - 必須環境変数取得用 _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* 等）。
      - KABUSYS_ENV / LOG_LEVEL の値検証、便宜的プロパティ（is_live / is_paper / is_dev）を追加。
  - データ取得・保存（J-Quants API クライアント）
    - src/kabusys/data/jquants_client.py
      - API レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
      - リトライ（指数バックオフ、最大3回）と 429 の Retry-After 優先処理、408/429/5xx を再試行対象に。
      - 401 発生時は自動でトークンをリフレッシュ（1 回）して再試行する仕組みを実装。
      - ページネーション対応の fetch_* 系（株価/財務/カレンダー）、および DuckDB への冪等保存 save_*（ON CONFLICT / DO UPDATE）を実装。
      - 型変換ユーティリティ _to_float / _to_int を追加。
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィード収集・正規化・raw_news への冪等保存機能を実装。
      - 記事 ID は正規化後の URL の SHA-256 ハッシュ（先頭32文字）を使用して冪等性を確保。
      - defusedxml を用いて XML 攻撃対策、受信サイズ制限（MAX_RESPONSE_BYTES）、SSRF を避けるためスキーム検査等の安全対策を実装。
      - トラッキングパラメータ除去・URL 正規化ロジックを実装。
  - リサーチ（ファクター計算・解析）
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value（PER, ROE など）ファクター計算を DuckDB（prices_daily / raw_financials）上で実装。
      - 各ファンクションは date, code キーの dict リストを返す設計。
      - ATR、移動平均、windows の不足時の None ハンドリング等を考慮。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（Spearman の ρ）計算 calc_ic、factor_summary、rank 等の統計ユーティリティを実装。
      - pandas など外部依存を使わない実装。
    - src/kabusys/research/__init__.py に主要 API を公開。
  - 特徴量エンジニアリング
    - src/kabusys/strategy/feature_engineering.py
      - 研究環境で算出した raw factor を結合・ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）で絞り込み、指定カラムを z-score 正規化（zscore_normalize を利用）して ±3 でクリップ後、features テーブルへ日付単位の置換（トランザクション + バルク挿入）で保存する処理を実装。
      - ルックアヘッドを防止するため target_date 時点のデータのみ参照する設計。
  - シグナル生成
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して最終スコア final_score を計算。重み付け（デフォルト: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（デフォルト 0.60）で BUY シグナルを生成。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、ただしサンプル閾値あり）で BUY を抑制。
      - エグジット（SELL）判定（ストップロス -8%・スコア低下）を実装。保有ポジションの価格欠損や features 欠如時の安全策あり。
      - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）で保存。SELL 優先のポリシーで BUY から除外し順位を再付与。
  - 内部ユーティリティ・安全化
    - SQL 実行は適切にトランザクションで囲み、例外時に ROLLBACK を試みる。
    - None/NaN/Inf の扱い、欠損データに対する中立補完（0.5）など保守性の高い設計。
    - ロギングメッセージを各所に配置して運用観察を支援。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Security
- news_collector: defusedxml による XML 攻撃対策、受信サイズ制限、SSRF 回避のためのスキーム制限などを実装。
- jquants_client: トークン自動リフレッシュ、再試行制御により認証・通信エラーへの堅牢性を強化。

Notes / Implementation details
- DuckDB 上のテーブル名（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）を前提とした処理になっています。データベーススキーマの準備が必要です。
- .env パーシングはかなり寛容に実装していますが、意図しない値を防ぐため重要な環境変数は Settings で必須化しています。
- AI スコア（news / regime）は存在しない場合にも動作するよう中立値で補完します（シグナルの過度な偏りを防ぐ目的）。
- 将来的な拡張候補（実装メモ）
  - signal_generator: トレーリングストップや保有日数による時間決済は positions に peak_price / entry_date 情報が必要であり未実装。
  - news_symbol（ニュース→銘柄紐付け）や Slack 通知、execution 層（実際の注文送信）は別モジュールとして予定。

Acknowledgements
- 本リリースは内部仕様書（StrategyModel.md, DataPlatform.md 等）に基づいて実装されています。実運用前にデータスキーマ・環境変数・外部 API の動作確認を推奨します。