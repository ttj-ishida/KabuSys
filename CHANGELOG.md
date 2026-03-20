# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに従います。  

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。主な機能・モジュールは以下の通りです。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - public API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイル・環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で特定）。
  - .env / .env.local の読み込み順序と `.env.local` による上書きをサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト向け）。
  - 強力な .env パーサ実装（コメント、export プレフィックス、引用符内エスケープ、インラインコメント処理など）。
  - 必須環境変数を取得する `_require` と型検証を備えた `Settings` クラスを提供。
  - J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等のプロパティを提供（デフォルト値および検証あり）。

- データ取得・保存 (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ）。
  - 固定間隔スロットリングによるレート制御（120 req/min）。
  - 再試行ロジック（指数バックオフ、408/429/5xx 対応）、429 の Retry-After 優先処理。
  - get_id_token によるリフレッシュトークンからの ID トークン取得。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応でデータ取得。
  - save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB への冪等保存（ON CONFLICT で更新）、データ変換ユーティリティ `_to_float` / `_to_int` を提供。
  - 保存時に fetched_at を UTC ISO8601 で記録（Look-ahead バイアス管理を想定）。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集基盤（既定ソースに Yahoo Finance のビジネス RSS を登録）。
  - 記事の正規化（URL 正規化・トラッキングパラメータ除去・タイトル/本文前処理）。
  - セキュリティ対策：defusedxml を使用した XML パース、防止策（XML Bomb 等）、受信サイズ制限（MAX_RESPONSE_BYTES）、HTTP(S) スキーム検証、SSRF 回避の考慮。
  - 記事ID を URL 正規化＋SHA-256（先頭32文字）で付与して冪等性を確保。
  - DB バルク挿入のチャンク化と単一トランザクションでの効率的な保存（ON CONFLICT DO NOTHING を想定）。

- リサーチ / ファクター計算
  - ファクター計算群 (`kabusys.research.factor_research`)
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を算出。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio) を算出。
    - calc_value: raw_financials からの最新財務データと株価を組み合わせて PER / ROE を算出。
    - いずれも DuckDB の prices_daily / raw_financials テーブルのみを参照する設計（本番発注 API への依存なし）。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算（単一クエリで効率的に取得）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（結合・欠損除外・サンプル閾値）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median 集計。
    - rank: 同順位の平均ランク処理を含むランク変換ユーティリティ。
  - research パッケージのエクスポートを集約（calc_momentum 等と zscore_normalize を公開）。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - build_features を実装。
    - research の生ファクター（momentum/volatility/value）を取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションで一括実行し原子性を保証）。
    - 冪等性を考慮した実装。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - generate_signals を実装。
    - features / ai_scores / positions を参照して最終スコア(final_score) を計算。
    - momentum/value/volatility/liquidity/news のコンポーネントスコアを計算し、重み付け合算（デフォルト重みを提供）。
    - 重みはユーザ指定で上書き可（不正値は無視、合計が 1.0 でない場合は再スケール）。
    - Z スコア → シグモイド変換を用いることで各コンポーネントを [0,1] に正規化。
    - Bear レジーム検出（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）で BUY シグナルを抑制。
    - BUY シグナル生成（閾値デフォルト 0.60）、SELL シグナル生成（ストップロス -8%、スコア低下）を実装。
    - 保有ポジションに対するエグジット条件は positions と最新価格を参照。価格欠損時の安全策（判定スキップ）あり。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。

### Security
- news_collector にて defusedxml を用いた XML パースを採用し、XML ベースの攻撃に対する防御を実装。
- J-Quants クライアントの HTTP エラー処理で認証失敗（401）や 429 の Retry-After を適切に扱い、再試行ポリシーを明確化。

### Design / Implementation notes
- DuckDB を主要な時系列データストアとして使用（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルを想定）。
- ルックアヘッドバイアス防止に配慮：各処理は target_date 時点で利用可能なデータのみを参照し、fetched_at を記録することで「データがいつ取得されたか」を追跡可能にしている。
- 外部依存を限定（defusedxml を利用する以外は標準ライブラリ中心）し、研究用途と本番用途の分離を意識した構成。
- トランザクション + バルク挿入によりデータ更新の原子性とパフォーマンスを確保。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

--------------------------------------------------------------------------------
保持すべき注意点:
- 本リリースはライブラリのコア機能を提供しますが、実運用に際しては環境変数（トークン・パス等）の正しい設定、DuckDB のスキーマ整備（期待されるテーブル・カラムの作成）、および外部 API 利用に伴う鍵管理・レート管理のテストを行ってください。