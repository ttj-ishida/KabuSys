# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
このファイルは、コードベースから推測される機能追加・修正・設計上の決定をまとめたものです。

なお、このリリースはパッケージの初期公開相当（v0.1.0）としてまとめています。

## [Unreleased]

（現状のコードでは明示的な未リリース変更はありません。次版での変更点はここに追記してください。）

---

## [0.1.0] - 2026-03-20

初期リリース相当。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントの定義（kabusys.__init__）とバージョン情報を追加。
  - サブパッケージ公開 API: data, strategy, execution, monitoring を公開。

- 環境変数・設定管理 (`kabusys.config`)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定（配布後も安定）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
  - .env パーサーは次をサポート:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォートとバックスラッシュエスケープ。
    - クォートなしの行におけるインラインコメントの取り扱い（前が空白/タブの場合にのみコメントと認識）。
  - 必須設定取得 `_require`、Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルの検証・取得を実装。
    - KABUSYS_ENV / LOG_LEVEL の不正値検出とエラー報告。

- Data 層（`kabusys.data`）
  - J-Quants API クライアント (`jquants_client`)
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter 実装。
    - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンから ID トークンを再取得して 1 回リトライ（トークンキャッシュ共有）。
    - ページネーション対応のデータ取得（daily_quotes / statements / trading_calendar）。
    - DuckDB へ冪等保存する関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
      - ON CONFLICT DO UPDATE により重複を排除。
      - PK 欠損レコードはスキップし警告を出力。
    - 変換ユーティリティ `_to_float`, `_to_int`（頑健な型変換、空値/不正値は None）。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead bias のトレースを可能に。

  - ニュース収集モジュール (`news_collector`)
    - RSS フィード取得→前処理→raw_news への冪等保存ワークフローを実装。
    - 記事 ID の生成は正規化 URL の SHA-256（先頭 32 文字）で冪等性を保証。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート。
    - セキュリティ対策:
      - defusedxml を利用して XML Bomb 等に対処。
      - HTTP/HTTPS 以外のスキームを拒否し SSRF リスクを低減（実装上の意図）。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - バルクINSERTのチャンク化とトランザクションで性能と一貫性を確保。

- 研究 / ファクター計算（`kabusys.research`）
  - ファクター計算関数群:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: 最新の財務データと株価から PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算（1,5,21 日がデフォルト）。
    - calc_ic: Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ。
  - 実装方針: DuckDB と標準ライブラリのみで動作（pandas 等に依存しない）、prices_daily / raw_financials のみ参照。

- 戦略層（`kabusys.strategy`）
  - 特徴量生成 (`feature_engineering.build_features`)
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（z-score）と ±3 でのクリップを実施。
    - features テーブルへの日付単位 UPSERT（削除→挿入のトランザクション）で冪等性を保証。
    - ルックアヘッドバイアス対策: target_date 時点のデータのみを使用。
  - シグナル生成 (`signal_generator.generate_signals`)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを計算。
    - デフォルト重みと閾値（threshold=0.60）を実装。カスタム weights のバリデーションとリスケール処理を実装。
    - final_score の計算、スコア降順ランク付け、BUY/SELL シグナル生成を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制）。
    - 保有ポジションに対するエグジット判定（stop_loss：-8% 超過、スコア低下）を実装。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）による冪等性を保証。

### 変更 (Changed)
- なし（初期リリースのため新規実装が主体）。ただし設計方針・安全策（例: defusedxml の採用、ID トークンのキャッシュ、リトライポリシー等）は実装時に明示的に盛り込まれています。

### 修正 (Fixed)
- なし（初期リリース）。ログ出力や警告メッセージにより不整合時の挙動を明示。

### 既知の制限・未実装の機能 / TODO
- signal_generator 内の一部エグジット条件は未実装:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過） — positions テーブルに entry_date 等が必要
- news_collector の実際のネットワーク制約（タイムアウトやフィード個別の扱い）や RSS ソース追加は今後の拡張対象。
- execution 層（kabusys.execution）はパッケージに含まれるが今回のコードでは具体的な実装が示されていません（プレースホルダ）。
- DB スキーマ（テーブル定義: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）はコード側で前提になっているため、初期セットアップ手順でのスキーマ整備が必要。

### セキュリティ (Security)
- XML パーシングに defusedxml を採用して XML 関連の攻撃（XML bomb 等）に対処。
- RSS URL 正規化とスキーム検査による SSRF 緩和の設計が含まれる。
- J-Quants クライアントは認証トークンの自動リフレッシュ時に無限再帰を防止するフラグを実装。

---

作成にあたっては、各モジュール内のドキュメンテーション文字列、ログメッセージ、定数・関数名から機能と設計意図を推測して記載しました。実際のリリースノート作成時は以下を追記してください:
- 実際のリリース日（ここでは 2026-03-20 を仮指定）
- 具体的な DB スキーマ定義とセットアップ手順
- 既知のバグや issue 番号（存在する場合）
- 将来的な変更（Breaking Changes を伴う場合は明示）