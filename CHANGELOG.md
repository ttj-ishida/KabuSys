CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ説明: "KabuSys - 日本株自動売買システム"
  - パブリック API エクスポート: data, strategy, execution, monitoring

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを追加
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）
  - .env の自動ロード順序: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - インラインコメントの取り扱い（クォート内を除外、クォート外は直前が空白/tab の場合に # をコメントと認識）
  - Settings クラスで必須変数取得関数 (_require) を提供（未設定時は ValueError）
  - 各種設定プロパティを提供（J-Quants / kabu API / Slack / DB パス / 環境フラグ / ログレベル検証）
  - env/log_level の許容値検証を実装（不正値で例外を発生）

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
    - レート制限管理（固定間隔スロットリング、120 req/min）
    - 冪等性を意識した DuckDB への保存関数（ON CONFLICT による UPSERT）
    - ページネーション対応（pagination_key）
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの id_token キャッシュ
    - JSON デコードエラーやネットワークエラーの明示的な扱い
  - データ保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供
    - PK 欠損行のスキップ、スキップ数のログ出力
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス対策）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する基盤を追加
  - セキュリティと頑健性設計:
    - defusedxml による XML パース（XML Bomb 対策）
    - HTTP/HTTPS スキームのみ許可（SSRF 緩和）
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）
    - トラッキングパラメータ除去（utm_* など）および URL 正規化
    - 記事 ID を SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保
    - バルク INSERT のチャンク処理による DB 書き込み負荷の抑制
  - デフォルト RSS ソース定義 (Yahoo Finance のビジネスカテゴリ RSS)

- リサーチ・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）
    - 各関数でウィンドウサイズや欠損取り扱いを明確化（ex. MA200 のカウントチェック、ATR の true_range 計算）
    - パフォーマンス配慮（スキャン範囲バッファ、ウィンドウ集計を SQL で実行）
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一度に取得）
    - calc_ic（Spearman ランク相関に基づく IC 計算、サンプル数閾値あり）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank ユーティリティ（同順位は平均ランク、丸めによる ties 対応）
  - すべて外部ライブラリに依存せず、DuckDB 接続を受け取る設計

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research の生ファクターを組み合わせて features テーブルを生成
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 クリップ
    - 日付単位での置換（DELETE + バルク INSERT、トランザクションで原子性保証）
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features と ai_scores を統合して各銘柄の final_score を計算
    - コンポーネントスコア計算: momentum / value / volatility / liquidity / news
    - スコア変換ユーティリティ: シグモイド関数、欠損コンポーネントは中立 0.5 で補完
    - 重みの取り扱い:
      - デフォルト重みを定義し、ユーザ提供の weights をバリデート・マージ・正規化（合計 = 1 に再スケール）
      - 不正な重み（非数値/負値/NaN/Inf/未知キー）は無視し警告
    - Bear レジーム判定（AI レジームスコアの平均が負かつサンプル数閾値を満たす場合）
      - Bear の場合は BUY シグナルを抑制
    - BUY シグナル閾値（デフォルト 0.60）、SELL 条件（ストップロス -8%、スコア低下）
    - 保有ポジションに対するエグジット判定（positions と最新価格を参照）
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）

- データ変換ユーティリティ
  - jquants_client にて _to_float / _to_int を実装し、安全に型変換
  - raw API レスポンスのバリデーションとスキップロジックを実装

- ロギング / エラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを追加（info/debug/warning）
  - トランザクション時の COMMIT/ROLLBACK 保護と失敗時の警告ログ

Changed
- 初回公開のため該当なし（初出の機能群を追加）

Fixed
- 初回公開のため該当なし

Removed
- 初回公開のため該当なし

Security
- news_collector で defusedxml を利用して XML の脆弱性を緩和
- RSS URL の正規化・スキームチェック・受信サイズ上限などにより SSRF／DoS リスクを低減

Notes / Implementation decisions
- Look-ahead bias の防止を設計方針として徹底:
  - API データは fetched_at を UTC で記録
  - feature/signal の計算は target_date 時点でシステムが知り得るデータのみを使用
- 冪等性を重視:
  - DuckDB への保存は ON CONFLICT / 日付単位の DELETE+INSERT を利用して置換可能な形を採用
- 外部依存を最小化:
  - research モジュールは標準ライブラリと DuckDB SQL のみで実装（pandas などに依存しない）

Known limitations / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに追加フィールドが必要）
- ニュース記事の銘柄紐付け（news_symbols）処理の詳細実装はドキュメントで言及されているが、実装の拡張が必要
- rate limiter は単純な固定間隔方式（スロットリング）。将来的にはトークンバケット等の方式検討余地あり

参考
- パッケージバージョンは src/kabusys/__init__.py 内の __version__ = "0.1.0" に一致します。