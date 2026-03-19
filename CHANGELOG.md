Keep a Changelog
=================

すべての注記はセマンティックバージョニングに従います。
このファイルはプロジェクトの重要な変更点を追跡するための要約です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
--------------------

Added
- 初期リリース: KabuSys — 日本株自動売買支援ライブラリの基本機能を実装。
  - パッケージエントリポイント (src/kabusys/__init__.py) とバージョン定義。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - export 形式やクォート・コメントを考慮した堅牢な .env パーサー（_parse_env_line）。
  - 必須変数チェック用の Settings クラス（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の検証）と利便性プロパティ（is_live 等）。
  - デフォルトパス設定（DUCKDB_PATH/SQLITE_PATH）と kabu_api_base_url の既定値。
- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API からの日次株価、財務データ、取引カレンダー取得用クライアントの実装。
  - 固定間隔スロットリングによるレート制御（120 req/min）を行う RateLimiter 実装。
  - リトライ（指数バックオフ、最大 3 回）・HTTP ステータス処理（408/429/5xx を再試行対象）。
  - 401 受信時のトークン自動リフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュ共有。
  - ページネーション対応 fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - ON CONFLICT DO UPDATE による上書き、PK 欠損行のスキップとログ出力。
  - 入力値変換ユーティリティ（_to_float / _to_int）。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集処理骨格（デフォルトソース: Yahoo ビジネス RSS）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
  - defusedxml を使った XML パース、安全制約（最大受信バイト数制限、SSRF 対策方針）を考慮した設計。
  - 記事ID を正規化 URL のハッシュで生成する方針（冪等性の担保）。
  - DB バルク挿入のチャンク処理等、パフォーマンス配慮。
- リサーチ機能 (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を組み合わせて算出
    - DuckDB によるウィンドウ集計と欠損制御を考慮した実装
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応
    - IC（calc_ic）: Spearman ランク相関の実装（ties の平均ランク処理を含む）
    - 統計サマリー（factor_summary）と rank ユーティリティ
  - これらをまとめてエクスポート（src/kabusys/research/__init__.py）。
- 戦略層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research モジュールから取得した生ファクターをマージ・ユニバースフィルタ適用・正規化（Z スコア）・クリップ（±3）して features テーブルへ UPSERT（トランザクションで日付単位の置換、冪等）。
    - ユニバースフィルタ条件（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - ルックアヘッドバイアス回避の設計（target_date 時点のみ使用）。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を計算。
    - デフォルト重みや閾値（デフォルト threshold=0.60）を定義。外部から weights を渡して補正可能（不正値の除外・正規化を実施）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
    - エグジット判定（ストップロス -8% / final_score の閾値未満）と SELL シグナル生成。保有銘柄の価格欠損時のスキップ・ログ出力。
    - signals テーブルへ日付単位の置換（トランザクションで冪等）。
    - 生成関数は generate_signals(conn, target_date, threshold, weights) を公開し、書き込んだシグナル数を返す。
- 共通ユーティリティ
  - zscore_normalize 等の統計ユーティリティは kabusys.data.stats で提供され、research・strategy 層で利用。
- パッケージエクスポート
  - strategy.build_features / strategy.generate_signals をトップレベルからインポート可能に設定。

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Security
- J-Quants クライアント・ニュース収集において外部入力・XML を安全に扱う設計（defusedxml、SSRF/DoS 対策、リクエスト上限など）。
- .env 読み込みで OS 環境変数の上書き保護（protected set を使用）。

Notes / Known limitations
- 未実装機能（今後の改良予定）
  - strategy のエグジット条件に記載されているトレーリングストップや時間決済（positions テーブルに peak_price / entry_date 情報が必要）。
  - Value ファクターの一部（PBR、配当利回り）は未実装。
- news_collector の完全実装（RSS パースから DB 保存までのフローの細部）はこのコミットで基礎を提供しているが、外部フィードの拡充やシンボル紐付けロジックは今後の追加を想定。
- execution / monitoring パッケージはエントリポイントに含まれるが、発注・監視の実働ロジックは別途実装が必要。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は別途定義が必要（本リリースでは利用前提で SQL スキーマは含まれていない）。

参考
- 主な設計方針: ルックアヘッドバイアス回避、冪等性（トランザクション＋日付単位置換／ON CONFLICT UPDATE）、外部 API の安全な取り扱い（レート制御・リトライ・トークン更新）。
- API/関数の主要戻り値: build_features -> upsert した銘柄数、generate_signals -> 書き込んだシグナル合計数、fetch_* / save_* は取得・保存レコード数を返す。

--- 

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース手順に基づく補足（DB スキーマ、運用手順、環境変数の具体例など）を追記してください。