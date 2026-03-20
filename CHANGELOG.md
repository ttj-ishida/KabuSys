CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
慣例により重要な変更点をカテゴリ別に整理しています。

[0.1.0] - 2026-03-20
-------------------

Added（追加）
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を実装。
- パッケージ初期化:
  - kabusys パッケージとバージョン定義（__version__ = "0.1.0"）。
- 設定管理（kabusys.config）:
  - .env ファイルまたは環境変数から設定を自動読み込み（優先度: OS 環境変数 > .env.local > .env）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env パーサーは export 句、引用符（シングル/ダブル）内のエスケープ、インラインコメント処理に対応。
  - Settings クラスにアプリケーション設定プロパティを提供（J-Quants トークン、kabu API、Slack、DB パス、環境 / ログレベル判定等）。
  - env 値や LOG_LEVEL の妥当性検査を実装（不正値で ValueError を送出）。
- データ収集 / 保存（kabusys.data.jquants_client）:
  - J-Quants API クライアントを実装（フェッチ / ページネーション対応）。
  - 固定間隔の RateLimiter（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx のリトライ）と 401 時の自動トークンリフレッシュ（1 回）をサポート。
  - ページネーション間でのトークンキャッシュ共有。
  - fetch_*/save_* 関数群を実装:
    - fetch_daily_quotes / save_daily_quotes（raw_prices 保存、ON CONFLICT DO UPDATE）
    - fetch_financial_statements / save_financial_statements（raw_financials 保存、ON CONFLICT DO UPDATE）
    - fetch_market_calendar / save_market_calendar（market_calendar 保存、ON CONFLICT DO UPDATE）
  - 保存時に取得時刻（fetched_at）を UTC ISO 文字列で記録（Look-ahead バイアス対策）。
  - 型変換ユーティリティ _to_float / _to_int を提供（堅牢なパースと不正値処理）。
- ニュース収集（kabusys.data.news_collector）:
  - RSS フィード収集基盤を実装（デフォルトソースに Yahoo Finance）。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成する想定（冪等性確保）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - defusedxml による XML パース、受信サイズ上限（10 MB）、SSRF 対策等のセキュリティ考慮。
  - DB バルク登録のチャンク化やトランザクションまとめによる効率化（設計方針）。
- リサーチ（kabusys.research）:
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials ベース）。
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一度に取得）
    - calc_ic（スピアマンランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位を平均ランクとするランク変換）
  - zscore_normalize ユーティリティ参照をエクスポート。
- 戦略（kabusys.strategy）:
  - feature_engineering.build_features:
    - research モジュールの生ファクターをマージ、ユニバースフィルタ（価格・流動性）、Z スコア正規化、±3 クリップ、features テーブルへの日付単位置換（トランザクションで原子性保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグナル重みのマージ／正規化、AI スコアの統合、Bear レジーム検出（regime_score の平均 < 0 で判定）による BUY 抑制。
    - BUY シグナル（閾値デフォルト 0.60）／SELL シグナル（ストップロス -8% とスコア低下）を生成し signals テーブルへ日付単位置換で保存。
    - SELL 優先ポリシー（SELL 対象を BUY から除外してランク付け）。
- モジュール エクスポート:
  - strategy パッケージから build_features / generate_signals を公開。
  - research パッケージから主要ユーティリティを公開。

Changed（変更）
- —（初回リリースのため過去からの変更はなし）

Fixed（修正）
- —（初回リリースのため過去からの修正はなし）

Security（セキュリティに関する重要な実装）
- news_collector は defusedxml を利用して XML 関連の攻撃（XML Bomb など）に対処。
- ニュース収集で受信サイズを制限しメモリ DoS を軽減。
- jquants_client はトークン管理と HTTP エラー処理を堅牢に実装（401 の自動リフレッシュや Retry-After の考慮）。

Known issues / Limitations（既知の制限）
- signal_generator の一部エグジット条件は未実装（コメントで明示）:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の実装ファイルは主要設計を含むが、一部細部（DB への完全な挿入処理など）は設計方針に基づく実装が必要な場合がある（README/ドキュメント参照）。
- 実行層（kabusys.execution）は空のパッケージとして用意。発注 API を呼ぶ具体的な実装は別途必要。

その他
- DuckDB による分析基盤を前提に設計されており、ほとんどの関数は DuckDB 接続を受け取って動作する（外部ネットワークや発注 API への不要な依存を排除）。
- ロギングやトランザクション設計により、再実行や冪等性を重視した実装になっている。

今後の予定（短期ロードマップ）
- execution 層の実装（kabu API への送信・注文管理）。
- ニュース記事の銘柄マッチング（news_symbols テーブル連携）および INSERT RETURNING を用いた正確な挿入カウント。
- テストカバレッジの拡充、CI での環境変数周りの検証。
- 一部アルゴリズム（トレーリングストップ等）の実装完了。

---

この CHANGELOG は、コードベース内のドキュメント文字列・関数実装・コメントから推測して作成しています。実際のリリースノートとして公開する際は、リリース時に差分／コミット情報に基づいて更新してください。