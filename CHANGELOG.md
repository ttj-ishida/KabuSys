KEEP A CHANGELOG — kabusys

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

### Added
- パッケージの初期設計・実装を追加（バージョン 0.1.0 として切り出し予定）。
  - パッケージルート: kabusys（__version__ = 0.1.0）。
- 環境設定管理（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込む仕組みを実装。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動読み込みを無効化可能（テスト対策）。
  - .env の行パーサを実装（`export KEY=val`、クォート内のエスケープ、インラインコメント処理等に対応）。
  - 既存の OS 環境変数を保護する「protected」扱いの読み込みと上書き制御をサポート。
  - 設定アクセス用の Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境値・ログレベル検証など）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを追加。

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - レート制限を守る固定間隔スロットリング（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンによるトークン更新と再試行を 1 回行う機能。
    - ページネーション対応の取得関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供し、冪等性を ON CONFLICT / DO UPDATE で担保。
    - 取得時に UTC の fetched_at を記録し、look-ahead bias のトレーサビリティを確保。
    - 型変換ユーティリティ (_to_float / _to_int) を実装し、不正データ耐性を向上。

  - ニュース収集モジュール（news_collector）
    - RSS フィードの収集と raw_news への保存処理を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - defusedxml を用いた XML パーシング（XML Bomb 対策）。
    - 受信サイズ制限（最大 10MB）や SSRF 対策（スキーム検査／IP 検査等の実装予定箇所を想定）、トラッキングパラメータ除去、チャンク単位のバルク挿入などを設計・実装。
    - デフォルト RSS ソース（Yahoo Finance）を定義。

- リサーチ（kabusys.research）
  - factor_research: Momentum / Value / Volatility / Liquidity を DuckDB の prices_daily / raw_financials を元に計算する関数群を実装（calc_momentum / calc_value / calc_volatility）。
    - 200日移動平均、ATR（20日）、出来高比率、平均売買代金などを計算。
    - データ不足時の None 扱い、窓幅チェック等を適切に処理。
  - feature_exploration: 将来リターン（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - Spearman（ランク相関）に基づく IC 計算。サンプル不足時は None を返す等、堅牢な実装。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research 側で計算した生ファクターを統合、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - DuckDB 上の features テーブルへ「日付単位の置換（トランザクション + バルク挿入）」で冪等に保存。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損コンポーネントの中立補完（0.5）により安定性を確保。
    - デフォルト重みや閾値を定義（デフォルト閾値 0.60、重みは momentum 0.40 など）。ユーザー指定 weights は妥当性検査後に合計が 1.0 となるよう再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数条件を満たす場合）、Bear 時は BUY を抑制。
    - 保有ポジションに対するエグジット判定を実装（ストップロス -8% / スコア低下による売却）。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）で冪等に保存。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し XML ベースの攻撃を軽減。
- J-Quants クライアントのトークン管理でリフレッシュ処理を制御、401 再帰を防止。

### Notes / Known limitations / TODO
- generate_signals 内の一部エグジット条件は未実装（コメントにトレーリングストップ／保有期間時間決済の記載あり）。positions テーブルに peak_price / entry_date 等の項目が必要。
- news_collector における SSRF/IP 検査・詳細ネットワーク制限の実装は意図が明示されているが、運用環境に応じた追加の堅牢化が推奨される。
- 本実装は DuckDB のスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）に依存するため、データベーススキーマの準備が必要。
- research モジュールは外部（pandas 等）に依存しない設計だが、実際の大量データ処理ではパフォーマンス評価が必要。
- ニュース記事 ID のハッシュ化（先頭 32 文字）などは運用上の要件に合わせて変更可能。

---

## [0.1.0] - 2026-03-20

初回パブリックリリース。上記「Added」に記載の機能群を提供。

- コア: パッケージ設定・バージョン管理
- 環境設定読み込み・Settings クラス
- J-Quants クライアント（取得・保存・リトライ・レート制限・認証）
- ニュース収集（RSS -> raw_news、正規化・安全対策）
- DuckDB ベースのデータ保存ユーティリティ（冪等性対応）
- リサーチ: ファクター計算（momentum/value/volatility）・将来リターン・IC・統計サマリー
- 戦略: feature_engineering（特徴量作成）・signal_generator（BUY/SELL 判定、Bear レジーム判定）
- ログ出力・例外処理・トランザクション保護等の堅牢化

---

参照:
- バージョンはパッケージ定義（src/kabusys/__init__.py）で管理されています。