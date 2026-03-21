CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。

[Unreleased]
------------

なし。

0.1.0 - 2026-03-21
------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0"、主要モジュールの __all__ を定義。

- 環境設定 / ロード機能を追加（src/kabusys/config.py）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 独自の .env パーサ実装:
    - コメント・export 句・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント処理に対応。
    - 既存 OS 環境変数の保護（protected set）と override 挙動を提供。
  - Settings クラスを提供し、必須変数取得メソッド（_require）を通じたバリデーションを実施。
    - J-Quants / kabu API / Slack / DB パス 等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の値チェックを実装（許容値を列挙）。
    - Path 系設定は expanduser を実行。

- データ取得 / 保存（J-Quants クライアント）を追加（src/kabusys/data/jquants_client.py）。
  - API 呼び出しユーティリティ:
    - 固定間隔のレートリミッタ (_RateLimiter) を実装（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回）と 408/429/5xx のリトライ。
    - 401 を受けた場合はトークン自動リフレッシュを 1 回行い再試行。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - JSON デコードやネットワークエラー時の明確な例外メッセージ。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等保存。
    - fetched_at を UTC で記録し Look-ahead バイアス追跡を可能に。
    - 型変換ユーティリティ (_to_float / _to_int) を導入、PK 欠損行はスキップしてログ出力。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS 取得・パース・正規化・DB保存の処理を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等の対策）。
    - URL 正規化（utm_* 等のトラッキングパラメータ除去、スキーム・ホストの正規化、フラグメント削除、クエリキーソート）。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）等。
  - 冪等性・性能:
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し重複を防止。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）とトランザクション集約。
    - INSERT RETURNING 相当の挿入件数正確取得を想定した実装方針（DuckDB 用に最適化可能）。

- リサーチ / ファクター計算ライブラリを追加（src/kabusys/research/*）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）、欠損ハンドリング。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio（20 日窓、true_range の NULL 伝播制御）。
    - calc_value: per（株価/EPS）、roe（raw_financials から最新報告を取得）。
    - SQL を活用し DuckDB のウィンドウ関数で効率的に算出。
    - スキャン範囲にカレンダーバッファを設け、週末・祝日欠損に耐性。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターン計算（LEAD を利用、ホライズンの検証: 1〜252 日）。
    - calc_ic: スピアマンランク相関（ランク化 & ties は平均ランクで処理）、有効レコード 3 未満で None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank ユーティリティ: 同順位は平均ランク、浮動小数点の丸め (round(..., 12)) を使用して ties の誤検出を防止。
  - research/__init__.py で主要関数を再エクスポート。

- 特徴量生成（Feature Engineering）を追加（src/kabusys/strategy/feature_engineering.py）。
  - build_features(conn, target_date): research のファクター計算を統合して features テーブルへ UPSERT（日付単位で削除→挿入の置換、トランザクションで原子性保証）。
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円、20 日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）。
  - 正規化:
    - zscore_normalize を利用、対象カラムを Z スコア化して ±3 でクリップ（外れ値抑制）。
  - Look-ahead バイアス対策: target_date 時点のデータのみ使用。

- シグナル生成モジュールを追加（src/kabusys/strategy/signal_generator.py）。
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、コンポーネント（momentum / value / volatility / liquidity / news）を算出。
    - Z スコアはシグモイド変換（_sigmoid）して [0,1] にマッピング。
    - AI スコアが未登録の場合は中立（0.5）で補完。
    - 重みの入力検証・合計が 1.0 でない場合のリスケール処理、無効値は無視。
    - Bear レジーム判定（_is_bear_regime）により BUY シグナルを抑制可能。
    - BUY は閾値超過銘柄、SELL はポジションに対してストップロス（-8%）やスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位の置換で保存（トランザクション）。
  - ロギングと不整合時の警告を充実（価格欠損 / features 欠損等）。

- strategy/__init__.py で build_features / generate_signals を公開。

Other
- DuckDB 接続を引数に取る API 設計を一貫して採用し、本番の発注 API に依存しないアーキテクチャを実現（テスト・リサーチとの分離）。
- 各モジュールでログメッセージを充実させ、失敗時の ROLLBACK 処理と警告出力を実装。

Known issues / TODO (既知の制限)
- エグジット条件のうち以下は未実装（要 positions テーブルの追加情報: peak_price / entry_date 等）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- calc_value: PBR・配当利回り等は未実装。
- news_collector: 記事と銘柄の紐付け（news_symbols）周りの細部実装は DataPlatform.md に基づく拡張が想定される。
- save_* 系は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar / features / signals / positions / ai_scores 等）が事前に存在することを前提としている（マイグレーション/DDL ツールは別途必要）。
- calc_forward_returns は horizons が 252 を超えると ValueError を送出する設計（保守的な上限）。

Security
- defusedxml の採用、受信バイト制限、URL 正規化、外部リクエストのスキーム検証など、外部入力に対する脆弱性対策を導入。

Acknowledgments / Notes
- 設計方針として「ルックアヘッドバイアス防止」「冪等性」「トランザクションによる原子性」「ログによる可観測性」を重視して実装しています。
- 将来的なリリースでは発注（execution）層との連携、バックテスト・運用監視（monitoring）機能の充実、AI スコア算出の詳細実装を予定しています。