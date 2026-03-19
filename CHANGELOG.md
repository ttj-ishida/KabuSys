Keep a Changelog
=================

すべての重要な変更履歴はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

注: コードベースから推測した変更点を基に作成しています（初回リリース想定）。

[Unreleased]


0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリースを追加。
  - パッケージ情報:
    - バージョン: 0.1.0
    - モジュール群: data, strategy, execution, monitoring（__all__ に公開）
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（CWD に依存しない挙動）。
    - 読み込み優先度: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは以下に対応:
    - 空行・コメント行の無視、export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、
      インラインコメントの扱い（クォート有無で挙動を区別）。
    - 誤った行やキー欠損を安全にスキップ。
  - Settings クラスを提供（settings インスタンスでアクセス）。
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを定義。
    - KABUSYS_ENV の検証（development / paper_trading / live）、LOG_LEVEL の検証。
    - Path 型でのデフォルト DB パス（DuckDB / SQLite）。
    - 必須環境変数未設定時に ValueError を送出する _require 実装。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - ページネーション対応（pagination_key を使って継続取得）。
    - 再試行（指数バックオフ）ロジック: 最大 3 回、408/429/5xx を対象。
    - 401 受信時にリフレッシュトークンから自動的に ID トークンを更新して 1 回リトライ。
    - ID トークンのモジュールレベルキャッシュを保持（ページネーション間で共有）。
    - JSON デコード失敗やネットワークエラーをハンドリング。
  - データ保存関数:
    - save_daily_quotes/save_financial_statements/save_market_calendar を実装。
    - DuckDB への保存は冪等性を保つ（ON CONFLICT DO UPDATE）。
    - PK 欠損行のスキップとスキップ件数ログ出力。
    - fetched_at を UTC ISO フォーマットで記録し、Look-ahead バイアス可視化に配慮。
  - ユーティリティ: 安全な型変換関数 _to_float / _to_int を提供。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news に保存する機能の実装（設計仕様に沿う）。
    - デフォルト RSS ソースを定義（例: Yahoo Finance のカテゴリ RSS）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除、小文字化）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）等で冪等性を確保する設計を記載。
    - XML パースに defusedxml を使用して XML Bomb 等の攻撃を防止。
    - HTTP レスポンス受信サイズ上限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を防止。
    - HTTP スキームの検証や SSRF 想定の対策を設計に明記。
    - DB へのバルク INSERT はチャンク化（_INSERT_CHUNK_SIZE）して実行。
- リサーチ機能 (kabusys.research)
  - ファクター計算モジュールを提供:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio。
    - calc_value: 最新財務データ（raw_financials）と prices_daily を組み合わせて PER / ROE を算出。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマン順位相関（Information Coefficient）を実装。サンプル不足時は None を返す。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位（ties）を平均ランクで処理する安定的なランク付けを実装（round による tie 対策付き）。
  - すべて DuckDB 接続を受け取り、prices_daily / raw_financials を参照する設計（外部依存最小化）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research の calc_* を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）し冪等性と原子性を確保（トランザクション）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）から final_score を計算。
    - コンポーネントごとのスコア算出:
      - momentum: 複数シグナルを sigmoid→平均。
      - value: PER に基づく非線形変換（PER=20 で 0.5 に対応）。
      - volatility: atr_pct の Z スコアを反転して sigmoid。
      - liquidity: volume_ratio を sigmoid。
      - news: ai_score を sigmoid（未登録は中立 0.5）。
    - 重みはデフォルト値を持ち、不正な user weights を除外、合計が 1 でない場合は再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数が閾値以上）で BUY を抑制。
    - BUY は threshold を超える銘柄、SELL はポジションに対するストップロス（-8%）やスコア低下で判定。
    - SELL 優先ポリシー: SELL になった銘柄は BUY から除外しランクを再計算。
    - signals テーブルへ日付単位で置換（トランザクション）し冪等性を保証。
- 内部ユーティリティと設計注意点
  - zscore_normalize 等の正規化ユーティリティは kabusys.data.stats 経由で利用する設計。
  - DuckDB を中心とした SQL + Python ハイブリッド実装でパフォーマンスと可監査性を両立。
  - ルックアヘッドバイアス対策: 各種取得・計算で target_date 以前の情報のみを使用する方針を明確にしている。
  - ロギング・警告を随所に配置し、価格欠損や入力異常時の挙動を説明している。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- ニュースパーサで defusedxml を使用し XML 関連の脆弱性に配慮。
- ニュース URL 正規化でトラッキングパラメータを除去、SSRF 対策を検討した設計が含まれる。
- J-Quants クライアントで 401 リフレッシュ時の失敗や再試行ロジック、タイムアウトなどを明示的にハンドリング。

Notes / Known limitations
- execution パッケージの初期化ファイルのみ存在し、実際の発注ロジックはこのスナップショットには含まれていない（execution 層は strategy 層から分離されている設計）。
- 一部の高度なエグジット条件（トレーリングストップ、時間決済など）はコメントで未実装として記載されている（positions テーブルに追加のメタ情報が必要）。
- 外部依存（DuckDB、defusedxml）を前提としており、運用環境での接続/インストールが必要。
- テスト用の自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意しているが、CI/テストでの完全な互換は追加テストが必要。

References
- コード内のコメントに StrategyModel.md / DataPlatform.md 等外部仕様を参照する記述あり。リリース後の詳細な仕様書・ドキュメント整備を推奨。