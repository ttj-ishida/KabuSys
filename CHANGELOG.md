# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

現在のバージョン順: 変更は新しいものを上に記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システムのコア機能を実装しました。主にデータ取得・保存、ファクター計算、特徴量作成、シグナル生成、環境設定の読み込みに関する機能を提供します。

### Added
- パッケージ化
  - pakage エントリポイント: `src/kabusys/__init__.py`（バージョン 0.1.0、公開 API: data, strategy, execution, monitoring）。

- 設定管理 (`src/kabusys/config.py`)
  - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env の読み取りロジック: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応する堅牢なパーサー実装。
  - OS 環境変数保護: `.env.local` の上書き時に既存 OS 環境変数を保護する仕組み。
  - `Settings` クラスにアプリケーション設定プロパティを提供:
    - J-Quants / kabu API / Slack トークンやチャネル、DB パス（DuckDB/SQLite）、環境種別（development/paper_trading/live）、ログレベル、ユーティリティ判定プロパティ（is_live/is_paper/is_dev）など。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - 必須環境変数未設定時の明示的エラー（_require）。

- データ取得・永続化（J-Quants クライアント） (`src/kabusys/data/jquants_client.py`)
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を満たす `_RateLimiter`。
    - 冪等性を意識したデータ保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
    - ページネーション対応の `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の場合は `Retry-After` ヘッダを尊重。
    - 401 受信時の自動 ID トークンリフレッシュ（1 回）とモジュールレベルのトークンキャッシュ共有。
    - データ整形ユーティリティ `_to_float` / `_to_int`。
    - 取得時の `fetched_at` を UTC ISO8601 で記録（Look-ahead bias 対策）。

- ニュース収集モジュール (`src/kabusys/data/news_collector.py`)
  - RSS フィードからの記事収集ロジック（デフォルトソースとして Yahoo Finance のカテゴリ RSS を設定）。
  - 安全対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - 受信バイト数上限（10 MB）でメモリ DoS を軽減。
    - URL 正規化（スキーム/ホストの小文字化、追跡パラメータ（utm_* 等）の除去、フラグメント削除、クエリソート）と記事 ID の SHA-256 ハッシュ化により冪等性を保証。
    - HTTP/HTTPS 以外のスキームや不正な URL に対する防御（SSRF に配慮した設計方針）。
  - バルク INSERT のチャンク化（チャンクサイズ 1000）とトランザクションでの DB 保存。実際に挿入された件数を正確に返す方針。

- リサーチモジュール (`src/kabusys/research/*`)
  - ファクター計算（`src/kabusys/research/factor_research.py`）:
    - `calc_momentum`（mom_1m / mom_3m / mom_6m / ma200_dev）
    - `calc_volatility`（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - `calc_value`（per / roe、raw_financials から最新財務データを取得）
    - 時系列スキャンのためのバッファや NULL/データ不足時の処理を明確に実装。
  - 特徴量探索（`src/kabusys/research/feature_exploration.py`）:
    - `calc_forward_returns`（任意ホライズンの将来リターンを一括取得）
    - `calc_ic`（Spearman ランク相関による IC 計算）
    - `factor_summary`（count/mean/std/min/max/median の統計サマリー）
    - `rank`（同順位は平均ランクにするランク関数）
  - `src/kabusys/research/__init__.py` で上記を公開。

- 戦略モジュール (`src/kabusys/strategy/*`)
  - 特徴量生成 (`src/kabusys/strategy/feature_engineering.py`):
    - 研究環境で計算した生ファクターを読み込み、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）に対する Z スコア正規化（外部 zscore_normalize を使用）、±3 でクリップ。
    - 日付単位での冪等的な features テーブルへの置換（トランザクション + bulk insert）。
    - `build_features(conn, target_date)` を公開。
  - シグナル生成 (`src/kabusys/strategy/signal_generator.py`):
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換等で [0,1] にマッピング。欠損値は中立 0.5 で補完。
    - デフォルト重みと閾値（weights default: momentum 0.40 等、threshold=0.60）を実装。外部から重みを与えた場合は妥当性チェックと再スケールを行う。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合。閾値: _BEAR_MIN_SAMPLES=3）で BUY を抑制。
    - SELL（エグジット）判定: ストップロス（-8%）優先、スコア低下（final_score < threshold）などを実装。保有銘柄の価格欠損時は判定をスキップする安全措置。
    - 日付単位での冪等的な signals テーブルへの置換（トランザクション + bulk insert）。
    - `generate_signals(conn, target_date, threshold=None, weights=None)` を公開。

- データ統計ユーティリティ
  - `kabusys.data.stats.zscore_normalize` を利用（research/strategy での正規化処理に依存、research/__init__ から再公開）。

### Fixed
- .env パーサーの細かな振る舞いを明確化:
  - export プレフィックス対応、クォート内エスケープの扱い、インラインコメント判定ルール（クォートなしで '#' の直前がスペース/タブの場合のみコメント扱い）を実装し実用性と互換性を向上。

### Security
- RSS パースに defusedxml を利用して XML 関連の攻撃ベクタを軽減。
- .env 読み込みで OS 環境変数を保護する設計（.env.local の上書きでも既存 OS 環境変数を上書きしない）。
- J-Quants クライアントのネットワーク例外/HTTP エラーに対してリトライや最大試行の制御を実装し、サービス異常時の誤動作を低減。

### Notes / Design decisions
- DuckDB に対する書き込みは可能な限り冪等かつトランザクション単位で行い、途中失敗時は ROLLBACK で安全に復帰するように設計されています。
- データ取得時のタイムスタンプは UTC で保存し、「いつデータが利用可能だったか」を追跡可能にしてルックアヘッドバイアスを防止する方針を採用しています。
- 本リリースでは発注（execution）層や実口座との接続は含まれず、strategy 層はシグナル生成までを担当し、発注は別モジュールで扱う想定です。
- 一部の戦略ロジック（例: トレーリングストップ、時間決済）は comments にて未実装として明示されています。

---

署名: kabusys 開発チーム（ソースコード注釈に基づきCHANGELOGを作成）