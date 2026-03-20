KEEP A CHANGELOG準拠の CHANGELOG.md（日本語）を以下に作成しました。リポジトリのコード内容から推測して記載しています（初回リリース v0.1.0）。

なお日付は本日（2026-03-20）を記載しています。必要に応じて日付や文言を調整してください。

---
All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [0.1.0] - 2026-03-20

### Added
- パッケージ初回リリース。
- 基本構成
  - パッケージ名: kabusys、バージョン 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ を定義）。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする機能。
  - プロジェクトルート検出（.git または pyproject.toml を起点）により、CWD に依存しない自動ロードを実現。
  - .env / .env.local の読み込み順（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサーの強化: export プレフィックス対応、シングル／ダブルクォート内のエスケープ処理、インラインコメント処理、無効行スキップ。
  - 環境変数必須チェック用の _require ヘルパー。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス（duckdb/sqlite）/ 環境モード（development/paper_trading/live）/ログレベル等のプロパティを提供。env 値検証ロジック（許容値チェック）。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装（認証、ページネーション、取得・保存ユーティリティ）。
  - レート制限対応（固定間隔スロットリング、120 req/min）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）、429 の Retry-After ヘッダ尊重。
  - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュール内トークンキャッシュ。
  - fetch_* 系: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
  - save_* 系: save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存、ON CONFLICT を利用）。
  - 型変換ユーティリティ: _to_float / _to_int（不正値ハンドリング）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead バイアス対策を考慮。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news へ冪等保存するモジュール。
  - URL 正規化（トラッキングパラメータ除去、順序ソート、フラグメント削除、小文字化）と記事ID生成（正規化後の SHA-256 部分使用）により冪等性を確保。
  - defusedxml を使用した XML パース（XML Bomb 対策）。
  - SSRF 対策と受信サイズ上限（MAX_RESPONSE_BYTES）設定。
  - バルク INSERT のチャンク処理による DB 負荷低減。
- リサーチ (kabusys.research)
  - ファクター計算モジュール（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）計算。
    - calc_volatility: 20日 ATR / 相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE（raw_financials からの直近財務データを使用）。
    - 入出力は DuckDB の prices_daily / raw_financials テーブルのみ参照。
  - 特徴量探索モジュール（feature_exploration）:
    - calc_forward_returns: 与えられたホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（サンプル不足時は None を返す）。
    - rank / factor_summary: ランク計算（同順位の平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
  - zscore_normalize は data.stats から再公開（__all__ に含む）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research 側で計算した生ファクターをマージ、ユニバースフィルタ（株価>=300円、20日平均売買代金>=5億円）を適用、指定カラムの Z スコア正規化、±3 クリップ、features テーブルへ日付単位で置換挿入（トランザクションで原子性確保）。
  - ルックアヘッドバイアス対策として target_date 時点のデータのみ利用。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換挿入。
  - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を算出。
  - デフォルト重みと閾値を定義（デフォルト threshold=0.60）。ユーザ指定 weights のバリデーションと再スケーリングを実装。
  - Sigmoid 変換、欠損コンポーネントの中立補完（0.5）、AI が未登録のときは中立扱い。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
  - 売り判定（_generate_sell_signals）: ストップロス（終値/avg_price - 1 < -8%）とスコア低下（final_score < threshold）。価格欠損時には判定スキップして誤クローズを回避。
  - 永続化はトランザクション + バルク挿入で原子性を確保。
- ロギング: 主要処理で logger を利用。重要な異常系は warning/info/log として通知。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- news_collector: defusedxml を採用して XML パースに起因する攻撃を防止。
- news_collector: URL 正規化・スキーム制限・受信サイズ上限・IP/SSRF 関連対策（実装を示唆する設計）により外部からの攻撃面を低減。
- jquants_client: トークン管理・リフレッシュで認証エラー時に安全に復旧。HTTP リトライ戦略で一部一時的エラー耐性を確保。

### Notes / Implementation Decisions
- 「ルックアヘッドバイアス」を防ぐ設計方針が多数のモジュールで採用されている（データ取得時の fetched_at 記録、target_date 時点のデータのみ参照等）。
- DuckDB を主要なオンディスク分析 DB として使用。SQL と Python を組み合わせた実装で、外部（本番）API への依存を極力排除する設計。
- 一部アルゴリズム（例: トレーリングストップ、時間決済）は仕様コメントとして存在するが未実装。positions テーブルに追加メタ（peak_price / entry_date 等）が必要になる旨をコメントに記載。
- weights の取り扱いは保守的（未知キーや不正値を無視、合計が 1.0 でなければ自動正規化）でユーザ誤操作による影響を抑止。
- DB 書き込みは基本的に「日付単位の置換」パターン（DELETE + INSERT within トランザクション）を採用して冪等性を担保。

### Breaking Changes
- 初回リリースのため該当なし。

---

もし CHANGELOG に追記したい詳細（例えば各関数の戻り値例、未実装 TODO の優先度、サンプル環境変数一覧など）があれば、それに合わせてセクションを追加します。