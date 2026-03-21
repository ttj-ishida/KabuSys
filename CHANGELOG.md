CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。
このファイルは日本語で、リポジトリの初期リリース（v0.1.0）の変更点をコードベースから推測してまとめたものです。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-21
--------------------

追加 (Added)
- パッケージの初期リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0

- 基本パッケージ構成:
  - モジュール群をエクスポート: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定 / 設定管理:
  - kabusys.config.Settings クラスを実装。環境変数から各種設定を取得（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、環境設定、ログレベルなど）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される仕組みを採用。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント解析など）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
  - settings インスタンスをモジュールレベルで公開。

- データ取得 / 保存（data.jquants_client）:
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象ステータスを考慮（408/429/5xx）。
    - 401 受信時にリフレッシュトークンでトークン自動更新して 1 回リトライ。
    - ページネーション対応で複数ページを取得。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアス対策を考慮。
    - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
    - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を利用して重複更新を避ける。
    - レスポンス値を安全に変換するユーティリティ _to_float / _to_int を実装。

- ニュース収集（data.news_collector）:
  - RSS フィードからの記事収集機能を実装（デフォルトソースに Yahoo Finance のカテゴリ RSS を登録）。
  - defusedxml を使った安全な XML 解析を導入（XML Bomb 等の防御）。
  - 記事 URL の正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ攻撃を緩和。
  - 記事ID生成の方針（URL 正規化後の SHA-256 ハッシュの先頭部分など）をドキュメントで示唆。
  - バルク INSERT のチャンク化を導入（パフォーマンス・SQL 長制限対策）。
  - HTTP/HTTPS 以外のスキーム拒否や SSRF・トラッキング排除等の方針を採用。

- 研究用モジュール（research）:
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE を計算（EPS がゼロまたは欠損時は PER=None）。
    - SQL ウィンドウ関数を多用して DuckDB 内で効率的に計算。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）での将来リターンを計算。ホライズンが不正な場合はエラー。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル不足（<3）や定数系列時は None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
    - rank: 同順位の平均ランクを取るランク付けユーティリティ（丸めによる ties 対応）。
  - research パッケージの __all__ を整備して主要関数を公開。

- 戦略モジュール（strategy）:
  - feature_engineering モジュールを実装:
    - 研究環境で得た raw ファクターを読み込み、ユニバースフィルタを適用（最低株価 300 円、20 日平均売買代金 5 億円）。
    - 正規化 (z-score 正規化) を適用し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE → INSERT のトランザクションにより冪等化・原子性を確保）。
  - signal_generator モジュールを実装:
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルトの重み付けを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。与えられた weights は検証・正規化（合計1へスケーリング）される。
    - final_score の閾値デフォルトは 0.60（これを超えると BUY 候補）。Bear レジーム（ai_scores の regime_score 平均が負）検知時は BUY を抑制。
    - SELL ロジック（エグジット判定）を実装: ストップロス（終値ベースで -8% 以下）とスコア低下（final_score < threshold）。保有銘柄で価格データが欠損している場合は判定をスキップするロバスト性を実装。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - ロギングによる運用情報出力（検出した Bear、生成した BUY/SELL 数など）。
  - strategy パッケージの __all__ を整備して build_features / generate_signals を公開。

変更 (Changed)
- 初期リリースのため既存コードの「変更」は無し（新規実装群）。

修正 (Fixed)
- 初期リリースのため既存バグ修正は無し。

非推奨 (Deprecated)
- なし。

削除 (Removed)
- なし。

セキュリティ (Security)
- news_collector で defusedxml を使用し XML パースの安全性を高めた点を明記。
- RSS パース時に受信サイズ上限を設けることでメモリ DoS を軽減。

運用上の注記
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後やテスト環境で挙動を制御する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- J-Quants API のレート制限・トークン管理や DuckDB の upsert 方針は運用想定に基づく実装です。実運用では API 利用状況や DB スキーマ（特に UNIQUE/PK 制約）に合わせた確認を推奨します。
- signal_generator の一部条件（トレーリングストップや時間決済など）は comments に未実装箇所として残されています（将来的な拡張ポイント）。

お問い合わせ・貢献
- リポジトリに対する問題報告や改善提案は issue を通じてお願いします。README / ドキュメントに沿って設定・DB スキーマを準備のうえ動作確認してください。