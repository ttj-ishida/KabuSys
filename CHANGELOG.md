CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

[Unreleased]
------------

- ドキュメントや設計仕様に基づく実装上の注意点・未実装項目を追記しました（トレーリングストップ・時間決済・一部ファクター等）。
- テスト運用向けに環境変数自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグの存在を明確化しました。

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース。
- パッケージエントリポイントを定義（kabusys.__version__ = "0.1.0", __all__ に主要モジュールを公開）。
- 環境設定管理モジュール (kabusys.config)
  - .env/.env.local をプロジェクトルート (.git または pyproject.toml を基準) から自動読み込みするロジックを実装。
  - export 形式やクォート、インラインコメントの扱いに対応した .env パーサーを実装。
  - OS 環境変数の保護（protected set）・override 制御を実装。
  - 必須設定取得ヘルパー _require と Settings クラスを実装（J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル検証を含む）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）を導入。

- データ取得・保存関連 (kabusys.data)
  - J-Quants クライアント (jquants_client)
    - API 呼び出しユーティリティを実装（固定間隔レートリミッタ、再試行（指数バックオフ）、HTTP 401 時のトークン自動リフレッシュ、ページネーション対応）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装（ページネーション考慮）。
    - DuckDB への冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT / DO UPDATE を用いて重複を排除。
    - データ型変換ユーティリティ（_to_float / _to_int）を実装し、変換失敗や空値を安全に扱う。
    - 取得時刻を UTC で記録し、Look-ahead バイアスに配慮。
  - ニュース収集モジュール (news_collector)
    - RSS フィード取得と raw_news への冪等保存ロジックを実装。
    - 記事 ID を URL 正規化後のハッシュで生成し冪等性を担保。
    - XML パーシングに defusedxml を利用してセキュリティ対策を実施。
    - URL 正規化（トラッキングパラメータ削除・スキーム/ホスト正規化・フラグメント除去・ソート）や受信サイズ上限（MAX_RESPONSE_BYTES）などの安全対策を実装。
    - HTTP スキーム検証や SSRF/メモリ DoS 対策を考慮した設計（制限・サニタイズ処理を導入）。
    - バルク挿入チャンク化により SQL の長さ/パラメータ数を抑制。

- リサーチ/ファクター関連 (kabusys.research)
  - ファクター計算モジュール (factor_research)
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離率）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - スキャン範囲やウィンドウサイズに関する定数（多数）を明示。
    - データ不足時の None ハンドリングを実装。
  - 特徴量探索モジュール (feature_exploration)
    - 将来リターン計算ユーティリティ calc_forward_returns（任意ホライズンの一括取得）、calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
    - pandas 等の外部依存を用いず標準ライブラリで完結する実装。
  - zscore_normalize は kabusys.data.stats から提供し、research/__init__.py で再エクスポート。

- 戦略関連 (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering)
    - 研究環境の生ファクターを読み込み、ユニバースフィルタ（最低株価・平均売買代金）を適用、指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション）する build_features を実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照する設計。
    - 冪等動作（DELETE してから INSERT）およびトランザクションによる原子性確保。
  - シグナル生成 (signal_generator)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を計算する generate_signals を実装。
    - デフォルト重み、閾値、ストップロス等の定数を実装。weights は入力補完・検証・再スケールされる。
    - Bear レジーム（AI レジームスコア平均が負）検出により BUY シグナルを抑制するロジックを実装。
    - 保有ポジションに対するエグジット判定（ストップロス・スコア低下）を実装（_generate_sell_signals）。Sell の優先処理により BUY から除外。
    - signals テーブルへの日付単位置換（トランザクション）を実装。
    - 欠損データ時の中立補完（None を 0.5）や、価格欠損時の SELL 判定スキップ等の堅牢性を確保。
  - strategy/__init__.py で主要 API を公開（build_features, generate_signals）。

Changed
- n/a（初期リリースのため履歴は追加のみ）。

Fixed
- n/a（初期リリースのため修正履歴はなし）。

Deprecated
- n/a。

Removed
- n/a。

Security
- news_collector: defusedxml を使用した XML パース、安全な URL 正規化、受信サイズ制限、スキーム検証等の対策を導入。
- jquants_client/_request: 外部ネットワークエラーや HTTP ステータスに対する安全なリトライとトークン自動再取得を実装。

Notes / Known limitations
- 一部エグジット条件は未実装（kabusys.strategy.signal_generator 内のコメント参照）。
  - トレーリングストップ（peak_price が positions テーブルで必要）
  - 時間決済（保有 60 営業日超過）
- Value ファクターの PBR・配当利回りは未実装。
- news_collector の RSS パースは基本的なフローを実装済みだが、実運用向けのソース数増加や言語処理は今後の拡張対象。
- DuckDB スキーマ（テーブル定義）はこのリリースに含まれないため、実行前に適切なスキーマ作成が必要。
- 実運用前に API トークン（J-Quants / Slack / kabuAPI）や DB パス等の環境変数を .env に設定する必要あり（Settings._require が必須変数未設定で例外を投げる）。

作者ノート
- 設計は「ルックアヘッドバイアス回避」「データ収集の冪等性」「トランザクションによる原子性」「外部依存の最小化」を重視しています。今後はテストカバレッジ拡充、エラー監視・メトリクス、追加ファクターや執行層との統合を進める予定です。