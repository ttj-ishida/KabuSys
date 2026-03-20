Keep a Changelog に準拠した CHANGELOG.md (日本語)
※コードベースから推測して作成しています。実際の変更履歴がある場合は適宜修正してください。

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- (今後の作業・未実装/改善案)
  - execution パッケージの実装（現在 __init__.py のみで具体的な発注処理は未実装）
  - signals/positions に必要な追加フィールド（peak_price / entry_date 等）を用いたトレーリングストップや時間決済の実装
  - news -> 銘柄紐付け（news_symbols）周りの追加ロジック・テスト強化
  - 大量データ処理時のパフォーマンスプロファイリング・最適化（DuckDB クエリ・バッチサイズ等）
  - 単体テスト・統合テストの追加（特にネットワーク/外部API周りのモック）

[0.1.0] - 2026-03-20
-------------------
Added
- パッケージ基盤
  - kabusys パッケージ初期版を追加。__version__ = "0.1.0"、公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に検索（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理などをサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別・ログレベル等の設定プロパティを安全に取得。
    - 必須キーが未設定の場合は明示的な ValueError を発生させる。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
    - パス系設定は Path オブジェクトで返す。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
    - レート制限対策: 固定間隔スロットリング（120 req/min 相当）の RateLimiter を実装。
    - リトライ: 指数バックオフ、最大 3 回、対象ステータスコード/ネットワークエラーに対する再試行ロジックを実装。
    - 401 時の自動トークンリフレッシュ（1 回のみ）と再試行を実装。id_token のモジュールレベルキャッシュを保持。
    - ページネーション対応の fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB への保存（冪等性）
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 各 save_* は PK 欠損行のスキップ、ON CONFLICT を使った更新（UPSERT）により冪等に保存。
    - 型変換ユーティリティ _to_float / _to_int を提供し、入力の頑健性を確保。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードの取得・解析モジュールを追加。
    - デフォルト RSS ソース定義（yahoo_finance 等）。
    - XML のパースに defusedxml を使用して XML Bomb 等の攻撃を軽減。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - URL 正規化: スキーム・ホストの小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリソート。
    - 記事 ID は正規化後の URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保する設計方針。
    - バルク INSERT のチャンク処理とトランザクションの考慮（INSERT CHUNK サイズ設定）。
  - 安全対策: HTTP スキームチェック、SSRF 想定の防御、DefusedXml の例外処理を想定。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュールを実装し、prices_daily / raw_financials を用いて複数のファクターを計算。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を算出。過去データスキャンのバッファ処理あり。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、volume_ratio を算出。true_range の NULL 伝播を慎重に扱う。
    - calc_value: target_date 以前の最新財務データを用い、per / roe を計算（EPS が 0 か欠損なら per=None）。
  - feature_exploration モジュールを実装。
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21）で将来リターンを計算。取得クエリはスキャン範囲を限定。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル数不足時（<3）は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー実装。
    - rank: 同順位は平均ランクを採るランク付け関数（丸め誤差対策の round を使用）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装。
    - research の calc_* から得た raw ファクターをマージ。
    - ユニバースフィルタ: 最低株価（300円）・20日平均売買代金（5億円）を適用。
    - 正規化: zscore_normalize を適用し ±3 でクリップ（外れ値対策）。
    - features テーブルへ日付単位の置換（DELETE + INSERT をトランザクションで実行し冪等性を保証）。
    - DuckDB クエリで当日欠損に対応するため target_date 以前の最新価格を参照するロジックを実装。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装。
    - features / ai_scores / positions を参照して最終スコア（final_score）を算出。
    - 各コンポーネントスコア: momentum/value/volatility/liquidity/news の算出ロジックを実装（シグモイド変換、逆数変換など）。
    - weights のマージ・検証・再スケール処理を実装（不正値はスキップ、合計が 1.0 でない場合は正規化）。
    - Bear レジーム検出: ai_scores の regime_score の平均が負であれば BUY シグナルを抑制（サンプル数閾値を設定）。
    - BUY シグナルは閾値（デフォルト 0.60）を超えた銘柄に対して付与。SELL シグナルは保有ポジションに対するストップロスやスコア低下で生成。
    - SELL 優先ポリシー: SELL 銘柄は BUY から除外、その後ランクを再付与。
    - signals テーブルへの日付単位置換をトランザクションで実行（冪等性確保）。
  - 実装上の注意点として、トレーリングストップ等はいくつか未実装（positions テーブルに追加情報が必要）である旨を明記。

Changed
- （初期リリースのため「追加」が中心。将来的に設定名前や DB スキーマ変更があればここに記載）

Fixed
- （初期リリース。既知の警告ログやエラーハンドリングを改善済み）
  - .env 読み込み失敗時に warnings.warn を利用して処理を継続するように変更。
  - DB へのトランザクション失敗時に ROLLBACK を試行し、失敗ログ（logger.warning）を出力するように実装。

Security
- defusedxml を用いた RSS パース（XML 攻撃対策）
- RSS / HTTP 取得時の受信サイズ制限など DOS 対策
- API トークンの自動リフレッシュは allow_refresh フラグで制御し、無限再帰を防止

内部実装上の設計判断（要点）
- ルックアヘッドバイアス対策: すべての解析・シグナルは target_date 時点のデータのみを使用することを原則としている。
- 冪等性: 外部データの保存は基本的に ON CONFLICT / DELETE+INSERT を用いて同一日付の再実行で上書き可能にしている。
- 外部依存の最小化（research モジュールは外部ライブラリに依存しない設計）および DuckDB による SQL ベースの集計を重視。

補足 / 既知の制約
- execution パッケージの具体的な発注実装は現状未実装（空パッケージ）。本番発注ロジックは今後追加予定。
- 一部の SELL 条件（トレーリングストップ・時間決済）は positions テーブルに追加情報（peak_price, entry_date 等）が必要であり未実装。
- news_collector の記事→銘柄の紐付け（news_symbols）の具体的ロジックや DB スキーマ詳細は実装/記載が必要。

---- END ----

変更点やリリース日付について修正・追記したい点があれば教えてください。実際のコミット履歴やリリースノートがあればそれに合わせて正確な CHANGELOG を生成します。