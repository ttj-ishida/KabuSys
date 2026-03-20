# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]
（現状なし）

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: `src/kabusys/__init__.py` に `__version__ = "0.1.0"` とパブリック API (`__all__`) を追加（data, strategy, execution, monitoring を公開）。
- 環境設定 / ロード
  - 環境変数管理モジュール `src/kabusys/config.py` を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）を実装し、CWD に依存しない .env 自動読み込みを提供。
    - `.env` と `.env.local` の読み込み順序と上書きルールを実装。既存 OS 環境変数は保護される。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。
    - 複雑な .env パースをサポート（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
    - 必須設定取得ヘルパ `_require()` と、環境値検証（KABUSYS_ENV, LOG_LEVEL）のプロパティを持つ `Settings` クラスを提供。
    - デフォルトの DB パスや API ベース URL のデフォルト値を設定（duckdb/sqlite パス、Kabu API ベース等）。
- データ収集・保存（J-Quants API）
  - `src/kabusys/data/jquants_client.py` を追加。
    - 固定間隔スロットリングによる RateLimiter を実装（120 req/min を尊重）。
    - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）を実装。
    - 401 受信時の自動トークンリフレッシュ処理（1 回のみ）を実装。
    - ページネーション対応の fetch 関数を提供:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（市場カレンダー）
    - DuckDB への保存ユーティリティを実装（冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - レスポンスの fetched_at を UTC で記録することでデータ取得タイミングのトレーサビリティを確保。
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装。
- ニュース収集
  - `src/kabusys/data/news_collector.py` を追加（RSS フィード収集機能）。
    - RSS 取得 -> テキスト前処理 -> raw_news への冪等保存フローを設計。
    - URL 正規化機能（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）を実装。
    - defusedxml による XML パース（XML Bomb 等への対策）、受信サイズ上限（10MB）でメモリ DoS 対策、HTTP スキーム検証などのセキュリティ対策を導入。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保する設計。
    - 大量挿入時のチャンク処理（チャンクサイズ設定）を想定。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
- リサーチ（ファクター計算・探索）
  - `src/kabusys/research/factor_research.py` を追加。
    - Momentum / Volatility / Value のファクター計算を実装（prices_daily / raw_financials を参照）。
    - 具体的には mom_1m/mom_3m/mom_6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per/roe 等を計算。
    - ウィンドウ不足時の None 扱い、スキャンバッファ（カレンダー日をバッファ）等を考慮。
  - `src/kabusys/research/feature_exploration.py` を追加。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman の ρ）計算、factor_summary、rank 等の統計解析ユーティリティを実装。
    - pandas 等外部ライブラリに依存しない実装。欠損・サンプル数不足時の安全な挙動を確保。
  - `src/kabusys/research/__init__.py` で主要関数を再公開。
- 戦略（feature -> signals）
  - `src/kabusys/strategy/feature_engineering.py` を追加。
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（z-score）と ±3 クリップを行い、features テーブルへ日付単位の置換（トランザクション）で書き込む（冪等性）。
    - 価格欠損や数値の有効性チェックを実装。
  - `src/kabusys/strategy/signal_generator.py` を追加。
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - final_score は重み付き合算（デフォルト重みを採用）、weights の入力検証と正規化を実装。
    - Bear レジーム判定（AI の regime_score の平均が負かつ十分なサンプル数が存在する場合）を実装し、Bear 時は BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）以上を BUY、保有ポジションのエグジット条件（stop_loss -8%、score_drop）で SELL を生成。
    - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換（トランザクション）で書き込み（冪等性）。
    - ログ出力と入力検証（不正な weights 値の警告等）を実装。
  - `src/kabusys/strategy/__init__.py` で外部公開（build_features, generate_signals）。
- その他
  - `src/kabusys/execution/__init__.py` を追加（プレースホルダ、発注層の分離を想定）。
  - ロギング、警告メッセージを各所に導入し運用時の診断性を向上。

### 変更 (Changed)
- （初リリースのため基盤的実装のみ。既存コードの変更はなし。）

### 修正 (Fixed)
- （初リリース、既知のバグ修正履歴はなし。ただしドキュメント中に未実装機能の注記あり。）

### セキュリティ (Security)
- ニュース XML パースに defusedxml を使用し XML 関連攻撃に対策。
- RSS 取得で受信バイト上限を設定しメモリ DoS を軽減。
- ニュース URL の正規化でトラッキングパラメータ除去、SSRF を抑止するため HTTP/HTTPS 以外のスキームを拒否する設計（実装方針）。
- J-Quants クライアントでのトークン管理・リフレッシュを実装し、認証関連の異常に対して堅牢化。

### 注意 / 未実装 (Notes / Known limitations)
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は docstring に記載されているが現バージョンでは未実装（positions テーブルに peak_price / entry_date 等が必要）。
- news_collector の docstring では INSERT RETURNING による挿入件数精密取得を掲げているが、実装はチャンク化したバルク挿入を想定している（DB 実装に依存するため運用時調整が必要）。
- research モジュールは外部ライブラリに依存しない実装を行っているが、大規模データでのパフォーマンスチューニングは今後の課題。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後や特殊な配下配置で期待通り動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境を設定すること。

---

作成者注:
- この CHANGELOG は提示されたソースコードの内容から機能・設計・注意点を要約・推測して作成したものです。実際のコミット単位の変更履歴ではない点にご留意ください。