# Changelog

すべての変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを公開します。

### Added
- パッケージ初期化
  - kabusys.__version__ = 0.1.0 を設定。パッケージ公開のための __all__ を定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数読み込み (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルートを .git または pyproject.toml から検出するロジックを追加し、CWD に依存しない自動 .env ロードを実現。
  - .env / .env.local の読み込み順序を実装。OS 環境変数を保護する protected パラメータを導入。
  - .env パース実装: コメント・export プレフィックス・シングル/ダブルクォート・エスケープに対応する堅牢なパーサを追加。
  - テスト用に自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須キー取得時の検査（_require）と、KABUSYS_ENV / LOG_LEVEL の検証を実装（許容値チェック）。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）や Slack / API 周りの必須設定プロパティを提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（価格・財務・マーケットカレンダー取得）。
  - レート制限対策: 固定間隔スロットリング（120 req/min）を実装する _RateLimiter を導入。
  - 再試行ロジック: 指数バックオフで最大 3 回リトライ（408/429/5xx を対象）。429 の Retry-After を尊重。
  - 401 の場合は ID トークンを自動リフレッシュして再試行（1 回のみ）。
  - ページネーション対応の fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）：fetched_at を UTC で記録、PK ベースの UPSERT（ON CONFLICT DO UPDATE）により冪等性を確保。
  - 入力パースユーティリティ（_to_float, _to_int）を実装して受信データの堅牢な変換を提供。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集モジュールを追加（デフォルトで Yahoo Finance のカテゴリ RSS をサポート）。
  - セキュリティ対策: defusedxml の利用、受信最大サイズ制限（10 MB）、HTTP スキーム検査、SSRF を念頭に置いた実装方針。
  - URL 正規化: トラッキングパラメータ（utm_* 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリソートを実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保。
  - DB へのバルク保存時にチャンク処理とトランザクションを用い効率化。

- 研究用ファクター計算 (kabusys.research)
  - calc_momentum, calc_volatility, calc_value の factor_research モジュールを実装。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率（十分な履歴がない場合は None を返す）。
    - ボラティリティ/流動性: 20日 ATR（atr_pct）、20日平均売買代金、出来高比率等。
    - バリュー: 直近財務データ（raw_financials）と価格から PER/ROE を計算。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（同順位は平均ランクで扱う）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを提供。
    - rank: 同順位の平均ランクを取るランク関数（丸め対策あり）。
  - 研究モジュールは DuckDB の prices_daily / raw_financials のみ参照し、外部依存（pandas 等）を使わない設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research の生ファクターを取得し（calc_momentum, calc_volatility, calc_value）、ユニバースフィルタ（株価 >= 300円、20日平均売買代金 >= 5億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）して ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE → INSERT をトランザクションで行い原子性を保証）。
    - ルックアヘッドバイアス防止のため target_date 時点のみを参照する方針。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features テーブルと ai_scores を統合し、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントの変換関数（シグモイド、平均化、PER→value スコア等）を実装。
    - デフォルト重みと閾値を定義（デフォルト threshold=0.60、weights の合計は正規化して扱う）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かどうか、サンプル数検査あり）により BUY シグナルを抑制可能。
    - 保有ポジション（positions）に対するエグジット判定を実装（ストップロス -8% / スコア低下）。SELL シグナルは BUY より優先し、signals テーブルへ日付単位で置換して保存。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防ぐ設計。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Known issues / Notes
- 一部エグジット条件は未実装（コメントあり）:
  - トレーリングストップ（peak_price に依存）や時間決済（保有 60 営業日超）等は positions テーブルに追加情報が必要で現バージョンでは未実装。
- research モジュールは外部依存を避けるため pandas 等を利用していないため、大規模データの便利関数は将来的に追加検討の余地あり。
- jquants_client の再試行やスロットリングは単体テスト・統合テストで挙動確認が必要。実運用ではレート制限の変化や API 仕様変更に注意。
- news_collector は RSS フィードの多様な形式に対して堅牢性を持たせているが、実フィードに固有の XML 命名空間や文字エンコーディングの差異で追加対応が必要になる場合がある。

### Security
- defusedxml を用いた XML パースや受信バイト数制限など、外部入力に対する基本的な堅牢化を行っています。

---

今後のリリースでは以下を予定しています（候補）:
- Execution 層（kabuステーション API 経由の発注ロジック）とモニタリング機能の実装拡張
- positions テーブル拡張に伴うトレーリングストップ / 時間決済の実装
- News→AI スコア連携の強化（NLP パイプライン）および効率的な DB インデックス設計
- 単体テスト・統合テストの追加と CI ワークフロー整備

もし CHANGELOG に追記してほしい点や日付の修正等があれば教えてください。