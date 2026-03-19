Keep a Changelog
=================

すべての重要な変更はこのファイルで記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース。モジュール構成:
  - kabusys (トップレベル)
    - data: データ取得・保存ロジック（J-Quants クライアント、ニュース収集）
    - research: ファクター計算・探索ユーティリティ
    - strategy: 特徴量エンジニアリングとシグナル生成
    - execution / monitoring: エントリポイント用ディレクトリ（初期化ファイル含む）
- パッケージ情報:
  - version: 0.1.0（src/kabusys/__init__.py）
  - 公開 API: build_features, generate_signals などを __all__ でエクスポート

Config / 環境設定
- .env 自動ロード機能を追加（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）
- .env パーサを実装（引用符・エスケープ・export プレフィックス・インラインコメント対応）
- Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH, SQLITE_PATH
  - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）
  - ヘルパー: is_live / is_paper / is_dev

Data: J-Quants クライアント
- API クライアントを実装（src/kabusys/data/jquants_client.py）
  - レート制限（120 req/min）を固定間隔スロットリングで制御（_RateLimiter）
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）
  - 401 受信時はリフレッシュトークンを使ったトークン取得を自動実行して 1 回リトライ
  - ID トークンをモジュールキャッシュで共有（ページネーション間の効率化）
  - ページネーション対応で各種取得関数を提供:
    - fetch_daily_quotes(date 範囲 / code 任意)
    - fetch_financial_statements(...)
    - fetch_market_calendar(holiday_division 任意)
  - DuckDB への保存用関数（冪等: ON CONFLICT DO UPDATE を利用）
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 入力変換ユーティリティ: _to_float / _to_int（安全な型変換ルール）

Data: News Collector
- RSS 収集・正規化モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS 取得 → 記事抽出 → テキスト前処理 → raw_news への冪等保存を想定
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 対策）
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）
    - トラッキングパラメータ除去（utm_* 等）
    - URL 正規化（スキーム/ホスト小文字化・フラグメント削除・クエリソート）
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ先頭を使用して冪等性を担保
    - SSRF や不正スキームの検査を想定する実装方針
  - バルク INSERT のチャンク処理と INSERT RETURNING による正確な挿入数取得を想定
  - デフォルト RSS ソース: Yahoo Finance のビジネス RSS を含む

Research: ファクター計算・探索
- ファクター計算モジュール（src/kabusys/research/factor_research.py）
  - calc_momentum(conn, target_date):
    - mom_1m / mom_3m / mom_6m、ma200_dev（MA200 乖離率）を計算
    - 期間やスキャン範囲の定数化（21, 63, 126, MA=200 など）
  - calc_volatility(conn, target_date):
    - atr_20（20日 ATR）、atr_pct（ATR / close）、avg_turnover（20日平均売買代金）、volume_ratio
    - true_range の NULL 伝播やカウント条件を厳密に実装
  - calc_value(conn, target_date):
    - raw_financials の最新レコードを取得して PER（price / EPS）・ROE を算出（EPS が 0/欠損のときは None）
  - 全関数は prices_daily / raw_financials のみ参照し、プロダクションの発注 API へはアクセスしない設計
- 探索ユーティリティ（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターン計算（LEAD ウィンドウで一括取得）
  - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算（有効サンプルが 3 未満なら None）
  - rank(values): 同順位は平均ランクを付与（round(v, 12) による tie 安全化）
  - factor_summary(records, columns): count / mean / std / min / max / median を算出

Strategy: 特徴量生成・シグナル生成
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date):
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して生ファクターを集約
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE → bulk INSERT、トランザクションで原子性確保）
    - ルックアヘッドバイアス防止のため target_date 時点のみ使用する方針
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄の最終スコア final_score を計算
    - コンポーネントスコア:
      - momentum (momentum_20, momentum_60, ma200_dev)
      - value (per → 1/(1 + per/20) の変換)
      - volatility (atr_pct の Z スコアを反転してシグモイド)
      - liquidity (volume_ratio のシグモイド)
      - news (ai_score をシグモイド、未登録は中立)
    - デフォルト重み (_DEFAULT_WEIGHTS) を用意。ユーザ入力 weights は検証・補正（負値や非数は無視、合計で再スケール）
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合、BUY を抑制
    - BUY シグナル生成: threshold を超える銘柄をランク付け（Bear の場合は抑制）
    - SELL シグナル生成（エグジット判定）:
      - stop_loss: 終値 / avg_price - 1 < -8%
      - score_drop: final_score < threshold
      - （未実装メモ: トレーリングストップ、時間決済は将来的に positions に peak_price / entry_date を要求）
    - SELL 優先ポリシー: SELL 対象は BUY リストから除外し、BUY のランクを再付与
    - signals テーブルへ日付単位で置換（DELETE → INSERT、トランザクションで原子性確保）
    - 実行時の注意: features が空の場合は BUY なしで SELL 判定のみ実行

Quality / 非機能的改善
- ロギングを各モジュールに導入し、警告や情報ログを適切に出力
- DuckDB 操作はトランザクションとバルク挿入で原子性とパフォーマンスを意識
- Look-ahead Bias 防止方針: データの fetched_at を UTC で記録し、計算・取得は target_date 時点までのデータのみを使用

Security
- RSS パーサに defusedxml を採用（XML 関連攻撃の緩和）
- ネットワーク取得はサイズ上限やスキーム検証などを想定
- J-Quants クライアントは認証・再試行で失敗時の情報漏洩や無限ループを回避する設計

Notes for users / 移行・利用時の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD
  - ローカル実行時は .env/.env.local をプロジェクトルートに置くと自動読み込みされる
- 自動 .env 読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DuckDB / SQLite のデフォルトパスは Settings.duckdb_path / sqlite_path で指定可能
- 現時点の実装はデータ取得・解析・シグナル生成に重点を置いており、発注処理（execution 層）は別実装を想定

Unreleased
- （今後の予定）
  - execution 層の具体的発注ロジックとモニタリング機能の実装
  - news_collector の完全な挿入ロジック（news_symbols 連携など）と追加のセキュリティチェック
  - トレーリングストップ・時間決済などの SELL 条件の追加実装
  - 単体テストの整備と CI パイプライン統合

References
- ソース参照: src/ 以下のモジュール実装を基に本 CHANGELOG を作成しました。