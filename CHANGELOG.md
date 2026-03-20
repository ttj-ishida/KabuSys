# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ初期公開: kabusys — 日本株自動売買システムの基礎ライブラリを追加。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" と主要サブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS環境変数 > .env.local > .env）。
  - .env パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォートとエスケープ対応、インラインコメントの取り扱い等）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しないロードを実現。
  - Settings クラスを提供（必須環境変数のチェック、PATH プロパティ、KABUSYS_ENV／LOG_LEVEL の検証と便利プロパティ is_live/is_paper/is_dev）。
  - 自動ロード無効化スイッチ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

- Data 層（kabusys.data）
  - J-Quants API クライアント（jquants_client）を実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンから ID トークンを自動更新して 1 回リトライ。
    - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT によるアップサート）。
    - 日時は UTC で fetched_at を記録（Look-ahead バイアス対策）。
    - 入力変換ユーティリティ: _to_float, _to_int。
  - ニュース収集モジュール（news_collector）を追加（RSS 取得 → raw_news 保存の処理フロー）。
    - RSS URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）やチャンク挿入など DoS 緩和策を導入。
    - defusedxml 利用により XML 関連の脆弱性対策を導入。
    - 記事IDは正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
    - デフォルト RSS ソース定義（例: Yahoo Finance 日本のビジネス RSS）。

- 研究（research）モジュール
  - ファクター計算（factor_research）
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日移動平均乖離 ma200_dev）。
    - ボラティリティ/流動性: calc_volatility（20 日 ATR、atr_pct、avg_turnover、volume_ratio）。
    - バリュー: calc_value（最新の raw_financials と株価から PER/ROE を算出）。
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し、結果を (date, code) キーの dict リストで返す。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算: calc_forward_returns（複数ホライズンをサポート、1 クエリでまとめて取得）。
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関、最小サンプルチェック）。
    - 基本統計サマリー: factor_summary。
    - ランク関数: rank（同順位は平均ランク、丸め誤差対策あり）。
  - zscore_normalize をエクスポート（kabusys.data.stats に実装を委譲）。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング: build_features
    - research モジュールの生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（±3 クリップ）、features テーブルへ日付単位の置換（トランザクションで原子性確保）。
    - ルックアヘッドバイアス回避のため target_date 時点のみを使用。
  - シグナル生成: generate_signals
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み・閾値を実装（デフォルト final_score 閾値 = 0.60、重みは momentum 0.40 等）。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数十分なら BUY 抑制）。
    - BUY シグナル（閾値超過、Bear では抑制）と SELL シグナル（ストップロス -8% / final_score が閾値未満）を生成。
    - SELL 優先ポリシー（SELL 対象を BUY から除外）や、positions/prices の欠損ハンドリング（ログ出力）を備える。
    - 日付単位の置換で signals テーブルへ書き込み（トランザクションで原子性確保）。
    - 重みのバリデーションと再スケーリング（未知キーや非数値、負値、NaN/Inf を無視）。

- 実装上の非機能要件・設計方針（注記）
  - Look-ahead bias を防ぐためデータ取得・計算は target_date までの情報のみを使用する設計。
  - DuckDB 側の書き込みはトランザクション＋バルク挿入で原子性と性能を確保。
  - ログ出力を多用し、欠損/異常・ロールバック失敗等を警告・通知できるようにしている。
  - 外部ライブラリの依存を最小化（research の一部は標準ライブラリのみで実装）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 関連の攻撃（XML bomb 等）を軽減。
- news_collector は受信サイズ上限や URL スキームの検証を行い、SSR F / メモリ DoS の緩和策を追加。
- J-Quants クライアントはタイムアウト設定やリトライ制御を備え、外部 API 呼び出し時の一部障害に耐性を持たせている。

---

注: 本 CHANGELOG は現行コードベースから推測した初回リリースの内容をまとめたものです。実際のリリース履歴や日付はプロジェクト運用に合わせて調整してください。