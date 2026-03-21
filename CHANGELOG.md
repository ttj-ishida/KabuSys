# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して生成した初回リリースの変更履歴です。

## [0.1.0] - 2026-03-21

### 追加
- パッケージ基礎
  - kabusys パッケージ初期版を追加。公開 API として data, strategy, execution, monitoring を __all__ に定義（execution はプレースホルダ）。
  - バージョン番号: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装: export プレフィックス対応、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメント処理を考慮。
  - Settings クラスを導入し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境・ログレベル判定など）をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL）とデフォルト値を提供。

- データ取り込み & 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）と HTTP ステータスハンドリング（408/429/5xx の再試行）。
    - 401 Unauthorized 受信時にリフレッシュトークンを使って ID トークンを自動更新し1回だけ再試行する仕組みを実装（トークンキャッシュをモジュールレベルで保持）。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
  - DuckDB への保存ユーティリティを実装（冪等性を保つため ON CONFLICT DO UPDATE を利用）。
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
    - レコードの型変換ユーティリティ（_to_float, _to_int）を実装し、入力値の堅牢な扱いを保証。
    - fetched_at を UTC ISO フォーマットで保存（Look-ahead バイアスのトレース目的）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集するモジュールを実装。
    - defusedxml を使用して XML の脆弱性攻撃（XML Bomb 等）を防止。
    - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）や HTTP スキーム限定など SSRF / メモリ DoS を意識した対策を導入。
    - バルク INSERT のチャンク処理や INSERT RETURNING を想定した設計により効率的・冪等に raw_news を保存（実装の一部は引き続き補完可能）。

- リサーチ用ファクター計算 (kabusys.research)
  - factor_research モジュールを追加。prices_daily/raw_financials を参照して以下を計算:
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離、窓サイズ未満は None）
    - Volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR 計算で true_range の NULL 伝播を正しく制御）
    - Value: per, roe（target_date 以前の最新財務レコードを使用）
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて取得（1/5/21 日がデフォルト）、SQL で効率的に取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。ties は平均ランクで処理。サンプルが不足（<3）なら None を返す。
    - factor_summary, rank: 基本統計量およびランク付けユーティリティ（外部ライブラリ非依存で実装）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装。
    - research モジュールの calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）適用。
    - 指定カラムを zscore_normalize（kabusys.data.stats から提供）で正規化し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションで実行）して冪等性を確保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装。
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュース（AI）コンポーネントスコアを計算。
      - Z スコアは sigmoid で [0,1] に変換し、欠損コンポーネントは中立 0.5 で補完。
      - デフォルト重みは StrategyModel.md の仕様に準拠（momentum=0.40 等）。ユーザ指定の weights は検証・正規化して適用。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制）。サンプル数不足（<3）の場合は Bear とみなさない。
    - BUY シグナルは閾値を超えた銘柄、SELL シグナルはストップロス（-8%）やスコア低下で生成。
    - SELL を優先して BUY から除外し、signals テーブルへ日付単位で置換保存（トランザクション）。
    - エッジケース処理: 価格欠損時には SELL 判定をスキップするなど安全策を導入。

### 改善
- トランザクションの利用とバルク挿入により DB 操作の原子性と性能を考慮した実装。
- 各モジュールで入力検証や None / 非数値 (NaN/Inf) の扱いを一貫して行うよう実装。

### 既知の制限 / 未実装
- 一部仕様（StrategyModel.md に記載）の機能は未実装または将来の拡張対象:
  - トレーリングストップ（positions テーブルに peak_price 等が必要）や時間決済（保有 60 営業日超）などのエグジット条件は未実装。
  - news_collector の記事 ID 生成・news_symbols との紐付け等の詳細実装はドキュメント化されているが、コードベースの一部は補完可能。
- features 正規化は kabusys.data.stats.zscore_normalize に依存（本稿では定義ファイルを参照していないため、実装が別モジュールにある前提）。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）はこの履歴では定義されていない。実行時にはスキーマ準備が必要。
- news_collector は外部ネットワークアクセスおよび defusedxml に依存。環境により追加設定が必要。

### セキュリティ
- ニュース取り込みで defusedxml を使用し XML の脆弱性対応を実施。
- news_collector で受信サイズ上限や HTTP/HTTPS スキーム制限を採用し SSRF / DoS のリスクを軽減。
- J-Quants クライアントはトークン自動リフレッシュのロジックを持つが、secret は Settings 経由で安全に管理する想定。

### 破壊的変更
- なし（初回リリース）。

---

注: この CHANGELOG は提供されたソースコードからの仕様・挙動を推測して作成したもので、実際のドキュメントやリリースノートと差異がある場合があります。追加のコミットや実装差分があれば、該当バージョンに追記してください。