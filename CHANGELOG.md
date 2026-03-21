# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

- 変更種別の意味:
  - Added: 新機能の追加
  - Changed: 既存機能の変更
  - Fixed: バグ修正
  - Security: セキュリティに関する変更

## [Unreleased]

（現時点では開発中の変更はありません。初期リリースは下記参照）

## [0.1.0] - 2026-03-21

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎モジュール群を追加。
  - kabusys.config
    - .env ファイル/環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
    - .env パーサで以下に対応:
      - 空行・コメント行（#）を無視
      - export KEY=val 形式のサポート
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォートなし値でのインラインコメント処理（直前が空白/タブの場合のみ）
    - 複数の .env 読み込み順制御（OS 環境変数 > .env.local > .env）、既存 OS 環境変数の保護（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ。
    - Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン／チャンネル、DB パス等のプロパティとバリデーション）。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。
  - data モジュール（J-Quants クライアント・ニュース収集）
    - J-Quants API クライアントを実装（data/jquants_client.py）:
      - 固定間隔スロットリングによるレート制限制御（120 req/min）。
      - ページネーション対応（pagination_key を用いたループ取得）。
      - リトライ戦略（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に含む。
      - 401 受信時にリフレッシュトークンで自動トークン更新を行い 1 回だけリトライするロジック。
      - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
      - JSON パースのエラー報告。
    - DuckDB への保存（save_*）ユーティリティ:
      - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
      - 挿入は冪等性を保つため ON CONFLICT DO UPDATE を利用。
      - fetched_at を UTC ISO8601 で付与（Look-ahead バイアスのトレース用途）。
      - PK 欠損行のスキップおよびスキップ数の警告ログ。
    - news_collector: RSS からのニュース収集機能の骨組みを実装。
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）。
      - 記事 ID を URL 正規化後の SHA-256（先頭32文字等）で生成する方針（冪等性確保）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES）や defusedxml による XML の安全処理、バルク挿入チャンク化方針を採用。
  - research モジュール（研究用ファクター計算・解析）
    - factor_research:
      - calc_momentum / calc_volatility / calc_value を提供。prices_daily / raw_financials を参照して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per/roe）を計算。
      - ウィンドウ欠損時は None を返す設計。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足（<3）や分散ゼロ時は None。
      - factor_summary / rank: 要約統計量・ランク変換ユーティリティを実装（外部ライブラリに依存しない実装）。
    - research.__init__ で上記関数群を再公開。
  - strategy モジュール（特徴量作成・シグナル生成）
    - feature_engineering.build_features:
      - research 側で算出した生ファクターをマージし、ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8）を適用。
      - 正規化（zscore_normalize を利用）→ ±3 でクリップして外れ値を抑制。
      - features テーブルへ日付単位の置換（DELETE + INSERT）でトランザクションにより冪等性・原子性を保証。
    - signal_generator.generate_signals:
      - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を計算（デフォルト重みを採用、ユーザー指定 weights に対する検証と再スケール処理あり）。
      - シグモイド変換・欠損コンポーネントは中立 0.5 で補完。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数が閾値以上で判定）による BUY 抑制。
      - BUY（threshold デフォルト 0.60）および SELL（ストップロス -8% / スコア低下）を生成。
      - 保有ポジションの価格欠損時は SELL 判定をスキップする安全策、features 未登録の保有銘柄は score=0 と見なして SELL 対象に。
      - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。
  - パッケージ公開情報
    - パッケージバージョンを __version__ = "0.1.0" に設定し、主要 API（build_features, generate_signals）をエクスポート。

### Changed
- （初期リリースのため既存機能の変更はなし）

### Fixed
- （初期リリースのためバグ修正履歴はなし）

### Security
- news_collector で defusedxml を使用し XML 攻撃（XML bomb 等）への対処を想定。
- RSS URL 正規化／トラッキングパラメータ除去・受信サイズ制限などでメモリ DoS や追跡パラメータ混入の軽減方針を採用。
- J-Quants クライアントは 30 秒タイムアウト・リトライ・トークン自動リフレッシュなど堅牢化を図る。

### Notes / Known limitations
- signal_generator のエグジット条件は一部未実装（トレーリングストップ / 保有日数による時限決済は positions に peak_price / entry_date 情報が必要）。
- news_collector の完全な SSRF/IP ホワイトリスト検査など低レベルのネットワーク防御は骨子のみ（将来的にさらに厳格化予定）。
- research モジュールは DuckDB 上の prices_daily / raw_financials に依存。外部の時系列欠損や営業日補正は利用者側でデータ整備が必要。
- 外部依存を最小化する設計だが、実行環境には duckdb と defusedxml が必要。

---

上記はコードを読み取って推測した初期リリースの変更履歴です。項目の表現や追加したい細かな修正履歴（例えばコミット単位の詳細や作者情報など）があれば、追記して更新します。