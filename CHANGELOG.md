# Keep a Changelog

すべての公開変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※この CHANGELOG は与えられたコードベースから推測して作成した初期リリース記録です。

## [Unreleased]


## [0.1.0] - 2026-03-20
初回公開リリース。以下の主要機能とモジュールを実装しています。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期版を追加。公開 API として data, strategy, execution, monitoring を __all__ に公開。
  - パッケージバージョンを "0.1.0" に設定。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込むユーティリティを実装。
  - プロジェクトルート探索（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存しない自動ロードを実現。
  - .env と .env.local の優先順で読み込み。OS 環境変数は保護（上書き不可）し、.env.local での上書きを許可。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト用途）。
  - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメントなどの実用的なフォーマットに対応。
  - Settings クラスを実装。主要設定プロパティ（J-Quants / kabu / Slack / DB パス / 環境 / ログレベルなど）と入力検証を提供。

- データ取得/保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - API レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を搭載。
  - 再試行(指数バックオフ)ロジックを実装（最大 3 回、408/429/5xx を再試行対象）。
  - 401 レスポンス時のリフレッシュトークン自動更新（1 回のみ）を実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT による冪等保存を実現。
  - データ整形ヘルパー（安全な数値変換 _to_float/_to_int）を実装。
  - データ取得時に fetched_at を UTC ISO8601 で記録（look-ahead bias のトレース対応）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して raw_news 等へ保存する基盤を実装。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）機能を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保する設計方針。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を緩和。
  - HTTP レスポンスサイズ上限（10 MB）など DoS 対策、SSRF 対策の方針を反映。
  - バルク INSERT のチャンク処理（INSERT チャンク化）やトランザクションでオーバーヘッドを抑制。

- 研究用モジュール (kabusys.research)
  - ファクター計算群（factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターンと 200 日 SMA 乖離率を計算。
    - calc_volatility: 20 日 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位の平均ランク処理を含むランク変換ユーティリティ。
  - 研究 API を re-export（kabusys.research.__all__ に主要関数を公開）。

- 戦略モジュール (kabusys.strategy)
  - feature_engineering.build_features:
    - research で計算した生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）して冪等性と原子性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネント欠損値は中立 0.5 で補完し、不当に降格しない方針を採用。
    - final_score を重み付け合算（デフォルト重みを実装）し、閾値超過で BUY シグナル生成。Bear レジーム時は BUY を抑制。
    - SELL シグナル（ストップロス、スコア低下）ルールを実装。positions と最新価格を参照して判定。
    - 重みの入力検証と正規化（合計が 1.0 に再スケール）を実装。
    - signals テーブルへ日付単位の置換（トランザクション＋bulk insert）で冪等性を確保。
  - 上記により、戦略の特徴量生成からシグナル生成までが DBA への直接依存なく DuckDB 上で完結。

### 変更 (Changed)
- 設計上の注意事項・安全策をコード化:
  - ルックアヘッドバイアス対策（データ取得時の fetched_at 記録 / target_date 時点のデータのみ参照）。
  - 外部 API 呼び出し部分における再試行・レート制限・トークン自動更新の実装で堅牢性を向上。
  - DB への書き込みは可能な限り冪等化（ON CONFLICT / 日付単位の置換）を採用。

### 修正 (Fixed)
- （初期リリースのため過去のバグ修正履歴はなし。コード内に多くの注意ログ・例外処理を含め安全性を高める実装を行っています。）

### 注意・未実装（既知の制約）
- signal_generator のトレーリングストップ・時間決済等、いくつかのエグジット条件は positions テーブルの追加情報（peak_price / entry_date 等）がないため未実装（コメントにて明記）。
- news_collector の詳細な記事抽出・シンボル紐付け（news_symbols 作成処理）は設計方針に言及しているが、与えられたコード断片では完全実装箇所が限定的。
- 外部依存（duckdb, defusedxml 等）のバージョン互換性・運用設定は別途 README / CI で管理する想定。

---

作成にあたり、ソース内のドキュメント文字列、ログ出力、関数シグネチャ、SQL クエリ、例外・検証ロジック等から機能と設計意図を抽出してまとめました。実装の詳細やリリース日付（ヘッダーの日付）は推測に基づき設定しています。必要であればリリース日や項目の細分化（Fixed / Changed の追加分割）を更新します。