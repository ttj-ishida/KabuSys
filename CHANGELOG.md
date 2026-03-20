Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトでは Keep a Changelog のガイドラインに従います。

フォーマット: YYYY-MM-DD（リリース日）

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース。kabusys パッケージを追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - サブパッケージ公開: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートとバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート有無での扱いを区別）
  - .env ファイル読み込み時の上書き制御 (override) と protected（OS 環境変数保護）機能。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルのプロパティを提供。値検証（許容値チェック、未設定時は ValueError）。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限 (_RateLimiter, 120 req/min)。
  - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象に含む。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動トークン再取得して再試行（1 回のみ）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 財務データ（四半期）
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による上書き
    - fetched_at（UTC）を記録
  - データ変換ユーティリティ: _to_float / _to_int（安全に None を返す）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集基盤を実装（デフォルトソースに Yahoo）。
  - セキュリティ / 安全性考慮:
    - defusedxml を利用して XML 攻撃を防止
    - HTTP/HTTPS のみ許可、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減
    - トラッキング用クエリパラメータ（utm_*, fbclid 等）を除去して URL 正規化
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（説明に準拠）で生成して冪等性を確保（設計）
  - バルク INSERT のチャンク処理や INSERT RETURNING を意識した実装方針を採用

- 研究用ファクター計算・探索 (src/kabusys/research/*.py)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: PER、ROE（raw_financials と prices_daily の組み合わせ）
    - DuckDB（prices_daily / raw_financials）に依存し、外部 API に依存しない計算設計
  - 特徴量探索・評価 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）の将来リターン計算（単一クエリ実装）
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（サンプル不足時は None）
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクとするランク変換ユーティリティ（丸めで ties を安定検出）
  - research パッケージから関連関数を再エクスポート（__all__）

- 戦略（strategy）モジュール (src/kabusys/strategy/*.py)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research モジュールの生ファクターを取得してマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を確保
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算
    - コンポーネント毎にスコア変換（sigmoid 等）を適用し、重み付き合算で final_score を算出（デフォルト閾値 0.60）
    - Bear レジーム判定（ai_scores の regime_score 平均が負且つサンプル数閾値以上）
    - BUY シグナル生成（Bear レジームでは抑制）、SELL シグナル生成（ストップロス -8% など）
    - positions / prices を参照してエグジット判定を行い、signals テーブルへ日付単位の置換で保存（冪等）
    - カスタム重み受け付け（不正値フィルタリングと合計 1.0 への再スケーリング実装）
  - strategy パッケージは build_features と generate_signals をエクスポート

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーシングに defusedxml を使用して XML による攻撃を軽減
- ニュース収集で受信サイズ上限やトラッキングパラメータ除去、HTTP/HTTPS チェック等の SSRF/DoS 対策を設計に反映
- J-Quants クライアントでトークン自動リフレッシュや安全な再試行ロジックを実装

Notes / Implementation details
- DuckDB を中心とした設計で、各保存処理は基本的に SQL のウィンドウ関数・集約を多用し、単一接続（DuckDBPyConnection）を受け取る API を提供。
- 多くの DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入で原子性・性能を考慮している。ROLLBACK に失敗した場合はログに警告を出す実装。
- 外部依存は最小化（標準ライブラリ中心）。ただし XML の安全化のため defusedxml を利用。
- execution パッケージはプレースホルダ（現時点では実装なし）として存在。

Known issues / TODO
- signal_generator のエグジット条件においてトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の一部（記事 ID 生成やニュース→銘柄の紐付け処理等）はドキュメントに設計方針があり、実装詳細は拡張の余地あり。
- 単体テスト・統合テストのカバレッジは今後拡充予定。

Acknowledgements
- 本リリースはシステム設計（StrategyModel.md, DataPlatform.md 等）の仕様に基づいて実装されています。

-----------
（注）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートや履歴管理はプロジェクトの運用方針に応じて調整してください。