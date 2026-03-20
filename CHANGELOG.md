CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" と Semantic Versioning に準拠しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - public API: build_features, generate_signals（kabusys.strategy 経由）

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を自動ロード（ルート検出は .git / pyproject.toml を基準）。
  - .env / .env.local の読み込み順序をサポート（.env.local は上書き、OS 環境変数は保護）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パースの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォートあり/なしでの差分処理）
  - Settings クラスで必須キー取得メソッドとバリデーションを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の値チェック
    - データベースパス取得（DUCKDB_PATH, SQLITE_PATH）ユーティリティ

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先処理、408/429/5xx に対する再試行
    - 401 発生時の自動 ID トークンリフレッシュ（1 回のみ再試行）
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB へ冪等保存する save_* 関数:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - データ保存時に fetched_at を UTC ISO 形式で記録
    - 型変換ユーティリティ: _to_float / _to_int（不正値・空値を None に）

- ニュース収集 (kabusys.data.news_collector)
  - RSS 収集パイプライン実装（DataPlatform.md に基づく）
    - デフォルト RSS ソース（例: Yahoo Finance）
    - URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント除去、小文字化）
    - 記事 ID は正規化 URL の SHA-256 ハッシュで生成（先頭 32 文字）
    - defusedxml を用いた XML パースで XML Bomb 等の対策
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を回避
    - SSRF 対策（非 http/https スキーム拒否、ホストチェックなどを想定）
    - DB へのバルク挿入（チャンク化）・トランザクションによる効率化と冪等性（ON CONFLICT DO NOTHING）
    - 挿入件数を正確に返すための INSERT RETURNING を想定した設計（DuckDB の制限に合わせた実装）

- 戦略（feature engineering / signal generation）
  - feature_engineering.build_features:
    - research モジュールから取得した生ファクターをマージ、ユニバースフィルタ（最低株価・平均売買代金）適用
    - 指定日以前の最新株価参照（休場日考慮）
    - 数値ファクターを Z スコア正規化し ±3 でクリップ
    - 日付単位で features テーブルへ冪等 upsert（トランザクション + バルク挿入で原子性）
  - signal_generator.generate_signals:
    - features と ai_scores を統合して最終スコアを計算（momentum/value/volatility/liquidity/news の重み付け）
    - デフォルト重みと閾値を定義（デフォルト threshold=0.60）
    - weights に対する入力検証・補完・再スケーリング処理
    - Sigmoid/Zスコア変換・欠損コンポーネントを中立値 0.5 で補完するポリシー
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数 sufficient）により BUY を抑制
    - BUY/SELL シグナル生成（STOP LOSS / スコア低下によるエグジットを実装）
    - positions / prices_daily を参照し SELL 判定は価格欠損時に慎重にスキップ
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播を制御）
    - calc_value: per, roe（raw_financials の最新財務データと prices_daily の組み合わせ）
    - 計算は DuckDB のウィンドウ関数を多用し、営業日欠損やデータ不足に対して None を返す設計
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（有効レコードが 3 未満なら None）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
    - rank: 同順位は平均ランク（round(..., 12) による ties 対応）
  - research.__init__ で主要関数をエクスポート

- ロギングとエラーハンドリング
  - 各モジュールで logger を使用し、重要な警告・情報を出力
  - DB トランザクションの ROLLBACK 処理失敗時は警告を出力して例外を再送出

Security / Safety
- 外部入力（RSS/XML/HTTP）に対して defusedxml、受信サイズ制限、URL 正規化を導入して攻撃面を低減
- API クライアントでのトークン管理・自動更新の実装により認証エラーに対処

Known limitations / TODO
- signal_generator の一部エグジット条件は未実装（ドキュメントに記載の通り）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の具体的なホスト/IP レベルの SSRF 制約（ipaddress / ソケット検査等）は設計に盛り込まれているが、環境に依存した追加設定が必要な場合がある
- data.stats（zscore_normalize）実装は本リリースで別モジュールとして存在（research で利用） — 実装は既存コードベースで提供
- DuckDB スキーマ（tables）の作成・管理/マイグレーションは本パッケージ外での準備が前提

Authors
- 初回リリース（内部開発）: 開発チーム

ライセンス
- ソースコード内に明記されているライセンスに従ってください（リポジトリに LICENSE ファイルがある想定）。

注記
- この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートはリポジトリの履歴・コミットメッセージに基づき適宜更新してください。