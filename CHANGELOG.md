# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- 基本パッケージ初期リリースを追加
  - パッケージ version: 0.1.0（src/kabusys/__init__.py）

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数を統合して読み込む自動ロード機能を実装
    - 読み込み順: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定（CWD に依存しない）
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）
  - 読み込み時の上書き制御（override）と保護キーセット（protected）をサポート
  - Settings クラスを提供（settings インスタンス）
    - J-Quants, kabu API, Slack, DB パス (DuckDB/SQLite), システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを提供
    - KABUSYS_ENV/LOG_LEVEL の値検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制限を守る固定間隔スロットリング実装（120 req/min）
  - 冪等・堅牢な HTTP 呼び出しユーティリティ
    - リトライ（指数バックオフ、最大 3 回）と特定ステータス（408/429/5xx）での再試行
    - 401 時はリフレッシュトークンで ID トークンを更新して1回リトライ（トークン自動リフレッシュ）
    - ページネーション対応（pagination_key を用いた取得ループ）
    - JSON デコードエラー等の明確な例外化
  - 高レベル API: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装
  - DuckDB への保存ユーティリティを実装（save_daily_quotes, save_financial_statements, save_market_calendar）
    - 挿入は ON CONFLICT / DO UPDATE により冪等性を確保
    - fetched_at を UTC ISO8601 で記録（Look-ahead bias の追跡）
    - PK 欠損行はスキップして警告出力
    - 型変換ユーティリティ (_to_float / _to_int) を実装

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news へ保存する機能を実装
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）、記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
  - defusedxml を用いた XML パース（XML Bomb 等の防御）
  - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）などの DoS 防御
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で DB 負荷を制御
  - 複数セキュリティ設計方針（トラッキングパラメータ除去、SSRF/スキーム検証や受信サイズ制限の記載）

- リサーチ機能 (src/kabusys/research/*.py)
  - factor_research.py: モメンタム / ボラティリティ / バリュー関連のファクター計算を実装
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均のデータ存在チェック）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（true_range の NULL 伝播を考慮）
    - calc_value: per / roe（raw_financials の最新レコード結合）
  - feature_exploration.py: 将来リターン計算・IC計算・統計サマリーを実装
    - calc_forward_returns: 複数ホライズン（default [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマンのランク相関（ties の平均ランク処理を含む）
    - factor_summary: count/mean/std/min/max/median の集計
    - rank: 同順位は平均ランクとするランク付けユーティリティ
  - research パッケージの __all__ を整備

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装
    - research の calc_momentum / calc_volatility / calc_value から生ファクターを取得
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 にクリップ
    - 日付単位での置換（DELETE → INSERT）をトランザクションで実行し原子性を保証（冪等）

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装
    - features テーブルと ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換・欠損コンポーネントは中立値 0.5 で補完
    - 重みはデフォルト値でフォールバックし、ユーザー指定 weights を検証・正規化（合計が 1.0 になるよう再スケール）
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）により BUY シグナルを抑制
    - エグジット判定（stop_loss=-8% / final_score < threshold 等）による SELL シグナル生成
    - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換をトランザクションで実施（冪等）

### 変更 (Changed)
- パッケージ構成を整理し strategy, data, research, execution, monitoring 等のモジュールを公開（src/kabusys/__init__.py の __all__ を設定）

### 修正 (Fixed)
- 各所でデータ欠損・数値の非有限（NaN/Inf）を考慮する防御的実装を導入
  - zscore / シグモイド / 平均計算 / ファクター結合等で None/非有限値を適切に扱う
  - DuckDB クエリでは NULL 伝播や行不足時の保護（例: cnt_200, cnt_atr 条件）を実装

### セキュリティ (Security)
- news_collector: defusedxml を用いた安全な XML パース、受信サイズ制限、トラッキングパラメータ排除などの対策を導入し、RSS 起因の攻撃リスクを低減
- jquants_client: トークン自動リフレッシュとリトライ処理により認証・通信失敗時の安全な復旧をサポート

---

注:
- 本リリースはコードベースから推測して作成した初期リリースノートです。実運用時のリリースではテスト状況、互換性、既知の制限事項などを追加で明記してください。