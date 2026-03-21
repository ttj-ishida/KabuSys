# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、ソースコードから推測できる機能追加・実装方針・重要な仕様をもとに作成した初期リリースの変更履歴です。

フォーマット:
- Unreleased: 今後の変更予定（現状なし）
- 各リリース: 追加 (Added)、変更 (Changed)、修正 (Fixed)、セキュリティ (Security) のカテゴリで記載

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-21
初回公開リリース。日本株自動売買システム「KabuSys」の基本モジュールを実装。

### Added
- パッケージ情報
  - kabusys パッケージのバージョンを `0.1.0` として設定（src/kabusys/__init__.py）。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env/.env.local ファイルおよび OS 環境変数から設定値を自動読み込みする仕組みを実装。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に実施し、配布後の使用でも動作するように設計。
  - .env のパースロジックを独自実装（export プレフィックス、シングル/ダブルクォートやバックスラッシュエスケープ、コメント処理を考慮）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数取得のための `_require()` と Settings クラスを提供。J-Quants / kabu ステーション / Slack / DB パス / システム環境（env, log_level）などのプロパティを定義し、値検証を行う（例: KABUSYS_ENV の許容値, LOG_LEVEL の許容値）。
  - デフォルトの DB パス（DuckDB, SQLite）や kabu API のデフォルト base URL を設定するプロパティを提供。

- データ収集クライアント：J-Quants API（src/kabusys/data/jquants_client.py）
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを取得するクライアントを実装。
  - レート制限管理（_RateLimiter）を実装し、120 req/min を守る固定間隔スロットリングを適用。
  - リトライロジックを実装（指数バックオフ、最大試行回数 3 回、HTTP 408/429/5xx をリトライ対象に設定）。429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized を受けた場合はリフレッシュトークンを用いた id token 自動更新を 1 回行い再試行する仕組みを実装。モジュールレベルで id token をキャッシュしてページネーション間で共有。
  - ページネーション対応の fetch 系関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）を実装。
  - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。保存は冪等（ON CONFLICT DO UPDATE）で行い、fetched_at を UTC で記録。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装し、入力の安全な正規化を行う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存するための基盤を実装。デフォルトソースとして Yahoo Finance のニュース RSS を定義。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）やバルク挿入チャンク（_INSERT_CHUNK_SIZE）など、リソース保護を考慮した設計。
  - URL 正規化ロジック（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装するユーティリティ `_normalize_url`。
  - defusedxml を用いた XML パースを前提とし、セキュリティを考慮した設計（XML Bomb 等への防御策を想定）。

- リサーチ系ユーティリティ（src/kabusys/research/）
  - ファクター計算モジュール（factor_research.py）
    - momentum（1M/3M/6M リターン、200 日移動平均乖離）、volatility（20 日 ATR／相対 ATR、20 日平均売買代金、出来高比率）、value（PER、ROE）を DuckDB の window 関数等で計算する関数を実装。
    - データ不足時の扱い（所定のウィンドウ未満で None を返す）を明確化。
  - 特徴量探索モジュール（feature_exploration.py）
    - calc_forward_returns：指定ホライズン（デフォルト: 1/5/21 営業日）の将来リターンを一括で取得する実装。
    - calc_ic：Spearman のランク相関（Information Coefficient）を実装。データ不足（有効ペア数 < 3）の場合は None を返す。
    - factor_summary：指定カラムの count/mean/std/min/max/median を標準ライブラリのみで計算するユーティリティを実装。
    - rank：平均ランク（同順位は平均ランク）を返すユーティリティを実装。丸めを用いた ties の安定化処理あり。
  - research パッケージの __all__ を整備して主要 API をエクスポート。

- 戦略モジュール（src/kabusys/strategy/）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research で算出した raw ファクターを統合・正規化して features テーブルへ UPSERT（ターゲット日単位での置換）する build_features を実装。
    - ユニバースフィルタを実装（最低株価 = 300 円、20 日平均売買代金 >= 5 億円）。
    - 正規化は zscore_normalize を使用し、対象カラムを ±3 でクリップ。
    - トランザクション + バルク挿入で原子性を確保。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）とデフォルト閾値（0.60）を採用。ユーザー指定の weights は妥当性チェック・正規化される。
    - Bear レジーム判定（AI の regime_score 平均が負）。Bear 時は BUY シグナルを抑制。
    - エグジット（SELL）判定に以下を実装：
      - ストップロス（終値 / avg_price - 1 <= -8%）
      - final_score が閾値未満（score_drop）
    - 保有ポジションのない場合や価格欠損時の安全処理（ログ出力と判定スキップ）を実装。
    - signals テーブルへの日付単位の置換をトランザクションで実施。

- データ統計ユーティリティ（kabusys/data/stats を参照）
  - feature_engineering 等で利用される z スコア正規化ユーティリティを参照・利用。

### Changed
- （初回リリースのため履歴的変更なし。将来的に環境依存の設定読み込み順や閾値等は設定可能にする余地あり。）

### Fixed
- （初回リリースのためバグ修正履歴はなし。実装では可能な限り入力検証／例外回避を行う設計を採用。）

### Security
- defusedxml の使用、受信サイズ制限、HTTP リトライ／認証更新の際の再試行制御など、外部入力・ネットワーク処理に対する安全策を導入。
- .env の自動読み込みは環境変数で無効化可能（テスト環境や CI での安全性向上）。

---

注意
- 本 CHANGELOG はソースコード内容から推測して作成しています。実際のリリースノートや過去のコミット履歴は別途ご確認ください。
- docstring に記載された設計方針や未実装機能（例: トレーリングストップ、時間決済、news と銘柄紐付けの細かい実装など）は、将来のリリースで追加される可能性があります。