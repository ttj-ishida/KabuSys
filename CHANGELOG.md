# Changelog

すべての注目すべき変更をここに記載します。これは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下はコードベースから推測してまとめた主な追加・設計方針・既知の制約です。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パブリック API として data/strategy/execution/monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は .git または pyproject.toml を基準に探索（__file__ からの親ディレクトリ探索）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 高機能な .env パーサー実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、行頭のコメント無視、インラインコメントルール（# の取り扱い）など。
  - Settings クラスを提供（必須設定取得で未設定時は ValueError を送出）。
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティ。
    - 環境 (`KABUSYS_ENV`) とログレベルの検証（許容値チェック）。
    - convenience プロパティ: is_live / is_paper / is_dev。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx に対応）。
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回だけリトライ。
    - ページネーション対応（pagination_key を使用して全件取得）。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead バイアスのトレースを容易化。
  - DuckDB へ保存する冪等的保存関数を実装:
    - save_daily_quotes: raw_prices に対して ON CONFLICT DO UPDATE（重複更新）。
    - save_financial_statements: raw_financials に対して ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar に対して ON CONFLICT DO UPDATE。
    - データ整形ユーティリティ `_to_float`, `_to_int` を用いた型安全な変換。
  - 実装上の挙動など:
    - モジュールレベルで ID トークンをキャッシュ（ページネーション間で共有）。
    - fetch_* 系は id_token を省略可能（キャッシュ／自動リフレッシュ利用）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と raw_news への保存機能。
  - セキュリティ・堅牢性設計:
    - defusedxml を使用して XML Bomb 等の攻撃を防御。
    - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10 MB) を設定してメモリ DoS を防止。
    - URL 正規化（スキーム/ホスト小文字化、追跡パラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - HTTP/HTTPS 以外のスキームを拒否する等の SSRF への配慮（実装コメントより）。
  - バルク挿入時のチャンク制御やトランザクションまとめによる性能配慮。

- 研究（research）モジュール
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - Volatility（atr_20、atr_pct、avg_turnover、volume_ratio）
    - Value（per、roe）— raw_financials と prices_daily を組合せ
    - SQL＋ウィンドウ関数中心に DuckDB 上で直接計算し、prices_daily/raw_financials のみ参照。
    - 各関数は (date, code) をキーとする dict のリストを返す。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（horizons デフォルト [1,5,21]、ホライズンは営業日ベース）。
    - IC（Spearman の rho）計算、ランク関数（同順位は平均ランク、round 精度 12 桁で ties 検出）。
    - factor_summary: count/mean/std/min/max/median を算出。
  - research パッケージの __all__ に必要関数をエクスポート。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究で算出した raw ファクターを読み込み、ユニバースフィルタ・正規化・クリップして features テーブルへ UPSERT。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - 正規化: 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - 日付単位の置換（DELETE→INSERT をトランザクションでラップ）により冪等化。
  - 外部 API / 実際の発注レイヤには依存しない純粋なデータ処理ロジック。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ書き込む。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。
    - デフォルト BUY 閾値: 0.60。
    - コンポーネントスコア計算: モメンタム（シグモイド平均）、バリュー（PER→スコア変換）、ボラティリティ（ATR を反転）、流動性（出来高比率→シグモイド）。
    - AI ニューススコアは未登録時に中立値を補完。regime_score を集計して Bear 相場判定（サンプル数閾値あり）。
    - SELL 条件としてストップロス（-8%）と final_score の低下を実装。
    - SELL は BUY より優先、signals テーブルへ日付単位で置換。
    - weights の入力は検証され、既知キーのみ受け付け合計が 1.0 に正規化。

- その他
  - research/__init__ と strategy/__init__ に主要関数をエクスポート。
  - execution パッケージは初期化ファイルのみ（将来的な発注レイヤのためのプレースホルダと推測）。

### Security
- defusedxml を利用した XML パース、防御的な URL 正規化、受信バイト上限などニュース収集まわりでセキュリティ対策を実施。
- J-Quants クライアントでのトークン自動リフレッシュおよびレート制限・リトライ制御により API 認証・可用性面に配慮。

### Known limitations / TODOs
- signal_generator 内でコメントされている未実装事項:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- calc_value: PBR・配当利回りは現バージョンでは未実装。
- positions テーブルの schema に依存する機能（peak_price / entry_date 等）は未整備の可能性あり。
- news_collector の実際のネットワークフェッチ／パーシング詳細はファイル末尾が途中で終わっている（提供コードの抜粋に依存）。完全実装時には SSRF 対策や IP/ホスト検証の追加が期待される。
- 外部依存:
  - DuckDB を前提としている（DuckDBPyConnection 型）。
  - defusedxml を利用。
  - 標準ライブラリの urllib を HTTP クライアントに使用（必要に応じて requests 等への置換検討）。

### Breaking Changes
- 初回リリースのため適用なし。

### Upgrade notes / Migration
- 初期導入時の注意点:
  - 環境変数を .env または .env.local に定義する想定。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings 経由で参照すると ValueError が発生するため事前に設定してください。
  - DuckDB のスキーマ（raw_prices/raw_financials/features/signals/ai_scores/positions/market_calendar 等）が期待どおりであることを確認してください（ON CONFLICT 句は PK/UNIQUE 制約に依存します）。

---

（注）本 CHANGELOG は提示されたソースコードの実装内容・コメントから推測して作成しています。実際のリポジトリの履歴や外部ドキュメントと差異がある場合があります。必要であれば、各モジュールのファイルや実際のコミット履歴を元に追記・修正します。