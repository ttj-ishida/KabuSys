# CHANGELOG

すべての変更は Keep a Changelog の慣習に従って記載しています。  
各リリースの要約はコードベースから推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-19

初回リリース。日本株の自動売買システム「KabuSys」のコア機能を実装しています。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API（data, strategy, execution, monitoring）を定義。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により、CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み順序と .env.local による上書き処理、既存 OS 環境変数の保護機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート。
  - .env 行パーサー（export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメント処理）を実装。
  - 設定アクセス用の Settings クラスを提供（必須環境変数取得の _require、デフォルト値、値検証: KABUSYS_ENV, LOG_LEVEL）。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）設定。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制御（120 req/min）を実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回）・特定ステータス（408, 429, 5xx）でのリトライ実装。
  - 401 応答時の自動トークンリフレッシュ（get_id_token）とモジュールレベルの ID トークンキャッシュを実装。
  - ページネーション対応のデータ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB へ冪等保存する save_* 関数を実装（raw_prices, raw_financials, market_calendar）。ON CONFLICT による更新を行うことで重複を排除。
  - レスポンスパースと型変換ユーティリティ（_to_float, _to_int）を実装。
  - データ取得時に fetched_at を UTC で記録し、Look-ahead バイアス追跡を可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集フローを実装（デフォルト: Yahoo Finance ビジネス RSS）。
  - 記事 ID の冪等化（URL 正規化後の SHA-256 ハッシュ）、トラッキングパラメータ除去、クエリソート、フラグメント除去を含む URL 正規化を実装。
  - defusedxml を用いた XML パースで XML 攻撃対策を実装。
  - SSRF 対策の方針、受信最大バイト数上限（10 MB）、バルク INSERT のチャンク化などの実装方針を反映。
  - raw_news / news_symbols への保存を意図した処理（設計に基づく実装）。

- 研究モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（mom_1m/mom_3m/mom_6m、ma200_dev）
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー（per, roe） — raw_financials と prices_daily を組み合わせて計算
    - DuckDB を用いた SQL ベースの高速かつ外部ライブラリ非依存の実装
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応
    - IC（Information Coefficient）計算（calc_ic）：Spearman ランク相関の実装（タイズ処理含む）
    - ファクター統計サマリー（factor_summary）およびランク変換ユーティリティ（rank）
    - 外部ライブラリに依存せず、DuckDB のみを参照する設計

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価 300 円／20 日平均売買代金 5 億円）を適用。
  - 指定カラムに対する Z スコア正規化（zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
  - features テーブルへの日付単位の置換（トランザクション＋バルク挿入による原子性保証）を実装。
  - 冪等性を重視（target_date の既存レコードを削除してから挿入）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を計算。
  - コンポーネントスコア：momentum / value / volatility / liquidity / news（AI スコア）を計算するユーティリティを実装。
  - シグモイド変換、欠損値を中立 0.5 で補完するポリシー、重み付けのマージと正規化（デフォルト重みは StrategyModel.md に準拠）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負）による BUY シグナル抑制。
  - BUY（閾値 default=0.60）と SELL（ストップロス -8%、スコア低下）の生成ロジックを実装。
  - positions / prices_daily を参照したエグジット判定、SELL 優先ポリシー（SELL の対象は BUY から除外）。
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入で原子性保証）。
  - ユーザー指定 weights のバリデーション（未知キーや非数値の除外、合計 1.0 への再スケール）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- RSS XML パースに defusedxml を利用して XML ベースの攻撃を軽減。
- ニュース収集での受信サイズ制限と URL 正規化によるトラッキング除去、SSRF リスク軽減の設計。

### Notes / Known limitations
- _generate_sell_signals 内でコメントにある通り、トレーリングストップ（peak_price に基づく）や時間決済（保有 60 営業日超過）は未実装。positions テーブルへ peak_price / entry_date を追加することで将来的に実装予定。
- calc_value は現時点で PBR・配当利回りを未実装。
- news_collector の設計では INSERT RETURNING による正確な挿入件数取得を想定しているが、実装はバルク INSERT（executemany）ベースであり、DB 側の実装差異に注意が必要。
- data.jquants_client のリトライ対象は主にネットワーク・サーバー側エラー（408, 429, 5xx）。その他のエラー条件下の動作は利用環境に依存するため運用での観察を推奨。

---

開発・運用に関するドキュメント（StrategyModel.md, DataPlatform.md 等）を参照することで、アルゴリズムの設計方針や各閾値の根拠を確認できます。今後のリリースでは以下を予定しています（例）:
- エグジット戦略の追加（トレーリングストップ・時間決済）
- PBR / 配当利回りなどバリューファクターの拡張
- news_collector の多ソース対応・NLU 統合
- execution 層（kabuステーション連携）の実装とモニタリング機能の強化

--- 

（この CHANGELOG はソースコードのコメント・実装から推測してまとめたものであり、実際のリリースノートと差異がある可能性があります。）