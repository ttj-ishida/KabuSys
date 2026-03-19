# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠しています。セマンティックバージョニングに従います。

## [0.1.0] - 2026-03-19

初回リリース。本リポジトリは日本株自動売買のための内部ライブラリ群（データ収集、リサーチ、特徴量生成、シグナル生成、環境設定ユーティリティ等）を提供します。主要な追加点は以下の通りです。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）
  - 公開モジュール: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）
  - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理等に対応）
  - OS 環境変数を保護する override/protected ロジック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション
  - Settings クラスによる型付きプロパティ（J-Quants トークン、kabu API 設定、Slack、DB パス、環境名、ログレベル等）
  - env / log_level の値検証（許容値チェック）および is_live/is_paper/is_dev のユーティリティ

- データ収集クライアント: J-Quants API (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ（ページネーション対応）
  - 固定間隔スロットリングによるレート制限管理（120 req/min）
  - 再試行ロジック（指数バックオフ、特定ステータスでのリトライ、最大試行回数）
  - 401 発生時のトークン自動リフレッシュ（1 回まで）
  - データ保存ユーティリティ（DuckDB 用）
    - save_daily_quotes: raw_prices への冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials への冪等保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar への冪等保存（ON CONFLICT DO UPDATE）
  - データ整形ユーティリティ: _to_float / _to_int

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と正規化機能（デフォルトに Yahoo Finance のカテゴリ RSS を含む）
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、スキーム/ホスト小文字化）
  - セキュリティ対策: defusedxml を利用した XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）、HTTP スキーム検証、SSRF 対策考慮
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）等で生成して冪等性を確保
  - DB へのバルク保存のチャンク化（_INSERT_CHUNK_SIZE）

- リサーチ用ユーティリティ (src/kabusys/research/)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率の計算
    - calc_value: EPS と株価からの PER、ROE の取得（raw_financials と prices_daily を参照）
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）での将来リターン計算（LEAD を利用）
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（ランクは同順位を平均ランクで処理）
    - factor_summary: 基本統計量（count, mean, std, min, max, median）
    - rank: 値リストを平均ランクで変換するユーティリティ
  - 研究用 API を __all__ で公開

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで計算された生ファクターを統合し、ユニバースフィルタ（最低株価、最低平均売買代金）を適用
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）および ±3 でのクリップ
  - features テーブルへの日付単位の置換（トランザクション + バルク挿入で冪等性・原子性を確保）
  - 欠損・非有限値の扱いを明確化

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
  - スコア変換ユーティリティ（シグモイド、平均集約、コンポーネント計算）
  - デフォルト重みとスコア閾値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD）を実装し、ユーザー指定 weights の検証と正規化を行う
  - Bear レジーム判定（ai_scores の regime_score 平均 < 0）による BUY シグナル抑制
  - BUY シグナル閾値判定、SELL（エグジット）判定（ストップロス -8%、スコア低下）
  - positions / prices_daily を参照したエグジット判定と warnings ログ出力
  - signals テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性を保証）
  - SELL 優先ポリシー（SELL 対象は BUY から除外しランク再付与）

### 変更 (Changed)
- （初回リリースのため過去からの変更はありません）

### 修正 (Fixed)
- （初回リリースのため既知のバグ修正はありません）

### 既知の制限 / 未実装 (Known issues / Todo)
- signal_generator のエグジットルール:
  - トレーリングストップ（直近最高値基準）および時間決済（保有 60 営業日超）については positions テーブルに peak_price / entry_date 等の追加情報が必要であり、現状未実装としてドキュメントやコード内に明記。
- news_collector: RSS の多様なフォーマットに対する完全な互換性は未検証。追加のフィードやタグ処理が必要になる可能性あり。
- jquants_client:
  - rate limiter は単一プロセス内での保護を目的としており、マルチプロセス／分散環境での共有制御は別途必要。
  - 一部の HTTP エラーでのリトライポリシーは簡易実装（最大 3 回）であり、運用状況に応じたチューニングが推奨される。
- 外部依存の最小化方針により、pandas 等の分析ライブラリを使わずに純 Python + DuckDB SQL を用いているため、大規模データ集計時の柔軟性やパフォーマンスチューニングの余地あり。

### セキュリティ
- news_collector で defusedxml を使用、受信サイズ制限、URL 正規化等の対策を実装。
- jquants_client はトークン自動リフレッシュと API-rate 制御を実装し、安定性・耐障害性を向上。

---

今後のリリースで想定される追加事項（例）
- execution 層の実装（kabu-station 経由の発注ラッパー）
- モデル学習 / AI スコア生成パイプラインの実装
- モニタリング / アラート機能（Slack 通知など）の追加
- マルチプロセス/分散環境でのレートリミッティング共有化

もし特定ファイルや機能に対して詳細な CHANGELOG の分割や日付変更、貢献者の追加などをご希望であれば指示ください。