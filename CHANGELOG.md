# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の方針に従って作成されています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回公開リリース。

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - プロジェクトルート探索は __file__ 起点で .git または pyproject.toml を探すため、CWD に依存しない
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - OS 環境変数は protected として上書きを防止
  - .env パーサーを実装（コメント・export 形式・クォートやバックスラッシュエスケープに対応）
  - settings クラスを実装（J-Quants トークン、kabu API、Slack、DB パス、環境種別・ログレベルの検証など）
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL のバリデーションを実装
    - duckdb/sqlite のデフォルトパスを提供

- データ収集/保存 (kabusys.data)
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - レート制限（120 req/min）を固定間隔スロットリングで実装（RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回）を実装（408/429/5xx 対応）
    - 401 受信時の自動トークンリフレッシュ（1 回）を実装
    - ページネーション対応で複数ページ取得可能
    - 取得タイムスタンプ（fetched_at）を UTC で記録して look-ahead bias を抑制
    - DuckDB への冪等保存関数を実装
      - save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE）
    - 入力パースユーティリティ（_to_float/_to_int）を実装
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィード収集の基礎を実装（デフォルトに Yahoo Finance ビジネス RSS を登録）
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）
    - セキュリティ対策:
      - defusedxml を利用して XML Bomb 等を防止
      - HTTP/HTTPS スキーム以外は拒否（SSRF 緩和）
      - 応答サイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS を防止
    - バルク INSERT チャンク化とトランザクションまとめ挿入

- リサーチ（研究）モジュール (kabusys.research)
  - factor_research: ファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: PER、ROE（raw_financials と prices_daily を組み合わせて計算）
  - feature_exploration: 探索用ユーティリティを実装
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（単一 SQL クエリで取得）
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・最小サンプルチェック）
    - factor_summary: count/mean/std/min/max/median の統計サマリー
    - rank: 同順位は平均ランクになるランク関数（丸めで ties 検出バイアスを低減）
  - 研究モジュールは pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装
    - research モジュールで計算した生ファクターを取得しマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT、冪等）

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - デフォルト重みを定義（momentum 0.40 等）、ユーザ上書きは検証・正規化して合計 1.0 に再スケール
    - final_score による BUY シグナル生成（デフォルト閾値 0.60）
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数 >= 3 の場合 BUY を抑制）
    - エグジット判定（STOP LOSS -8% または final_score が閾値未満）
    - SELL 優先ポリシー（SELL 対象は BUY から除外）
    - signals テーブルへ日付単位で置換（冪等）

### 変更 (Changed)
- （初回リリースのため特段の過去変更はなし。設計方針・ドキュメントは各モジュールの docstring に含める）

### 修正 (Fixed)
- （初回リリースのため過去バグ修正の履歴はありません）

### セキュリティ (Security)
- ニュース XML 解析に defusedxml を採用（XML エンティティ攻撃対策）
- 外部 URL 正規化・スキームチェック・トラッキングパラメータ除去・応答サイズ制限などの各種ハードニングを実装
- .env 読み込みで OS 環境変数を保護する仕組みを導入（.env.local の override でも OS 環境変数は上書きされない）

### 既知の制限 / TODO
- signal_generator のエグジット条件について、下記は未実装（将来実装予定）:
  - トレーリングストップ（peak_price 情報が positions に必要）
  - 時間決済（保有日数に基づく強制決済）
- news_collector の記事 ID 生成・記事→銘柄紐付けの細部（SHA-256 トークン化や news_symbols 連携）は実装の続きを想定
- research モジュールは現時点で DuckDB の prices_daily/raw_financials の良好なデータが前提
- 一部ユーティリティ（zscore_normalize など）は別モジュール（kabusys.data.stats）依存で、そちらの入出力仕様に合わせる必要がある
- 外部 API（J-Quants / kabuステーション / Slack）への実行・発注層（execution）との統合は別モジュールで実装予定（execution パッケージは存在するが中身は未実装または空）

---

作業方針や設計選択は各モジュールの docstring に詳述しています。リリースノートに不足があれば、どの点を詳しく追記すべきか指示してください。