CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初回リリース。モジュール群を追加。
- パッケージメタ
  - kabusys パッケージを導入。__version__ = 0.1.0、主要サブモジュールを __all__ で公開（data, strategy, execution, monitoring）。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサー実装（コメント、export プレフィックス、クォートとエスケープ対応、インラインコメント処理等）。
  - Settings クラスを提供し、必須環境変数の取得・検証（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）、パスの Path 型変換、KABUSYS_ENV / LOG_LEVEL のバリデーション補助プロパティ（is_live / is_paper / is_dev）を実装。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔の RateLimiter（120 req/min）を実装してレート制限を順守。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）を実装。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュを実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT / DO UPDATE）。
  - 入力パース用ユーティリティ (_to_float, _to_int) を追加し、不正値を安全に None に変換。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集基盤を追加。既定ソースに Yahoo Finance のカテゴリ RSS を登録。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）実装。
  - メモリ DoS 防止のため受信バイト数上限（MAX_RESPONSE_BYTES）を設定。
  - XML 解析に defusedxml を利用して XML Bomb 等への対策を実施。
  - SSRF 対策指針・受信スキーム制限など設計コメントを追加。
  - raw_news への冪等保存方針（ON CONFLICT DO NOTHING）や記事 ID の SHA-256 ベース生成方針を記載。
- 研究（research）モジュール
  - factor_research: モメンタム / ボラティリティ / バリュー（PER, ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。すべて DuckDB の prices_daily / raw_financials を参照する設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、基本統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージ __init__ で主要ユーティリティを再公開。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究で算出した生ファクターを取り込み、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 指定カラムを Z スコア正規化（zscore_normalize 利用）し ±3 でクリップ。features テーブルへ日付単位で置換（トランザクション + バルク挿入）する build_features を実装（冪等）。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
  - コンポーネントを重み付き合算して final_score を算出（デフォルト重みを定義）。weights 引数で上書き可能。合計が 1.0 になるよう正規化。
  - Bear レジーム判定（ai_scores の regime_score 平均が負）に基づく BUY 抑制。
  - BUY シグナル閾値（デフォルト 0.60）以上の銘柄に BUY を生成。SELL は保有ポジションに対するストップロス（-8%）およびスコア低下で判定。
  - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）する generate_signals を実装（冪等）。
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止する設計。
- API エクスポート
  - strategy パッケージのトップレベルから build_features / generate_signals を公開。

Security
- defusedxml を用いた RSS XML の安全な解析を採用。
- ニュース収集で受信バイト数上限を設定してメモリ DoS を防止。
- URL 正規化とトラッキングパラメータ除去を実装し、記事 ID の安定化および重複検出を容易に。
- J-Quants クライアントでタイムアウト設定・限定的な再試行・レート制御を実装。

Notes / Known limitations / TODO
- signal_generator にて記載の通り、以下のエグジット条件は未実装（コメントあり）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- calc_value は PBR・配当利回りを現バージョンでは未実装（コメントあり）。
- news_collector モジュールは設計上の安全対策を多く含むが、RSS のパース/収集フロー全体は将来の拡張でさらに堅牢化可能（例: ソースごとのカスタムパーサー、非同期収集等）。
- get_id_token は settings.jquants_refresh_token に依存。適切な環境変数設定が必須。
- .env 自動読み込みはプロジェクトルートを探索するため、パッケージ配布後などでルートが特定できない場合は自動ロードをスキップする（設計上の挙動）。
- DuckDB のテーブルスキーマや positions / features / ai_scores / raw_* テーブルの事前準備（カラム定義）は本リリースに含まれない。これらのテーブルは運用前にスキーマを作成する必要がある。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed / Deprecated
- 初回リリースのため該当なし。

連絡・貢献
- バグ報告や機能提案は issue を立ててください。