CHANGELOG
=========

すべての重要な変更点は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の方針に従って記載しています。  
バージョン番号はパッケージの __version__ に合わせています。

Unreleased
----------

- なし

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 基本パッケージ構成を実装
  - パッケージルート: kabusys（data, strategy, execution, monitoring を公開）。
- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数から設定を読み込む自動ロードを実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、カレントワーキングディレクトリに依存しない挙動。
  - .env パースは export プレフィックス・クォート・インラインコメント・エスケープに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得時の _require による明示的エラー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - 環境値の検証: KABUSYS_ENV（development, paper_trading, live のみ許可）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可）。
  - データベースパス設定 (DUCKDB_PATH, SQLITE_PATH) を Path 型で返すユーティリティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しラッパー _request を実装。JSON デコードエラーの明示的ハンドリング。
  - 固定間隔レートリミッタ（120 req/min）を実装（モジュール内 _RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）と 408/429/5xx の再試行処理。
  - 401 受信時は自動でトークンをリフレッシュして 1 回だけ再試行する挙動。トークンはモジュールレベルでキャッシュ（_ID_TOKEN_CACHE）。
  - ページネーション対応のフェッチ関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数（冪等実装、ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 値変換ユーティリティ (_to_float / _to_int) を用いて不正データに対処。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news へ保存するためのユーティリティを実装。
  - セキュリティ設計: defusedxml を用いた XML パース、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、HTTP スキーム検証など。
  - URL 正規化ロジックを実装: トラッキングパラメータ除去（utm_*, fbclid, gclid 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で冪等性を確保。
  - バルク INSERT のチャンク化、トランザクションを用いた効率的な保存と挿入件数の正確な取得。

- リサーチ用ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - calc_volatility（atr_20、atr_pct、avg_turnover、volume_ratio）
    - calc_value（per、roe。raw_financials の最新レコードを参照）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) キーの dict リストを返す。
    - データ不足（ウィンドウ未満等）は None を返す設計。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得、horizons 検証あり）
    - calc_ic（Spearman ランク相関による IC 計算、サンプル不足時は None）
    - factor_summary（count/mean/std/min/max/median）
    - rank（平均ランクを扱う tie 処理。round(v, 12) を用いた同値検出）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
  - 指数: Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
  - 日付単位で features テーブルへ置換（DELETE + bulk INSERT をトランザクション内で実行）し冪等性を確保。
  - universe 条件: _MIN_PRICE = 300 円、_MIN_TURNOVER = 5e8 円。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news（AI）
    - momentum はシグモイド変換後の平均、value は PER からの逆変換
    - volatility は atr_pct の逆符号をシグモイド化して低ボラ＝高スコアに変換
  - 重み付けの取り扱い:
    - デフォルト重みを提供（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
    - ユーザ指定 weights は検証後にデフォルトとマージ、合計が 1 でない場合は再スケール
    - 無効なキー・値はスキップして警告ログを出す
  - Bear レジーム検出:
    - ai_scores の regime_score の平均が負の場合に Bear と判定（サンプル数が _BEAR_MIN_SAMPLES 未満なら Bear 判定しない）
    - Bear 時は BUY シグナルを抑制
  - BUY シグナル閾値デフォルト: 0.60
  - SELL（エグジット）ルール:
    - ストップロス: 終値 / avg_price - 1 < -0.08（-8%）
    - final_score が閾値未満 → score_drop
    - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換（トランザクション）
  - 生成結果は signals テーブルへ書き込み、関数は書き込み件数を返す。

Changed
- 初版のため該当項目なし。

Fixed
- 初版のため該当項目なし。

Deprecated
- 初版のため該当項目なし。

Removed
- 初版のため該当項目なし。

Security
- news_collector で defusedxml を利用し XML 実行攻撃を軽減。
- RSS ダウンロード時の最大受信サイズ制限を導入（メモリ DoS 対策）。
- URL 正規化とスキーム検証で SSRF リスク低減。

注意事項 / 既知の制約
- データベーススキーマ依存:
  - 多くの処理は DuckDB 上の特定テーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）を前提とする。これらのスキーマが期待通りでない場合はエラーや不整合が発生します。
  - save_* 系は ON CONFLICT に依存した列を利用しているため、PK/UNIQUE 制約が必要。
- 自動 .env ロード:
  - パッケージはデフォルトでプロジェクトルートの .env / .env.local を自動で読み込みます。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- トークンキャッシュ:
  - J-Quants の ID トークンはモジュールレベルでキャッシュされます（ページネーションや複数フェッチで共有）。マルチプロセス環境ではプロセス間で共有されません。
- エラーハンドリング:
  - 一部の集計・ファクター計算はデータ不足時に None を返す設計です（欠損や不十分な履歴に対する安全策）。上流で None の扱いに注意してください（generate_signals はコンポーネント None を 0.5 で補完する等の施策あり）。
- 未実装 / 将来の拡張点:
  - signal_generator の SELL 条件でトレーリングストップや保持期間による時間決済は要 positions テーブル拡張（peak_price / entry_date）を想定しており未実装。
  - feature_engineering の一部変換や research の追加指標は将来追加予定。
- 外部依存:
  - news_collector は defusedxml に依存します。環境にインストールされていることを確認してください。

開発者向けメモ
- ログ出力は各モジュールで logger.getLogger(__name__) を用いており、アプリ側でハンドラを設定できます。
- DuckDB 接続は呼び出し側で用意して渡してください（関数は DuckDBPyConnection を受け取る設計）。
- 単体関数は外部 API（kabu や Slack の発注処理等）に依存しておらず、研究やテストでローカル DuckDB を用いた検証が可能です。

ライセンス・貢献
- 初版リリース。今後の機能追加やバグ修正はこの CHANGELOG に逐次追記します。貢献は Pull Request を通じて受け付けてください。